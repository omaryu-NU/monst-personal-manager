# Monst Personal Manager — Phase 2 (family forms)

## What changed
- `scripts/technophere_catalog.py`: parses the explicit `形態ごとのステータスとアビリティ` section of each profile, adding **each confirmed No.** as an independent character record. The profile's representative form is no longer the sole candidate.
- Adds Lv極 HP/attack/speed, separately labelled abilities/gauge/connect, SS/friendship, icon image URLs, form/rarity/trait metadata **only where visibly present**.
- Maintains `verifiedFamilyURLs` in `catalog-update-state.json` to avoid repeatedly fetching the same parsed page.
- Report `familiesDiscovered`, `familiesVerified`, `familiesRemaining`, `formsExtractedThisRun` in coverage. 'Verified' here means the parser found at least one form, **not** that the page's forms were exhaustively cross-checked.
- Existing IDs/names/images/details preserved; new form IDs added. No Firebase user data is written.
- The Workflow runs both Phase 1 quality tests and Phase 2 family tests; limits individual family requests to 5 and delays 2.5 seconds between requests.

## IMPORTANT limitations
- The 50-page scan is not yet verified on the actual deployed repository. Inspect `catalog-coverage.json` after Actions run.
- Profile extraction tested using **representative offline HTML fixtures**, not a complete live HTML snapshot. Selectors may need adjustment after real Actions logs.
- Technophere publicly groups 3,929 character *families* into 50 listing pages. GameWith's 4,433 records and Technophere 3,929 families are **not equivalent units**. 1,999 local records are an incomplete subset.
- Images are URLs found in source HTML, **not validated HTTP 200**; licensing/permission must cover reuse. Existing user authorization was previously indicated.
- Reaching all 50 listing pages does not prove all forms and details are present. Do not mark complete until audit passes against independently confirmed expected IDs.
- This patch DOES NOT modify `.env`, Firestore collections, Firebase Hosting configuration, or existing personal data.

## Installation (Mac, root of existing project)
1. Before applying, commit or stash your local changes; download a backup.
2. Unzip archive in project root, preserving `.github/workflows/` and `scripts/` relative paths.
3. `python3 -m pip install -r scripts/requirements-catalog.txt`
4. `python3 -m unittest discover -s scripts -p 'test_catalog_*.py'`
5. `git status` and inspect diffs for workflow and scraper.
6. `git add scripts/technophere_catalog.py scripts/test_catalog_family.py scripts/test_catalog_quality.py .github/workflows/catalog-update.yml`
7. `git commit -m "feat: collect Technophere character forms and details"`
8. `git pull --rebase origin main && git push origin main` (if an Actions run is in progress, wait for it to complete before pushing).
9. In GitHub Actions, manually trigger **Update Technophere catalog**. Inspect `Collect and verify catalog`, `catalog-coverage.json`, and `catalog-audit-summary.json`.

## Go / No-go after first Actions run
- Go: tests green, parser logs `families_verified > 0`, `forms > 0`, record count never falls, `rateLimited=false`.
- No-go: zero forms from multiple successful family responses, warnings `family parse failed`, image or name mismatches, or HTTP 429. Keep old data intact; adjust parser based on sanitized HTML sample or logs and lower profile pace.
- For a safe manual test before production auto deployment, set repository variable `AUTO_DEPLOY_HOSTING=false` while validating new parser, then turn on after results confirmed.
