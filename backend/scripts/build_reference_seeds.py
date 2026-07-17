#!/usr/bin/env python3
"""Rebuild project-authored reference SVGs and the local LanceDB catalog."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from somethings_on.reference_catalog import (
    DEFAULT_DB_PATH,
    DEFAULT_MANIFEST_PATH,
    ReferenceCatalog,
    load_reference_manifest,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
DEFAULT_ASSET_DIR = REPOSITORY_ROOT / "app" / "public" / "reference-seeds"


def render_reference_svg(item: dict[str, Any]) -> str:
    """Render one deterministic, monochrome outline study."""

    illustration = item["illustration"]
    template = illustration["template"]
    variant = illustration["variant"]
    try:
        artwork = _RENDERERS[template](variant)
    except KeyError as exc:
        raise ValueError(f"Unknown illustration template: {template}") from exc

    title = escape(item["title"])
    alt = escape(item["image_alt"])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 360"
  role="img" aria-labelledby="title desc">
  <title id="title">{title}</title>
  <desc id="desc">{alt}. Project-authored outline study.</desc>
  <rect width="480" height="360" fill="#0a0a09"/>
  <path d="M24 52H456M24 316H456" fill="none" stroke="#3b3b38" stroke-width="1"/>
  <g fill="none" stroke="#f1efe9" stroke-width="2.5"
    stroke-linecap="round" stroke-linejoin="round">
{artwork}
  </g>
  <g fill="none" stroke="#969590" stroke-width="1" stroke-linecap="square">
    <path d="M24 28H68M24 34H44"/>
    <path d="M412 330H456M436 336H456"/>
  </g>
</svg>
"""


def write_reference_svgs(
    manifest: dict[str, Any],
    asset_dir: Path,
    *,
    check: bool = False,
) -> int:
    """Write or verify the 30 deterministic SVG assets."""

    expected = {
        Path(item["image_url"]).name: render_reference_svg(item) for item in manifest["items"]
    }
    if len(expected) != 30:
        raise ValueError("The asset build must resolve to exactly 30 unique SVG filenames")

    if check:
        errors: list[str] = []
        existing = {path.name for path in asset_dir.glob("*.svg")} if asset_dir.is_dir() else set()
        for filename, content in expected.items():
            path = asset_dir / filename
            if not path.is_file():
                errors.append(f"missing {filename}")
            elif path.read_text(encoding="utf-8") != content:
                errors.append(f"out of date {filename}")
        for filename in sorted(existing - expected.keys()):
            errors.append(f"unexpected {filename}")
        if errors:
            raise RuntimeError("Reference SVG check failed: " + "; ".join(errors))
        return len(expected)

    asset_dir.mkdir(parents=True, exist_ok=True)
    unexpected = sorted(path.name for path in asset_dir.glob("*.svg") if path.name not in expected)
    if unexpected:
        raise RuntimeError(
            "Refusing to overwrite a directory with unexpected SVGs: " + ", ".join(unexpected)
        )
    for filename, content in expected.items():
        path = asset_dir / filename
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
    return len(expected)


def _render_tshirt(variant: int) -> str:
    parameters = [
        (174, 306, 113, 179, 92),
        (164, 268, 104, 169, 92),
        (184, 316, 130, 172, 88),
        (168, 304, 106, 194, 92),
        (176, 298, 126, 204, 86),
    ]
    try:
        body_left, hem_y, sleeve_x, sleeve_y, shoulder_y = parameters[variant]
    except IndexError as exc:
        raise ValueError(f"Unsupported T-shirt illustration variant: {variant}") from exc
    body_right = 480 - body_left
    right_sleeve_x = 480 - sleeve_x
    collar_y = 104 if variant != 4 else 92
    raised_neck = '    <path d="M220 91V76H260V91" stroke="#85847f"/>\n' if variant == 4 else ""
    vents = (
        f'    <path d="M{body_left} {hem_y - 28}V{hem_y}H{body_left + 18}" stroke="#85847f"/>\n'
        if variant == 3
        else ""
    )
    return (
        f'    <path d="M204 {shoulder_y}L{body_left} {shoulder_y + 12} '
        f"L{sleeve_x} 132L{sleeve_x + 26} {sleeve_y}L{body_left} {sleeve_y - 12} "
        f"V{hem_y}H{body_right}V{sleeve_y - 12}L{right_sleeve_x - 26} {sleeve_y} "
        f'L{right_sleeve_x} 132L{body_right} {shoulder_y + 12}L276 {shoulder_y}"/>\n'
        f'    <path d="M212 {shoulder_y + 2}Q240 {collar_y + 30} 268 '
        f'{shoulder_y + 2}" stroke="#85847f"/>\n'
        f'    <path d="M{body_left + 12} {hem_y - 10}H{body_right - 12}" '
        'stroke="#85847f"/>\n'
        f"{raised_neck}{vents}"
    )


