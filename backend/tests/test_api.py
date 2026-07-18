from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest
from chatkit.server import NonStreamingResult
from fastapi.testclient import TestClient
from PIL import Image

from somethings_on.config import Settings
from somethings_on.image_service import ImageQuality
from somethings_on.main import create_app
from somethings_on.product_catalog import load_product_manifest
from somethings_on.product_image_cache import ProductImageCache


class FakeImageProvider:
    model = "fake-image"

    async def generate(
        self,
        prompt: str,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        del prompt, quality
        return make_png(64, 64)

    async def edit(
        self,
        prompt: str,
        reference_path: Path,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        del prompt, reference_path, quality
        return make_png(64, 64)


class RecordingRevisionProvider:
    model = "fake-image"

    def __init__(self) -> None:
        self.generate_calls: list[tuple[str, ImageQuality]] = []
        self.edit_calls: list[tuple[str, Path, bytes, ImageQuality]] = []

    async def generate(
        self,
        prompt: str,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        self.generate_calls.append((prompt, quality))
        return make_png(72, 96, "white")

    async def edit(
        self,
        prompt: str,
        reference_path: Path,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        self.edit_calls.append((prompt, reference_path, reference_path.read_bytes(), quality))
        return make_png(72, 96, "black")


def make_png(width: int = 80, height: int = 100, color: str = "white") -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), color).save(output, format="PNG")
    return output.getvalue()


def make_webp(width: int = 80, height: int = 100, color: str = "white") -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), color).save(output, format="WEBP", quality=80)
    return output.getvalue()


