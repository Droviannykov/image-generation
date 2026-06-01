# GPT-Image-2 Realism Guide

A portable, self-contained playbook for getting **photorealistic** results out of
OpenAI's `gpt-image-2`. Copy this file into any project — it has no project-specific
dependencies.

Sources:
- [OpenAI image-generation guide](https://developers.openai.com/api/docs/guides/image-generation)
- [OpenAI cookbook prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)

---

## TL;DR — the realism recipe

1. **Anchor on a real image** via edit / image-to-image mode whenever you have any
   source. This is the single biggest realism lever — the model modifies real pixels
   instead of inventing (and averaging toward a plastic look) from scratch.
2. **Push resolution high.** More pixels = more compute spent on fine skin/hair
   texture. Cost-no-object → go large (see size limits below).
3. **Trigger photorealism explicitly:** the words *photorealistic*, *real photograph*,
   *professional photography*, *taken on a real camera* activate the right mode.
4. **Demand imperfection:** "visible pores, fine lines, fabric wear, subtle
   imperfections… no glamorization, no heavy retouching, no plastic/CGI look." Avoid
   *flawless / perfect / smooth / beautiful* — they push toward the artificial look.
5. **On edits, repeat the preserve-list** every iteration and **end with a constraints
   line** ("no text, no watermark, no border"). This kills drift and invented artifacts.
6. **Match the recipe to the image type.** The "amateur snapshot" recipe is the single
   strongest realism lever — but **only for casual imagery**. Applying it to a
   clinical/studio shot breaks the intended look. See *Realism recipes by image type*.

---

## Why grounding on a real photo wins (the key insight)

| | Text-to-image (from scratch) | Image-to-image (edit) |
|---|---|---|
| Source of detail | Model invents every pixel | Inherits real pore texture, subsurface scattering, asymmetry, sensor noise, lens falloff |
| Failure mode | Averages toward idealized, smooth, plastic faces | Spends effort only on the *change* |
| Identity | Can't reproduce a specific person | Preserves identity from the reference |

`gpt-image-2` **automatically processes image inputs at high fidelity** (no
`input_fidelity` param needed — that was a `gpt-image-1` thing). That auto-fidelity is
why identity holds so well in edit mode.

---

## API parameters that affect quality

| Parameter | Values | Recommendation |
|---|---|---|
| `quality` | `low` / `medium` / `high` / `auto` | **`high`** for final assets; `low` for drafts |
| `size` | up to **3840×2160**, total **≤8,294,400 px** (≥655,360), each edge a **multiple of 16**, long:short **≤3:1** | Go high. Good picks: `2048x2048`, `3072x2048`, `3840x2160` |
| `input_fidelity` | (gpt-image-1 only) | **Omit** — gpt-image-2 is high-fidelity automatically |
| `output_format` | `png` / `jpeg` / `webp` | **`png`** (lossless, no compression artifacts) |
| `output_compression` | 0–100 (jpeg/webp only) | N/A if using png |
| `background` | `auto` / opaque | gpt-image-2 does **not** support `transparent` |
| `moderation` | `auto` / `low` | **`low`** for clinical/medical/aesthetic imagery to avoid false refusals |
| `n` | integer | Generate several, pick the best |
| `partial_images` | 0–3 | Streaming preview only (UX, not quality); +100 tokens each |

**Edits:** one or more reference images supported. Masks supported (same
format/size as the base, with alpha channel) but are **prompt-guided, not
pixel-precise**.

---

## Prompting best-practices

**Structure (in this order):** `scene/background → subject → key details → constraints`.
Use short labeled segments or line breaks, not one long paragraph.

**Photorealism cues:**
- Trigger words: *photorealistic, real photograph, professional photography, captured on a real camera in the moment*.
- Camera/lens/lighting as *look* (not exact physics): "medium close-up at eye level, 50mm lens, soft daylight, shallow depth of field, subtle film grain, natural color balance."
- Texture/imperfection: "real skin texture with visible pores and fine lines, worn materials, everyday detail. No glamorization, no heavy retouching."

**Editing an existing image:**
- "Change ONLY X." + "Keep everything else the same."
- **List the invariants** to preserve: identity, bone structure, geometry, layout,
  labels, camera angle, lighting, surrounding objects, colors.
- **Repeat the preserve-list on every iteration** to reduce drift.

**Multi-image / compositing:** reference each input by index and describe how they
interact — "Image 1: product photo… Image 2: style reference… put the X from Image 1
onto the Y in Image 2."

**Iteration:** start from a clean base prompt, then refine with small **single-change**
follow-ups ("warm the lighting", "restore the original background"). Re-specify
critical details if they start to drift.

**Always end with a constraints line:** "No text, no labels, no watermarks, no borders."
The model invents these unless told not to.

**Text rendering:** put exact copy in "quotes" or ALL CAPS; spell tricky words letter
by letter.

---

## Realism recipes by image type (validated on gpt-image-2)

**Core lesson, confirmed by experiment:** match the recipe to the image type. The
amateur-snapshot recipe produces the most convincing realism, but only for *casual*
imagery; for *clinical/studio* shots the polished look is correct and the snapshot cues
must be dropped. Camera/texture/DoF cues transfer to both.

### Candid / amateur (strongest realism)
- Frame as a snapshot, not a shoot: "amateur snapshot, candid, unposed, slightly
  imperfect framing, mid-action."
- **Imperfect lighting is the #1 tell that sells it:** "on-camera flash mixed with warm
  indoor + cool window light, uneven exposure, one blown-out highlight, hard flash
  shadow on the wall behind." (Even, consistent lighting is the giveaway that an image
  is AI — real snapshots have messy light.)