def _render_outerwear(variant: int) -> str:
    drawings = [
        """    <path d="M196 86L166 100 118 137 145 190 170 175V306H310V175L335 190
      362 137 314 100 284 86Z"/>
    <path d="M220 88L204 123 240 144 276 123 260 88M240 144V304" stroke="#85847f"/>
    <path d="M188 164H226V205H188ZM254 164H292V205H254Z" stroke="#85847f"/>
    <path d="M188 230H226V282H188ZM254 230H292V282H254Z" stroke="#85847f"/>""",
        """    <path d="M198 92Q162 97 142 125L112 192 153 210 174 169 167 286
      Q240 314 313 286L306 169 327 210 368 192 338 125Q318 97 282 92Z"/>
    <path d="M212 94Q240 125 268 94M240 124V287M174 270Q240 288 306 270"
      stroke="#85847f"/>
    <path d="M148 151Q170 170 174 201M332 151Q310 170 306 201" stroke="#85847f"/>""",
        """    <path d="M202 101Q204 67 240 66Q276 67 278 101L310 116 350 161
      319 194 306 174V315H174V174L161 194 130 161 170 116Z"/>
    <path d="M202 101Q240 124 278 101M240 118V314M176 214H304" stroke="#85847f"/>
    <path d="M190 176L218 192 200 235M290 176L262 192 280 235" stroke="#85847f"/>""",
        """    <path d="M202 82L172 98 124 140 151 187 174 174V304
      Q240 316 306 304V174L329 187 356 140 308 98 278 82Z"/>
    <path d="M202 84L240 122 278 84M240 122V309M184 151H231V207H184"
      stroke="#85847f"/>
    <path d="M178 281Q240 295 302 281" stroke="#85847f"/>""",
        """    <path d="M202 91L170 103 121 144 151 190 174 175V300
      Q240 314 306 300V175L329 190 359 144 310 103 278 91Z"/>
    <path d="M220 93Q240 117 260 93M240 117V306" stroke="#85847f"/>
    <path d="M175 152H305M175 190H305M175 228H305M175 266H305
      M207 102V306M273 102V306" stroke="#5f5f5b" stroke-width="1.5"/>""",
        """    <path d="M197 91Q164 97 141 124L112 178 151 199 175 159
      169 257Q240 279 311 257L305 159 329 199 368 178 339 124Q316 97 283 91Z"/>
    <path d="M211 93L240 124 269 93M240 124V265M172 238Q240 254 308 238"
      stroke="#85847f"/>
    <path d="M318 144H339V184H316" stroke="#85847f"/>""",
    ]
    try:
        return drawings[variant]
    except IndexError as exc:
        raise ValueError(f"Unsupported outerwear illustration variant: {variant}") from exc


