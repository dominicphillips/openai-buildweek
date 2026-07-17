from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from somethings_on.config import Settings
from somethings_on.image_service import ImageQuality
from somethings_on.main import create_app


class FakeImageProvider:
    model = "fake-image"

    async def create(
        self,
        prompt: str,
        reference_path: Path | None = None,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        del prompt, reference_path, quality
        output = io.BytesIO()
        Image.new("RGB", (64, 64), "white").save(output, format="PNG")
        return output.getvalue()


def make_png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (80, 100), "white").save(output, format="PNG")
    return output.getvalue()


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
