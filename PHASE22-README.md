# Phase 22 — Offline quality gap reconciliation

This is a **read-only** diagnosis patch, not a new scraper or a proof of completeness.

Install in project root:

```sh
unzip -o ~/Downloads/monst-catalog-phase22-quality-gaps-patch.zip
python3 -m unittest discover -s scripts -p 'test_catalog_phase22.py'
python3 -m unittest discover -s scripts -p 'test_catalog_*.py'
python3 scripts/catalog_phase22.py public/catalog --state catalog-update-state.json --output local-reports/phase22
```

If an earlier Phase 19 summary exists, optionally add `--baseline local-reports/phase19/summary.json`.

Output:
- `summary.json`: totals and missing fields by verified/unverified family
- `form-quality.csv`: form ID, source family, missing fields and count
- `family-quality.csv`: previously parsed status, number of recorded forms, missing verified form IDs

WARNING: A previously parsed family is not proven complete. Missing fields can be legitimate for some forms, so output is **review evidence**, not an automatic quality gate or deletion instruction. It makes no network requests and never edits `public/catalog`, state or Firestore.

Commit only code/report documentation:
```sh
git add scripts/catalog_phase22.py scripts/test_catalog_phase22.py PHASE22-README.md
git commit -m "test: audit verified family detail gaps"
```

Do not commit local report files. If Git rebase is blocked by generated `catalog-coverage.json`, use the previously installed sync guard after reviewing its backup report. Do not blindly discard other changes.
