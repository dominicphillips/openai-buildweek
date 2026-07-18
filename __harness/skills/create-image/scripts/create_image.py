#!/usr/bin/env python3
"""Generate or edit one image with OpenAI's Image API."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from contextlib import ExitStack
from pathlib import Path
from typing import NoReturn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", help="Concrete image generation or edit instruction")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reference", action="append", default=[], type=Path)
    parser.add_argument("--mask", type=Path)
    parser.add_argument("--model", default="gpt-image-2")
    parser.add_argument("--size", default="1024x1536")
    parser.add_argument("--quality", choices=("low", "medium", "high", "auto"), default="medium")
    parser.add_argument("--format", choices=("png", "jpeg", "webp"), default="png")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def validate(args: argparse.Namespace) -> None:
    if args.mask and not args.reference:
        raise SystemExit("--mask requires at least one --reference")
    for source in [*args.reference, *([args.mask] if args.mask else [])]:
        if source and not source.is_file():
            raise SystemExit(f"Input does not exist: {source}")
    if args.output.suffix.lower() not in {
        f".{args.format}",
        ".jpg" if args.format == "jpeg" else f".{args.format}",
    }:
        raise SystemExit(f"Output suffix must match --format {args.format}")


def plan(args: argparse.Namespace) -> dict[str, object]:
    return {
        "operation": "edit" if args.reference else "generate",
        "provider": "openai",
        "model": args.model,
        "prompt": args.prompt,
        "references": [str(path) for path in args.reference],
        "mask": str(args.mask) if args.mask else None,
        "size": args.size,
        "quality": args.quality,
        "format": args.format,
        "output": str(args.output),
    }


def fail(
    resolved: dict[str, object],
    *,
    error_code: str,
    message: str,
    http_status: int | None = None,
) -> NoReturn:
    raise SystemExit(
        json.dumps(
            {
                **resolved,
                "status": "failed",
                "error_code": error_code,
                "http_status": http_status,
                "message": message,
            },
            indent=2,
        )
    )


def main() -> None:
    args = parse_args()
    validate(args)
    resolved = plan(args)
    if args.dry_run:
        print(json.dumps(resolved, indent=2))
        return

    common = {
        "model": args.model,
        "prompt": args.prompt,
        "size": args.size,
        "quality": args.quality,
        "output_format": args.format,
    }

    from openai import APIConnectionError, APIStatusError, APITimeoutError

    try:
        result, request_id = run_openai(args, common)
    except APIStatusError as error:
        fail(
            resolved,
            error_code=error.code or error.type or f"http_{error.status_code}",
            message=status_message(error),
            http_status=error.status_code,
        )
    except APITimeoutError:
        fail(resolved, error_code="timeout", message="The Images API request timed out.")
    except APIConnectionError as error:
        fail(resolved, error_code="connection_error", message=str(error))

    data = getattr(result, "data", None)
    encoded = data[0].b64_json if data else None
    if not encoded:
        fail(
            resolved,
            error_code="empty_response",
            message="The Images API returned no image data.",
        )
    try:
        content = base64.b64decode(encoded, validate=True)
    except ValueError:
        fail(
            resolved,
            error_code="invalid_image_data",
            message="The Images API returned invalid base64 image data.",
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(content)
    record = {
        **resolved,
        "status": "succeeded",
        "request_id": request_id,
        "sha256": hashlib.sha256(content).hexdigest(),
        "response": summarize_response(result),
    }
    sidecar = args.output.with_name(f"{args.output.name}.json")
    sidecar.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({**record, "provenance": str(sidecar)}, indent=2))


def status_message(error: object) -> str:
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        inner = body.get("error")
        details = inner if isinstance(inner, dict) else body
        message = details.get("message")
        if isinstance(message, str) and message:
            return message
    return str(getattr(error, "message", error))


def run_openai(args: argparse.Namespace, common: dict[str, str]) -> tuple[object, str | None]:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required")

    from openai import OpenAI

    client = OpenAI()
    with ExitStack() as stack:
        if args.reference:
            images = [stack.enter_context(path.open("rb")) for path in args.reference]
            request = {**common, "image": images}
            if args.mask:
                request["mask"] = stack.enter_context(args.mask.open("rb"))
            result = client.images.edit(**request)
        else:
            result = client.images.generate(**common)
    return result, getattr(result, "_request_id", None)


def summarize_response(result: object) -> dict[str, object]:
    usage = getattr(result, "usage", None)
    return {
        "created": getattr(result, "created", None),
        "size": getattr(result, "size", None),
        "quality": getattr(result, "quality", None),
        "output_format": getattr(result, "output_format", None),
        "usage": usage.model_dump(exclude_none=True) if usage is not None else None,
    }


if __name__ == "__main__":
    main()
