# Product brief

## Working idea

**SOMETHINGS-ON** is a guided studio for emerging fashion designers. It turns a loose field of screenshots, links, photos, labels, and half-formed preferences into a visible design conversation: collect, name what matters, change one thing, compare, and continue.

The name is an homage to Virgil Abloh and Nike's *Something's Off*: a small verbal turn from deconstruction toward the moment an idea starts working. The product must not imply endorsement or borrow the publication's visual identity.

The product is not a one-click clothing generator. Its value is the guided path from taste to an authored decision.

## Audience

The first user is a visually literate emerging designer who has strong taste but may not yet have formal fashion vocabulary, a team, or expensive tools. They often work from camera-roll images, browser tabs, saved posts, sketches, and piles of references.

## Core promise

Bring what catches your eye. SOMETHINGS-ON helps you understand why it matters and turn that understanding into a design that is recognizably yours.

## Experience arc

1. **Arrive** — a nearly black screen slows the pace and asks for one deliberate start.
2. **Set the room** — music and a 30-second pause are offered, never required or autoplayed.
3. **Locate taste** — select a few labels as hypotheses, then confirm or reject the traits inferred from them.
4. **Name the object** — choose one durable garment category, such as a T-shirt. Color belongs to the active version.
5. **Gather evidence** — add screenshots, URLs, phone photos, or other references; one is enough.
6. **Open the studio** — references land as a starter pile around one centered object. Chat remains on the left.
7. **Make a change** — choose one quality to carry forward and one variable to alter.
8. **Compare and branch** — preview, accept, reject, undo, or branch each generated version.

## Onboarding copy direction

Use short, permissive language. Key lines for the first build:

- `Start with what you notice.`
- `Put on something you love. We'll wait. Silence works too.`
- `Take 30 seconds. Breathe at your own pace. We'll keep the time.`
- `You don't need the whole idea.`
- `Which labels do you return to?`
- `What are we making first?`
- `Show us what you mean.`
- `Keep what matters. Change one thing.`

Avoid faux-spiritual language, performance pressure, and hype. Always expose skip, back, sound-off, and reduced-motion paths.

## First vertical slice

The hackathon slice proves one continuous flow:

- complete or skip the opening ritual;
- choose 3–5 labels from the initial catalog;
- name `T-shirt` or another durable garment category, then record white or another color on the active version;
- add 1–3 local image references; pasted URLs may be saved as link cards but are not fetched server-side in the first slice;
- arrive in a workspace with chat left, object centered, and references arranged around it;
- ask the agent to analyze selected references;
- request one reference-conditioned `gpt-image-2` iteration;
- receive a new version card with the prompt, source lineage, and accept/reject/undo affordances.

## Initial state model

The frontend should be able to represent the first slice without waiting for persistence:

- `project`: id, title, object type, created time
- `tasteProfile`: selected labels, approved traits, rejected traits
- `references`: id, kind, source, local preview, analysis, position, pile id
- `designVersions`: id, parent id, image URL, change summary, prompt, source reference ids, status
- `canvas`: viewport, object positions, pile membership, selected object id
- `conversation`: ChatKit thread id and active design/reference context

## Non-goals for the first slice

- production-ready authentication or multi-user collaboration
- manufacturing specifications, grading, or tech packs
- a marketplace or public social feed
- automatic scraping of authenticated social networks
- exact brand/style replication
- photorealistic virtual try-on

These may become future tracks, but they must not dilute the first authored edit loop.
