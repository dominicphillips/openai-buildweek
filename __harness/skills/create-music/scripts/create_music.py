#!/usr/bin/env python3
"""Generate one music track with Replicate's Lyria model."""

from __future__ import annotations

import argparse
import json
import os
from contextlib import ExitStack
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--image", action="append", default=[], type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--model", default="google/lyria-3-pro")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prompt = (
        args.prompt_file.read_text(encoding="utf-8")
        if args.prompt_file
        else args.prompt
    )
    if not prompt or not prompt.strip():
        raise SystemExit("Prompt cannot be empty")
    for image in args.image:
        if not image.is_file():
            raise SystemExit(f"Image does not exist: {image}")

    resolved = {
        "model": args.model,
        "prompt": prompt.strip(),
        "images": [str(path) for path in args.image],
        "seed": args.seed,
        "output": str(args.output),
    }
    if args.dry_run:
        print(json.dumps(resolved, indent=2))
        return
    if not os.environ.get("REPLICATE_API_TOKEN"):
        raise SystemExit("REPLICATE_API_TOKEN is required")

    import replicate

    with ExitStack() as stack:
        payload: dict[str, object] = {"prompt": prompt.strip()}
        if args.image:
            payload["images"] = [
                stack.enter_context(path.open("rb")) for path in args.image
            ]
        if args.seed is not None:
            payload["seed"] = args.seed
        output = replicate.run(args.model, input=payload)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output.read())
    print(json.dumps({**resolved, "status": "saved"}, indent=2))


if __name__ == "__main__":
    main()
