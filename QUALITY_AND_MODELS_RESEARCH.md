# Quality & Model Research — Reference-Driven Photorealism

Research + decisions for maximizing photorealistic quality and beating the "generic AI
look" in our gpt-image-2 portrait pipeline. Companion to `REFERENCE_LIBRARY_PLAN.md`.
Last updated 2026-05-30. **Status: paused — resume here.**

---

## Locked decisions (so far)
- **Quality target:** *Quality-first API MVP* — gpt-image-2 + **masked/sequential editing**
  + **high resolution** + **post-process skin/film pass**. Highest fidelity without
  leaving the API.
- **Build order:** *Quality pipeline first* — prove the masked/sequential + post-process
  pipeline on a few hand-picked references **before** building the tagging/retrieval
  library.
- Earlier: API lane first; OpenAI vision for tagging; owned/self-shot image rights.
- Open-model lane = the quality *ceiling*, deferred. Nano Banana = identity hedge, deferred.

---

## The quality ranking (what actually moves photorealism, most → least)

1. **Editing STRATEGY beats reference COUNT.** Dumping multiple refs into one blended
   `images.edit` call degrades quality (blend-mush, soft artifacts). **Masked + sequential
   editing is the single best quality move on the API**: each stage is a focused edit, and
   everything outside a mask stays **pixel-perfect from the real photo** — retaining
   genuine photographic texture instead of letting the model re-render (and plastic-ify)
   the whole frame.

2. **Open-model lane is the true ceiling.** For *extreme* photorealism nothing closed
   beats FLUX/Qwen + ControlNet/IP-Adapter **plus a dedicated skin upscaler** (Magnific
   Skin Enhancer / SeedVR2). Heaviest path; deferred.

3. **Post-processing is a reliable multiplier** on any lane: skin/film pass (we already
   have `scripts/iphone7_filter.py`) + high resolution. Real photos aren't clean; a light
   grain/texture pass consistently reads more real.

4. **Model choice is a smaller lever than expected.** gpt-image-2 = better precise,
   instruction-faithful edits + texture control. Nano Banana = better identity
   consistency, *not* raw quality, exact-likeness mixed. So Nano Banana is an identity
   hedge, not a quality upgrade.

---

## Workarounds to the API's limits (researched)

### W1 — Masked / regional editing = the API's native pseudo-isolation (BIG)
`gpt-image-2`'s edit endpoint **accepts an optional mask** (PNG; transparent = edit
region, opaque = preserve — **verify polarity empirically**, sources conflict; mask must
match image dimensions). Apply a reference's influence to **one region only** (makeup →
face mask; background → background mask). Prompt-only region inference is unreliable for
small edits, so **generate precise masks** (face/skin segmentation: mediapipe / `rembg` /
a cheap seg model). Mitigates blending *and* identity leakage, and preserves real texture
outside the mask = higher fidelity.

### W2 — Sequential / layered editing instead of one blended call (BIG)
Build in stages, **one reference per step**, feeding each output into the next:
1. BACKGROUND (background ref) → 2. inpaint SUBJECT (identity ref) →
3. inpaint MAKEUP on the masked face (text or eyes-only crop — never a foreign face) →
4. POSE from the identity ref / text at step 2.
Each ref acts in isolation → far less cross-bleed; reuses `run_job` iteratively.
Cost: more calls (~$0.07 standard / ~$0.19 high per image — acceptable).

### W3 — Identity-leak mitigations (always on)
Never pass a foreign full face as a makeup/pose donor. Instead: (a) describe makeup/pose
in TEXT, (b) crop the donor to a non-identifying region (eyes-only for shadow, silhouette
for pose), or (c) apply via mask to the subject's own face. Keep the identity ref first
and ideally the only face in the input set.

### W4 — Alternative model lanes (provider bake-off) — DEFERRED
Make the runner provider-pluggable so the same spec/registry can target multiple models.

