Paper:
- doi:
- id: MANDATORY IF DOI NOT PRESENT, SHOULD NOT BE PRESENT IF DOI PRESENT. DOI
  always prefered. id in form 'surname2010firstword'
- title
- authors: list of [id:[<ORCID>|<id>]|canonical name]
  - if orcid: or sha256: corresponding entry MUST exist in authors.db.json
  - orcid always prefered
- year
- journal/conference
- thumbnail
- URL
- link to pdf
- sha256 pdf
- keywords


Author:
- orcid (optional)
- if no orcid, id in the form lemaignan_s (all lower case)
- canonical (eg 'Lemaignan, S.')
- URL
- photo
- name
- firstname

sha256 computed from canonical name:
eg: echo "Lemaignan, S." | sha256sum