- Device: "mobile phone photo, older smartphone / CCD aesthetic, subtle digital noise."
- **Deep DoF, no bokeh:** phones keep the background sharp — "deep depth of field,
  background fully in focus, no bokeh." (Models default to background blur.)
- Ordinary subject: "uncommon real-looking face, subtle natural asymmetry, not a model;
  flyaway hairs, freckles, faint blemishes."

### Clinical / studio / professional
- Even, polished lighting is *correct here* — do **not** add flash or uneven exposure.
- Concrete capture spec: "shot on Canon EOS R5, 85mm f/8, softbox + ring lighting."
- Deep DoF still applies: clinical photos are sharp throughout — "entire face sharp,
  background in focus, no bokeh."
- Micro-texture + anti-plastic: "visible micro-pores, fine lines, subtle specular
  highlights, natural skin-tone variation; no plastic/waxy CGI sheen, no airbrushing."
- Preserve subtle facial asymmetry so identity reads as real.

### Universal cues (any image type)
- Concrete camera + lens + film beats "professional photo": "shot on Fujifilm X-T5,
  35mm f/1.4", "35mm film grain".
- Micro-pore / specular-highlight language plus an explicit anti-plastic line.
- Kill default bokeh unless you genuinely want shallow depth of field.
- Specify uncommon, slightly asymmetric features to defeat "sameface".

### Structured (JSON) prompts — experimental, unverified
Feed a reference image to an LLM, get back a JSON spec (subject / face / photography /
background), and pass that as the prompt. Popular for organizing complex scenes with
LLM-encoder models like gpt-image-2. Contested (CLIP-based encoders ignore structure);
A/B test against plain prose rather than assuming it helps.

### Beyond the API (downstream pipeline, not OpenAI)
- **Two-stage refine:** base generation → low-denoise (~0.4) pass on skin. Approximate
  in gpt-image-2 by re-editing your own output ("enhance realistic skin texture and
  pores, keep identity").
- **Skin-specific upscalers** beat generic ones for portraits: Magnific Skin Enhancer,
  SeedVR2 (downscale to 0.35 MP *first*), Topaz. Rule: fix structure before upscaling —
  "don't rely on upscaling to fix AI artifacts."
- **Open-weight realism leaders (early 2026)**, if ever self-hosting: Qwen-Image-2512,
  Z-Image (Turbo/Base), FLUX.2 Klein, WAN 2.2; realism LoRAs UltraReal / Lenovo /
  Amateur Photography / Juggernaut Pro FLUX. Heavy VRAM; relevant only off-API.

---

## What to avoid (the "AI sheen")

- Adjectives like *flawless, perfect, smooth, beautiful, stunning, hyper-detailed*.
- "Studio polish / staged / retouched" language when you want candid realism.
- Over-stuffed single prompts — scope one change per generation.
- Pure text-to-image when a reference image is available.

---

## Reference example (OpenAI's portrait prompt)

> "Create a photorealistic candid photograph of an elderly sailor standing on a small
> fishing boat. He has weathered skin with visible wrinkles, pores, and sun texture…
> Shot like a 35mm film photograph, medium close-up at eye level, using a 50mm lens.
> Soft coastal daylight, shallow depth of field, subtle film grain, natural color
> balance. The image should feel honest and unposed, with real skin texture, worn
> materials, and everyday detail."

---

## Using this in code (this project's `generate.py`)

```bash
# Text-to-image with the reusable realism preamble prepended
python3 generate.py --prompt-file prompts/<file>.txt \
  --preamble prompts/realism_preamble.txt \
  --size 2048x2048 --quality high --moderation low

# Image-to-image / edit (preserves identity from a reference)
python3 generate.py --prompt-file prompts/same_person_edit.txt \
  --image images/<ref>.png \
  --size 3072x2048 --quality high --moderation low

# Several variations to pick from
python3 generate.py "<prompt>" --n 3 --size 2048x2048
```

Key files:
- `prompts/realism_preamble.txt` — drop-in realism cues to prepend to any prompt.
- `prompts/same_person_edit.txt` — full edit prompt in the recommended structure.
