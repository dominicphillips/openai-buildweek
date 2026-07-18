from __future__ import annotations

from pathlib import Path

from somethings_on.product_catalog import (
    EXPECTED_PRODUCT_COUNT,
    ProductCatalog,
    load_product_manifest,
)


def test_reviewed_product_manifest_is_complete() -> None:
    manifest = load_product_manifest()
    items = manifest["items"]

    assert len(items) == EXPECTED_PRODUCT_COUNT
    assert {item["seed_order"] for item in items} == set(range(1, 601))
    assert len({item["id"] for item in items}) == 600
    assert len({item["brand_id"] for item in items}) == 20
    assert {
        brand: sum(item["brand"] == brand for item in items)
        for brand in {item["brand"] for item in items}
    } == {brand: 30 for brand in {item["brand"] for item in items}}
    assert len({item["source_url"] for item in items}) == 600
    assert len({item["image_url"] for item in items}) == 600
    assert all(item["source_url"].startswith("https://") for item in items)
    assert all(item["image_url"].startswith("https://") for item in items)


def test_product_identity_metadata_matches_the_sourced_product_name() -> None:
    items = load_product_manifest()["items"]
    by_order = {item["seed_order"]: item for item in items}

    assert (by_order[242]["category"], by_order[242]["object_type"]) == (
        "shirts",
        "shirt",
    )
    assert (by_order[243]["category"], by_order[243]["object_type"]) == (
        "outerwear",
        "overshirt",
    )
    assert (by_order[333]["category"], by_order[333]["object_type"]) == (
        "bags",
        "bag",
    )
    assert (by_order[334]["category"], by_order[334]["object_type"]) == (
        "outerwear",
        "blazer",
    )
    assert (by_order[541]["category"], by_order[541]["object_type"]) == (
        "tops",
        "t-shirt",
    )
    assert (by_order[584]["category"], by_order[584]["object_type"]) == (
        "pants",
        "trousers",
    )
    assert all("READ MORE MATERIALS" not in item["product_name"].upper() for item in items)
    assert all("â" not in item["product_name"] for item in items)


def test_product_catalog_builds_browses_and_searches(tmp_path: Path) -> None:
    catalog = ProductCatalog(
        db_path=tmp_path / "products.lancedb",
        image_cache_path=tmp_path / "product-images",
    )

    assert catalog.build() == 600
    browse = catalog.search(limit=30)
    assert len(browse) == 30
    assert browse[0]["source_url"].startswith("https://")
    assert browse[0]["source_image_url"].startswith("https://")
    assert browse[0]["image_url"].startswith("/api/inspiration/images/")
    assert browse[0]["image_cached"] is False
    assert browse[0]["metadata"]["provenance"]["kind"] == "official-product"
    assert browse[0]["metadata"]["provenance"]["source_image_url"].startswith("https://")

    bombers = catalog.search("bomber", limit=30)
    assert bombers
    assert any("bomber" in item["product_name"].casefold() for item in bombers)

    jil = catalog.search(limit=30, brands="Jil Sander")
    assert len(jil) == 30
    assert all(item["brand"] == "Jil Sander" for item in jil)

    facets = catalog.facets()
    assert facets["total"] == 600
    assert {entry["value"]: entry["count"] for entry in facets["brands"]}["Jil Sander"] == 30
