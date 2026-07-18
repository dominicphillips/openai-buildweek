from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from somethings_on.product_image_cache import (
    CACHE_MEDIA_TYPE,
    ProductImageCache,
    ProductImageCacheError,
    ProductImageNotFoundError,
    load_cache_index,
)


def make_webp() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (48, 64), "#202020").save(output, format="WEBP", quality=80)
    return output.getvalue()


def write_index(root: Path, *, product_id: str = "product-001") -> bytes:
    root.mkdir(parents=True, exist_ok=True)
    content = make_webp()
    (root / f"{product_id}.webp").write_bytes(content)
    index = {
        "schema_version": 1,
        "items": [
            {
                "id": product_id,
                "filename": f"{product_id}.webp",
                "source_image_url": "https://images.example.test/product-001.jpg",
                "source_page_url": "https://shop.example.test/products/product-001",
                "media_type": CACHE_MEDIA_TYPE,
                "width": 48,
                "height": 64,
                "byte_size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        ],
    }
    (root / "index.json").write_text(json.dumps(index), encoding="utf-8")
    return content


def test_cache_resolves_only_indexed_local_webp(tmp_path: Path) -> None:
    content = write_index(tmp_path)
    cache = ProductImageCache(tmp_path)

    record = cache.resolve("product-001")

    assert record.path.read_bytes() == content
    assert record.media_type == "image/webp"
    assert record.source_image_url.startswith("https://")
    assert cache.public_url("product-001") == (
        f"/api/inspiration/images/product-001?v={record.sha256[:16]}"
    )
    with pytest.raises(ProductImageNotFoundError):
        cache.resolve("../product-001")


def test_cache_rejects_a_traversal_filename(tmp_path: Path) -> None:
    content = make_webp()
    outside = tmp_path.parent / "outside.webp"
    outside.write_bytes(content)
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "index.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "items": [
                    {
                        "id": "product-001",
                        "filename": "../outside.webp",
                        "source_image_url": "https://images.example.test/product.jpg",
                        "source_page_url": "https://shop.example.test/product",
                        "media_type": "image/webp",
                        "width": 48,
                        "height": 64,
                        "byte_size": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProductImageCacheError, match="must use"):
        load_cache_index(tmp_path)


def test_cache_detects_an_indexed_size_mismatch(tmp_path: Path) -> None:
    write_index(tmp_path)
    (tmp_path / "product-001.webp").write_bytes(b"changed")

    with pytest.raises(ProductImageCacheError, match="indexed size"):
        load_cache_index(tmp_path)
