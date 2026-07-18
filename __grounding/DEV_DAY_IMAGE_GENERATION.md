# DevDay image generation record

The three committed DevDay garment rasters and the V3 lookbook raster are real `gpt-image-2`
outputs. At backend startup they are checksum-verified, copied byte-for-byte into ignored runtime
asset storage, and imported into the reserved `devday-swag` project. V1/V2/V3 become ready,
immutable `DesignVersion` records with exact parent lineage; the lookbook becomes a separate ready
`PresentationRender` linked to V3 with preset `edgy-european-guy`.

This is an explicit import of documented, prepared outputs—not a simulated provider response and
not a live Images API call. The importer is idempotent, restores a missing prepared runtime copy,
and stops without changing the project if its seed, version lineage, or presentation history has
diverged into user-authored work.

## Shared settings

- Provider route: direct OpenAI Images API
- Model/deployment: `gpt-image-2`
- Size: `1024x1536`
- Quality: `medium`
- Output format: PNG
- Subject: one original, unbranded bomber jacket layered over one blank T-shirt on a headless
  ghost mannequin
- Exclusions: people, logos, marks, readable text, recognizable campaigns, illustration, CGI,
  and collage

No brand image or campaign photograph was supplied. The John Elliott signal is limited to the
neutral design vocabulary already documented in the repository: refined essentials, fabric
focus, layered neutrals, and restrained proportion.

## Version 01 — washed flight

Operation: generation from text.

OpenAI request ID: `req_7b960b06ae9a4d4c906fac3019b16cc9`

Prompt:

> Photorealistic high-end fashion design-review product photograph, not illustration and not
> CGI. One original distressed washed-charcoal bomber jacket layered open over one heavyweight
> blank optic-white T-shirt on a headless ghost mannequin, complete garments fully visible from
> collar through hem, front three-quarter view, no person or skin. Roomy flight proportion,
> dropped shoulder, matte cotton-nylon shell, worn rib collar cuffs and hem, two-way metal zip,
> side-entry welt pockets, subtle abrasion and repaired wear, tiny restrained safety-orange
> bartack accents. The T-shirt has substantial cotton jersey, clean crew neck, blank surface and
> visible hem. Neutral near-black charcoal studio sweep, soft controlled overhead light plus
> narrow warm edge light, technically legible fabric grain, seams, ribbing and hardware. Original
> unbranded design, inspection-friendly negative space. No logos, brand marks, readable text,
> watermark, accessories, lower-body styling, recognizable campaign, cartoon, drawing, vector,
> collage, distorted garment, cropped garment, hidden closures.

Output: `app/public/devday/devday-look-v1.png`

SHA-256: `8e6f5d8930a1459e80d76498829b765b4053fbde6a87ad8e2e66ac666af87282`

## Version 02 — exposed construction

Operation: edit of the exact Version 01 PNG.

OpenAI request ID: `req_6175c7e7d2c4489d9b5501b348a8c6c3`

Prompt:

> Edit the supplied current garment image as the sole visual source of truth. Make exactly one
> visible design change: convert the bomber's construction expression to a restrained inside-out
> treatment, with selected seam allowances and raw construction lines visibly externalized and a
> small number of precise safety-orange bartacks at high-stress joins. KEEP unchanged: the exact
> bomber category, roomy flight silhouette, length, dropped shoulder, washed-charcoal color,
> distressed matte shell, rib collar cuffs and hem, two-way zip, pocket placement, blank
> optic-white heavyweight T-shirt, ghost-mannequin presentation, camera, crop, charcoal
> background, lighting, and all proportions. Do not redesign or replace the garment. No person,
> skin, logos, text, watermark, extra styling, cartoon, drawing, CGI or collage.

Input: `app/public/devday/devday-look-v1.png`

Output: `app/public/devday/devday-look-v2.png`

SHA-256: `097d6be9c2412493004fc430c18535fe0f12a42561f89669ba8951187788f29a`

## Version 03 — high-hip crop

Operation: edit of the exact Version 02 PNG.

OpenAI request ID: `req_c84abff3667b49a2aa024fe28d7d70c8`

Prompt:

> Edit the supplied current garment image as the sole visual source of truth. Make exactly one
> visible design change: shorten only the bomber body length by approximately 90 millimeters so
> the rib hem finishes at the high hip; preserve sleeve length and keep the white T-shirt extending
> visibly below the jacket. KEEP unchanged: the exact bomber identity, roomy flight width, dropped
> shoulder, washed-charcoal color, distressed matte shell, externalized seam construction,
> safety-orange bartacks, rib collar cuffs and hem, two-way zip, pocket design and placement, blank
> optic-white heavyweight T-shirt, ghost-mannequin presentation, camera, crop, charcoal
> background, lighting, and every other proportion. Do not redesign or replace the garment. No
> person, skin, logos, text, watermark, extra styling, cartoon, drawing, CGI or collage.

Input: `app/public/devday/devday-look-v2.png`

Output: `app/public/devday/devday-look-v3.png`

SHA-256: `c29dfb9a2e800224057224158d533a96ec413ecf678c47f307181cd152f9cf6b`

## V3 presentation — fictional adult lookbook

Operation: presentation edit using the exact Version 03 PNG as the canonical garment reference.
This is a separate `PresentationRender` conceptually; it is never an input to the next garment
change.

OpenAI request ID: `req_dc76d3df262f43f38d02a11a3b24b3db`

Prompt:

> Use the supplied garment image as the exact canonical wardrobe reference. Create a separate
> photorealistic editorial lookbook presentation with one entirely fictional, non-identifiable
> adult model, male-presenting, apparent age 28 to 34, tall lean build, short dark hair,
> understated contemporary European casting, calm neutral expression. Show the model full-body
> in a restrained raw-concrete Los Angeles studio, relaxed contrapposto, wearing the exact
> washed-charcoal cropped distressed bomber open over the exact blank heavyweight white T-shirt
> from the reference, with straight black trousers and unbranded black leather shoes. Preserve the
> jacket's high-hip body length, roomy width, dropped shoulder, external seam allowances, orange
> bartacks, rib, zips, pockets, abrasion, color, and the T-shirt neckline and hem. Soft overcast
> daylight with a warm edge, real camera, realistic skin and textiles, high-end independent
> fashion casting sheet, no borrowed campaign. Do not alter or hide the garment; no logos, brand
> marks, readable text, watermark, celebrity, recognizable real person, cartoon, drawing, CGI,
> collage, excessive styling, jewelry, hat, bag, or dramatic pose.

Input: `app/public/devday/devday-look-v3.png`

Output: `app/public/devday/devday-presentation-v3.png`

SHA-256: `a2da00bc1f3b551dc901e0a4273318edf7044f891967eb8d79e09a386ec2f4f6`

## Runtime boundary

The prepared import makes the canonical demo inspectable and editable through the same backend
asset and version APIs as any successful raster. Subsequent revisions and new presentations still
use the live ChatKit and Images API paths. Any live billing, quota, authentication, moderation,
timeout, or provider failure remains visible and must not advance the version pointer or fabricate
a successful presentation.
