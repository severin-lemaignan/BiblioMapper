
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
CACHE_ROOT = Path("./cache")

ARTICLES_ROOT= CACHE_ROOT / "articles"
AUTHORS_ROOT= CACHE_ROOT / "authors"


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

class ArticleDB():

    def __init__(self, articles_root):

        self.articles = {p.parts[-1]: Article(p) for p in articles_root.iterdir() if not p.is_symlink()}

    def __getitem__(self, val):
        return self.articles[val]

    def __contains__(self, val):
        return val in self.articles

    def get_network(self, article_id, authors):

        article = self.articles[article_id]

        links = {}
        for a in article.authors:
            #if a.startswith("id:"): # we know about this author!
            #    links[a[3:]] =  LinkType.AUTHOR
            links[a] =  LinkType.AUTHOR

        return links



class Article():

    def __init__(self, path):

        self.id = path.parts[-1]

        self.path = path
        self.metadata_path = path / "metadata.json"
        self.pdf_path = path / "article.pdf"
        self.has_pdf = self.pdf_path.exists()

        if not self.metadata_path.exists():

            if self.has_pdf:
                print(f"Article meta-data inexistant for {path}! Trying to recreate the article from the PDF...")
                Article.create_from_pdf(self.pdf_path)
            else:
                raise RuntimeError("No PDF or metadata found in %s. You need to fix this article folder." % path)

        with open(path / "metadata.json") as fp:
            metadata = json.load(fp)

        self.metadata = metadata
        self.type = metadata["type"]
        self.title = metadata["title"]
        self.year = metadata["year"]
        self.container = metadata["container-title"]
        self.authors = metadata["authors"]
        self.keywords = metadata.get("keywords",[])

        self.doi = metadata.get("doi", None)

        # TODO: make that async!
        self.generate_thumbnail()

    def __str__(self):
        return "{title}, by {authors}".format(title=self.title,
                                              authors = ", ".join(self.authors))

    def __repr__(self):
        return self.id

    @staticmethod
    def crossref(title, first_author, save_as=None):
        print("Querying crossref about %s by %s et al..." % (title, first_author))
        response = requests.get(CROSSREF_URL.format(title=title, author = first_author),
                                headers=CROSSREF_HEADERS)
        res = response.json()["message"]["items"]

        if not res:
            return None

        metadata = {
            "title": res[0]["title"][0],
            "URL": res[0]["URL"],
            "DOI": res[0]["DOI"],
            "authors": [a["family"] for a in res[0]["author"]],
            "year": res[0]["created"]["date-parts"][0][0],
            "container-title": res[0]["container-title"][0],
            "type": res[0]["type"]
        }
        #TODO: use ORCID when available; use nested references if possible

        if save_as is not None:
            with open(save_as, "w") as fp:
                json.dump(metadata, fp)

        return metadata

    @staticmethod
    def create_from_pdf(tmp_path):
        sha = sha256sum(tmp_path)

        if not (ARTICLES_ROOT/sha).exists():
            (ARTICLES_ROOT / sha).mkdir()
            pdf_file_name = ARTICLES_ROOT / sha / "article.pdf"
            os.rename(tmp_path, pdf_file_name)

        if not (ARTICLES_ROOT / sha / "metadata.json").exists():

            rawmetadata = extract_metadata(ARTICLES_ROOT/sha / "article.pdf")

            metadata = Article.crossref(rawmetadata["title"],
                                   rawmetadata["authors"][0]["name"],
                                   save_as=ARTICLES_ROOT/sha/"metadata.json")

            if not metadata:
                raise KeyError("No Crossref DOI found for this paper! Maybe the title was incorrectly parsed. Try to input the title or DOI directly.")

        else:
            print("Article already known! Loading existing metadata")
            with open(ARTICLES_ROOT / sha / "metadata.json") as fp:
                metadata = json.load(fp)


        new_path = ARTICLES_ROOT / metadata["DOI"].replace("/","_")

        ## We have a DOI -> rename the paper's directory, and link the SHA folder to the new directory
        if not new_path.exists():
            os.rename(ARTICLES_ROOT / sha, new_path)
            os.symlink(new_path.resolve(), (ARTICLES_ROOT / sha).resolve())

        return Article(new_path)

    def get_article_path(self, pdf_file_path):
        """Return the path where the article's details are cached.
        If the path does not exist yet, create it as well.
        """

        sha = sha256sum(pdf_file_path)
        article_path = ARTICLES_ROOT / sha
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
                    references.append(res)
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

    def generate_thumbnail(self):
        """Generates a thumbnail of the PDF file (if required and PDF available),
        and sets self.thumbnail_path to the corresponding path.

        Sets self.thumbnail_path to None if no thumbnail available.
        """

        thumbnail_path = path / "thumbnail.jpg"

        if not thumbnail_path.exists():

            if self.has_pdf:
                cmd_line = f"convert -thumbnail 200x200 -density 300 -background white -alpha remove {file_path}[0] {thumbnail}"
                subprocess.run(cmd_line,shell=True)
                self.thumbnail_path = thumbnail_path
            else:
                self.thumbnail_path = None
        else:
            self.thumbnail_path = thumbnail_path



