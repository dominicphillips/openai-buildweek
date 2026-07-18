"""Reviewed official-product inspiration metadata backed by LanceDB FTS."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import lancedb

from .product_image_cache import (
    DEFAULT_PRODUCT_IMAGE_CACHE_PATH,
    CachedProductImage,
    ProductImageCache,
    ProductImageNotFoundError,
)

TABLE_NAME = "official_products"
SEARCH_COLUMN = "search_text"
EXPECTED_PRODUCT_COUNT = 600
EXPECTED_BRAND_COUNT = 20
PRODUCTS_PER_BRAND = 30
MAX_RESULTS = 30
MAX_SEARCH_CANDIDATES = 1000
SCHEMA_VERSION = 1

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = BACKEND_ROOT / "seeds" / "product_inspiration.json"
DEFAULT_DB_PATH = BACKEND_ROOT / "data" / "reference-catalog.lancedb"

_REQUIRED_STRING_FIELDS = (
    "id",
    "validation_status",
    "brand",
    "brand_id",
    "product_name",
    "title",
    "category",
    "object_type",
    "description",
    "source_url",
    "image_url",
    "image_alt",
    "silhouette",
    "rights_note",
    "source_note",
)
_LIST_FIELDS = (
    "neutral_attributes",
    "materials",
    "construction",
    "palette",
    "tags",
)


class ProductCatalogError(RuntimeError):
    """Raised when reviewed product inspiration cannot be built or queried."""


def load_product_manifest(path: str | Path = DEFAULT_MANIFEST_PATH) -> dict[str, Any]:
    manifest_path = Path(path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ProductCatalogError(f"Product manifest not found: {manifest_path}") from error
    except json.JSONDecodeError as error:
        raise ProductCatalogError("Product manifest is not valid JSON") from error

    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ProductCatalogError(f"Product manifest schema_version must be {SCHEMA_VERSION}")
    items = manifest.get("items")
    if not isinstance(items, list) or len(items) != EXPECTED_PRODUCT_COUNT:
        raise ProductCatalogError(
            f"Product manifest must contain exactly {EXPECTED_PRODUCT_COUNT} items"
        )

    seen_ids: set[str] = set()
    seen_source_urls: set[str] = set()
    seen_image_urls: set[str] = set()
    seen_orders: set[int] = set()
    brand_counts: Counter[str] = Counter()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ProductCatalogError(f"Product item {index} must be an object")
        for field in _REQUIRED_STRING_FIELDS:
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ProductCatalogError(f"Product item {index} requires {field}")
        for field in _LIST_FIELDS:
            value = item.get(field)
            if not isinstance(value, list) or not all(
                isinstance(entry, str) and entry.strip() for entry in value
            ):
                raise ProductCatalogError(
                    f"Product item {index} requires a string list for {field}"
                )
        if not item["neutral_attributes"] or not item["tags"]:
            raise ProductCatalogError(
                f"Product item {index} requires neutral attributes and search tags"
            )
        for field in ("source_url", "image_url"):
            parsed = urlparse(item[field])
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ProductCatalogError(f"Product item {index} has an invalid {field}")

        item_id = item["id"]
        seed_order = item.get("seed_order")
        if item_id in seen_ids:
            raise ProductCatalogError(f"Duplicate product id: {item_id}")
        if item["source_url"] in seen_source_urls:
            raise ProductCatalogError(f"Duplicate product source_url: {item['source_url']}")
        if item["image_url"] in seen_image_urls:
            raise ProductCatalogError(f"Duplicate product image_url: {item['image_url']}")
        if isinstance(seed_order, bool) or not isinstance(seed_order, int):
            raise ProductCatalogError(f"Product item {index} requires integer seed_order")
        if seed_order in seen_orders:
            raise ProductCatalogError(f"Duplicate product seed_order: {seed_order}")
        seen_ids.add(item_id)
        seen_source_urls.add(item["source_url"])
        seen_image_urls.add(item["image_url"])
        seen_orders.add(seed_order)
        brand_counts[item["brand"]] += 1

    if seen_orders != set(range(1, EXPECTED_PRODUCT_COUNT + 1)):
        raise ProductCatalogError(
            f"Product seed_order must be the contiguous range 1 through {EXPECTED_PRODUCT_COUNT}"
        )
    if len(brand_counts) != EXPECTED_BRAND_COUNT:
        raise ProductCatalogError(
            f"Product manifest must contain exactly {EXPECTED_BRAND_COUNT} brands"
        )
    invalid_brand_counts = {
        brand: count for brand, count in brand_counts.items() if count != PRODUCTS_PER_BRAND
    }
    if invalid_brand_counts:
        raise ProductCatalogError(
            f"Each brand must contain exactly {PRODUCTS_PER_BRAND} products: {invalid_brand_counts}"
        )
    return manifest


def _search_text(item: dict[str, Any]) -> str:
    values = [
        item["brand"],
        item["product_name"],
        item["category"],
        item["object_type"],
        item["description"],
        item["silhouette"],
    ]
    for field in _LIST_FIELDS:
        values.extend(item[field])
    return " ".join(values)


def _row(item: dict[str, Any]) -> dict[str, Any]:
    return {**item, SEARCH_COLUMN: _search_text(item)}


def _normalize_filter(values: str | Iterable[str] | None) -> set[str]:
    if values is None:
        return set()
    candidates = [values] if isinstance(values, str) else list(values)
    return {value.strip().casefold() for value in candidates if value.strip()}


def _matches(value: str, allowed: set[str]) -> bool:
    return not allowed or value.casefold() in allowed


class ProductCatalog:
    """Build and browse 30 reviewed product records for each supported brand."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
        image_cache_path: str | Path = DEFAULT_PRODUCT_IMAGE_CACHE_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.manifest_path = Path(manifest_path)
        self.image_cache = ProductImageCache(image_cache_path)
        self._source_by_id: dict[str, tuple[str, str]] = {}

    def build(self) -> int:
        manifest = load_product_manifest(self.manifest_path)
        self._source_by_id = {
            item["id"]: (item["image_url"], item["source_url"]) for item in manifest["items"]
        }
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        database = lancedb.connect(str(self.db_path))
        table = database.create_table(
            TABLE_NAME,
            data=[_row(item) for item in manifest["items"]],
            mode="overwrite",
        )
        table.create_fts_index(SEARCH_COLUMN, replace=True)
        return len(manifest["items"])

    def search(
        self,
        query: str = "",
        limit: int = MAX_RESULTS,
        *,
        brands: str | Iterable[str] | None = None,
        categories: str | Iterable[str] | None = None,
        object_types: str | Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RESULTS:
            raise ValueError(f"limit must be between 1 and {MAX_RESULTS}")

        database = lancedb.connect(str(self.db_path))
        if TABLE_NAME not in set(database.list_tables(limit=100).tables):
            raise ProductCatalogError("Product catalog has not been built")
        table = database.open_table(TABLE_NAME)
        normalized_query = query.strip()
        if normalized_query:
            fts_query = " ".join(re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", normalized_query))
            if not fts_query:
                return []
            rows = (
                table.search(fts_query, query_type="fts")
                .limit(MAX_SEARCH_CANDIDATES)
                .to_arrow()
                .to_pylist()
            )
        else:
            rows = table.to_arrow().to_pylist()
            rows.sort(key=lambda candidate: candidate["seed_order"])

        self.image_cache.refresh_if_changed()

        brand_filter = _normalize_filter(brands)
        category_filter = _normalize_filter(categories)
        object_filter = _normalize_filter(object_types)
        rows = [
            row
            for row in rows
            if _matches(row["brand"], brand_filter)
            and _matches(row["category"], category_filter)
            and _matches(row["object_type"], object_filter)
        ]
        return [self._result(row) for row in rows[:limit]]

    def facets(self) -> dict[str, Any]:
        """Return complete browse filters without sending every product to the browser."""

        database = lancedb.connect(str(self.db_path))
        if TABLE_NAME not in set(database.list_tables(limit=100).tables):
            raise ProductCatalogError("Product catalog has not been built")
        rows = database.open_table(TABLE_NAME).to_arrow().to_pylist()

        def counted(field: str) -> list[dict[str, str | int]]:
            counts = Counter(str(row[field]) for row in rows)
            return [
                {"value": value, "count": count}
                for value, count in sorted(counts.items(), key=lambda entry: entry[0].casefold())
            ]

        return {
            "total": len(rows),
            "brands": counted("brand"),
            "categories": counted("category"),
            "object_types": counted("object_type"),
        }

    def resolve_image(self, product_id: str) -> CachedProductImage:
        """Resolve only a cache entry that still matches its reviewed source row."""

        expected_source = self._source_by_id.get(product_id)
        if expected_source is None:
            raise ProductImageNotFoundError("Product image is not cached")
        record = self.image_cache.resolve(product_id)
        if (record.source_image_url, record.source_page_url) != expected_source:
            raise ProductImageNotFoundError("Product image is not cached")
        return record

    def _cached_image(self, row: dict[str, Any]) -> CachedProductImage | None:
        record = self.image_cache.get(row["id"])
        if record is None:
            return None
        if (record.source_image_url, record.source_page_url) != (
            row["image_url"],
            row["source_url"],
        ):
            return None
        return record

    def _result(self, row: dict[str, Any]) -> dict[str, Any]:
        neutral_attributes = list(row["neutral_attributes"])
        source_image_url = row["image_url"]
        cached_image = self._cached_image(row)
        local_image_url = f"/api/inspiration/images/{row['id']}"
        if cached_image is not None:
            local_image_url = f"{local_image_url}?v={cached_image.version}"
        return {
            "id": row["id"],
            "title": row["title"],
            "brand": row["brand"],
            "product_name": row["product_name"],
            "category": row["category"],
            "object_type": row["object_type"],
            "description": row["description"],
            "source_url": row["source_url"],
            "neutral_attributes": neutral_attributes,
            "image_url": local_image_url,
            "source_image_url": source_image_url,
            "image_cached": cached_image is not None,
            "image_alt": row["image_alt"],
            "metadata": {
                "seed_order": row["seed_order"],
                "brand": row["brand"],
                "product_name": row["product_name"],
                "source_url": row["source_url"],
                "source_image_url": source_image_url,
                "neutral_attributes": neutral_attributes,
                "silhouette": row["silhouette"],
                "materials": list(row["materials"]),
                "construction": list(row["construction"]),
                "palette": list(row["palette"]),
                "tags": list(row["tags"]),
                "label_association": {
                    "id": row["brand_id"],
                    "name": row["brand"],
                    "matched_traits": neutral_attributes,
                    "basis": "official-product-source",
                    "note": row["source_note"],
                },
                "provenance": {
                    "kind": "official-product",
                    "label": row["brand"],
                    "note": row["source_note"],
                    "rights": row["rights_note"],
                    "source_image_url": source_image_url,
                    "local_cache": (
                        "runtime-only research copy; permission not verified; not for "
                        "redistribution"
                    ),
                },
            },
        }
