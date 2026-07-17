#!/usr/bin/env python3
"""Run a read-only Claude CLI review."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt")
    parser.add_argument("--mode", choices=("ask", "plan"), default="ask")
    parser.add_argument("--dir", type=Path, default=Path.cwd())
    parser.add_argument("--model", default="opus")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workdir = args.dir.resolve()
    if not workdir.is_dir():
        raise SystemExit(f"Directory does not exist: {workdir}")
    prefix = (
        "Return a read-only implementation plan."
        if args.mode == "plan"
        else "Answer read-only."
    )
    command = [
        "claude",
        "-p",
        f"{prefix}\n\n{args.prompt}",
        "--model",
        args.model,
        "--permission-mode",
        "plan",
        "--output-format",
        "text",
    ]
    if args.dry_run:
        print(json.dumps({"cwd": str(workdir), "command": command}, indent=2))
        return
    if not shutil.which("claude"):
        raise SystemExit("The claude CLI is not installed or not on PATH")
    completed = subprocess.run(command, cwd=workdir, check=True, text=True)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
