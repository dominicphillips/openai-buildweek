#!/usr/bin/env python3
"""Normalize product identity metadata in the 600-item inspiration catalog.

The source manifests contain reviewed URLs and rights/provenance fields, but some
rows inherited the category template used by a nearby sitemap result.  This
script classifies each row from its displayed product identity, replaces only
the identity/search metadata, and proves that source lineage and reviewed
materials/palette data did not move.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFESTS = (
    REPOSITORY_ROOT / "__grounding" / "INSPIRATION_PRODUCTS_600.json",
    REPOSITORY_ROOT / "backend" / "seeds" / "product_inspiration.json",
)
EXPECTED_ITEMS = 600
EXPECTED_BRANDS = 20
PRODUCTS_PER_BRAND = 30

NORMALIZED_FIELDS = {
    "product_name",
    "title",
    "category",
    "object_type",
    "description",
    "image_alt",
    "neutral_attributes",
    "silhouette",
    "tags",
}


@dataclass(frozen=True)
class IdentitySpec:
    category: str
    attributes: tuple[str, str, str]
    silhouette: str


def spec(category: str, attributes: tuple[str, str, str], silhouette: str) -> IdentitySpec:
    return IdentitySpec(category, attributes, silhouette)


IDENTITY_SPECS: dict[str, IdentitySpec] = {
    "fragrance": spec(
        "fragrance",
        ("bottle geometry", "material contrast", "closure design"),
        "Bottle proportion defined by vessel profile, cap scale, and package relationship.",
    ),
    "tote bag": spec(
        "bags",
        ("body geometry", "handle proportion", "opening construction"),
        "Carry shape defined by body depth, handle drop, and opening width.",
    ),
    "shoulder bag": spec(
        "bags",
        ("body geometry", "strap placement", "closure construction"),
        "Carry shape defined by body scale, strap drop, and closure placement.",
    ),
    "handbag": spec(
        "bags",
        ("body geometry", "handle placement", "closure construction"),
        "Carry shape defined by body volume, handle scale, and opening line.",
    ),
    "bowling bag": spec(
        "bags",
        ("rounded body geometry", "handle placement", "zip opening"),
        "Carry shape defined by curved body volume, handle drop, and zip line.",
    ),
    "crossbody bag": spec(
        "bags",
        ("body geometry", "strap adjustment", "closure construction"),
        "Carry shape defined by compact body volume, strap length, and closure placement.",
    ),
    "camera bag": spec(
        "bags",
        ("compact body geometry", "strap placement", "zip opening"),
        "Carry shape defined by compact volume, strap drop, and perimeter opening.",
    ),
    "phone pouch": spec(
        "bags",
        ("device-scale geometry", "strap placement", "opening construction"),
        "Carry shape defined by device-sized volume, strap drop, and opening line.",
    ),
    "pouch": spec(
        "bags",
        ("compact body geometry", "opening construction", "carry attachment"),
        "Carry shape defined by flat volume, opening width, and attachment point.",
    ),
    "backpack": spec(
        "bags",
        ("body geometry", "strap placement", "compartment construction"),
        "Carry shape defined by back-panel scale, depth, and shoulder-strap placement.",
    ),
    "bag": spec(
        "bags",
        ("body geometry", "carry construction", "closure placement"),
        "Carry shape defined by body volume, handle or strap position, and opening line.",
    ),
    "cap": spec(
        "accessories",
        ("crown profile", "brim shape", "adjustment detail"),
        "Headwear profile defined by crown height, brim projection, and back adjustment.",
    ),
    "socks": spec(
        "accessories",
        ("rib structure", "cuff height", "material blend"),
        "Sock proportion defined by cuff height, leg width, and foot length.",
    ),
    "keychain": spec(
        "accessories",
        ("object scale", "attachment method", "surface finish"),
        "Accessory profile defined by object size, attachment point, and hanging length.",
    ),
    "card holder": spec(
        "accessories",
        ("pocket layout", "edge finish", "compact proportion"),
        "Small-leather-goods profile defined by width, height, and pocket placement.",
    ),
    "wallet": spec(
        "accessories",
        ("folding structure", "pocket layout", "closure detail"),
        "Small-leather-goods profile defined by folded size, thickness, and opening direction.",
    ),
    "phone holder": spec(
        "accessories",
        ("device-scale geometry", "attachment method", "opening construction"),
        "Accessory profile defined by device-sized volume, attachment point, and opening line.",
    ),
    "belt": spec(
        "accessories",
        ("strap width", "buckle geometry", "surface finish"),
        "Belt profile defined by strap width, buckle scale, and adjustment spacing.",
    ),
    "scarf": spec(
        "accessories",
        ("length-to-width ratio", "edge finish", "surface pattern"),
        "Scarf proportion defined by overall length, width, and end treatment.",
    ),
    "earrings": spec(
        "accessories",
        ("object scale", "attachment method", "surface finish"),
        "Jewelry profile defined by drop length, width, and attachment point.",
    ),
    "sunglasses": spec(
        "accessories",
        ("frame geometry", "lens proportion", "temple line"),
        "Eyewear profile defined by frame width, lens shape, and temple angle.",
    ),
    "accessory": spec(
        "accessories",
        ("object scale", "attachment method", "material expression"),
        "Accessory profile defined by body geometry, scale, and point of use.",
    ),
    "high-top sneaker": spec(
        "footwear",
        ("sole proportion", "ankle height", "closure construction"),
        "Footwear profile defined by sole scale, ankle height, and upper volume.",
    ),
    "sneaker": spec(
        "footwear",
        ("sole proportion", "upper construction", "closure construction"),
        "Footwear profile defined by sole scale, upper volume, and fastening placement.",
    ),
    "boot": spec(
        "footwear",
        ("shaft height", "toe shape", "sole proportion"),
        "Footwear profile defined by shaft height, toe volume, and sole scale.",
    ),
    "mule": spec(
        "footwear",
        ("open-back construction", "toe shape", "sole proportion"),
        "Footwear profile defined by open heel, upper coverage, and sole scale.",
    ),
    "loafer": spec(
        "footwear",
        ("vamp proportion", "toe shape", "sole construction"),
        "Footwear profile defined by vamp depth, toe volume, and sole scale.",
    ),
    "pump": spec(
        "footwear",
        ("heel placement", "toe shape", "upper cut"),
        "Footwear profile defined by heel geometry, toe volume, and topline.",
    ),
    "slip-on shoe": spec(
        "footwear",
        ("opening shape", "upper construction", "sole proportion"),
        "Footwear profile defined by opening depth, upper volume, and sole scale.",
    ),
    "shoe": spec(
        "footwear",
        ("sole proportion", "upper construction", "closure construction"),
        "Footwear profile defined by sole scale, upper volume, and fastening placement.",
    ),
    "jumpsuit": spec(
        "dresses",
        ("torso-to-leg proportion", "waist construction", "closure placement"),
        "One-piece silhouette defined by torso length, waist position, and leg volume.",
    ),
    "shirt dress": spec(
        "dresses",
        ("collar shape", "placket construction", "hem length"),
        "Dress silhouette defined by shoulder line, body volume, and hem length.",
    ),
    "dress": spec(
        "dresses",
        ("neckline shape", "body volume", "hem length"),
        "Dress silhouette defined by neckline, waist position, and hem length.",
    ),
    "apron skirt": spec(
        "skirts",
        ("waist attachment", "panel overlap", "hem length"),
        "Skirt silhouette defined by waist placement, wrap or panel volume, and hem length.",
    ),
    "denim skirt": spec(
        "denim",
        ("waist construction", "panel layout", "wash and finish"),
        "Skirt silhouette defined by rise, body volume, and hem length.",
    ),
    "skirt": spec(
        "skirts",
        ("waist placement", "body volume", "hem length"),
        "Skirt silhouette defined by waist position, volume, and hem length.",
    ),
    "coat": spec(
        "outerwear",
        ("overall length", "front closure", "layering volume"),
        "Outerwear silhouette defined by shoulder line, body volume, and coat length.",
    ),
    "parka": spec(
        "outerwear",
        ("hood volume", "body length", "pocket placement"),
        "Outerwear silhouette defined by hood scale, layering volume, and body length.",
    ),
    "anorak": spec(
        "outerwear",
        ("pullover opening", "hood or collar volume", "hem adjustment"),
        "Outerwear silhouette defined by shoulder line, body volume, and pullover length.",
    ),
    "bomber jacket": spec(
        "outerwear",
        ("body volume", "rib finish", "sleeve shape"),
        "Bomber silhouette defined by shoulder line, sleeve volume, and ribbed hem position.",
    ),
    "denim jacket": spec(
        "outerwear",
        ("panel construction", "pocket placement", "wash and finish"),
        "Jacket silhouette defined by shoulder line, torso length, and sleeve volume.",
    ),
    "trucker jacket": spec(
        "outerwear",
        ("panel construction", "chest pocket placement", "waist length"),
        "Jacket silhouette defined by shoulder line, waist-length body, and sleeve volume.",
    ),
    "leather jacket": spec(
        "outerwear",
        ("seam placement", "closure construction", "surface finish"),
        "Jacket silhouette defined by shoulder structure, body length, and sleeve line.",
    ),
    "track jacket": spec(
        "outerwear",
        ("collar shape", "zip construction", "hem and cuff finish"),
        "Jacket silhouette defined by shoulder line, athletic body volume, and hem position.",
    ),
    "coach jacket": spec(
        "outerwear",
        ("collar shape", "front closure", "hem adjustment"),
        "Jacket silhouette defined by relaxed shoulder, straight body, and hip-length hem.",
    ),
    "down jacket": spec(
        "outerwear",
        ("insulation volume", "baffle construction", "closure placement"),
        "Outerwear silhouette defined by insulated volume, body length, and sleeve shape.",
    ),
    "padded jacket": spec(
        "outerwear",
        ("insulation volume", "quilting construction", "closure placement"),
        "Outerwear silhouette defined by padded volume, body length, and sleeve shape.",
    ),
    "blazer": spec(
        "outerwear",
        ("shoulder structure", "lapel shape", "body length"),
        "Tailored silhouette defined by shoulder line, waist suppression, and jacket length.",
    ),
    "blouson": spec(
        "outerwear",
        ("collar shape", "body volume", "hem finish"),
        "Jacket silhouette defined by shoulder line, compact body volume, and hem position.",
    ),
    "overshirt": spec(
        "outerwear",
        ("layering volume", "pocket placement", "front closure"),
        "Layering silhouette defined by shoulder line, shirt-like body length, and sleeve volume.",
    ),
    "vest": spec(
        "outerwear",
        ("armhole shape", "body length", "layering volume"),
        "Sleeveless silhouette defined by shoulder width, armhole depth, and hem position.",
    ),
    "jacket": spec(
        "outerwear",
        ("shoulder structure", "body length", "closure construction"),
        "Jacket silhouette defined by shoulder line, torso volume, and hem position.",
    ),
    "zip hoodie": spec(
        "sweatshirts",
        ("hood volume", "center-front zip", "rib finish"),
        "Sweatshirt silhouette defined by hood scale, body volume, and hem position.",
    ),
    "hoodie": spec(
        "sweatshirts",
        ("hood volume", "body length", "rib finish"),
        "Sweatshirt silhouette defined by hood scale, body volume, and hem position.",
    ),
    "sweatshirt": spec(
        "sweatshirts",
        ("neckline shape", "body volume", "rib finish"),
        "Sweatshirt silhouette defined by shoulder line, torso volume, and hem position.",
    ),
    "cardigan": spec(
        "knitwear",
        ("front opening", "knit structure", "hem and cuff finish"),
        "Knit silhouette defined by shoulder line, body volume, and opening depth.",
    ),
    "sweater": spec(
        "knitwear",
        ("knit structure", "neckline shape", "body volume"),
        "Knit silhouette defined by shoulder line, torso volume, and hem position.",
    ),
    "knit polo": spec(
        "knitwear",
        ("collar proportion", "placket depth", "knit structure"),
        "Polo silhouette defined by shoulder line, body volume, and hem position.",
    ),
    "polo shirt": spec(
        "tops",
        ("collar proportion", "placket depth", "body volume"),
        "Polo silhouette defined by shoulder line, torso volume, and sleeve length.",
    ),
    "tank top": spec(
        "tops",
        ("neckline shape", "armhole depth", "body length"),
        "Sleeveless top silhouette defined by shoulder width, armhole depth, and hem position.",
    ),
    "long-sleeve t-shirt": spec(
        "tops",
        ("shoulder line", "body length", "sleeve proportion"),
        "T-shirt silhouette defined by shoulder width, torso volume, and full sleeve length.",
    ),
    "t-shirt": spec(
        "tops",
        ("shoulder line", "body length", "sleeve proportion"),
        "T-shirt silhouette defined by shoulder width, torso volume, and sleeve length.",
    ),
    "jersey": spec(
        "tops",
        ("shoulder line", "neckline construction", "athletic body volume"),
        "Jersey silhouette defined by shoulder width, torso volume, and sleeve length.",
    ),
    "blouse": spec(
        "shirts",
        ("neckline treatment", "body volume", "sleeve construction"),
        "Blouse silhouette defined by shoulder line, drape, and hem position.",
    ),
    "tunic": spec(
        "tops",
        ("neckline shape", "extended body length", "side opening"),
        "Tunic silhouette defined by shoulder line, elongated torso, and hem position.",
    ),
    "shirt": spec(
        "shirts",
        ("collar shape", "placket construction", "body volume"),
        "Shirt silhouette defined by shoulder line, torso length, and sleeve volume.",
    ),
    "top": spec(
        "tops",
        ("neckline shape", "body volume", "hem position"),
        "Top silhouette defined by shoulder line, torso volume, and hem position.",
    ),
    "denim shorts": spec(
        "denim",
        ("rise", "leg opening", "wash and finish"),
        "Shorts silhouette defined by rise, inseam length, and leg opening.",
    ),
    "cargo shorts": spec(
        "shorts",
        ("pocket placement", "rise", "leg opening"),
        "Shorts silhouette defined by rise, utility-pocket volume, and leg opening.",
    ),
    "track shorts": spec(
        "shorts",
        ("waistband construction", "inseam length", "hem treatment"),
        "Shorts silhouette defined by rise, athletic volume, and leg opening.",
    ),
    "basketball shorts": spec(
        "shorts",
        ("waistband construction", "long inseam", "wide leg opening"),
        "Shorts silhouette defined by rise, long athletic volume, and leg opening.",
    ),
    "swim shorts": spec(
        "shorts",
        ("waistband construction", "inseam length", "quick-dry volume"),
        "Shorts silhouette defined by rise, swim-ready volume, and leg opening.",
    ),
    "shorts": spec(
        "shorts",
        ("rise", "inseam length", "leg opening"),
        "Shorts silhouette defined by rise, inseam length, and leg opening.",
    ),
    "jeans": spec(
        "denim",
        ("rise", "leg shape", "wash and finish"),
        "Denim silhouette defined by rise, thigh volume, and hem width.",
    ),
    "cargo pants": spec(
        "pants",
        ("pocket placement", "rise", "leg volume"),
        "Trouser silhouette defined by rise, utility-pocket volume, and hem width.",
    ),
    "track pants": spec(
        "pants",
        ("waistband construction", "leg line", "cuff or hem finish"),
        "Trouser silhouette defined by rise, athletic leg volume, and hem treatment.",
    ),
    "trousers": spec(
        "pants",
        ("rise", "leg volume", "hem treatment"),
        "Trouser silhouette defined by rise, thigh volume, and hem width.",
    ),
}


# Overrides are limited to names that omit the product noun, contain a scraped
# fragment, or use a product-family term that is not classifiable on its own.
# The replacement names are conservative descriptions of the sourced product
# view, not invented commercial names.
IDENTITY_OVERRIDES: dict[str, tuple[str | None, str]] = {
    "core-149-off-white-jitney-1-0-shoulder-ownn172c99lea0011000": (
        "Jitney 1.0 Shoulder Bag",
        "shoulder bag",
    ),
    "core-072-represent-star-long-sleeve-jersey-jet-black": (None, "jersey"),
    "official-our-legacy-17-extended-third-cut-in-blue-bleu-denim": (None, "jeans"),
    "official-kiko-kostadinov-04-asics-ilargi-ff-ii-driftwood-dioptase-kiko-kostadinov": (
        None,
        "sneaker",
    ),
    "official-kiko-kostadinov-05-asics-ilargi-ff-ii-sage-frost-tatami-green-kiko-kostadin": (
        None,
        "sneaker",
    ),
    "official-maison-margiela-18-new-bauletto-j-mini": (None, "handbag"),
    "official-stone-island-02-4100001-nylon-metal-colour-weft-stand-collar-jacket": (
        None,
        "jacket",
    ),
    "official-stone-island-17-4100119-nylon-metal-watro-tc-hooded-jacket-in-black": (
        None,
        "jacket",
    ),
    "official-undercover-06-cotton-fleece-zip": ("Cotton Fleece Zip Hoodie", "zip hoodie"),
    "official-undercover-08-cotton-t": ("Cotton T-Shirt", "t-shirt"),
    "official-undercover-09-cotton-zip": ("Cotton Zip Hoodie", "zip hoodie"),
    "official-undercover-10-cupro-cotton-all": (
        "Cupro/Cotton All-Over Print Skirt",
        "skirt",
    ),
    "official-undercover-12-nylon-ma": ("Nylon MA-1 Bomber Jacket", "bomber jacket"),
    "official-undercover-17-polyester-organza-zip": (
        "Polyester Organza Zip Jacket",
        "jacket",
    ),
    "official-undercover-20-rayon-open": ("Rayon Open-Collar Shirt", "shirt"),
    "official-undercover-24-wool-double": ("Wool Double-Breasted Blazer", "blazer"),
    "official-craig-green-05-embroidered-linestitch-sport": (
        "Embroidered Linestitch Sport Jacket",
        "jacket",
    ),
}


def clean_display_text(value: str) -> str:
    value = value.replace("â", "\u2013").replace("\u00e2\u0080\u0093", "\u2013")
    value = re.sub(r"\s+READ MORE MATERIALS\b.*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+(?:\u2013|-)\s+KIKO KOSTADINOV\s*$", "", value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", value).strip()


def classification_text(brand: str, product_name: str) -> str:
    value = clean_display_text(product_name).casefold()
    if brand == "Comme des Garçons":
        # CDG Shirt is a label prefix, not the garment identity.
        value = re.sub(r"^cdg shirt forever\s*-\s*", "", value)
        value = re.sub(r"^cdg shirt\s*-\s*", "", value)
    return value


def matches(value: str, pattern: str) -> bool:
    return re.search(pattern, value, flags=re.IGNORECASE) is not None


def classify(item: dict[str, Any], product_name: str) -> str:
    override = IDENTITY_OVERRIDES.get(item["id"])
    if override is not None:
        return override[1]

    value = classification_text(item["brand"], product_name)

    if matches(value, r"\b(parfum|perfume|fragrance)\b"):
        return "fragrance"

    # Bags precede apparel because names such as "bowling bag" include a form
    # word that could otherwise be mistaken for a garment family.
    if matches(value, r"\b(zipped pouch charm|charm pouch)\b"):
        return "keychain"
    if matches(value, r"\b(backpack|porter bag)\b"):
        return "backpack"
    if matches(value, r"\b(tote(?: bag)?)\b"):
        return "tote bag"
    if matches(value, r"\bbowling bag\b"):
        return "bowling bag"
    if matches(value, r"\b(camera bag)\b"):
        return "camera bag"
    if matches(value, r"\b(crossbody|cross-body)\b"):
        return "crossbody bag"
    if matches(value, r"\b(phone strap with pouch|pouch on strap)\b"):
        return "phone pouch"
    if matches(value, r"\b(shoulder bag|jitney .*shoulder)\b"):
        return "shoulder bag"
    if matches(value, r"\b(handbag|bauletto)\b"):
        return "handbag"
    if matches(value, r"\b(pouch)\b"):
        return "pouch"
    if matches(value, r"\b(sling bag)\b"):
        return "shoulder bag"
    if matches(value, r"\b(bag)\b"):
        return "bag"

    if matches(value, r"\b(geobasket|basketball sneaker)\b"):
        return "high-top sneaker"
    if matches(value, r"\b(sneakers?|trainers?|asics ilargi|ldv waffle|vaporwaffle)\b"):
        return "sneaker"
    if matches(value, r"\bboots?\b"):
        return "boot"
    if matches(value, r"\bmule\b"):
        return "mule"
    if matches(value, r"\bloafer(?:s)?\b"):
        return "loafer"
    if matches(value, r"\bpump\b"):
        return "pump"
    if matches(value, r"\bslip-on\b"):
        return "slip-on shoe"
    if matches(value, r"\b(shoe|shoes)\b"):
        return "shoe"

    # One-piece and skirt identities precede vest/shirt parsing: "vest dress"
    # and "shirt dress" describe dresses, not layering pieces.
    if matches(value, r"\bjumpsuit\b"):
        return "jumpsuit"
    if matches(value, r"\bt[- ]?shirt dress\b"):
        return "dress"
    if matches(value, r"\bshirt dress\b"):
        return "shirt dress"
    if matches(value, r"\bvest dress\b"):
        return "dress"
    if matches(value, r"\bdress\b"):
        return "dress"
    if matches(value, r"\bapron skirt\b"):
        return "apron skirt"
    if matches(value, r"\bdenim (?:sliced )?skirt\b"):
        return "denim skirt"
    if matches(value, r"\bskirt\b"):
        return "skirt"

    # Shirt-jackets and overshirts are evaluated before the word "shirt".
    if matches(value, r"\b(?:shirt[- ]jacket|shirt jacket)\b"):
        return "overshirt"
    if matches(value, r"\b(?:reversible |leather |spliced leather |padded )?bomber\b|\bma-?1\b"):
        return "bomber jacket"
    if matches(value, r"\bdenim\b.*\bjacket\b|\btrucker jacket\b"):
        return "denim jacket" if "denim" in value else "trucker jacket"
    if matches(value, r"\btrack(?:suit)?\b.*\bjacket\b"):
        return "track jacket"
    if matches(value, r"\bcoach jacket\b"):
        return "coach jacket"
    if matches(value, r"\b(?:leather|shearling) (?:race |pilot )?jacket\b"):
        return "leather jacket"
    if matches(value, r"\b(?:suit jacket|blazer)\b"):
        return "blazer"
    if matches(value, r"\bparka\b"):
        return "parka"
    if matches(value, r"\bcoat\b"):
        return "coat"
    if matches(value, r"\banorak\b"):
        return "anorak"
    if matches(value, r"\b(?:down|puffer) (?:blouson|jacket)\b"):
        return "down jacket"
    if matches(value, r"\b(?:padded|quilted) (?:hooded )?jacket\b"):
        return "padded jacket"
    if matches(value, r"\bblouson\b"):
        return "blouson"
    if matches(value, r"\b(?:overshirt|outershirt)\b"):
        return "overshirt"
    if matches(value, r"\b(?:vest|gilet)\b"):
        return "vest"
    if matches(value, r"\bjacket\b"):
        return "jacket"

    if matches(value, r"\bzip(?:-up)? hoodie\b"):
        return "zip hoodie"
    if matches(value, r"\bhoodie\b"):
        return "hoodie"
    if matches(value, r"\bcardigan\b"):
        return "cardigan"
    if matches(value, r"\b(?:sweater|turtleneck)\b"):
        return "sweater"
    if matches(value, r"\b(?:wool |knit )?pullover\b"):
        return "sweater" if matches(value, r"\b(wool|knit)\b") else "sweatshirt"
    if matches(value, r"\b(?:sweatshirt|crewneck|full-zip|half zip)\b"):
        return "sweatshirt"

    if matches(value, r"\bknit(?:ted)? polo\b"):
        return "knit polo"
    if matches(value, r"\bpolo\b"):
        return "polo shirt"
    if matches(value, r"\b(?:tank|sleeveless tee)\b"):
        return "tank top"
    if matches(
        value,
        r"\b(?:longsleeve|long[- ]sleeve|ls|l/s)\b.*\b(?:t[- ]?shirt|tee)\b",
    ):
        return "long-sleeve t-shirt"
    if matches(value, r"\b(?:t[- ]?shirt|tee)\b"):
        return "t-shirt"
    if matches(value, r"\b(?:football top|football jersey|jersey)\b"):
        return "jersey"
    if matches(value, r"\b(?:longsleeve|long[- ]sleeve|ls|l/s)\b"):
        return "long-sleeve t-shirt"
    if matches(value, r"\bblouse\b"):
        return "blouse"
    if matches(value, r"\btunic\b"):
        return "tunic"
    if matches(value, r"\b(?:shirt|button up|button-up|cloak)\b"):
        return "shirt"
    if matches(value, r"\btop\b"):
        return "top"

    if matches(value, r"\bcargo\b.*\bshorts?\b"):
        return "cargo shorts"
    if matches(value, r"\bdenim\b.*\bshorts?\b"):
        return "denim shorts"
    if matches(value, r"\bcargo shorts?\b"):
        return "cargo shorts"
    if matches(value, r"\b(?:track|traxedo) shorts?\b"):
        return "track shorts"
    if matches(value, r"\bbasketball shorts?\b"):
        return "basketball shorts"
    if matches(value, r"\b(?:swim trunks|swim shorts?)\b"):
        return "swim shorts"
    if matches(value, r"\b(?:shorts?|sweatshorts)\b"):
        return "shorts"
    if matches(value, r"\b(?:jeans|third cut)\b"):
        return "jeans"
    if matches(value, r"\bcargo(?: pants?| trouser)?\b"):
        return "cargo pants"
    if matches(value, r"\btrackpants\b|\b(?:track|traxedo)\b.*\bpants?\b"):
        return "track pants"
    if matches(value, r"\b(?:trousers?|pants?|chino)\b"):
        return "trousers"
    if matches(value, r"\b(?:motopants|denim)\b"):
        return "jeans" if "denim" in value else "trousers"

    if matches(value, r"\b(?:baseball cap|ballcap|cap|hat)\b"):
        return "cap"
    if matches(value, r"\bsocks?\b"):
        return "socks"
    if matches(value, r"\b(?:keychain|charm)\b"):
        return "keychain"
    if matches(value, r"\bcard holder\b"):
        return "card holder"
    if matches(value, r"\bwallet\b"):
        return "wallet"
    if matches(value, r"\bphone holder\b"):
        return "phone holder"
    if matches(value, r"\bbelt\b"):
        return "belt"
    if matches(value, r"\bscarf\b"):
        return "scarf"
    if matches(value, r"\bearrings?\b"):
        return "earrings"
    if matches(value, r"\bsunglasses\b"):
        return "sunglasses"

    raise ValueError(f"Unclassified product {item['seed_order']} {item['brand']}: {product_name!r}")


def joined(values: tuple[str, str, str]) -> str:
    return f"{values[0]}, {values[1]}, and {values[2]}"


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = value.strip()
        folded = clean.casefold()
        if clean and folded not in seen:
            seen.add(folded)
            result.append(clean)
    return result


def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)
    original_product_name = item["product_name"]
    cleaned_product_name = clean_display_text(original_product_name)
    override = IDENTITY_OVERRIDES.get(item["id"])
    product_name = override[0] if override and override[0] else cleaned_product_name
    object_type = classify(item, product_name)
    identity = IDENTITY_SPECS[object_type]

    normalized["product_name"] = product_name

    title = clean_display_text(item["title"])
    if cleaned_product_name in title and product_name != cleaned_product_name:
        title = title.replace(cleaned_product_name, product_name)
    normalized["title"] = title

    image_alt = clean_display_text(item["image_alt"])
    if cleaned_product_name in image_alt and product_name != cleaned_product_name:
        image_alt = image_alt.replace(cleaned_product_name, product_name)
    normalized["image_alt"] = image_alt

    normalized["category"] = identity.category
    normalized["object_type"] = object_type
    normalized["description"] = (
        f"{object_type.capitalize()} reference focused on {joined(identity.attributes)}. "
        "Use the cited product image to inspect exact proportions and construction."
    )
    normalized["neutral_attributes"] = list(identity.attributes)
    normalized["silhouette"] = identity.silhouette
    normalized["tags"] = unique(
        [
            object_type,
            identity.category,
            *identity.attributes,
            *item["materials"],
            *item["palette"],
        ]
    )

    # Assert the fields explicitly protected by the catalog contract.  The
    # broader check prevents the normalizer from silently moving provenance or
    # any future field not listed above.
    for field, value in item.items():
        if field not in NORMALIZED_FIELDS and normalized[field] != value:
            raise AssertionError(f"Protected field changed for {item['id']}: {field}")
    return normalized


def validate_manifest(manifest: dict[str, Any]) -> None:
    items = manifest.get("items")
    if not isinstance(items, list) or len(items) != EXPECTED_ITEMS:
        raise ValueError(f"Expected exactly {EXPECTED_ITEMS} product rows")

    brand_counts = Counter(item["brand"] for item in items)
    if len(brand_counts) != EXPECTED_BRANDS:
        raise ValueError(f"Expected exactly {EXPECTED_BRANDS} brands, got {len(brand_counts)}")
    invalid_counts = {
        brand: count for brand, count in brand_counts.items() if count != PRODUCTS_PER_BRAND
    }
    if invalid_counts:
        raise ValueError(f"Expected {PRODUCTS_PER_BRAND} products per brand: {invalid_counts}")

    checks = {
        "id": [item["id"] for item in items],
        "source_url": [item["source_url"] for item in items],
        "image_url": [item["image_url"] for item in items],
        "seed_order": [item["seed_order"] for item in items],
    }
    for field, values in checks.items():
        if len(set(values)) != EXPECTED_ITEMS:
            raise ValueError(f"Expected {EXPECTED_ITEMS} unique {field} values")
    if set(checks["seed_order"]) != set(range(1, EXPECTED_ITEMS + 1)):
        raise ValueError("seed_order must be the contiguous range 1 through 600")

    for item in items:
        if item["object_type"] not in IDENTITY_SPECS:
            raise ValueError(f"Unknown object_type for {item['id']}: {item['object_type']}")
        expected = IDENTITY_SPECS[item["object_type"]]
        if item["category"] != expected.category:
            raise ValueError(f"Category/object mismatch for {item['id']}")
        if item["neutral_attributes"] != list(expected.attributes):
            raise ValueError(f"Attribute template mismatch for {item['id']}")
        if item["silhouette"] != expected.silhouette:
            raise ValueError(f"Silhouette template mismatch for {item['id']}")
        if "READ MORE MATERIALS" in item["product_name"].upper() or "â" in item["product_name"]:
            raise ValueError(f"Scraped text remains in product_name for {item['id']}")


def canonical_manifest(source: dict[str, Any]) -> tuple[dict[str, Any], Counter[str]]:
    before = source["items"]
    after = [normalize_item(item) for item in before]
    result = dict(source)
    result["items"] = after
    validation_summary = dict(result.get("validation_summary", {}))
    validation_summary.update(
        {
            "metadata_normalized_rows": EXPECTED_ITEMS,
            "metadata_normalization_script": "backend/scripts/normalize_product_catalog.py",
            "metadata_identity_rule": "product-name-first with reviewed explicit overrides",
        }
    )
    result["validation_summary"] = validation_summary
    validate_manifest(result)

    changes: Counter[str] = Counter()
    for old, new in zip(before, after, strict=True):
        for field in NORMALIZED_FIELDS:
            if old[field] != new[field]:
                changes[field] += 1
    return result, changes


def rendered(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def process(path: Path, *, check: bool) -> Counter[str]:
    source_text = path.read_text(encoding="utf-8")
    source = json.loads(source_text)
    canonical, changes = canonical_manifest(source)
    output = rendered(canonical)
    if check:
        if source_text != output:
            raise ValueError(f"Catalog is not normalized: {path}")
    else:
        path.write_text(output, encoding="utf-8")
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Manifest paths to normalize")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate canonical content without writing changes",
    )
    arguments = parser.parse_args()
    paths = tuple(arguments.paths) or DEFAULT_MANIFESTS

    for path in paths:
        changes = process(path, check=arguments.check)
        action = "checked" if arguments.check else "normalized"
        changed_summary = ", ".join(
            f"{field}={count}" for field, count in sorted(changes.items()) if count
        )
        print(f"{action} {path}: {EXPECTED_BRANDS} brands x {PRODUCTS_PER_BRAND} products")
        print(f"  field corrections: {changed_summary or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
