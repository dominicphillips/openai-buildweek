"""Local, project-authored fashion reference catalog backed by LanceDB FTS."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import lancedb

TABLE_NAME = "candidates"
SEARCH_COLUMN = "search_text"
EXPECTED_SEED_COUNT = 30
MAX_RESULTS = 30
SCHEMA_VERSION = 1
PROVENANCE_ID = "somethings-on-project-authored-v1"
RIGHTS_STATUS = "project-authored-original"

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = BACKEND_ROOT / "seeds" / "reference_catalog.json"
DEFAULT_DB_PATH = BACKEND_ROOT / "data" / "reference-catalog.lancedb"

_REQUIRED_ITEM_FIELDS = {
    "id",
    "seed_order",
    "title",
    "category",
    "object_type",
    "description",
    "silhouette",
    "materials",
    "construction",
    "palette",
    "tags",
    "image_url",
    "image_path",
    "image_alt",
    "label_association",
    "provenance_id",
    "rights_status",
    "illustration",
}
_LIST_FIELDS = ("materials", "construction", "palette", "tags")
_EXPECTED_CATEGORIES = {
    "t-shirts",
    "outerwear",
    "pants",
    "shorts",
    "footwear",
    "bags",
    "headwear",
}
SUPPORTED_LABEL_IDS = {
    "a-cold-wall",
    "acne-studios",
    "balenciaga",
    "comme-des-garcons",
    "craig-green",
    "fear-of-god",
    "jil-sander",
    "john-elliott",
    "kiko-kostadinov",
    "maison-margiela",
    "martine-rose",
    "off-white",
    "our-legacy",
    "represent",
    "rhude",
    "rick-owens",
    "sacai",
    "stone-island",
    "undercover",
    "vetements",
}


class ReferenceCatalogError(RuntimeError):
    """Base error for a malformed or unavailable local reference catalog."""


class CatalogNotBuiltError(ReferenceCatalogError):
    """Raised when search is attempted before the local LanceDB build exists."""


@dataclass(frozen=True)
class CatalogBuildSummary:
    """A small, serializable account of a deterministic catalog build."""

    table_name: str
    row_count: int
    db_path: Path


def load_reference_manifest(path: str | Path = DEFAULT_MANIFEST_PATH) -> dict[str, Any]:
    """Load and validate the reviewable source manifest."""

    manifest_path = Path(path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReferenceCatalogError(f"Reference manifest not found: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise ReferenceCatalogError(f"Reference manifest is not valid JSON: {exc}") from exc

    if not isinstance(manifest, dict):
        raise ReferenceCatalogError("Reference manifest must be a JSON object")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ReferenceCatalogError(f"Reference manifest schema_version must be {SCHEMA_VERSION}")

    for field in (
        "catalog_id",
        "catalog_title",
        "source_note",
        "rights_note",
        "label_association_note",
    ):
        if not _nonempty_string(manifest.get(field)):
            raise ReferenceCatalogError(f"Reference manifest field {field!r} is required")

    provenance = manifest.get("provenance")
    if provenance != {
        "id": PROVENANCE_ID,
        "kind": "project-authored",
        "rights_status": RIGHTS_STATUS,
    }:
        raise ReferenceCatalogError("Reference manifest provenance does not match the contract")

    items = manifest.get("items")
    if not isinstance(items, list) or len(items) != EXPECTED_SEED_COUNT:
        raise ReferenceCatalogError(
            f"Reference manifest must contain exactly {EXPECTED_SEED_COUNT} items"
        )

    seen_ids: set[str] = set()
    seen_orders: set[int] = set()
    categories: set[str] = set()
    label_ids: set[str] = set()
    for index, item in enumerate(items, start=1):
        _validate_item(item, index=index, seen_ids=seen_ids, seen_orders=seen_orders)
        categories.add(item["category"])
        label_ids.add(item["label_association"]["id"])

    expected_orders = set(range(1, EXPECTED_SEED_COUNT + 1))
    if seen_orders != expected_orders:
        raise ReferenceCatalogError("seed_order values must be the contiguous range 1 through 30")
    if categories != _EXPECTED_CATEGORIES:
        missing = sorted(_EXPECTED_CATEGORIES - categories)
        extra = sorted(categories - _EXPECTED_CATEGORIES)
        raise ReferenceCatalogError(
            "Reference categories do not match the catalog contract; "
            f"missing={missing}, extra={extra}"
        )
    if label_ids != SUPPORTED_LABEL_IDS:
        missing = sorted(SUPPORTED_LABEL_IDS - label_ids)
        extra = sorted(label_ids - SUPPORTED_LABEL_IDS)
        raise ReferenceCatalogError(
            "Reference label associations do not cover the selector catalog; "
            f"missing={missing}, extra={extra}"
        )

    return manifest


def compose_search_text(item: dict[str, Any]) -> str:
    """Compose the lexical evidence indexed by LanceDB full-text search."""

    parts: list[str] = [
        item["title"],
        item["category"],
        item["object_type"],
        item["description"],
        item["silhouette"],
    ]
    for field in _LIST_FIELDS:
        parts.extend(item[field])
    association = item["label_association"]
    parts.extend([association["name"], *association["matched_traits"]])
    return " ".join(parts)


class ReferenceCatalog:
    """Build and query the local, lexical reference catalog.

    This adapter intentionally has no vector column. The 30-item seed set is
    small, and full-text evidence is both sufficient and inspectable. No hash
    vector is presented as semantic truth.
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.manifest_path = Path(manifest_path)

    def build(self) -> CatalogBuildSummary:
        """Rebuild the ``candidates`` table and its FTS index from the manifest."""

        manifest = load_reference_manifest(self.manifest_path)
        rows = [_manifest_item_to_row(manifest, item) for item in manifest["items"]]

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        database = lancedb.connect(str(self.db_path))
        table = database.create_table(TABLE_NAME, data=rows, mode="overwrite")
        table.create_fts_index(SEARCH_COLUMN, replace=True)

        return CatalogBuildSummary(
            table_name=TABLE_NAME,
            row_count=len(rows),
            db_path=self.db_path,
        )

    def search(
        self,
        query: str,
        limit: int = MAX_RESULTS,
        *,
        label_ids: str | Iterable[str] | None = None,
        categories: str | Iterable[str] | None = None,
        object_types: str | Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return at most 30 image-backed references and their local metadata.

        A blank query is the browse path and returns manifest order. A nonblank
        query uses only the composed ``search_text`` full-text index.
        """

        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be an integer")
        if not 1 <= limit <= MAX_RESULTS:
            raise ValueError(f"limit must be between 1 and {MAX_RESULTS}")

        normalized_label_ids = _normalize_filter(label_ids, name="label_ids")
        normalized_categories = _normalize_filter(categories, name="categories")
        normalized_object_types = _normalize_filter(object_types, name="object_types")

        table = self._open_table()
        normalized_query = query.strip()
        if normalized_query:
            rows = (
                table.search(normalized_query, query_type="fts")
                .limit(MAX_RESULTS)
                .to_arrow()
                .to_pylist()
            )
        else:
            rows = table.to_arrow().to_pylist()
            rows.sort(key=lambda row: row["seed_order"])

        rows = [
            row
            for row in rows
            if _matches_filter(row["label_id"], normalized_label_ids)
            and _matches_filter(row["category"], normalized_categories)
            and _matches_filter(row["object_type"], normalized_object_types)
        ]
        return [_row_to_result(row) for row in rows[:limit]]

    def _open_table(self):
        if not self.db_path.is_dir():
            raise CatalogNotBuiltError("Reference catalog has not been built")

        database = lancedb.connect(str(self.db_path))
        if TABLE_NAME not in set(database.list_tables(limit=MAX_RESULTS).tables):
            raise CatalogNotBuiltError(f"Reference catalog table {TABLE_NAME!r} is missing")
        return database.open_table(TABLE_NAME)


def _manifest_item_to_row(manifest: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "seed_order": item["seed_order"],
        "title": item["title"],
        "category": item["category"],
        "object_type": item["object_type"],
        "description": item["description"],
        "silhouette": item["silhouette"],
        "materials": item["materials"],
        "construction": item["construction"],
        "palette": item["palette"],
        "tags": item["tags"],
        "image_url": item["image_url"],
        "image_path": item["image_path"],
        "image_alt": item["image_alt"],
        "label_id": item["label_association"]["id"],
        "label_name": item["label_association"]["name"],
        "label_traits": item["label_association"]["matched_traits"],
        "label_association_basis": item["label_association"]["basis"],
        "label_association_note": manifest["label_association_note"],
        "provenance_id": item["provenance_id"],
        "provenance_kind": manifest["provenance"]["kind"],
        "rights_status": item["rights_status"],
        "source_kind": "project-authored",
        "source_label": manifest["catalog_title"],
        "source_note": manifest["source_note"],
        "rights_note": manifest["rights_note"],
        SEARCH_COLUMN: compose_search_text(item),
    }


def _row_to_result(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "object_type": row["object_type"],
        "description": row["description"],
        "image_url": row["image_url"],
        "image_path": row["image_path"],
        "image_alt": row["image_alt"],
        "metadata": {
            "seed_order": row["seed_order"],
            "silhouette": row["silhouette"],
            "materials": row["materials"],
            "construction": row["construction"],
            "palette": row["palette"],
            "tags": row["tags"],
            "search_text": row[SEARCH_COLUMN],
            "label_association": {
                "id": row["label_id"],
                "name": row["label_name"],
                "matched_traits": row["label_traits"],
                "basis": row["label_association_basis"],
                "note": row["label_association_note"],
            },
            "provenance": {
                "id": row["provenance_id"],
                "kind": row["provenance_kind"],
                "rights_status": row["rights_status"],
                "label": row["source_label"],
                "note": row["source_note"],
                "rights": row["rights_note"],
            },
        },
    }


def _validate_item(
    item: Any,
    *,
    index: int,
    seen_ids: set[str],
    seen_orders: set[int],
) -> None:
    if not isinstance(item, dict):
        raise ReferenceCatalogError(f"Reference item {index} must be a JSON object")

    missing = sorted(_REQUIRED_ITEM_FIELDS - item.keys())
    if missing:
        raise ReferenceCatalogError(f"Reference item {index} is missing fields: {missing}")

    for field in (
        "id",
        "title",
        "category",
        "object_type",
        "description",
        "silhouette",
        "image_url",
        "image_path",
        "image_alt",
        "provenance_id",
        "rights_status",
    ):
        if not _nonempty_string(item[field]):
            raise ReferenceCatalogError(f"Reference item {index} field {field!r} is required")

    item_id = item["id"]
    if item_id in seen_ids:
        raise ReferenceCatalogError(f"Duplicate reference id: {item_id}")
    seen_ids.add(item_id)

    seed_order = item["seed_order"]
    if isinstance(seed_order, bool) or not isinstance(seed_order, int):
        raise ReferenceCatalogError(f"Reference item {item_id} seed_order must be an integer")
    if seed_order in seen_orders:
        raise ReferenceCatalogError(f"Duplicate seed_order: {seed_order}")
    seen_orders.add(seed_order)

    expected_image_url = f"/reference-seeds/{item_id}.svg"
    if item["image_url"] != expected_image_url:
        raise ReferenceCatalogError(
            f"Reference item {item_id} image_url must be {expected_image_url!r}"
        )
    expected_image_path = f"app/public{expected_image_url}"
    if item["image_path"] != expected_image_path:
        raise ReferenceCatalogError(
            f"Reference item {item_id} image_path must be {expected_image_path!r}"
        )

    for field in _LIST_FIELDS:
        values = item[field]
        if (
            not isinstance(values, list)
            or not values
            or not all(_nonempty_string(value) for value in values)
        ):
            raise ReferenceCatalogError(
                f"Reference item {item_id} field {field!r} must be a nonempty string list"
            )

    if item["provenance_id"] != PROVENANCE_ID:
        raise ReferenceCatalogError(
            f"Reference item {item_id} provenance_id must be {PROVENANCE_ID!r}"
        )
    if item["rights_status"] != RIGHTS_STATUS:
        raise ReferenceCatalogError(
            f"Reference item {item_id} rights_status must be {RIGHTS_STATUS!r}"
        )

    association = item["label_association"]
    if not isinstance(association, dict):
        raise ReferenceCatalogError(
            f"Reference item {item_id} label_association must be a JSON object"
        )
    if set(association) != {"id", "name", "matched_traits", "basis"}:
        raise ReferenceCatalogError(
            f"Reference item {item_id} label_association fields do not match the contract"
        )
    if not _nonempty_string(association["id"]) or association["id"] not in SUPPORTED_LABEL_IDS:
        raise ReferenceCatalogError(
            f"Reference item {item_id} has an unsupported label association id"
        )
    if not _nonempty_string(association["name"]):
        raise ReferenceCatalogError(f"Reference item {item_id} label association name is required")
    matched_traits = association["matched_traits"]
    if (
        not isinstance(matched_traits, list)
        or not matched_traits
        or not all(_nonempty_string(value) for value in matched_traits)
    ):
        raise ReferenceCatalogError(
            f"Reference item {item_id} label matched_traits must be a nonempty string list"
        )
    if association["basis"] != "editorial-trait-overlap":
        raise ReferenceCatalogError(
            f"Reference item {item_id} label association basis must be editorial-trait-overlap"
        )

    illustration = item["illustration"]
    if not isinstance(illustration, dict):
        raise ReferenceCatalogError(f"Reference item {item_id} illustration must be a JSON object")
    if not _nonempty_string(illustration.get("template")):
        raise ReferenceCatalogError(f"Reference item {item_id} illustration template is required")
    variant = illustration.get("variant")
    if isinstance(variant, bool) or not isinstance(variant, int) or variant < 0:
        raise ReferenceCatalogError(
            f"Reference item {item_id} illustration variant must be a nonnegative integer"
        )
    details = illustration.get("details")
    if (
        not isinstance(details, list)
        or not details
        or not all(_nonempty_string(value) for value in details)
    ):
        raise ReferenceCatalogError(
            f"Reference item {item_id} illustration details must be a nonempty string list"
        )


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalize_filter(
    values: str | Iterable[str] | None,
    *,
    name: str,
) -> set[str] | None:
    if values is None:
        return None
    candidates = [values] if isinstance(values, str) else list(values)
    if not all(_nonempty_string(value) for value in candidates):
        raise TypeError(f"{name} must contain only nonempty strings")
    normalized = {value.strip().casefold() for value in candidates}
    return normalized or None


def _matches_filter(value: str, accepted: set[str] | None) -> bool:
    return accepted is None or value.casefold() in accepted
