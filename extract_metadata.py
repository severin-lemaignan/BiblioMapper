import logging
from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X] ", handlers=[RichHandler()]
)

log = logging.getLogger("rich")

from rich.traceback import install
install()

import sys
import subprocess

import PyPDF2

import xml.etree.ElementTree as ET


def extract_metadata(article_path):

    # Are the title + authors set in the metadata?
    # if so, it is quick and easy
    pdfReader = PyPDF2.PdfFileReader(str(article_path))
    a = pdfReader.documentInfo["/Author"]
    t = pdfReader.documentInfo["/Title"]
    if a and t:
        return {"title": t, "authors": a}

    # otherwise, we need to mine the PDF with CERMINeR:

    article_dir = article_path.parent
    jats_filepath = article_dir / ("article.cermxml")

    if not jats_filepath.exists():
        log.info("Running CERMINeR to extract PDF metadata...")
        cmd_line = f"java -cp cermine-impl-1.13-jar-with-dependencies.jar pl.edu.icm.cermine.ContentExtractor -path {article_dir}"
        try:
            result = subprocess.run(cmd_line,shell=True, capture_output=True, check=True)
            if "Invalid PDF file" in result.stderr.decode():
                raise RuntimeError("The submitted PDF is invalid. Could not extract the metadata. Try to provide directly the name/DOI of the article") 
        except subprocess.CalledProcessError as cpe:
            log.error(cpe.stderr)
            raise cpe

        


    return parse_jats(jats_filepath)



def parse_jats(filepath):

    DEMANGLE = {" e´":"é",
                "o ̈ ": "ö"
            }
    def demangle(string):
        for k,v in DEMANGLE.items():
            string = string.replace(k,v)

        return string


    root = ET.parse(filepath).getroot()

    title = demangle(root.find('.//article-title').text)

    authors = []

    for author in root.findall(".//*[@contrib-type='author']"):
        name = demangle(author.find("string-name").text)
        email_tag = author.find("email")
        if email_tag is not None:
            email = demangle(email_tag.text)
        else:
            email = ""

        affs = []
        for aff in author.findall("*[@ref-type='aff']"):
            affs.append(demangle(
                root.find(".//aff[@id='%s']/institution" % aff.attrib["rid"]).text))

        #print(name)
        #if email:
        #    print("\t" + email)
        #if affs:
        #    print("\t" + ", ".join(affs))

        authors.append({"name": name,
                        "email": email,
                        "affiliations": affs
                        })

    log.info("Found title <%s> by <%s>" % (title, ", ".join([a["name"] for a in authors])))

    return {"title": title,
            "authors": authors
            }


