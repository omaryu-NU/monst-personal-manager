# Phase 17 — scheduled image backfill safety gate

## What this changes

This patch **only adds** an offline scheduling guard and updates `.github/workflows/catalog-update.yml`. The existing Phase16 image backfill and evidence logic remains intact. It does not access Firebase/Firestore. Normal catalog scraping still runs on its prior cron.

- **Manual execution**: `IMAGE_BACKFILL_ENABLED=true`, `IMAGE_PROBE_DRY_RUN=false`, `AUTO_DEPLOY_HOSTING=false` => up to **3 HTTP candidate checks**, 4 seconds apart.
- **Scheduled execution**: requires `IMAGE_BACKFILL_ENABLED=true`, `IMAGE_BACKFILL_SCHEDULED=true`, `IMAGE_PROBE_DRY_RUN=false`, and `AUTO_DEPLOY_HOSTING=false`, plus a valid existing state file and evidence and **6 hours elapsed** since `state.updatedAt`. Checks **at most 1** image candidate, with a 6-second delay.
- Invalid/missing state, future timestamp, active cooldown, no evidence or hosting enabled => **skip scheduled image requests**, with the reason written to `local-reports/image-backfill/phase17-schedule-guard.json` (Artifact `catalog-image-phase17-schedule-guard`). Normal catalog update continues.
- Standard integrity and image evidence consistency gates still run before committing and publishing.
- **Important:** HTTP 200 / WebP signatures and ID-named filenames do not establish that the image shows the correct character. Do not enable Hosting publishing of new image backfill results until verified by an independent identity review.
- If Technophere's authorization/robots/usage rules restrict scheduled image retrieval, keep `IMAGE_BACKFILL_SCHEDULED=false`. The 6-hour period is a technical **minimum**, not permission or a guarantee that the volume is acceptable.

## Install on Mac

From the Monst Personal Manager repository directory:

```bash
git status --short
cp .github/workflows/catalog-update.yml ~/catalog-update-before-phase17.yml
unzip -o ~/Downloads/monst-catalog-phase17-scheduled-safety-patch.zip
python3 -m unittest discover -s scripts -p 'test_catalog_phase17.py'
python3 -m unittest discover -s scripts -p 'test_catalog_*.py'
git diff -- .github/workflows/catalog-update.yml
```

Before pushing, check for uncommitted generated files. Preserve local changes using a backup or targeted `git stash` before `git pull --rebase`.

```bash
git add .github/workflows/catalog-update.yml scripts/catalog_image_schedule_guard.py scripts/test_catalog_phase17.py PHASE17-README.md
git commit -m 'ci: gate scheduled image probes with six hour cooldown'
git status --short
git pull --rebase origin main
git push origin main
```

## Validation on GitHub

Initially keep `IMAGE_BACKFILL_SCHEDULED=false`, `AUTO_DEPLOY_HOSTING=false`. First ensure the repo actually contains the **committed** `catalog-image-backfill-state.json` and `catalog-image-evidence.json`, and that evidence records correspond to intended characters. The user's previous Phase16 2nd run reported 11 image evidence items and last ID 152, but these files were not uploaded for independent inspection.

To test the gate locally *without network*:

```bash
python3 scripts/catalog_image_schedule_guard.py \
  --state catalog-image-backfill-state.json \
  --evidence catalog-image-evidence.json \
  --min-hours 6 \
  --report local-reports/image-backfill/phase17-local-guard.json
cat local-reports/image-backfill/phase17-local-guard.json
```

**Only after checking permission and identity, and when ready for bounded scheduled checks**, set `IMAGE_BACKFILL_SCHEDULED=true` and leave `AUTO_DEPLOY_HOSTING=false`. GitHub cron remains `17 */3 * * *`; the image guard allows *at most* one image request at eligible runs and skips within the 6-hour cooldown. Observe the guard and Phase16 artifacts over multiple runs. Set `IMAGE_BACKFILL_SCHEDULED=false` immediately if rate limits, image mismatch, or unexpected behavior occur.

### Known limitations

- With only 1 image per eligible run and a minimum 6-hour gap, completing several thousand images would take a long time; prioritize accuracy and authorized access over speed.
- State `updatedAt` only changes after a Phase16 apply; a 429 aborts workflow (no commit) and the previous state will remain eligible. The HTTP 429 handling prevents continuation within that run but does **not** create a persistent multi-run cooldown. Keep schedule disabled after a 429 and review logs.
- GitHub Actions updates the catalog in the same workflow, so local `catalog-coverage.json` changes may block a subsequent local `git pull --rebase`. Do not discard user data or force push.