def _render_pants(variant: int) -> str:
    drawings = [
        """    <path d="M178 78H302L310 116 296 312H242L240 157 238 312H184
      L170 116Z"/>
    <path d="M184 96H296M213 112L232 250M267 112L248 250" stroke="#85847f"/>
    <path d="M174 116Q240 128 306 116" stroke="#85847f"/>""",
        """    <path d="M178 78H302L312 115 292 312H248L240 164 232 312H188
      L168 115Z"/>
    <path d="M177 181H222V237H180M303 181H258V237H300" stroke="#85847f"/>
    <path d="M184 243L226 261M296 243L254 261M180 299H231M249 299H300"
      stroke="#85847f"/>""",
        """    <path d="M180 78H300L310 112Q325 205 291 312H247L240 165
      233 312H189Q155 205 170 112Z"/>
    <path d="M184 107Q155 197 203 299M296 107Q325 197 277 299" stroke="#85847f"/>
    <path d="M184 111Q203 133 222 110M296 111Q277 133 258 110" stroke="#85847f"/>""",
        """    <path d="M178 84Q240 70 302 84L308 116 292 312H247L240 158
      233 312H188L172 116Z"/>
    <path d="M183 99H297M225 84Q240 103 255 84M233 84L225 124M247 84L255 124"
      stroke="#85847f"/>
    <path d="M177 118Q240 130 303 118" stroke="#85847f"/>""",
        """    <path d="M176 78H304L310 114 292 312H247L240 160 233 312H188
      L170 114Z"/>
    <path d="M180 105L244 129 224 229 245 302M300 105L258 121 274 219 250 292"
      stroke="#85847f"/>
    <path d="M184 126L218 113M296 126L262 113" stroke="#85847f"/>""",
    ]
    try:
        return drawings[variant]
    except IndexError as exc:
        raise ValueError(f"Unsupported pants illustration variant: {variant}") from exc


def _render_shorts(variant: int) -> str:
    drawings = [
        """    <path d="M176 78H304L312 116 288 283H246L240 160 234 283H192
      L168 116Z"/>
    <path d="M184 99H296M210 115L226 248M270 115L254 248" stroke="#85847f"/>
    <path d="M190 263H233M247 263H290" stroke="#85847f"/>""",
        """    <path d="M174 84Q240 70 306 84L312 116 302 245H248L240 154
      232 245H178L168 116Z"/>
    <path d="M181 99H299M224 83L218 119M256 83L262 119" stroke="#85847f"/>
    <path d="M178 218L169 237M302 218L311 237" stroke="#85847f"/>""",
        """    <path d="M176 78H304L312 116 295 270H247L240 158 233 270H185
      L168 116Z"/>
    <path d="M176 151H225V218H180M304 151H255V218H300" stroke="#85847f"/>
    <path d="M225 158L240 181 255 158M181 113Q240 125 299 113" stroke="#85847f"/>""",
    ]
    try:
        return drawings[variant]
    except IndexError as exc:
        raise ValueError(f"Unsupported shorts illustration variant: {variant}") from exc


def _render_footwear(variant: int) -> str:
    drawings = [
        """    <path d="M92 235Q137 213 176 163H273Q299 194 334 210L390 226
      Q405 234 395 254H102Q83 251 92 235Z"/>
    <path d="M98 238Q240 250 396 237M193 174L267 203M204 162L279 192"
      stroke="#85847f"/>
    <path d="M218 171L205 192M237 177L224 199M256 184L243 205" stroke="#85847f"/>""",
        """    <path d="M86 233Q123 211 162 161L255 151 301 190 350 205 399 229
      388 259H101Q78 251 86 233Z"/>
    <path d="M100 224L151 206 191 174 249 169 283 201 337 217 377 239"
      stroke="#85847f"/>
    <path d="M91 247L112 261 133 247 154 261 175 247 196 261 217 247 238 261
      259 247 280 261 301 247 322 261 343 247 364 261 388 247" stroke="#85847f"/>
    <path d="M195 173L264 204M211 165L279 195" stroke="#85847f"/>""",
        """    <path d="M112 225Q158 207 191 163H287Q310 190 340 209L389 228
      Q401 239 390 254H118Q99 248 112 225Z"/>
    <path d="M191 163L179 218M105 237Q236 247 394 237M245 165Q260 196 293 211"
      stroke="#85847f"/>""",
        """    <path d="M94 236Q138 215 178 174L188 100H276L293 183Q313 201 344 211
      L397 229Q407 239 395 257H104Q85 252 94 236Z"/>
    <path d="M188 108L273 177M188 139L284 198M102 240Q245 250 401 239"
      stroke="#85847f"/>
    <path d="M216 127L204 150M237 144L225 168M258 161L246 185" stroke="#85847f"/>""",
        """    <path d="M111 226Q159 210 202 191H292Q332 205 381 226L393 248
      Q250 261 103 248Z"/>
    <path d="M160 213Q189 160 232 183L288 225M224 197Q260 151 305 202L331 226"
      stroke="#85847f"/>
    <path d="M109 238Q245 247 388 238" stroke="#85847f"/>""",
    ]
    try:
        return drawings[variant]
    except IndexError as exc:
        raise ValueError(f"Unsupported footwear illustration variant: {variant}") from exc


