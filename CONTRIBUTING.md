# Contributing

Changes should connect a concrete operating decision to evidence and a testable procedure.

1. Use `book/manifest.yaml` for publication order. Author publication content in explicit body blocks under the bundled YAML Markup Standard 1.1.0.
2. Keep prose folded (`>`) and code literal (`|`). Use explicit reader-facing labels, stable document/block IDs and resolvable cross-references.
3. Keep executable code in native files. Use synthetic telemetry only in public fixtures. Label illustrative thresholds and scenarios.
4. Run `python -m unittest discover -s tests -v`, `python tools/publication.py --pdf` and `python -m lab --simulate-approved`.
5. Review the generated PDF visually when publication content changes. Check the build report and preserve the original source drafts for editorial comparison.
6. Describe evidence and limitations in the PR. Never imply production effectiveness from synthetic tests.

The publisher handles the explicit block subset this manual uses. Add validation, rendering support and meaningful tests before introducing a different block type. It is not a general implementation of every target in the standard.

Before adding a real response adapter, design an authenticated approval boundary, durable transactional state, scoped credentials, provider verification and a controlled test environment. The existing local approval and ledger are simulation inputs.