| Model | Multi-ref / identity | Mask/regional | API (automatable) | Note |
|---|---|---|---|---|
| **gpt-image-2** (baseline) | up to 16, blends | **yes (mask)** | yes (OpenAI) | best instruction-following + in-image text |
| **Nano Banana Pro** (Gemini) | **identity-lock, up to 14 refs / 5 chars** | partial | yes (Gemini API) | best identity consistency, fast (3–5s); exact-likeness mixed → verify; needs `GEMINI_API_KEY` |
| **FLUX.2 Pro / FLUX.1 Kontext** | strong in-context edit | yes | yes (fal/Replicate/BFL) | strong reference editing |
| **Seedream 4.0** | strong | yes | yes (fal) | strong editing alt |
| **Midjourney Omni-Ref** | per-ref **weight dial** (`--ow` 0–1000), `--sref` style | no | **no official API** | only one with explicit per-ref weight; manual/Discord only |

---

## Recommended path when we resume

**Quality-first API MVP (build first):**
1. **Mask utility** — `imagegen/mask.py`: face / skin / background segmentation → PNG mask
   matching the source dimensions. Verify mask polarity against the API empirically on the
   first run.
2. **Sequential render mode** — extend `scripts/render.py` (or a `--sequential` flag /
   `imagegen/pipeline.py`) to run the staged background → subject → makeup pipeline,
   chaining `run_job`, one reference per stage, high quality + high resolution.
3. **Post-process skin/film pass** — reuse `scripts/iphone7_filter.py` (and/or a lighter
   grain/texture variant) as the final step; emit the recommended command in the sidecar.
4. **Hand-picked refs** — skip the registry for now; pass a few curated real images
   directly to prove the quality pipeline. (Tagging/retrieval library is deferred.)
5. **Eyeball + iterate** — compare blended single-call vs. masked-sequential on the same
   target to confirm the fidelity gain before investing further.

**Deferred (data-gated / later):**
- Tagged reference library + retrieval (`imagegen/{vocab,select,assemble}.py`,
  `scripts/ingest.py`, `registry.json`) — already scaffolded in the repo; wire in once the
  quality pipeline is dialed.
- Provider abstraction + **Nano Banana** lane (identity hedge).
- **Open-model ceiling**: FLUX/Qwen + ControlNet + IP-Adapter + Magnific/SeedVR2 skin
  upscaler — the route to *extreme* photorealism if the API plateaus.

---

## Already scaffolded in the repo (Phase 0/1 from the earlier session)
- `imagegen/` package: `env.py`, `paths.py`, `run.py` (shared `run_job`), `vocab.py`,
  `select.py`, `assemble.py`.
- `scripts/ingest.py` (auto-tag + embed), `scripts/render.py` (tag-driven runner + dry-run
  + sidecars).
- `generate.py` refactored to use the shared `load_env` / `run_job`.
- NOTE: these were created but **not yet run/verified** — and the chosen path defers the
  library, so the immediate next work is the mask + sequential + post-process pipeline.

---

## Sources
- [GPT Image 2 vs Nano Banana 2 (2026) — CometAPI](https://www.cometapi.com/gpt-image-2-vs-nano-banana-2/)
- [GPT-Image-2 vs Nano Banana Pro — Apiyi](https://help.apiyi.com/en/gpt-image-2-vs-nano-banana-pro-comparison-en.html)
- [Best AI Image Editing Models 2026 — Atlas Cloud](https://www.atlascloud.ai/blog/guides/best-ai-image-editing-models-2026)
- [gpt-image-2 Edit API developer guide — AI API Playbook](https://aiapiplaybook.com/blog/openai-gpt-image-2-edit-api-complete-developer-guide/)
- [Midjourney Omni Reference docs](https://docs.midjourney.com/hc/en-us/articles/36285124473997-Omni-Reference)
- [ComfyUI ControlNet + IP-Adapter workflow](https://comfyui.org/en/image-style-transfer-controlnet-ipadapter-workflow)
- [Comfy.org — The Complete AI Upscaling Handbook (skin upscalers)](https://blog.comfy.org/p/upscaling-in-comfyui)
