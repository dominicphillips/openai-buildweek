# Design principles

## Responsible basis

This product draws process-level inspiration from documented parts of Virgil Abloh's practice: restrained edits to familiar forms, visible process, mixing established and street languages, storytelling through garments, openness to nontraditional entrants, and respect for curiosity as a creative force.

It does not copy his visual codes, simulate his voice, present a legal rule, or imply endorsement. “Three percent” is treated as a metaphor for an intentional small delta, not a measurable originality threshold.

## Product principles

### Start from evidence

Begin with an archetype or a reference the designer supplies. Ask what must remain before proposing what could change.

### Change one meaningful variable

Localize each iteration: proportion, material, construction, finish, placement, color, or mood. Small scope should sharpen authorship, not reduce ambition.

### Make process visible

Show source references, the current version, the requested change, and the resulting branch together. A designer should be able to explain how an outcome emerged.

### Preserve agency

The agent proposes and operates; the designer chooses. Preview every mutation and keep reject, undo, and branch available.

### Translate taste, do not clone it

Turn selected labels into neutral traits that users can approve or remove. Never prompt for “a [brand] design,” copy logos or signature graphics, or claim a style transfer is original simply because a small percentage changed.

### Welcome tourist and purist

Let a newcomer work in plain language while progressively exposing expert controls for silhouette, fabric, seam, construction, finish, and placement. Neither surface should feel like a lesser mode.

### Keep the studio tactile

References should collect like working piles, not database rows. Preserve overlap, imperfect alignment, notes, tape-like labels, and spatial memory while keeping controls accessible.

### Use motion as orientation

Fades and spatial movement should explain where the designer is going and what changed. Respect `prefers-reduced-motion`, avoid long unskippable sequences, and never make animation the only carrier of state.

### Keep ritual optional

Music, breathing, and a pause may create room for attention, but they are not therapy and not a gate. No autoplay; offer immediate skip and silent paths.

## Image-generation rules

- Default drafts to low quality for iteration speed; move to medium/high only when the designer chooses to refine.
- Use the current design as the first reference and attach only references relevant to the requested delta.
- Ask the model to preserve named invariants and state the one intended change.
- Record model, prompt, parent version, reference ids, output settings, and request id where available.
- Do not request transparent output from `gpt-image-2`; it is not supported.
- Treat moderation and user-correctable errors as product states with neutral guidance.

## A useful agent question

“What should stay exactly as it is, and what is the one thing you want to move?”
