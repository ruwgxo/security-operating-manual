# Security Operating Manual
 
Enterprise security architecture built from work in the field since 2012.
 
Five available chapters covering detection engineering, threat intelligence, IAM, automation, and incident response.
 
No theory. Just what works at scale.
 
---
 
## Chapters
 
**Detection & Response:**
- [1. Detection Engineering](book/chapter_01_index.yaml) — Alert management, SIEM strategies, detection maturity
- [5. Threat Intelligence](book/chapter_05_index.yaml) — Intel programs, enrichment, operationalization
- [4. Incident Response](book/chapter_04_index.yaml) — War rooms, playbooks, post-mortems
**Infrastructure & Access:**
- [2. IAM at Scale](book/chapter_02_index.yaml) — RBAC, least privilege, access governance
- [3. Security Automation](book/chapter_03_index.yaml) — Orchestration, auto-remediation, tooling
---
 
## Built From
 
- Enterprise detection platforms at fleet scale
- Multi-cloud security architecture (AWS, Azure, GCP, IBM Cloud)
- Zero Trust implementations at scale
- eMasters in Cyber Security (IIT Kanpur)
---
 
## Format
 
All chapters in YAML for structured knowledge management. The book lives in `book/`: a book index
(`security_operating_manual_book_index.yaml`), one index per chapter (`chapter_NN_index.yaml`) and one
file per section (`section_NN_MM_<topic>.yaml`). Chapters are numbered 1-5 in reading order; each
chapter index records its original manual number (2.4, 3.1, 4.1, 4.3, 4.4) as `source_chapter`.
 
Each includes maturity models, 0-to-60 implementation roadmaps, real-world architectures, and cross-references between chapters.
 
---
 
## License
 
MIT — use freely, adapt as needed, build better security programs.
 
---
 
**Author:** Raghav Dinesh | [github.com/ruwgxo](https://github.com/ruwgxo) | [ruwgxo.com](https://ruwgxo.com) | Working in security since 2012
