# Phase 10: Image URL audit (read only)

This adds only `scripts/catalog_image_audit.py` and its tests. It does not modify the collector, GitHub Actions, JSON, Firestore, or Hosting.

From the repository root:

```bash
python3 -m unittest discover -s scripts -p 'test_catalog_image_audit.py'
python3 scripts/catalog_image_audit.py public/catalog --output local-reports/image-audit
```

Open `local-reports/image-audit/summary.json` and `image-audit.csv`. By default, this makes **zero network requests**. `format_ok` means the URL matches the strict expected convention: HTTPS on Technophere, extension PNG/JPEG/WebP, filename stem exactly equal to the character's catalog ID. This is a diagnostic convention, **not a proof** the image is correct; nonnumeric or CDN paths may legitimately work and should be reviewed separately.

Optionally, after confirming site permission and rate rules, run a tiny sample of up to 10 image requests:

```bash
python3 -m pip install requests
python3 scripts/catalog_image_audit.py public/catalog --output local-reports/image-audit-sample --online-limit 5 --delay 3
```

Online mode checks `robots.txt` and then uses a limited HTTPS GET for a magic-byte/content-type check; no authentication or bypassing. Stop on HTTP 429. `image_ok` means bytes appear to be an image, **not** that it depicts the correct form. A failure of robots.txt retrieval should be treated as a reason to avoid online auditing (check the site's rules yourself).

The first 5 format-valid image URLs are checked (not a randomized sample). Do not commit the output folder. A strict numeric-filename check can flag valid site assets: investigate, don't delete catalog records based solely on this audit.
