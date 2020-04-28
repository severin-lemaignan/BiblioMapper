import sys
import subprocess

import xml.etree.ElementTree as ET


def extract_metadata(article_dir):

    jats_filepath = article_dir / ("article.cermxml")

    if not jats_filepath.exists():
        print("Running CERMINeR to extract PDF metadata...")
        cmd_line = f"java -cp cermine-impl-1.13-jar-with-dependencies.jar pl.edu.icm.cermine.ContentExtractor -path {article_dir}"
        try:
            result = subprocess.run(cmd_line,shell=True, capture_output=True, check=True)
            if "Invalid PDF file" in result.stderr.decode():
                raise RuntimeError("The submitted PDF is invalid. Could not extract the metadata. Try to provide directly the name/DOI of the article") 
        except subprocess.CalledProcessError as cpe:
            print(cpe.stderr)
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

    print("Found title <%s> by <%s>" % (title, ", ".join([a["name"] for a in authors])))

    return {"title": title,
            "authors": authors
            }


