# Fashion product research

Reviewed 2026-07-17. This is independent product-design research, not an
endorsement, affiliation, or imitation brief. The goal is to identify what makes
a digital garment feel inspectable, editable, and credible to a designer.

## Research method

Live official pages for John Elliott, Acne Studios, Our Legacy, Represent, and
the Fashion Institute of Technology were inspected in a browser at desktop
size. No third-party image was copied into the project or committed; temporary
browser screenshots remained in ignored local output. Stone Island, CLO, and
Techpacker help pages rejected automated browser access; their findings below
use text returned from the same official URLs.

## What current garment pages make legible

### A view set, not one hero image

- The current [John Elliott Core Hollywood Tee](https://www.johnelliott.com/products/core-hollywood-tee-drift)
  uses six consistent portrait views. Its product copy then fixes the design in
  concrete terms: boxy and cropped, 220 GSM ring-spun cotton, blind-stitched
  sleeves and hem, rib neck, cover-stitch detail, model height and worn size,
  and a garment-measurement view.
- The [John Elliott Summer Reversed Cropped Tee](https://www.johnelliott.com/collections/all/products/summer-reversed-cropped-tee-white)
  uses seven views. Browser inspection showed an isolated front flat followed
  by on-body views. The text names dropped shoulders, lightweight 30-single
  jersey, reversed seams, garment wash, country of manufacture, composition,
  fit advice, and model size.
- The [Our Legacy Tuxedo Bomber](https://www.ourlegacy.com/tuxedo-bomber-fresh-black-tarmac-twill)
  has seven still images plus another media slot. Five establish the garment on
  a person; two close-ups show the same shaped collar open and fastened. Those
  are useful garment states, not different designs.
- The [Represent Smart Bomber](https://eu.representclo.com/products/smart-bomber-nero)
  supplies eight images, model height/weight and worn size, a size chart, and a
  3D-view affordance. It pairs the visual record with a short construction list:
  light fill, forward shoulder seams, two-way zip, rib trims, pocket types, and
  elbow darts.

**Product implication:** one photorealistic output can be a draft, but it is not
a complete garment record. The accepted design needs an inspectable view set:
at minimum a canonical object view, front, back, on-body fit view, and close-ups
for each changed construction detail. The canvas may center one view while a
`VIEWS` control exposes the others. Every view must link to the same immutable
design version.

### Product truth and presentation are different

The John Elliott pages place isolated product imagery and on-body photography
in one sequence. Our Legacy uses clean, repeatable on-body framing, then opens
collar-detail images at inspection scale. Neither treats styling, pose, or a
collar being temporarily fastened as a new garment.

**Product implication:** the canonical garment image is the edit reference.
Model, pose, place, lighting, open/closed closures, and styled underlayers are
derived presentation controls. A change to any of them creates a new
presentation render or state view, never a new garment version. Conversely, a
new hem length, seam, pocket, fabric with different physical behavior, or
pattern proportion is a garment version even if the model does not change.

### Credible copy names observable decisions

Across the pages, useful copy repeatedly follows the same grammar:

- **fit:** boxy, cropped, relaxed, regular, below waist, dropped shoulder;
- **material:** fibre composition, fabric origin, yarn or fabric weight, hand,
  lining, fill;
- **construction:** collar, cuffs, hem, seam, dart, pocket, closure, hardware;
- **finish:** washed, piece dyed, rinsed, coated, distressed, anti-drop;
- **evidence:** model dimensions and worn size, garment measurements, style id.

The [Stone Island Indigo Micro Corduroy bomber](https://www.stoneisland.com/en-ca/collection/coats-and-jackets/bomber-jacket-with-pockets-and-light-padding-4100123-indigo-micro-corduroy-rinsed-K2S154100123S0J10V0021.html)
is especially explicit about textile behavior: fibre structure, indigo dye,
rinsing, light padding, trims, and fit are described separately. The point is
not to borrow its treatment; it is to observe that material, finish, function,
and silhouette are separate decisions.

**Product implication:** replace broad aesthetic adjectives with structured
fields and concrete nouns. The guide can still accept plain language, but its
restatement should resolve into `FIT`, `MATERIAL`, `CONSTRUCTION`, `FINISH`,
`COLOR`, or `PLACEMENT`. A phrase such as “make it more elevated” is not a
render instruction until one observable variable is named.

### A stable identity sits above variants

The [Acne Studios technical jacket](https://www.acnestudios.com/us/en/technical-jacket-with-logo-black/B90800-900.html)
shows six images, labels `Current colour`, links the other colour beside it, and
keeps a stable style id with the product details. Its description separately
records fit, length, closure, pockets, lining, composition, model height, and
worn size. Our Legacy pairs the product name with a named fabrication/colour
and a short style code; Represent exposes its product style code in the same
detail block as construction and composition.

**Product implication:** the project/object name should stay generic and
durable—`T-shirt`, not `white T-shirt`. White is a property of the active
version or colorway. Show a stable project/style id above version-specific fit,
material, construction, finish, and colour.

## What professional development workflows require

### Colorways are linked variants, not a loose image pile

The official [CLO Colorway manual](https://support.clo3d.com/hc/en-us/articles/32783140814105-Colorway)
starts a colorway from a selected colorway. Its default variation changes only
material properties such as colour and texture. It also distinguishes `All
Properties` for a genuinely different item and `Link` for an item that remains
the same across colorways. Users can snapshot all colorways together and choose
whether an assignment affects the current colorway or every colorway.

**Product implication:** represent invariants as linked properties, not only
prompt prose. A colorway may change appearance while sharing pattern geometry,
measurements, and construction. If a request changes physical fabric behavior,
button shape, pocket architecture, or silhouette, promote it to a garment
version. The UI should say which scope is being changed: `THIS VERSION`, `THIS
COLORWAY`, or `ALL LINKED COLORWAYS`.

### Revisions are locked, comparable, and recoverable

Techpacker's official [version workflow](https://helpcenter.techpacker.com/hc/en-us/articles/360033521034-How-to-create-a-techpack-version)
locks a change as a named, time-ordered version before it is shared. Restoring a
version creates a duplicate without altering the original. Its [version
comparison workflow](https://helpcenter.techpacker.com/hc/en-us/articles/360058355973-How-to-use-techpack-version-differences-feature)
places two revisions side by side and highlights their differences.

**Product implication:** each accepted image edit must append an immutable
child with `parent`, `change`, `preserved`, `sources`, `prompt`, model/settings,
and status. Reject leaves the current ready version untouched. Restore creates
a branch. Compare shows the two images and the declared delta together; a row
of unrelated thumbnails is not sufficient version history.

### A generated image is not production readiness

Techpacker's [guide to fashion tech packs](https://techpacker.com/blog/design/what-is-a-tech-pack/)
describes technical flats from multiple angles, including inside views where
needed, plus construction callouts, a bill of materials, garment measurements,
colorways, and revision history. Its [jacket example](https://techpacker.com/blog/design/how-to-make-a-clothing-tech-pack/)
starts with front/back flats and close-ups before material placement, lining,
closures, hardware, and measurements.

The [Fashion Institute of Technology's Technical Design program](https://www.fitnyc.edu/academics/academic-divisions/business-and-technology/technical-design/index.php)
frames professional development as patternmaking, specification review,
technical sketching, live-model fitting, 3D fit, PLM, and production. The
program's purpose is to make garments fit and function across sizes, not merely
to make a convincing image.

**Product implication:** SOMETHINGS-ON can be a serious ideation and design-
development tool without claiming that an image is a pattern or tech pack.
Expose a progressive `SPEC` record—fit, material, construction, finish,
measurements, and unresolved questions—and clearly label manufacturing fields
as incomplete until a designer or technical designer supplies and validates
them. A fictional-model render is presentation evidence, not a fit approval.

## Required interaction model

### 1. Name the object, then describe the version

Use `OBJECT / T-SHIRT`. Put `COLOR / OPTIC WHITE`, `FIT / BOXY`, `MATERIAL /
220 GSM COTTON`, and other decisions on the active version. This leaves the
object stable while the work changes.

### 2. Edit from the current garment

Every image edit follows one visible loop:

1. select the current ready design version;
2. attach its canonical garment image first in the image-edit payload;
3. attach only the inspiration references relevant to the requested delta;
4. restate `KEEP` and one `CHANGE`;
5. preview the generated child without replacing the parent;
6. accept, reject, undo, branch, or compare;
7. use the accepted child as the first image in the next edit.

This must be the real `gpt-image-2` edit path. A React illustration may explain
controls or provide an explicit offline state; it must not masquerade as the
current garment.

### 3. Separate four kinds of change

| Request | Record as | Example |
| --- | --- | --- |
| proportion, seam, pocket, closure, physical material | `DesignVersion` | shorten body by 40 mm |
| colour/texture while geometry and construction stay linked | `Colorway` | washed charcoal to mineral olive |
| model, pose, camera, place, light | `PresentationRender` | neutral studio to exterior daylight |
| zipped/open, collar up/down, cuff adjusted | `StateView` | show the same collar fastened |

### 4. Make the current delta inspectable

The centered object needs a small, persistent version ledger:

- `VERSION / 03 · CURRENT`
- `FROM / 02`
- `CHANGE / BODY LENGTH −40 MM`
- `PRESERVED / CHEST, SLEEVE, COLLAR, FABRIC`
- `VIEWS / FRONT · BACK · BODY · DETAIL`
- `STATUS / DRAFT · ACCEPTED · REJECTED`

The chat can remain conversational, but the garment record should read like a
concise product specification.

## DevDay demo threshold

The demo is credible when it proves one real branch rather than displaying
three disconnected concepts:

1. open `T-shirt` or `Bomber jacket` with one accepted, photorealistic current
   garment;
2. show the canonical image and the active fit/material/construction record;
3. request one construction or proportion change while naming invariants;
4. send the current image plus relevant references to `gpt-image-2`;
5. receive a child version with lineage and compare it against the parent;
6. accept or reject it;
7. create an on-model presentation from the accepted version without changing
   garment truth.

Pre-generated fixtures may make that story deterministic only when their API
provenance and parent/child lineage are real and visible. They must not be
presented as evidence of a live provider call.
