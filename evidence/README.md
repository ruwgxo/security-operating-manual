# Reproducible exercise evidence

All records are synthetic. These outputs are examples of the workflow, not production measurements.

Reproduce from the repository root:

```sh
python -m lab --simulate-approved --output build/evidence-review
python -m lab --simulate-approved --output build/evidence-review
python -m unittest discover -s tests -v
```

The first run simulates one action. The second reports `already simulated`. `run-manifest.json` here captures the second run; its report digest covers the same deterministic finding.

| Output | What to inspect |
|---|---|
| [report.json](report.json) | One case, evidence `auth-suspect`, `read-01`, `read-02`; 110,000,000 restricted bytes; one malformed-event quarantine; one duplicate |
| [run-manifest.json](run-manifest.json) | Scenario/policy/report digests and replay outcome |
| [response-state.json](response-state.json) | One local simulated action and explicit recovery semantics |

Twenty-nine tests currently cover positive and benign behavior, temporal/volume boundaries, intelligence expiry and provenance, malformed/unknown input, source gaps, changed context, approval safeguards and publication validation. Run the suite to obtain current results. This small fixture does not estimate real-world precision, recall or performance.

The local JSON ledger has no concurrent-writer protection and is not tamper-resistant. An approval reviewer string is not authentication. A report digest is not a forensic chain of custody.