def _render_bag(variant: int) -> str:
    drawings = [
        """    <path d="M140 141H340L358 299H122Z"/>
    <path d="M181 201V104Q240 68 299 104V201M181 141V299M299 141V299"
      stroke="#85847f"/>
    <path d="M206 213H274V267H206" stroke="#85847f"/>""",
        """    <path d="M120 216Q240 124 360 216L328 284Q240 311 152 284Z"/>
    <path d="M133 215Q240 189 347 215M167 259Q240 281 313 259" stroke="#85847f"/>
    <path d="M153 211Q178 97 297 89Q352 87 372 129" stroke="#85847f"/>""",
        """    <path d="M163 119L185 82H295L317 119V301H163Z"/>
    <path d="M164 143H316L290 101H190ZM240 143V282M212 142V231H268V142"
      stroke="#85847f"/>
    <path d="M205 177Q165 193 147 259M275 177Q315 193 333 259" stroke="#85847f"/>""",
    ]
    try:
        return drawings[variant]
    except IndexError as exc:
        raise ValueError(f"Unsupported bag illustration variant: {variant}") from exc


def _render_headwear(variant: int) -> str:
    drawings = [
        """    <path d="M127 224Q135 125 232 111 311 104 343 173L352 211
      Q273 197 206 220 165 235 127 224Z"/>
    <path d="M352 211Q403 207 420 231 351 244 286 230"/>
    <path d="M232 111L240 203M167 135Q215 154 240 203M303 125Q267 158 240 203"
      stroke="#85847f"/>""",
        """    <path d="M168 116Q240 78 312 116L334 225H146Z"/>
    <path d="M146 213Q95 231 77 263 240 295 403 263 385 231 334 213"/>
    <path d="M168 116Q240 142 312 116M102 251Q240 274 378 251M127 232Q240 255 353 232"
      stroke="#85847f"/>""",
        """    <path d="M157 228Q162 104 240 78 318 104 323 228Z"/>
    <path d="M147 220H333V278H147Z"/>
    <path d="M180 220V109M210 220V86M240 220V78M270 220V86M300 220V109
      M168 244H312M168 263H312" stroke="#85847f"/>""",
    ]
    try:
        return drawings[variant]
    except IndexError as exc:
        raise ValueError(f"Unsupported headwear illustration variant: {variant}") from exc


_RENDERERS: dict[str, Callable[[int], str]] = {
    "tshirt": _render_tshirt,
    "outerwear": _render_outerwear,
    "pants": _render_pants,
    "shorts": _render_shorts,
    "footwear": _render_footwear,
    "bag": _render_bag,
    "headwear": _render_headwear,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--asset-dir", type=Path, default=DEFAULT_ASSET_DIR)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Generate source SVGs without rebuilding the ignored runtime LanceDB artifact.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify committed SVGs match the deterministic renderer; never write files or a DB.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = load_reference_manifest(args.manifest)
    asset_count = write_reference_svgs(manifest, args.asset_dir, check=args.check)

    if args.check:
        print(f"Verified {asset_count} deterministic reference SVGs")
        return

    if args.skip_db:
        print(f"Wrote {asset_count} reference SVGs; skipped LanceDB build")
        return

    summary = ReferenceCatalog(db_path=args.db_path, manifest_path=args.manifest).build()
    print(
        f"Wrote {asset_count} reference SVGs and {summary.row_count} "
        f"rows to {summary.table_name!r} at {summary.db_path}"
    )


if __name__ == "__main__":
    main()
