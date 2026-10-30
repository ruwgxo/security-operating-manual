# Security Operating Manual

**A security operating model you can read, run and inspect.**

Five chapters connect identity, threat intelligence, detection engineering, investigation and automation. A reproducible offline scenario follows one suspicious session from telemetry to an evidence-linked case and an approved response simulation.

**[Read the PDF](docs/security-operating-manual.pdf)** · **[Download the readable HTML](docs/manual.html)** · **[Inspect example evidence](evidence/README.md)** · **[Explore the architecture](docs/architecture.md)**

![Reference security workflow](docs/architecture.svg)

## Run the reference workflow

Python 3.11 or newer. The lab uses only the Python standard library; no cloud account or API key is required.

```sh
git clone https://github.com/ruwgxo/security-operating-manual.git
cd security-operating-manual
git checkout codex/security-operating-system-v1
python -m lab --simulate-approved
python -m lab --simulate-approved
```

The first run produces one case and one simulated action. The second reports `already simulated`. Output is in `build/lab/`. The branch checkout is required while this edition is under review; use main after the PR is merged.

### What the example demonstrates

- Correlates an unusual-device authentication with valid intelligence and same-session restricted-object reads.
- Keeps identity/asset context, indicator provenance, event evidence and rule version with the case.
- Deduplicates repeated events, quarantines malformed/conflicting inputs and reports missing source kinds.
- Checks approval binding and expiry, protected identities, a kill switch and replay handling before recording a simulated response.
- Includes benign and unrelated activity so the finding can be inspected against controls.

The supplied fixture yields **110,000,000 bytes of restricted reads in one suspicious session**, one duplicate and one malformed-event quarantine. These are synthetic exercise results, not production measurements or proof of exfiltration.

## Read the manual

| Chapter | Focus | YAML source |
|---|---|---|
| 1. Security Context and Identity | Ownership, access, lifecycle and telemetry contracts | [Source](book/chapters/context-and-identity.yaml) |
| 2. Threat Intelligence and Prioritization | Requirements, provenance, validity and sharing | [Source](book/chapters/intelligence.yaml) |
| 3. Detection Engineering | Hypotheses, normalization, tests, metrics and tuning | [Source](book/chapters/detection.yaml) |
| 4. Investigation and Response | Evidence, authority, containment and recovery | [Source](book/chapters/response.yaml) |
| 5. Automation and Continuous Improvement | Approval boundaries, state, failure handling and review | [Source](book/chapters/automation.yaml) |

The [manifest](book/manifest.yaml) defines reading order. Publication content follows the bundled [YAML Markup Standard 1.1.0](standards/yaml-markup-standard.yaml), using explicit blocks and reader-facing labels. Metadata is kept out of the readable editions.

## Verify and rebuild

The workflow tests require only Python. Publication tests and builds need the dependencies below.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python tools/publication.py
python tools/publication.py --pdf
```

PDF output requires DejaVu Sans, DejaVu Sans Bold and DejaVu Sans Mono. On Ubuntu, install `fonts-dejavu-core`. On other systems, set `SOM_FONT_DIR` to a directory containing `DejaVuSans.ttf`, `DejaVuSans-Bold.ttf` and `DejaVuSansMono.ttf`. HTML builds do not need those fonts.

The publisher validates the bundled JSON Schema plus scalar styles, explicit body keys, IDs, references, table widths and manifest membership. It implements the block subset this manual uses; it is not a universal converter for every standard target. Output is in `docs/`, including a build report. The CI workflow runs tests, rebuilds the publication and checks the example replay.

## Scope and implementation boundaries

This is a **review candidate** for a complete five-chapter reference edition and one scenario. All identities, telemetry, indicators and approvals are synthetic. Response modifies local simulation state only.

The local approval reviewer label is not authentication, and the JSON action ledger is single-process and editable. Streaming ingestion, authenticated collectors, independent approvals, tamper-resistant evidence and real containment adapters are production extensions. See the [architecture and limits](docs/architecture.md) and [publication appendix](book/back/reference.yaml).

## Editorial provenance

The [source audit](editorial/source-audit.md) explains corrections and scope decisions. The five [original chapter drafts](chapters/) remain unchanged for comparison. They contain invalid YAML and unverified historical material and are excluded from the curated publication. This edition is a focused rewrite rather than a lossless conversion of those drafts.

## Author and license

Raghav Dinesh · [ruwgxo.com](https://ruwgxo.com) · [LinkedIn](https://linkedin.com/in/ruwgxo) · Working in software and security since 2012.

[MIT](LICENSE). The bundled YAML Markup Standard is authored by Raghav Dinesh; the repository license is retained.
