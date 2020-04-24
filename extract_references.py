
import hashlib
from pathlib import Path
import subprocess
import os.path



import requests
import json
import time

CROSSREF_URL = "https://api.crossref.org/works?query.bibliographic={title}&query.author={author}&rows=1"
CROSSREF_HEADERS = {
        'User-Agent': 'OntoBiblio 0.1 (mailto:severin@guakamole.org)'
}
CACHE_PATH="cache"

def sha256sum(filename):
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()



def get_references(pdf_file_path):

    sha = sha256sum(pdf_file_path)
    Path(CACHE_PATH).mkdir(exist_ok=True)

    # raw_references contains the references as extracted
    # from the PDF by anystyle. They might be incorrect/noisy
    raw_references_path = os.path.join(CACHE_PATH,f"{sha}.raw.refs.json")

    # references contains the reference list post-processed
    # through crossref (eg, including DOI). Some references
    # might be missing.
    references_path = os.path.join(CACHE_PATH,f"{sha}.refs.json")

    # no reference extracted yet? 
    # run anystyle (and cache the result)
    if not os.path.isfile(raw_references_path):
        print("Parsing the PDF for citations...")
        cmd_line = f"anystyle -f json find --no-layout {pdf_file_path} > {raw_references_path}"
        subprocess.run(cmd_line,shell=True)

    # raw references not post-processed yet?
    # try to get fully details through cross-ref, and
    # cache the result
    if not os.path.isfile(references_path):

        print("Fetching (and caching) DOIs... this may take a little while...")

        with open(raw_references_path) as raw_refs_fp:
            rawrefs = json.load(raw_refs_fp)

        references = []

        for idx, ref in enumerate(rawrefs):
            print("Processing citation %d/%d..." % (idx + 1, len(rawrefs)))
            response = requests.get(CROSSREF_URL.format(title=ref["title"][0], author = ref["author"][0]["family"]),
                                    headers=CROSSREF_HEADERS)
            res = response.json()["message"]["items"]
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
        with open(references_path,'w') as refs_fp:
            json.dump(references, refs_fp)
        return references

    else:
        with open(references_path) as refs_fp:
            return json.load(refs_fp)


