from __future__ import annotations

import base64
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from somethings_on.image_service import (
    GarmentPreservationAssessment,
    OpenAIImageProvider,
)


class FakeImagesResource:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def generate(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(("generate", kwargs))
        return self._response(kwargs.get("n", 1))

    async def edit(self, **kwargs: Any) -> SimpleNamespace:
        image = kwargs.pop("image")
        count = kwargs.get("n", 1)
        self.calls.append(
            (
                "edit",
                {
                    **kwargs,
                    "image_name": Path(image.name).name,
                },
            )
        )
        return self._response(count)

    @staticmethod
    def _response(count: int) -> SimpleNamespace:
        contents = (
            [b"rendered-image"]
            if count == 1
            else [f"rendered-image-{index}".encode() for index in range(1, count + 1)]
        )
        return SimpleNamespace(
            data=[
                SimpleNamespace(b64_json=base64.b64encode(content).decode("ascii"))
                for content in contents
            ]
        )


class FakeResponsesResource:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def parse(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        parsed = GarmentPreservationAssessment(
            preserves_garment=True,
            changed_or_hidden_details=[],
            summary="The design details remain visible and unchanged.",
        )
        return SimpleNamespace(
            output=[
                SimpleNamespace(
                    type="message",
                    content=[SimpleNamespace(type="output_text", parsed=parsed)],
                )
            ]
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.images = FakeImagesResource()
        self.responses = FakeResponsesResource()


@pytest.mark.asyncio
async def test_openai_image_provider_forwards_explicit_render_quality(tmp_path: Path) -> None:
    provider = OpenAIImageProvider("test-key")
    fake_client = FakeOpenAIClient()
    provider.client = fake_client  # type: ignore[assignment]
    reference = tmp_path / "canonical.png"
    reference.write_bytes(b"canonical-image")

    draft = await provider.generate("draft", quality="low")
    presentation = await provider.edit("lookbook", reference, quality="medium")

    assert draft == b"rendered-image"
    assert presentation == b"rendered-image"
    assert fake_client.images.calls == [
        (
            "generate",
            {
                "model": "gpt-image-2",
                "prompt": "draft",
                "size": "1024x1536",
                "quality": "low",
            },
        ),
        (
            "edit",
            {
                "model": "gpt-image-2",
                "prompt": "lookbook",
                "size": "1024x1536",
                "quality": "medium",
                "image_name": "canonical.png",
            },
        ),
    ]


@pytest.mark.asyncio
async def test_openai_image_provider_requests_each_four_candidate_set_once(
    tmp_path: Path,
) -> None:
    provider = OpenAIImageProvider("test-key")
    fake_client = FakeOpenAIClient()
    provider.client = fake_client  # type: ignore[assignment]
    reference = tmp_path / "canonical.png"
    reference.write_bytes(b"canonical-image")

    generated = await provider.generate_candidates("first set", count=4, quality="medium")
    edited = await provider.edit_candidates(
        "edit set",
        reference,
        count=4,
        quality="medium",
    )

    assert generated == [f"rendered-image-{index}".encode() for index in range(1, 5)]
    assert edited == [f"rendered-image-{index}".encode() for index in range(1, 5)]
    assert fake_client.images.calls == [
        (
            "generate",
            {
                "model": "gpt-image-2",
                "prompt": "first set",
                "size": "1024x1536",
                "quality": "medium",
                "n": 4,
            },
        ),
        (
            "edit",
            {
                "model": "gpt-image-2",
                "prompt": "edit set",
                "size": "1024x1536",
                "quality": "medium",
                "n": 4,
                "image_name": "canonical.png",
            },
        ),
    ]


@pytest.mark.asyncio
async def test_openai_preservation_review_uses_two_images_and_structured_output(
    tmp_path: Path,
) -> None:
    provider = OpenAIImageProvider("test-key", assessment_model="gpt-5.6")
    fake_client = FakeOpenAIClient()
    provider.client = fake_client  # type: ignore[assignment]
    canonical = tmp_path / "canonical.png"
    canonical.write_bytes(b"canonical-image")

    assessment = await provider.assess_preservation(
        canonical_path=canonical,
        presentation_content=b"presentation-image",
    )

    assert assessment.preserves_garment is True
    assert len(fake_client.responses.calls) == 1
    request = fake_client.responses.calls[0]
    assert request["model"] == "gpt-5.6"
    assert request["store"] is False
    assert request["text_format"] is GarmentPreservationAssessment
    assert "Do not use pixel similarity" in request["instructions"]
    content = request["input"][0]["content"]
    image_inputs = [item for item in content if item["type"] == "input_image"]
    assert len(image_inputs) == 2
    assert [item["detail"] for item in image_inputs] == ["high", "high"]
    assert image_inputs[0]["image_url"] == (
        "data:image/png;base64," + base64.b64encode(b"canonical-image").decode("ascii")
    )
    assert image_inputs[1]["image_url"] == (
        "data:image/png;base64," + base64.b64encode(b"presentation-image").decode("ascii")
    )