def write_product_cache(cache_root: Path) -> str:
    product = load_product_manifest()["items"][0]
    content = make_webp()
    cache_root.mkdir(parents=True)
    filename = f"{product['id']}.webp"
    (cache_root / filename).write_bytes(content)
    (cache_root / "index.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "items": [
                    {
                        "id": product["id"],
                        "filename": filename,
                        "source_image_url": product["image_url"],
                        "source_page_url": product["source_url"],
                        "media_type": "image/webp",
                        "width": 80,
                        "height": 100,
                        "byte_size": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return product["id"]


def test_inspiration_image_route_serves_only_reviewed_cached_images(tmp_path: Path) -> None:
    settings = Settings(
        SOMETHINGS_ON_DATABASE_PATH=tmp_path / "cache-route.sqlite3",
        SOMETHINGS_ON_ASSET_PATH=tmp_path / "assets",
    )
    product_id = write_product_cache(tmp_path / "product-images")
    app = create_app(settings, image_provider=FakeImageProvider())

    with TestClient(app) as client:
        app.state.product_catalog.image_cache = ProductImageCache(tmp_path / "product-images")
        response = client.get(f"/api/inspiration/images/{product_id}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert response.headers["cache-control"].endswith("immutable")
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["etag"].startswith('"')
        assert Image.open(io.BytesIO(response.content)).format == "WEBP"


def test_health_project_seed_and_safe_upload(tmp_path: Path) -> None:
    settings = Settings(
        OPENAI_API_KEY="test-key",
        SOMETHINGS_ON_CHATKIT_DOMAIN_KEY="test-domain-key",
        SOMETHINGS_ON_DATABASE_PATH=tmp_path / "test.sqlite3",
        SOMETHINGS_ON_ASSET_PATH=tmp_path / "assets",
    )
    app = create_app(settings, image_provider=FakeImageProvider())

    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["chatkit_ready"] is True
        assert health.json()["chatkit_domain_key"] == "test-domain-key"
        assert "test-key" not in health.text

        inspiration = client.get("/api/inspiration", params={"limit": 30})
        assert inspiration.status_code == 200
        products = inspiration.json()
        assert len(products) == 30
        assert all(product["source_url"].startswith("https://") for product in products)
        assert all(
            product["image_url"].startswith("/api/inspiration/images/") for product in products
        )
        assert all(product["source_image_url"].startswith("https://") for product in products)

        missing_product_image = client.get("/api/inspiration/images/not-a-catalog-product")
        assert missing_product_image.status_code == 404
        assert missing_product_image.json() == {"detail": "Product image not found"}

        facets = client.get("/api/inspiration/facets")
        assert facets.status_code == 200
        assert facets.json()["total"] == 600
        assert len(facets.json()["brands"]) == 20

        project = client.put(
            "/api/projects/look_001",
            json={
                "object_name": "white T-shirt",
                "taste_signals": [
                    {
                        "id": "acne-studios",
                        "name": "Acne Studios",
                        "tags": ["offbeat proportion", "denim"],
                    }
                ],
            },
        )
        assert project.status_code == 200
        assert project.json()["current_version"]["version_number"] == 1

        uploaded = client.post(
            "/api/projects/look_001/references",
            files={"file": ("reference.png", make_png(), "image/png")},
        )
        assert uploaded.status_code == 201
        asset = uploaded.json()
        assert asset["mime_type"] == "image/png"
        assert asset["width"] == 80
        assert asset["height"] == 100

        served = client.get(asset["url"])
        assert served.status_code == 200
        assert served.headers["content-type"] == "image/png"

        invalid = client.post(
            "/api/projects/look_001/references",
            files={"file": ("not-image.txt", b"not an image", "text/plain")},
        )
        assert invalid.status_code == 422


def test_health_is_offline_without_key(tmp_path: Path) -> None:
    settings = Settings(
        OPENAI_API_KEY="",
        SOMETHINGS_ON_DATABASE_PATH=tmp_path / "test.sqlite3",
        SOMETHINGS_ON_ASSET_PATH=tmp_path / "assets",
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").json()["chatkit_ready"] is False


def test_direct_version_endpoint_generates_v1_then_edits_exact_base_bytes(
    tmp_path: Path,
) -> None:
    settings = Settings(
        OPENAI_API_KEY="test-key",
        SOMETHINGS_ON_DATABASE_PATH=tmp_path / "test.sqlite3",
        SOMETHINGS_ON_ASSET_PATH=tmp_path / "assets",
    )
    provider = RecordingRevisionProvider()
    app = create_app(settings, image_provider=provider)

    with TestClient(app) as client:
        project = client.put(
            "/api/projects/revision_flow",
            json={
                "object_name": "Bomber jacket",
                "taste_signals": [
                    {
                        "id": "fabric-signal",
                        "name": "Fabric signal",
                        "tags": ["washed matte shell"],
                    }
                ],
            },
        )
        assert project.status_code == 200
        concept_id = project.json()["current_version"]["id"]

        generated = client.post(
            "/api/projects/revision_flow/versions",
            json={
                "requested_change": "Create a washed charcoal flight bomber",
                "preserve": ["full garment view"],
                "avoid": ["logos"],
            },
        )
        assert generated.status_code == 201
        first = generated.json()
        assert first["id"] == concept_id
        assert first["version_number"] == 1
        assert first["parent_version_id"] is None
        assert first["status"] == "ready"
        assert first["preserve"] == ["full garment view"]
        assert first["avoid"] == ["logos"]
        assert first["asset_url"]

        first_asset = client.get(first["asset_url"])
        assert first_asset.status_code == 200
        first_bytes_before_edit = first_asset.content

        edited = client.post(
            "/api/projects/revision_flow/versions",
            json={
                "requested_change": "Expose only the shoulder seam allowances",
                "preserve": ["flight volume", "washed charcoal shell"],
                "avoid": ["any other construction change"],
                "base_version_id": first["id"],
            },
        )
        assert edited.status_code == 201
        second = edited.json()
        assert second["version_number"] == 2
        assert second["parent_version_id"] == first["id"]
        assert second["status"] == "ready"
        assert second["asset_url"] != first["asset_url"]

        assert len(provider.generate_calls) == 1
        assert provider.generate_calls[0][1] == "medium"
        assert len(provider.edit_calls) == 1
        edit_prompt, reference_path, submitted_reference, edit_quality = provider.edit_calls[0]
        assert edit_quality == "medium"
        assert "Expose only the shoulder seam allowances" in edit_prompt
        assert submitted_reference == first_bytes_before_edit
        assert reference_path.read_bytes() == first_bytes_before_edit
        assert client.get(first["asset_url"]).content == first_bytes_before_edit
        assert client.get(second["asset_url"]).content != first_bytes_before_edit

        snapshot = client.get("/api/projects/revision_flow")
        assert snapshot.status_code == 200
        assert [version["id"] for version in snapshot.json()["versions"]] == [
            first["id"],
            second["id"],
        ]
        assert snapshot.json()["current_version"]["id"] == second["id"]


def test_direct_version_endpoint_maps_safe_validation_and_lineage_failures(
    tmp_path: Path,
) -> None:
    settings = Settings(
        OPENAI_API_KEY="test-key",
        SOMETHINGS_ON_DATABASE_PATH=tmp_path / "test.sqlite3",
        SOMETHINGS_ON_ASSET_PATH=tmp_path / "assets",
    )
    provider = RecordingRevisionProvider()
    app = create_app(settings, image_provider=provider)

    with TestClient(app) as client:
        missing_project = client.post(
            "/api/projects/missing/versions",
            json={"requested_change": "Create the first jacket"},
        )
        assert missing_project.status_code == 404
        assert missing_project.json()["detail"] == "Project not found"

        project = client.put(
            "/api/projects/lineage_failures",
            json={"object_name": "Bomber jacket"},
        ).json()
        concept_id = project["current_version"]["id"]

        assetless_base = client.post(
            "/api/projects/lineage_failures/versions",
            json={
                "requested_change": "Attempt an edit before generation",
                "base_version_id": concept_id,
            },
        )
        assert assetless_base.status_code == 409
        assert "no raster to edit" in assetless_base.json()["detail"]

        unknown_base = client.post(
            "/api/projects/lineage_failures/versions",
            json={
                "requested_change": "Attempt an unknown branch",
                "base_version_id": "ver_000000000000",
            },
        )
        assert unknown_base.status_code == 404
        assert unknown_base.json()["detail"] == "Design version not found"

        blank_change = client.post(
            "/api/projects/lineage_failures/versions",
            json={"requested_change": "   "},
        )
        assert blank_change.status_code == 422
        malformed_base = client.post(
            "/api/projects/lineage_failures/versions",
            json={
                "requested_change": "Attempt a malformed branch",
                "base_version_id": "not-a-version",
            },
        )
        assert malformed_base.status_code == 422
        extra_field = client.post(
            "/api/projects/lineage_failures/versions",
            json={"requested_change": "Create a jacket", "provider_key": "never-accepted"},
        )
        assert extra_field.status_code == 422

        generated = client.post(
            "/api/projects/lineage_failures/versions",
            json={"requested_change": "Create the first washed flight jacket"},
        )
        assert generated.status_code == 201
        first = generated.json()
        assert client.portal is not None

        async def resolve_first_asset() -> Path:
            return await client.app.state.image_service.resolve_asset(first["asset_id"])

        first_path = client.portal.call(resolve_first_asset)
        first_path.unlink()
        missing_raster = client.post(
            "/api/projects/lineage_failures/versions",
            json={
                "requested_change": "Attempt an edit without the stored raster",
                "base_version_id": first["id"],
            },
        )
        assert missing_raster.status_code == 409
        assert missing_raster.json()["detail"] == (
            "The selected design raster is unavailable. Choose another version."
        )
        assert provider.edit_calls == []


def test_direct_version_endpoint_reports_unconfigured_provider(tmp_path: Path) -> None:
    settings = Settings(
        OPENAI_API_KEY="",
        SOMETHINGS_ON_DATABASE_PATH=tmp_path / "offline.sqlite3",
        SOMETHINGS_ON_ASSET_PATH=tmp_path / "offline-assets",
    )
    with TestClient(create_app(settings)) as client:
        client.put(
            "/api/projects/offline_revision",
            json={"object_name": "T-shirt"},
        )
        response = client.post(
            "/api/projects/offline_revision/versions",
            json={"requested_change": "Create the first heavyweight jersey study"},
        )
        assert response.status_code == 503
        assert response.json()["detail"] == (
            "The studio is not connected yet. Start the image service and try again."
        )


def test_chatkit_base_version_is_validated_and_forwarded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        OPENAI_API_KEY="test-key",
        SOMETHINGS_ON_CHATKIT_DOMAIN_KEY="test-domain-key",
        SOMETHINGS_ON_DATABASE_PATH=tmp_path / "test.sqlite3",
        SOMETHINGS_ON_ASSET_PATH=tmp_path / "assets",
    )
    app = create_app(settings, image_provider=FakeImageProvider())

    with TestClient(app) as client:
        project_a = client.put(
            "/api/projects/look_a",
            json={"object_name": "white T-shirt"},
        ).json()
        project_b = client.put(
            "/api/projects/look_b",
            json={"object_name": "distressed bomber"},
        ).json()
        concept_a_id = project_a["current_version"]["id"]
        concept_b_id = project_b["current_version"]["id"]

        own_concept = client.post(
            f"/api/projects/look_a/chatkit?base_version_id={concept_a_id}",
            content=b"{}",
        )
        assert own_concept.status_code == 409
        assert "no raster to edit" in own_concept.json()["detail"]

        cross_project = client.post(
            f"/api/projects/look_b/chatkit?base_version_id={concept_a_id}",
            content=b"{}",
        )
        assert cross_project.status_code == 404
        assert cross_project.json()["detail"] == "Design version not found"

        unknown = client.post(
            "/api/projects/look_a/chatkit?base_version_id=ver_000000000000",
            content=b"{}",
        )
        assert unknown.status_code == 404
        malformed = client.post(
            "/api/projects/look_a/chatkit?base_version_id=not-a-version",
            content=b"{}",
        )
        assert malformed.status_code == 422

        async def create_ready_version():
            return await client.app.state.image_service.create_revision(
                project_id="look_a",
                requested_change="Create the first clean jersey study",
            )

        assert client.portal is not None
        ready = client.portal.call(create_ready_version)
        captured: dict[str, object] = {}

        async def capture_process(body: bytes, context: dict[str, object]):
            captured["body"] = body
            captured["context"] = context
            return NonStreamingResult(b'{"ok":true}')

        monkeypatch.setattr(client.app.state.chatkit_server, "process", capture_process)
        accepted = client.post(
            f"/api/projects/look_a/chatkit?base_version_id={ready.id}",
            content=b'{"type":"test"}',
            headers={"x-request-id": "request-123"},
        )
        assert accepted.status_code == 200
        assert accepted.json() == {"ok": True}
        assert captured == {
            "body": b'{"type":"test"}',
            "context": {
                "project_id": "look_a",
                "request_id": "request-123",
                "base_version_id": ready.id,
            },
        }

        captured.clear()
        accepted_from_stable_endpoint = client.post(
            "/api/projects/look_a/chatkit",
            content=b'{"type":"test"}',
            headers={
                "x-request-id": "request-456",
                "x-somethings-on-base-version-id": ready.id,
            },
        )
        assert accepted_from_stable_endpoint.status_code == 200
        assert accepted_from_stable_endpoint.json() == {"ok": True}
        assert captured == {
            "body": b'{"type":"test"}',
            "context": {
                "project_id": "look_a",
                "request_id": "request-456",
                "base_version_id": ready.id,
            },
        }

        malformed_header = client.post(
            "/api/projects/look_a/chatkit",
            content=b"{}",
            headers={"x-somethings-on-base-version-id": "not-a-version"},
        )
        assert malformed_header.status_code == 422

        conflicting_selection = client.post(
            f"/api/projects/look_a/chatkit?base_version_id={concept_b_id}",
            content=b"{}",
            headers={"x-somethings-on-base-version-id": ready.id},
        )
        assert conflicting_selection.status_code == 400
        assert conflicting_selection.json()["detail"] == "Conflicting design version selection"

        cross_project_ready = client.post(
            f"/api/projects/look_b/chatkit?base_version_id={ready.id}",
            content=b"{}",
        )
        assert cross_project_ready.status_code == 404
        assert concept_b_id != ready.id
