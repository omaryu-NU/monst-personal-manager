# Phase 7 — Prefer unvisited listing pages

## What this patch changes
- Selects never-visited listing pages before previously visited pages.
- Preserves the page-1 refresh behavior and current limit of `--pages` requests per run.
- Advances `nextPage` using the last planned page, accounting for wraparound.
- Preserves existing profile crawler, JSON output schema, retry/backoff rules and Firebase data.
- Does **not** raise request frequency or circumvent HTTP 429 / robots.txt restrictions.

## Evidence and expected progress
At the uploaded snapshot, 25/50 listing pages were visited. The next cursor is 46.
With `--pages 5`, next planned pages are `1,46,47,48,49`; assuming all succeed, after that `1,50,2,3,4`.
Observed success is subject to robots and HTTP errors. The file is not a claim that those pages have been fetched.

## Installation (from the root of your repo)
1. Back up current changes and run `git status`; do not overwrite uncommitted script edits.
2. Unzip the patch in the project root. Only these files are needed:
   - `scripts/technophere_catalog.py`
   - `scripts/test_catalog_phase7.py`
   - `scripts/fixtures_phase7/catalog-update-state.json` (test-only frozen sample)
   - `PHASE7-README.md`
3. Install requirements and run:
   `python3 -m pip install -r scripts/requirements-catalog.txt`
   `python3 -m unittest discover -s scripts -p 'test_catalog_*.py'`
4. Inspect the source diff:
   `git diff -- scripts/technophere_catalog.py`
5. Commit ONLY the patch paths above. Do not overwrite/update your current `catalog-update-state.json` or `/public/catalog` with this ZIP.
6. Set `AUTO_DEPLOY_HOSTING=false`, push to GitHub, run the workflow manually, inspect `catalog-coverage.json` and any integrity report. Once checked, re-enable if safe.

## Scope of completion
Listing-page coverage can reach 50/50, but that does not prove all forms are present, image URLs resolve, or abilities/stats are complete. Individual-family verification must be assessed independently.
