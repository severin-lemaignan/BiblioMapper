
import hashlib
from pathlib import Path
import subprocess
import os

import requests
import json
import time

from extract_metadata import extract_metadata

CROSSREF_URL = "https://api.crossref.org/works?query.bibliographic={title}&query.author={author}&rows=1"
CROSSREF_HEADERS = {
        'User-Agent': 'OntoBiblio 0.1 (mailto:severin@guakamole.org)'
}
CACHE_PATH= Path("./cache")

from enum import Enum
class LinkType(str,Enum):
    CITED_BY = "cited-by"
    AUTHOR = "author"
    IS_ABOUT = "is-about"
    SUBCLASS_OF = "subclass-of"

def sha256sum(filename):
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()

def get_article_network(article, articles, authors):

    links = {}
    for a in article.authors:
        if a.startswith("id:"): # we know about this author!
            links[a[3:]] =  LinkType.AUTHOR

    return links



class Author():

    def __init__(self, path):

        self.id = path.parts[-1]

        with open(path / "metadata.json") as fp:
            metadata = json.load(fp)

        self.metadata = metadata
        self.name = metadata["name"]
        self.firstname = metadata["firstname"]
        self.canonical = metadata["canonical"]

        self.orcid = metadata.get("orcid", None)


class Article():

    def __init__(self, path):

        self.id = path.parts[-1]

        with open(path / "metadata.json") as fp:
            metadata = json.load(fp)

        self.metadata = metadata
        self.title = metadata["title"]
        self.year = metadata["year"]
        self.venue = metadata["venue"]
        self.authors = metadata["authors"]
        self.keywords = metadata["keywords"]

        self.doi = metadata.get("doi", None)


    @staticmethod
    def crossref(title, first_author):
        print("Querying crossref about %s by %s et al..." % (title, first_author))
        response = requests.get(CROSSREF_URL.format(title=title, author = first_author),
                                headers=CROSSREF_HEADERS)
        res = response.json()["message"]["items"]
        return res

    @staticmethod
    def create_from_pdf(tmp_path):
        sha = sha256sum(tmp_path)
        (CACHE_PATH / sha).mkdir(exist_ok=True)
        pdf_file_name = CACHE_PATH / sha / (sha + ".pdf")
        os.rename(tmp_path, pdf_file_name)

        metadata = extract_metadata(CACHE_PATH/sha)

        res = Article.crossref(metadata["title"],
                               metadata["authors"][0]["name"])

        for ref in res:
            print(ref)

    def get_article_path(self, pdf_file_path):
        """Return the path where the article's details are cached.
        If the path does not exist yet, create it as well.
        """

        sha = sha256sum(pdf_file_path)
        article_path = CACHE_PATH / sha
        article_path.mkdir(parents=True, exist_ok=True)

        return article_path


    def get_references(self, pdf_file_path):

        article_path = self.get_article_path(pdf_file_path)

        # raw_references contains the references as extracted
        # from the PDF by anystyle. They might be incorrect/noisy
        raw_references_path = article_path / "raw.refs.json"

        # references contains the reference list post-processed
        # through crossref (eg, including DOI). Some references
        # might be missing.
        references_path = article_path / "refs.json"

        # no reference extracted yet? 
        # run anystyle (and cache the result)
        if not raw_references_path.exists():
            print("Parsing the PDF for citations...")
            cmd_line = f"anystyle -f json find --no-layout {pdf_file_path} > {raw_references_path}"
            subprocess.run(cmd_line,shell=True)

        # raw references not post-processed yet?
        # try to get fully details through cross-ref, and
        # cache the result
        if not references_path.exists():

            print("Fetching (and caching) DOIs... this may take a little while...")

            with raw_references_path.open() as raw_refs_fp:
                rawrefs = json.load(raw_refs_fp)

            references = []

            for idx, ref in enumerate(rawrefs):
                print("Processing citation %d/%d..." % (idx + 1, len(rawrefs)))
                res = Article.crossref(ref["title"][0], ref["author"][0]["family"])
                if res:
                    references.append(
                            {
                                "title": res[0]["title"][0],
                                "URL": res[0]["URL"],
                                "DOI": res[0]["DOI"],
                                "author": [a["family"] for a in res[0]["author"]],
                                "year": res[0]["created"]["date-parts"][0][0],
                            })
                            #TODO: use ORCID when available; use nested references if possible
                else:
                    print('Could not automatically retrieve reference {idx}'
                        ': "{title}" by {author} et al.: no DOI? wrong '
                        'reference parsing?'.format(idx=idx,
                                                    title=ref["title"][0], 
                                                    author = ref["author"][0]["family"]))
    #
    #                print('Reference {idx}: "{title}" by {author} et al.: found matching DOI.'.format(idx=idx,
    #                                                                                                title=ref["title"][0], 
    #                                                                                                author = ref["author"][0]["family"]))
    #                print("DOI: %s (%s)" % (res[0]["DOI"], res[0]["URL"]))
    #                print("%s by %s et al." % (res[0]["title"][0], res[0]["author"][0]["family"]))
    #            else:
    #                print('Reference {idx}: "{title}" by {author} et al.: NO DOI FOUND.'.format(idx=idx,
    #                                                                                            title=ref["title"][0], 
    #                                                                                            author = ref["author"][0]["family"]))
    #
                time.sleep(0.1)

            print("Successfully fetched DOI for %d out of %d citations" % (len(references), len(rawrefs)))
            with references_path.open('w') as refs_fp:
                json.dump(references, refs_fp)
            return references

        else:
            with references_path.open() as refs_fp:
                return json.load(refs_fp)


