"""Validated local cache access for third-party product-reference images.

The cache is runtime-only research material. Its index preserves the source image
and product page URLs, but it does not grant publication or redistribution rights.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

CACHE_SCHEMA_VERSION = 1
CACHE_INDEX_FILENAME = "index.json"
CACHE_MEDIA_TYPE = "image/webp"
PRODUCT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRODUCT_IMAGE_CACHE_PATH = BACKEND_ROOT / "data" / "product-images"


class ProductImageCacheError(RuntimeError):
    """Raised when the local product-image cache index is unsafe or invalid."""


class ProductImageNotFoundError(ProductImageCacheError):
    """Raised when a product does not have a usable local cached image."""


@dataclass(frozen=True, slots=True)
class CachedProductImage:
    """One validated cache record and its safe local file path."""

    product_id: str
    path: Path
    source_image_url: str
    source_page_url: str
    media_type: str
    width: int
    height: int
    byte_size: int
    sha256: str

    @property
    def version(self) -> str:
        """Short content version used to make the browser URL immutable."""

        return self.sha256[:16]


def sha256_file(path: Path) -> str:
    """Hash a file without loading the complete image into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _positive_int(value: Any, field: str, product_id: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ProductImageCacheError(
            f"Cached product image {product_id!r} requires a positive {field}"
        )
    return value


def _source_url(value: Any, field: str, product_id: str) -> str:
    if not isinstance(value, str):
        raise ProductImageCacheError(f"Cached product image {product_id!r} requires {field}")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ProductImageCacheError(f"Cached product image {product_id!r} has an invalid {field}")
    return value


def load_cache_index(cache_root: str | Path) -> dict[str, CachedProductImage]:
    """Load the cache index and reject traversal, type, and size mismatches.

    A missing index is a valid empty cache so a clean checkout can still start.
    Individual files are not re-hashed here because this function runs in the API
    process; the importer offers an explicit full integrity verification command.
    """

    root = Path(cache_root)
    index_path = root / CACHE_INDEX_FILENAME
    if not index_path.exists():
        return {}
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProductImageCacheError("Product image cache index is unreadable") from error
    if not isinstance(payload, dict) or payload.get("schema_version") != CACHE_SCHEMA_VERSION:
        raise ProductImageCacheError(
            f"Product image cache schema_version must be {CACHE_SCHEMA_VERSION}"
        )
    items = payload.get("items")
    if not isinstance(items, list):
        raise ProductImageCacheError("Product image cache index requires an items list")

    root_resolved = root.resolve()
    records: dict[str, CachedProductImage] = {}
    for position, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ProductImageCacheError(f"Cached product image {position} must be an object")
        product_id = item.get("id")
        if not isinstance(product_id, str) or not PRODUCT_ID_PATTERN.fullmatch(product_id):
            raise ProductImageCacheError(f"Cached product image {position} has an invalid id")
        if product_id in records:
            raise ProductImageCacheError(f"Duplicate cached product image id: {product_id}")

        expected_filename = f"{product_id}.webp"
        if item.get("filename") != expected_filename:
            raise ProductImageCacheError(
                f"Cached product image {product_id!r} must use {expected_filename!r}"
            )
        candidate = root / expected_filename
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root_resolved)
        except (FileNotFoundError, OSError, ValueError) as error:
            raise ProductImageCacheError(
                f"Cached product image {product_id!r} has no safe local file"
            ) from error
        if not resolved.is_file():
            raise ProductImageCacheError(
                f"Cached product image {product_id!r} is not a regular file"
            )

        media_type = item.get("media_type")
        if media_type != CACHE_MEDIA_TYPE:
            raise ProductImageCacheError(
                f"Cached product image {product_id!r} must be {CACHE_MEDIA_TYPE}"
            )
        byte_size = _positive_int(item.get("byte_size"), "byte_size", product_id)
        if resolved.stat().st_size != byte_size:
            raise ProductImageCacheError(
                f"Cached product image {product_id!r} does not match its indexed size"
            )
        sha256 = item.get("sha256")
        if not isinstance(sha256, str) or not SHA256_PATTERN.fullmatch(sha256):
            raise ProductImageCacheError(
                f"Cached product image {product_id!r} requires a SHA-256 digest"
            )
        records[product_id] = CachedProductImage(
            product_id=product_id,
            path=resolved,
            source_image_url=_source_url(
                item.get("source_image_url"), "source_image_url", product_id
            ),
            source_page_url=_source_url(item.get("source_page_url"), "source_page_url", product_id),
            media_type=media_type,
            width=_positive_int(item.get("width"), "width", product_id),
            height=_positive_int(item.get("height"), "height", product_id),
            byte_size=byte_size,
            sha256=sha256,
        )
    return records


class ProductImageCache:
    """Thread-safe view of an atomically written local cache index."""

    def __init__(self, cache_root: str | Path = DEFAULT_PRODUCT_IMAGE_CACHE_PATH) -> None:
        self.cache_root = Path(cache_root)
        self._lock = threading.RLock()
        self._index_mtime_ns: int | None = None
        self._records: dict[str, CachedProductImage] = {}
        self.refresh()

    @property
    def count(self) -> int:
        self.refresh_if_changed()
        with self._lock:
            return len(self._records)

    def refresh(self) -> None:
        records = load_cache_index(self.cache_root)
        index_path = self.cache_root / CACHE_INDEX_FILENAME
        mtime = index_path.stat().st_mtime_ns if index_path.exists() else None
        with self._lock:
            self._records = records
            self._index_mtime_ns = mtime

    def refresh_if_changed(self) -> None:
        index_path = self.cache_root / CACHE_INDEX_FILENAME
        mtime = index_path.stat().st_mtime_ns if index_path.exists() else None
        with self._lock:
            unchanged = mtime == self._index_mtime_ns
        if not unchanged:
            self.refresh()

    def get(self, product_id: str) -> CachedProductImage | None:
        if not PRODUCT_ID_PATTERN.fullmatch(product_id):
            return None
        self.refresh_if_changed()
        with self._lock:
            return self._records.get(product_id)

    def resolve(self, product_id: str) -> CachedProductImage:
        record = self.get(product_id)
        if record is None:
            raise ProductImageNotFoundError("Product image is not cached")
        # Recheck the material facts used by FileResponse after the index load.
        try:
            if not record.path.is_file() or record.path.stat().st_size != record.byte_size:
                raise ProductImageNotFoundError("Product image is not cached")
        except OSError as error:
            raise ProductImageNotFoundError("Product image is not cached") from error
        return record

    def public_url(self, product_id: str) -> str:
        record = self.get(product_id)
        base = f"/api/inspiration/images/{product_id}"
        return f"{base}?v={record.version}" if record is not None else base
