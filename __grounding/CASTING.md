# Casting and lookbook presentation

## Decision

SOMETHINGS-ON may place a finished design on an original fictional adult model for a lookbook view. Casting presets are art-direction bundles: they describe styling context, pose, setting, light, and camera attitude. They do not describe what people from a nationality, gender, profession, body type, or other group are supposedly like.

The deliberately conversational preset names `Edgy European Guy` and `Nerdy Tech Girl` are treated as mood-board shorthand only:

- `Edgy European Guy` means an after-dark, old-city editorial treatment. It never infers European nationality, ancestry, accent, or behavior, and its casting can vary across any origin.
- `Nerdy Tech Girl` means a precise, playful creative-studio treatment. It never equates glasses, gender, intelligence, occupation, or social behavior. Every subject is explicitly an adult.

Show this framing at the chooser, not only in policy copy. A preset must remain useful when every casting control is changed.

## Product boundary

A casting render presents a design; it is not a new design.

```text
DesignVersion (immutable garment truth)
    |
    +-- PresentationRender A (preset + casting controls + generated asset)
    +-- PresentationRender B (different presentation, same garment truth)
    +-- PresentationRender C (different presentation, same garment truth)
```

- `DesignVersion` remains immutable and retains its garment image, parent, requested delta, prompt, and reference lineage.
- `PresentationRender` is a separate asset linked to exactly one `design_version_id`. It stores `preset_id`, an immutable snapshot of the casting controls, the assembled presentation prompt, global and local avoid lists, generation settings, output asset id, status, and timestamps.
- Changing the model, pose, setting, or lighting creates another `PresentationRender`; it never overwrites a design image or appends a `DesignVersion`.
- Reject, retry, and delete affect only the presentation asset. Returning to the design always restores the linked canonical design image.
- A garment edit requested from a lookbook view branches from the linked `DesignVersion`, not from the model composite. This prevents pose, body, or scenery from entering garment lineage.
- The generation request uses the canonical garment image as its first reference and names cut, construction, color, graphics, finish, and placement as invariants. The model and scene are presentation-only variables.
- A render that materially changes, hides, or invents garment details should be marked `garment drift` and not saved as a successful lookbook view.
- Lookbook renders are editorial visualizations, not virtual try-on, sizing, fit, or body-prediction evidence.

A minimal presentation record can use this shape:

```text
id
design_version_id
preset_id
casting_controls_snapshot
prompt
avoid_list
asset_id
status: queued | running | ready | failed | rejected
created_at
```

## Preset contract

The committed seed is `backend/seeds/casting_presets.json`. Each preset has:

- a stable machine `id` that survives later display-copy changes;
- a user-facing `display_name`;
- `one_line_mood`, `wardrobe_context`, `pose`, `setting`, and `lighting`;
- `casting_variation_guidance` for body, skin tone, presentation, adult age, and pose/access needs;
- a `prompt_fragment` that can be combined with the canonical garment-invariant prompt; and
- a local `avoid_list`, appended after the collection-wide rules.

Preset fields never hard-code ethnicity, nationality, skin tone, body shape, disability, or gender identity. Those choices remain independent controls. The eight initial presets are fictional visual directions, not imitations of campaigns, publications, photographers, labels, living designers, celebrities, influencers, or other real people.

Only `prompt_fragment` enters the image prompt. `display_name` is chooser copy and must not be passed to the model; this keeps conversational titles from activating stereotypes.

## Casting controls

Expose the controls under `Vary the casting`; leave them collapsed until the designer wants them. `Varied` is the default for every dimension.

- **Body build** — varied, lean, straight, soft, muscular, broad, or full. This describes a generated adult body's visible build, never health, worth, or garment size.
- **Stature** — varied, short, medium, or tall. Do not make height a proxy for body build.
- **Skin tone** — varied or one of six neutral tonal ranges from deep through light. Skin tone is independent of facial structure, nationality, and preset.
- **Presentation** — varied, feminine, masculine, androgynous, or mixed cues. This is visible styling direction, not a claim about gender identity.
- **Adult age** — varied adult, 25–39, 40–59, or 60+. Never generate a minor or use youth-coded school styling.
- **Pose/access** — standing, seated, or mobility-aid-aware. A wheelchair, cane, crutches, prosthesis, or limb difference may be included when selected; treat it as ordinary casting, keep the whole garment legible, and avoid medicalized framing.
- **Continuity** — new fictional casting or keep this generated character. Continuity may reuse a generated presentation character id, but never a named or identifiable real person's likeness.

Controls are an immutable snapshot on each render. Do not infer one control from another, from the preset label, or from user-uploaded references. Randomized output should rotate adult age, body, skin tone, and presentation across a project rather than repeatedly converging on a single beauty norm.

## Originality and safety rules

The prompt assembler always adds these collection-wide rules, even if a preset is later edited:

1. Create one original fictional adult, visibly and explicitly age 25 or older.
2. Do not name, resemble, or invite comparison to a real person, celebrity, influencer, model, photographer, or living designer.
3. Do not use a brand, logo, trademark, signature graphic, recognizable campaign, magazine identity, or named style.
4. Preserve the linked garment design exactly. Add only neutral, unbranded supporting pieces that do not cover it.
5. Do not infer protected traits, personality, intelligence, occupation, health, or behavior from a preset name or appearance.
6. Avoid sexualization, fetish framing, age ambiguity, body shaming, caricature, exoticism, and tokenism.
7. Keep pose, crop, and contrast sufficient to inspect the complete garment.

If a designer enters a celebrity, brand, nationality stereotype, or exact-campaign request, retain the design but neutralize the direction into editable visual traits such as `cool overhead light`, `off-center stance`, or `raw masonry setting`. A future consented-self mode would require a separate likeness and privacy contract; casting presets do not accept real-person references.

## UX copy

Chooser entry:

- Action: `Style it on a model`
- Eyebrow: `CASTING DIRECTION`
- Heading: `Choose a point of view, not a person.`
- Body: `These fictional editorial setups change the pose, place, and light. Your design stays untouched.`
- Helper: `Preset names describe the image treatment—not anyone's nationality, identity, job, or personality.`
- Controls label: `Vary the casting`
- Controls helper: `Body, skin tone, age, and presentation move independently. Leave any field open for a new adult fictional model.`
- Policy note: `Adults only. No real-person lookalikes, celebrities, brands, or borrowed campaigns.`
- Primary action: `Make a lookbook view`

Render state:

- Link label: `Presentation of {version}`
- Invariant badge: `DESIGN UNCHANGED`
- Retry action: `Try another casting`
- Navigation action: `Back to the design`
- Drift error: `The garment changed in this render, so we didn't save it. Try again with fewer presentation changes.`
- Failure: `That lookbook view didn't finish. Your design is safe.`

The UI should show the linked version beside every presentation asset and never put a presentation render in the design-version stack.
