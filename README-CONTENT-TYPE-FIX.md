# GameWith image Content-Type compatibility fix

## Observed issue
For `https://img.gamewith.jp/article_tools/monst/gacha/112.jpg`, the user confirmed HTTP 200, no `Content-Type` header, and valid JPEG magic bytes. The former importer required the header and rejected the file.

## Changes
- `scripts/auto_import_approved_icons.py`: when the Content-Type header is missing, accept only valid JPEG, PNG, or WebP binary signatures; keep rejection of non-image MIME values, mismatched MIME, oversized content, and existing redirect host restrictions.
- `tests/test_icon_missing_content_type.py`: five regression tests; no real network requests.

## Install
From the project root, first save a copy of `scripts/auto_import_approved_icons.py`, then unzip this patch in the project root. This patch does not change the React UI or workflow configuration.

```bash
cp scripts/auto_import_approved_icons.py ~/auto_import_approved_icons-before-mime-fix.py
unzip -o ~/Downloads/monst-gamewith-content-type-fix.zip
python3 -m unittest discover -s tests -p 'test_auto_import_approved_icons.py'
python3 -m unittest discover -s tests -p 'test_icon_missing_content_type.py'
python3 -m unittest discover -s tests -p 'test_prepare_gamewith_icon_queue.py'
git diff -- scripts/auto_import_approved_icons.py
git status --short
```

If tests pass, commit only the two changed/added files:

```bash
git add scripts/auto_import_approved_icons.py tests/test_icon_missing_content_type.py README-CONTENT-TYPE-FIX.md
git commit -m "fix: accept verified images without Content-Type header"
```

Before pulling, safely back up any unstaged tracked changes and avoid overwriting or deleting local images. Then push with `git pull --rebase origin main` and `git push origin main` if the working tree is ready. Stop if rebase reports a conflict.

## Verification
After pushing, set `GAMEWITH_ICON_IMPORT_ENABLED=true`, run **Import GameWith approved character icons** manually once, and inspect its `downloaded`, `errors`, and `denied` fields. Start with its existing max of 10 new images per run. If verified, let scheduled runs proceed. Keep `APPROVED_ICON_HOST` for Technophere unchanged. Confirm that the Hosting deployment sees the new images by opening `/character-icons/<id>.jpg` on your production domain.

## Limitations
Only one URL (No.112) was confirmed from the user's screenshot. Other 4,454 URLs have not been validated in this patch. The patch does not bypass 403 or access controls or modify daily request rates. A successful image import does not automatically prove that Firebase Hosting has deployed the new files.
