---
name: cache-product-images
description: Build, resume, or verify the ignored local WebP cache for the 600-product Inspiration catalog. Use after the product manifest changes, when Inspiration images are missing, or before browser/demo QA that must not hotlink third-party image hosts.
---

# Cache Product Images

Use the repository importer; do not write a second downloader.

```bash
cd backend
uv run python scripts/cache_product_images.py
uv run python scripts/cache_product_images.py --verify
```

The first command resumes missing records, validates each raster, resizes it, and writes `data/product-images/index.json`. The second command performs an offline source-URL, file, size, and SHA-256 check. A complete demo cache contains 600 indexed WebP files.

Keep `backend/data/product-images/` ignored. The files are private local research copies of third-party, all-rights-reserved imagery; never commit, publish, or redistribute them. Preserve every original product-page and image URL in the committed manifest and cache index.

For a quick importer check, pass `--limit N`. Before calling the demo ready, run the full import and full verification, start the API, and confirm browser image requests use `/api/inspiration/images/{product_id}` rather than external hosts.
