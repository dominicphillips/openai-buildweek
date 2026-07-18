#!/usr/bin/env python3
"""Build or verify the ignored local product-image cache.

The source manifest retains public product-page and source-image URLs. This script
creates resized WebP research copies under ``backend/data/product-images`` so the
browser never hotlinks third-party hosts during the local demo. Cached files remain
third-party, all-rights-reserved material: do not commit or redistribute them.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
SOURCE_ROOT = BACKEND_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from somethings_on.product_catalog import load_product_manifest  # noqa: E402
from somethings_on.product_image_cache import (  # noqa: E402
    CACHE_INDEX_FILENAME,
    CACHE_MEDIA_TYPE,
    CACHE_SCHEMA_VERSION,
    DEFAULT_PRODUCT_IMAGE_CACHE_PATH,
    PRODUCT_ID_PATTERN,
    load_cache_index,
    sha256_file,
)

DEFAULT_MAX_SOURCE_BYTES = 24 * 1024 * 1024
DEFAULT_MAX_EDGE = 1600
DEFAULT_QUALITY = 86
DEFAULT_CONCURRENCY = 10
REQUEST_TIMEOUT_SECONDS = 45.0
MAX_ATTEMPTS = 3
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 "
    "SOMETHINGS-ON-local-research-cache/1.0"
)


class CacheImportError(RuntimeError):
    """Safe, bounded error for one cache import."""


@dataclass(frozen=True, slots=True)
class ImportedImage:
    id: str
    filename: str
    source_image_url: str
    source_page_url: str
    media_type: str
    width: int
    height: int
    byte_size: int
    sha256: str
    cached_at: str


def _manifest_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _encode_webp(content: bytes, *, max_edge: int, quality: int) -> tuple[bytes, int, int]:
    if len(content) == 0:
        raise CacheImportError("source returned an empty body")
    try:
        with Image.open(io.BytesIO(content)) as source:
            source.load()
            image = ImageOps.exif_transpose(source)
            if image.width < 1 or image.height < 1:
                raise CacheImportError("source image has invalid dimensions")
            if image.width * image.height > 60_000_000:
                raise CacheImportError("source image exceeds the pixel limit")
            image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
            has_alpha = "A" in image.getbands() or "transparency" in image.info
            prepared = image.convert("RGBA" if has_alpha else "RGB")
            output = io.BytesIO()
            prepared.save(
                output,
                format="WEBP",
                quality=quality,
                method=6,
                exact=has_alpha,
            )
            return output.getvalue(), prepared.width, prepared.height
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as error:
        raise CacheImportError("source did not contain a supported raster image") from error


async def _download(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_source_bytes: int,
) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            async with client.stream("GET", url) as response:
                if response.status_code in {408, 425, 429} or response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        "retryable source response",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > max_source_bytes:
                    raise CacheImportError("source image exceeds the byte limit")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > max_source_bytes:
                        raise CacheImportError("source image exceeds the byte limit")
                return bytes(body)
        except CacheImportError:
            raise
        except (httpx.HTTPError, ValueError) as error:
            last_error = error
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(0.6 * attempt)
    raise CacheImportError("source image could not be fetched") from last_error


def _existing_item(record: Any) -> ImportedImage:
    return ImportedImage(
        id=record.product_id,
        filename=record.path.name,
        source_image_url=record.source_image_url,
        source_page_url=record.source_page_url,
        media_type=record.media_type,
        width=record.width,
        height=record.height,
        byte_size=record.byte_size,
        sha256=record.sha256,
        cached_at="retained",
    )


async def build_cache(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    cache_root = Path(args.output)
    manifest = load_product_manifest(manifest_path)
    manifest_items = manifest["items"]
    source_items = manifest_items[: args.limit] if args.limit else manifest_items
    selected_ids = {item["id"] for item in source_items}
    cache_root.mkdir(parents=True, exist_ok=True)

    try:
        existing = load_cache_index(cache_root)
    except Exception as error:
        if not args.refresh:
            raise CacheImportError(
                "existing cache index is invalid; use --refresh after inspecting it"
            ) from error
        existing = {}

    retained: dict[str, ImportedImage] = {}
    pending: list[dict[str, Any]] = []
    for item in manifest_items:
        record = existing.get(item["id"])
        current_record = (
            record is not None
            and record.source_image_url == item["image_url"]
            and record.source_page_url == item["source_url"]
        )
        selected = item["id"] in selected_ids
        if current_record and (not selected or not args.refresh):
            retained[item["id"]] = _existing_item(record)
        elif selected:
            pending.append(item)

    semaphore = asyncio.Semaphore(args.concurrency)
    timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS, connect=20.0)
    limits = httpx.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8",
    }

    completed = 0
    failures: dict[str, str] = {}

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=timeout,
        limits=limits,
    ) as client:

        async def import_one(item: dict[str, Any]) -> ImportedImage | None:
            nonlocal completed
            product_id = item["id"]
            if not PRODUCT_ID_PATTERN.fullmatch(product_id):
                failures[product_id] = "invalid product id"
                return None
            try:
                async with semaphore:
                    source = await _download(
                        client,
                        item["image_url"],
                        max_source_bytes=args.max_source_bytes,
                    )
                encoded, width, height = await asyncio.to_thread(
                    _encode_webp,
                    source,
                    max_edge=args.max_edge,
                    quality=args.quality,
                )
                digest = hashlib.sha256(encoded).hexdigest()
                filename = f"{product_id}.webp"
                destination = cache_root / filename
                temporary = cache_root / f".{product_id}.{os.getpid()}.tmp"
                temporary.write_bytes(encoded)
                os.replace(temporary, destination)
                return ImportedImage(
                    id=product_id,
                    filename=filename,
                    source_image_url=item["image_url"],
                    source_page_url=item["source_url"],
                    media_type=CACHE_MEDIA_TYPE,
                    width=width,
                    height=height,
                    byte_size=len(encoded),
                    sha256=digest,
                    cached_at=datetime.now(UTC).isoformat(),
                )
            except Exception as error:
                failures[product_id] = (
                    str(error) if isinstance(error, CacheImportError) else type(error).__name__
                )
                return None
            finally:
                completed += 1
                if completed % 25 == 0 or completed == len(pending):
                    print(f"Fetched {completed}/{len(pending)} pending images", flush=True)

        imported = await asyncio.gather(*(import_one(item) for item in pending))

    records = dict(retained)
    records.update({item.id: item for item in imported if item is not None})
    ordered = [records[item["id"]] for item in manifest_items if item["id"] in records]
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest_path": "backend/seeds/product_inspiration.json",
        "manifest_sha256": _manifest_digest(manifest_path),
        "transform": {
            "format": "webp",
            "max_edge": args.max_edge,
            "quality": args.quality,
        },
        "rights": {
            "status": "third-party-all-rights-reserved",
            "permission_verified": False,
            "runtime_only": True,
            "redistribution_permitted": False,
            "note": (
                "Private local research cache only. Source and product-page URLs are retained. "
                "Do not commit, publish, or redistribute these files without permission."
            ),
        },
        "items": [asdict(item) for item in ordered],
        "failures": [
            {"id": item["id"], "reason": failures[item["id"]]}
            for item in source_items
            if item["id"] in failures
        ],
    }
    temporary_index = cache_root / f".{CACHE_INDEX_FILENAME}.{os.getpid()}.tmp"
    temporary_index.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary_index, cache_root / CACHE_INDEX_FILENAME)

    total_bytes = sum(item.byte_size for item in ordered)
    print(
        f"Cache contains {len(ordered)}/{len(manifest_items)} images "
        f"({total_bytes / (1024 * 1024):.1f} MiB) at {cache_root}"
    )
    if failures:
        print(f"{len(failures)} images failed; rerun to retry only the missing records")
        return 1
    return 0


def verify_cache(args: argparse.Namespace) -> int:
    manifest = load_product_manifest(args.manifest)
    source_items = manifest["items"][: args.limit] if args.limit else manifest["items"]
    expected = {item["id"]: item for item in source_items}
    records = load_cache_index(args.output)
    failures: list[str] = []
    for product_id, item in expected.items():
        record = records.get(product_id)
        if record is None:
            failures.append(f"{product_id}: missing")
            continue
        if record.source_image_url != item["image_url"]:
            failures.append(f"{product_id}: source image URL changed")
        if record.source_page_url != item["source_url"]:
            failures.append(f"{product_id}: source page URL changed")
        if sha256_file(record.path) != record.sha256:
            failures.append(f"{product_id}: SHA-256 mismatch")
    if failures:
        print("Cache verification failed:")
        for failure in failures[:25]:
            print(f"- {failure}")
        if len(failures) > 25:
            print(f"- …and {len(failures) - 25} more")
        return 1
    total_bytes = sum(records[product_id].byte_size for product_id in expected)
    print(f"Verified {len(expected)} cached images ({total_bytes / (1024 * 1024):.1f} MiB)")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=BACKEND_ROOT / "seeds" / "product_inspiration.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_PRODUCT_IMAGE_CACHE_PATH,
    )
    parser.add_argument("--verify", action="store_true", help="Check files and hashes offline")
    parser.add_argument("--refresh", action="store_true", help="Redownload selected images")
    parser.add_argument("--limit", type=int, default=0, help="Process only the first N records")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--max-edge", type=int, default=DEFAULT_MAX_EDGE)
    parser.add_argument("--quality", type=int, default=DEFAULT_QUALITY)
    parser.add_argument("--max-source-bytes", type=int, default=DEFAULT_MAX_SOURCE_BYTES)
    args = parser.parse_args()
    if args.limit < 0 or args.limit > 600:
        parser.error("--limit must be between 0 and 600")
    if not 1 <= args.concurrency <= 32:
        parser.error("--concurrency must be between 1 and 32")
    if not 256 <= args.max_edge <= 3000:
        parser.error("--max-edge must be between 256 and 3000")
    if not 1 <= args.quality <= 100:
        parser.error("--quality must be between 1 and 100")
    if not 1024 <= args.max_source_bytes <= 100 * 1024 * 1024:
        parser.error("--max-source-bytes must be between 1 KiB and 100 MiB")
    return args


def main() -> int:
    args = parse_args()
    if args.verify:
        return verify_cache(args)
    return asyncio.run(build_cache(args))


if __name__ == "__main__":
    raise SystemExit(main())
