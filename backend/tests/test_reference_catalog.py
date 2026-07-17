from __future__ import annotations

from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

import lancedb
import pytest

from somethings_on.reference_catalog import (
    EXPECTED_SEED_COUNT,
    PROVENANCE_ID,
    RIGHTS_STATUS,
    SEARCH_COLUMN,
    SUPPORTED_LABEL_IDS,
    TABLE_NAME,
    CatalogNotBuiltError,
    ReferenceCatalog,
    load_reference_manifest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = REPOSITORY_ROOT / "app" / "public" / "reference-seeds"


def test_manifest_has_exactly_30_project_authored_image_backed_items() -> None:
    manifest = load_reference_manifest()
    items = manifest["items"]

    assert len(items) == EXPECTED_SEED_COUNT
    assert [item["seed_order"] for item in items] == list(range(1, 31))
    assert Counter(item["category"] for item in items) == {
        "t-shirts": 5,
        "outerwear": 6,
        "pants": 5,
        "shorts": 3,
        "footwear": 5,
        "bags": 3,
        "headwear": 3,
    }
    assert "Project-authored" in manifest["rights_note"]
    assert "No scraped imagery" in manifest["rights_note"]
    assert {item["label_association"]["id"] for item in items} == SUPPORTED_LABEL_IDS

    expected_files = {Path(item["image_url"]).name for item in items}
    actual_files = {path.name for path in ASSET_ROOT.glob("*.svg")}
    assert actual_files == expected_files

    for item in items:
        assert item["tags"]
        assert item["materials"]
        assert item["image_url"] == f"/reference-seeds/{item['id']}.svg"
        assert item["image_path"] == f"app/public{item['image_url']}"
        assert item["label_association"]["basis"] == "editorial-trait-overlap"
        assert item["provenance_id"] == PROVENANCE_ID
        assert item["rights_status"] == RIGHTS_STATUS
        asset = ASSET_ROOT / Path(item["image_url"]).name
        root = ElementTree.parse(asset).getroot()
        assert root.tag == "{http://www.w3.org/2000/svg}svg"
        assert root.attrib["viewBox"] == "0 0 480 360"
        title = root.find("{http://www.w3.org/2000/svg}title")
        description = root.find("{http://www.w3.org/2000/svg}desc")
        assert title is not None and title.text == item["title"]
        assert description is not None and description.text.startswith(item["image_alt"])
        assert root.findall(".//{http://www.w3.org/2000/svg}text") == []


def test_builds_candidates_fts_and_returns_browse_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "reference-catalog.lancedb"
    catalog = ReferenceCatalog(db_path=db_path)

    summary = catalog.build()

    assert summary.table_name == TABLE_NAME
    assert summary.row_count == EXPECTED_SEED_COUNT
    database = lancedb.connect(str(db_path))
    assert set(database.list_tables(limit=30).tables) == {TABLE_NAME}

    table = database.open_table(TABLE_NAME)
    assert table.count_rows() == EXPECTED_SEED_COUNT
    assert SEARCH_COLUMN in table.schema.names
    assert "label_id" in table.schema.names
    assert "image_path" in table.schema.names
    assert "rights_note" in table.schema.names
    assert "provenance_id" in table.schema.names
    assert "rights_status" in table.schema.names
    assert "vector" not in table.schema.names
    indices = list(table.list_indices())
    assert any(index.index_type == "FTS" and index.columns == [SEARCH_COLUMN] for index in indices)

    results = catalog.search("", limit=30)
    assert len(results) == EXPECTED_SEED_COUNT
    assert [result["metadata"]["seed_order"] for result in results] == list(range(1, 31))
    assert results[0]["image_url"].endswith("ref-001-square-body-tee.svg")
    assert results[0]["image_path"].endswith("ref-001-square-body-tee.svg")
    assert results[0]["metadata"]["provenance"]["kind"] == "project-authored"
    assert results[0]["metadata"]["provenance"]["id"] == PROVENANCE_ID
    assert results[0]["metadata"]["provenance"]["rights_status"] == RIGHTS_STATUS
    assert "No scraped imagery" in results[0]["metadata"]["provenance"]["rights"]
    assert results[0]["metadata"]["label_association"]["id"] == "john-elliott"
    assert "Square Body White Tee" in results[0]["metadata"]["search_text"]


def test_fts_search_uses_composed_local_tags(tmp_path: Path) -> None:
    catalog = ReferenceCatalog(db_path=tmp_path / "reference-catalog.lancedb")
    catalog.build()

    boxy = catalog.search("boxy dropped shoulder", limit=5)
    quilted = catalog.search("quilted collarless", limit=5)
    bag = catalog.search("crescent sling", limit=5)

    assert boxy[0]["id"] == "ref-001-square-body-tee"
    assert quilted[0]["id"] == "ref-010-grid-stitch-liner"
    assert bag[0]["id"] == "ref-026-crescent-sling"
    assert all(result["image_url"].startswith("/reference-seeds/") for result in boxy)
    assert "tags" in boxy[0]["metadata"]


def test_search_filters_by_stable_studio_context(tmp_path: Path) -> None:
    catalog = ReferenceCatalog(db_path=tmp_path / "reference-catalog.lancedb")
    catalog.build()

    results = catalog.search(
        "",
        label_ids=["john-elliott", "vetements"],
        categories="t-shirts",
    )

    assert [result["id"] for result in results] == [
        "ref-001-square-body-tee",
        "ref-002-short-body-tee",
    ]
    assert {result["metadata"]["label_association"]["id"] for result in results} == {
        "john-elliott",
        "vetements",
    }

    high_top = catalog.search("", object_types="High-top shoe")
    assert [result["id"] for result in high_top] == ["ref-023-padded-high-top"]


def test_devday_john_elliott_context_finds_white_tee_and_distressed_bomber(
    tmp_path: Path,
) -> None:
    catalog = ReferenceCatalog(db_path=tmp_path / "reference-catalog.lancedb")
    catalog.build()

    john_elliott = catalog.search("", label_ids="john-elliott")
    white_tee = catalog.search("white tee", label_ids="john-elliott")
    bomber = catalog.search("distressed flight bomber", label_ids="john-elliott")

    assert [result["id"] for result in john_elliott] == [
        "ref-001-square-body-tee",
        "ref-011-cropped-flight-jacket",
    ]
    assert white_tee[0]["id"] == "ref-001-square-body-tee"
    assert bomber[0]["id"] == "ref-011-cropped-flight-jacket"
    assert "bomber" in bomber[0]["metadata"]["tags"]
    assert "flight bomber" in bomber[0]["metadata"]["search_text"]


@pytest.mark.parametrize("limit", [0, 31])
def test_search_rejects_limits_outside_the_30_item_contract(tmp_path: Path, limit: int) -> None:
    catalog = ReferenceCatalog(db_path=tmp_path / "reference-catalog.lancedb")
    catalog.build()

    with pytest.raises(ValueError, match="between 1 and 30"):
        catalog.search("tee", limit=limit)


def test_search_requires_a_built_catalog(tmp_path: Path) -> None:
    catalog = ReferenceCatalog(db_path=tmp_path / "not-built.lancedb")

    with pytest.raises(CatalogNotBuiltError, match="has not been built"):
        catalog.search("tee")
