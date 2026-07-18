# Initial label catalog

This is a taste-navigation set, not a ranking, endorsement, or claim that the labels are interchangeable. Tags are editorial hypotheses for the preference selector; the designer must be able to approve, remove, and contradict them.

## Seed labels

| Label | Selector tags |
| --- | --- |
| [Vetements](brands/vetements/README.md) | amplified volume · subversion · graphic tension · reconstructed basics |
| [John Elliott](brands/john-elliott/README.md) | refined essentials · fabric focus · layered neutrals · athletic influence |
| [Represent](brands/represent/README.md) | washed finishes · British streetwear · graphic staples · relaxed proportions |
| [Acne Studios](brands/acne-studios/README.md) | Scandinavian eclecticism · offbeat proportion · denim · art-school color |
| [Off-White](brands/off-white/README.md) | industrial graphics · high-low mix · quotation · visible construction |

## Fifteen adjacent labels

| Label | Selector tags |
| --- | --- |
| [Balenciaga](brands/balenciaga/README.md) | amplified volume · street-formal · techwear · sculptural tailoring |
| [Rick Owens](brands/rick-owens/README.md) | elongated silhouettes · monochrome · draping · architectural forms |
| [A-COLD-WALL*](brands/a-cold-wall/README.md) | industrial palette · performance materials · asymmetric utility · British sportswear |
| [Fear of God](brands/fear-of-god/README.md) | relaxed tailoring · muted neutrals · longline layering · sportswear |
| [Martine Rose](brands/martine-rose/README.md) | oversized tailoring · retro sportswear · club references · skewed proportions |
| [Kiko Kostadinov](brands/kiko-kostadinov/README.md) | ergonomic cutting · technical fabrics · utility details · color blocking |
| [Maison Margiela](brands/maison-margiela/README.md) | deconstruction · repurposed materials · exposed construction · trompe-l'oeil |
| [Stone Island](brands/stone-island/README.md) | garment dyeing · technical outerwear · modular utility · material research |
| [Undercover](brands/undercover/README.md) | punk graphics · layered styling · narrative motifs · tailored streetwear |
| [Jil Sander](brands/jil-sander/README.md) | precise minimalism · soft tailoring · clean geometry · restrained color |
| [Rhude](brands/rhude/README.md) | vintage Americana · motorsport graphics · washed finishes · relaxed tailoring |
| [Craig Green](brands/craig-green/README.md) | quilted structures · straps · modular panels · sculptural workwear |
| [Our Legacy](brands/our-legacy/README.md) | washed textures · relaxed tailoring · vintage references · understated palette |
| [sacai](brands/sacai/README.md) | hybrid garments · layered construction · contrast panels · military-sportswear |
| [Comme des Garçons](brands/comme-des-garcons/README.md) | asymmetry · conceptual tailoring · monochrome · sculptural volume |

## Official inspiration candidates

[`INSPIRATION_CANDIDATES.json`](INSPIRATION_CANDIDATES.json) records two verified product objects per adjacent label, including first-party source and image URLs plus neutral construction metadata. It is a review/provenance manifest, not a license or runtime hotlink feed; follow its rights policy before any image is downloaded, cached, redistributed, or rendered.

[`INSPIRATION_ADJACENT_450.json`](INSPIRATION_ADJACENT_450.json) expands that research set to 30 unique official product identities for each of the fifteen adjacent labels. Its external URLs are provenance and discovery records only; the manifest explicitly forbids downloading, caching, redistributing, or hotlinking the cited imagery without written permission.

[`INSPIRATION_CORE_150.json`](INSPIRATION_CORE_150.json) records 30 products for each of the five seed labels. Vetements is explicitly sourced through the retailer it delegates shopping to; the other four use official storefronts.

[`INSPIRATION_PRODUCTS_600.json`](INSPIRATION_PRODUCTS_600.json) is the validated combined review catalog used to build the local product library: 20 labels × 30 products, with unique product, source, and image URLs. External images are local-prototype research references, not repository-owned assets or a license grant.

## Selector behavior

- Let users choose 3–5 labels, search, or skip.
- After selection, synthesize traits and ask for confirmation instead of silently locking a style profile.
- Do not use brand logos in the UI without rights. Render names typographically in the product's own system.
- Keep label data separate from generated prompts. Prompts should use approved traits, not brand names.
- Record the date when the catalog is reviewed; creative direction and operating status change.

Last reviewed: 2026-07-17.
