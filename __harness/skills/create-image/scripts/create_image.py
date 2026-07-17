#!/usr/bin/env python3
"""Generate or edit one image with OpenAI's Image API."""

from __future__ import annotations

import argparse
import base64
import json
import os
from contextlib import ExitStack
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", help="Concrete image generation or edit instruction")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reference", action="append", default=[], type=Path)
    parser.add_argument("--mask", type=Path)
    parser.add_argument("--model", default="gpt-image-2")
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument(
        "--quality", choices=("low", "medium", "high", "auto"), default="low"
    )
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
        "model": args.model,
        "prompt": args.prompt,
        "references": [str(path) for path in args.reference],
        "mask": str(args.mask) if args.mask else None,
        "size": args.size,
        "quality": args.quality,
        "format": args.format,
        "output": str(args.output),
    }


def main() -> None:
    args = parse_args()
    validate(args)
    resolved = plan(args)
    if args.dry_run:
        print(json.dumps(resolved, indent=2))
        return

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required")

    from openai import OpenAI

    client = OpenAI()
    common = {
        "model": args.model,
        "prompt": args.prompt,
        "size": args.size,
        "quality": args.quality,
        "output_format": args.format,
    }

    with ExitStack() as stack:
        if args.reference:
            images = [stack.enter_context(path.open("rb")) for path in args.reference]
            request = {**common, "image": images}
            if args.mask:
                request["mask"] = stack.enter_context(args.mask.open("rb"))
            result = client.images.edit(**request)
        else:
            result = client.images.generate(**common)

    encoded = result.data[0].b64_json
    if not encoded:
        raise RuntimeError("Image API returned no base64 image")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(base64.b64decode(encoded))
    print(
        json.dumps(
            {**resolved, "request_id": getattr(result, "_request_id", None)}, indent=2
        )
    )


if __name__ == "__main__":
    main()
