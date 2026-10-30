# Source audit and editorial decisions

Baseline: `52c19c3723934669395d4838b3f417a09262f6c7` on main. Inspected repository inventory, source structure, parsing, major topic groups and representative technical passages. This is not a claim that every legacy technical statement has been independently verified.

The curated reference edition is a focused new publication. It is not a lossless conversion of the original drafts. All original chapter files remain unchanged under `chapters/` for comparison; the publication manifest includes only reviewed new content.

## Source inventory

| Source | Bytes | SHA-256 | Parse status |
|---|---:|---|---|
| 2.4-detection-engineering.yaml | 89757 | `fdfd31b1fe1a3b31db039a1d57a78fefbae2554f4538125f7a564e3ded845f0c` | Invalid at line 51: expected <block end>, but found '<block mapping start>' |
| 3.1-identity-and-access-management.yaml | 111089 | `5a7bd85e55778caf2e70de8144c15f6236fdca5f0747b42dc4ce9173c01a7e61` | Invalid at line 1775: expected <block end>, but found '?' |
| 4.1-security-automation.yaml | 92564 | `aa9487b153a71aabb1c25303f3705ad83c4ec457c03fe2aed2abe99e178bd34e` | Invalid at line 967: expected <block end>, but found '<block mapping start>' |
| 4.3-incident-response.yaml | 107185 | `788de4f9390eedb0515022faac188f46debdef09d0d09ae941aa314f9fd5d21c` | Invalid at line 1214: expected <block end>, but found '<block mapping start>' |
| 4.4-threat-intelligence.yaml | 145042 | `2b7461561b6430965da7d6ce4b2fbc617c085980e408f866b5364398b2384d22` | Invalid at line 50: expected <block end>, but found '<block mapping start>' |

## Substantive corrections

- Replaced alert-quality targets described as true positive rate with explicit precision, recall and false-positive-rate definitions. No synthetic effectiveness claims.
- Removed unsupported vendor costs, fixed deployment calendars and arbitrary universal performance targets from the curated edition.
- Replaced unverified enterprise incident anecdotes with one named synthetic scenario and reproducible evidence.
- Updated the incident-response orientation to NIST SP 800-61 Revision 3, superseding Revision 2.
- Updated TLP:WHITE to the current TLP:CLEAR vocabulary and explained the limited TLP policy in the public example.
- Distinguished session revocation from reversible rollback, indicator confidence from incident priority, and object reads from proven external exfiltration.
- Explicitly separated framework descriptions, author recommendations, synthetic inputs, implemented functions and production gaps.

## Topic disposition

| Original theme | Curated treatment |
|---|---|
| Detection principles, SIEM architecture, normalization, rule testing, noise and coverage | Detection chapter; runnable rule, boundary tests and architectural trade-offs |
| IAM principles, authorization models, federation, service accounts and lifecycle | Context chapter; operating procedure and synthetic identity/resource contract |
| Intelligence lifecycle, collection, analysis, sharing and outcome measurement | Intelligence chapter; provenance/validity contract, FIRST reference and case correlation |
| Response roles, preparation, investigation, containment, communication, exercises and learning | Response chapter and investigation record; synthetic approval and recovery semantics |
| Automation opportunity selection, orchestration, playbooks, code review, failure handling and measurement | Automation chapter and response simulator |
| Vendor pricing tables, fixed annual roadmaps, advanced ML, deception, named-actor attribution and regulatory deadlines | Kept in original drafts only; unverified and outside this bounded edition |

## Legacy principle identifiers

Identifiers are retained below as migration references. They are not silently presented as conforming YAML block IDs; the original uppercase IDs do not match the new standard's anchor syntax. New document/block anchors are explicit in the curated files.

### 2.4-detection-engineering.yaml

- `DE-P001`: Signal over noise
- `DE-P002`: Assume breach
- `DE-P003`: Coverage over complexity
- `DE-P004`: Detection as code
- `DE-P005`: Context drives priority
### 3.1-identity-and-access-management.yaml

- `IAM-P001`: Identity is the perimeter
- `IAM-P002`: Least privilege by default
- `IAM-P003`: Zero trust, always verify
- `IAM-P004`: Automate identity lifecycle
- `IAM-P005`: Ephemeral over persistent
- `IAM-P006`: Visibility enables security
### 4.1-security-automation.yaml

- `AUTO-P001`: Automate toil, amplify analysts
- `AUTO-P002`: Code over clicks
- `AUTO-P003`: Idempotent and reversible
- `AUTO-P004`: Fail safe, not fail deadly
- `AUTO-P005`: Measure everything
- `AUTO-P006`: Security as code
### 4.3-incident-response.yaml

- `IR-P001`: Preparation prevents panic
- `IR-P002`: Speed over perfection in containment
- `IR-P003`: Evidence preservation enables prosecution
- `IR-P004`: Communication clarity prevents chaos
- `IR-P005`: Learn from every incident
- `IR-P006`: Practice makes perfect
### 4.4-threat-intelligence.yaml

- `TI-P001`: Intelligence is not data - it's analyzed information that enables decisions
- `TI-P002`: Context over volume
- `TI-P003`: Timely and actionable trumps perfect and late
- `TI-P004`: Intelligence must drive action
- `TI-P005`: Share to receive - intelligence value compounds through collaboration
- `TI-P006`: Measure intelligence effectiveness by decisions made, not IOCs collected

## Scope and review gate

The five-chapter publication and one offline scenario are a complete bounded review candidate. Full migration of every legacy topic is not claimed. Review the PR before calling it a public v1.0 release. The standard is bundled without modification from the attached 1.1.0 file. Publication validation applies to `book/`, not legacy drafts or operational JSON fixtures.

Primary references checked on 2026-10-31:

- [NIST SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final)
- [NIST SP 800-61 Revision 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final)
- [FIRST TLP](https://www.first.org/tlp/)
