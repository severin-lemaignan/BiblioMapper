import json
from pathlib import Path

ROOT = Path(".")

def sha256sum(filename):
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


with open("articles.db.json") as fp:

    papers = json.load(fp)

for p in papers:

    if "doi" in p:
        
        id = p["doi"].replace("/","_")
    else:
        id = p["id"]

    (ROOT / "test" / "articles" / id).mkdir(parents=True, exist_ok=True)

    with (ROOT / "test" / "articles" / id / "metadata.json").open("w") as f:
        json.dump(p, f)
        
with open("authors.db.json") as fp:

    authors = json.load(fp)

for a in authors:

    if "orcid" in a:
        
        id = a["orcid"]
    else:
        id = a["name"].lower() + "_" + a["firstname"][0].lower()

    (ROOT / "test" / "authors" / id).mkdir(parents=True, exist_ok=True)

    with (ROOT / "test" / "authors" / id / "metadata.json").open("w") as f:
        json.dump(a, f)
