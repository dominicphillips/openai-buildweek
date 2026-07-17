#!/usr/bin/env python3
"""Ask Gemini for a second opinion with explicit text-file context."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

MAX_CONTEXT_BYTES = 2_000_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--file", action="append", default=[], type=Path)
    parser.add_argument(
        "--model", default=os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_context(paths: list[Path]) -> str:
    documents: list[str] = []
    used = 0
    for path in paths:
        if not path.is_file():
            raise SystemExit(f"Context file does not exist: {path}")
        data = path.read_bytes()
        used += len(data)
        if used > MAX_CONTEXT_BYTES:
            raise SystemExit(f"Context exceeds {MAX_CONTEXT_BYTES} bytes")
        text = data.decode("utf-8")
        documents.append(f'<document path="{path}">\n{text}\n</document>')
    return "\n\n".join(documents)


def main() -> None:
    args = parse_args()
    context = load_context(args.file)
    resolved = {
        "model": args.model,
        "question": args.question,
        "files": [str(path) for path in args.file],
        "context_bytes": len(context.encode("utf-8")),
    }
    if args.dry_run:
        print(json.dumps(resolved, indent=2))
        return

    from google import genai

    client = genai.Client()
    prompt = (
        f"{context}\n\n<question>{args.question}</question>"
        if context
        else args.question
    )
    response = client.models.generate_content(model=args.model, contents=prompt)
    if not response.text:
        raise RuntimeError("Gemini returned no text")
    print(response.text)


if __name__ == "__main__":
    main()
