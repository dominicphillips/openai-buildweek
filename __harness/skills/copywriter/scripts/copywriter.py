#!/usr/bin/env python3
"""Draft grounded copy with the OpenAI Responses API."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

MODE_INSTRUCTIONS = {
    "ux": "Write concise interface copy. Preserve user agency and make actions unambiguous.",
    "marketing": "Write specific, restrained marketing copy without hype or unsupported claims.",
    "technical": "Write accurate technical prose that preserves identifiers, constraints, and qualifiers.",
    "editorial": "Write clear editorial prose with a human cadence and no invented facts.",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief")
    parser.add_argument("--mode", choices=tuple(MODE_INSTRUCTIONS), default="ux")
    parser.add_argument("--file", action="append", default=[], type=Path)
    parser.add_argument(
        "--model", default=os.environ.get("COPYWRITER_MODEL", "gpt-5.6-luna")
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sources: list[str] = []
    for path in args.file:
        if not path.is_file():
            raise SystemExit(f"Source file does not exist: {path}")
        sources.append(
            f'<source path="{path}">\n{path.read_text(encoding="utf-8")}\n</source>'
        )
    resolved = {
        "model": args.model,
        "mode": args.mode,
        "brief": args.brief,
        "files": [str(path) for path in args.file],
    }
    if args.dry_run:
        print(json.dumps(resolved, indent=2))
        return
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required")

    from openai import OpenAI

    instructions = (
        f"{MODE_INSTRUCTIONS[args.mode]} Use only supplied facts. "
        "Sound like a talented human editor. Do not imitate a named person or add rationale."
    )
    request = "\n\n".join([*sources, f"<brief>{args.brief}</brief>"])
    response = OpenAI().responses.create(
        model=args.model, instructions=instructions, input=request
    )
    if not response.output_text:
        raise RuntimeError("OpenAI returned no copy")
    print(response.output_text)


if __name__ == "__main__":
    main()
