# Tagged Reference Library + Indexed Multi-Ref Injection for gpt-image-2

## Context
Our generated portraits keep landing on the same clichés — frontal pose, even studio
light, "samey" glam — because text-to-image collapses toward the training-distribution
average. The goal: build a large library of **real** reference images, **tag** them per
attribute, and **inject** the right references into each part of the prompt (background,
makeup, pose, look) so outputs are grounded in real photos instead of invented averages.

### Feasibility verdict (the honest roast — researched, not guessed)
- **The core idea is sound but the API is a blender, not a compositor.** `gpt-image-2`
  `images.edit` accepts up to **16** reference images and **blends** them. There are
  **no per-image weights, roles, or masks, and no ControlNet (pose) / IP-Adapter (style)
  equivalents.** Indexed prompt labels ("Reference 2 = background only") only *nudge*;
  attributes bleed across refs.
- **Biggest risk: identity leakage.** A different person's face used as a makeup/pose
  donor can drag *their* features into the subject. Identity must stay Reference 1, and
  donors must be capped.
- **"Image quality / film look" is the weakest axis** — the model re-renders everything,
  so a grain/iPhone reference won't transfer sensor characteristics. Quality belongs in
  **post-processing** (`scripts/iphone7_filter.py`), not a reference slot.
- **Where the real MVP win comes from: coherent variety, not surgical isolation.**
  Grounding identity + the most cliché axes (pose, background) on real, *mutually
  coherent* photos — plus the validated amateur/imperfect-lighting recipe — is what
  escapes the generic look. Practical sweet spot is **2–4 refs**, not 16.
- **True per-attribute control exists only in open-model tooling** (FLUX/Qwen + ControlNet
  + IP-Adapter + regional prompting). Scoped as an optional Phase 3, to build **only if**
  the Phase 2 eval shows the API lane plateaus.

### Decisions
- **API lane first** (Phases 0–2); open lane is Phase 3, data-gated.
- **OpenAI vision** (gpt-4.1/4o) for captioning+tagging, **text-embedding-3-small** for
  search — reuses existing `OPENAI_API_KEY`, no new deps/keys for MVP.
- **Owned/self-shot** images → registry defaults `consent="owned"`, faces eligible as
  identity anchors.

### Intended outcome
A tag-driven pipeline that selects coherent real references, assembles a role-labeled
indexed prompt, renders via the existing gpt-image-2 driver, logs provenance, and a
harness that **measures** whether multi-ref actually beats single-ref/text-only without
increasing identity drift.

---

## Phase 0 — Shared plumbing (refactor, no behavior change)
Create an `imagegen/` package and lift reusables out of `generate.py` so the new runner
doesn't duplicate API logic:
- `imagegen/env.py` — `load_env()` lifted verbatim from `generate.py:26`; re-imported back
  into `generate.py`.
- `imagegen/paths.py` — `ROOT`, `LIBRARY_DIR=images/library/`,
  `REGISTRY=images/library/registry.json`, `OUTPUT=output/`, sidecar suffix `.meta.json`.
- `imagegen/run.py` — extract `generate.py`'s edit/generate+save block (currently
  `generate.py:71-107`) into `run_job(images, prompt, size, quality, moderation, out) ->
  [paths]`; called by both `generate.py` (CLI unchanged) and the new runner.

---

## Phase 1 — MVP: registry + ingestion + retrieval + assembler + logging

### 1a. Registry schema — `images/library/registry.json` (flat list, one record per ref)
Fields per record: `id`, `path`, `sha256`, `caption`, `axes{identity{present,descr},
background, lighting, pose, wardrobe, makeup, camera_film}`, `embedding` (float32[]),
`embedding_kind`, `rights{consent, usable_as_identity, source, notes}`, `added`.
- Controlled vocab + a `LIGHTING_COMPATIBILITY` matrix live in **`imagegen/vocab.py`**
  (closed vocab → deterministic retrieval and coherence checks).
- Owned-default: `consent="owned"`, `usable_as_identity=true` for self-shot ingests.

### 1b. Ingestion — `scripts/ingest.py`
Flow: `image(s) → sha256 dedupe → OpenAI vision caption+tags → caption embedding →
append registry.json`.
- `python3 scripts/ingest.py images/incoming/*.png [--rights owned] [--identity-ok]`
- Functions: `sha256_of(path)` (skip dupes); `auto_tag(path)` (OpenAI vision, structured
  JSON constrained to `vocab.py` axes; invalid values → `"unknown"` + warn);
  `embed(caption)` (OpenAI `text-embedding-3-small`).
- Atomic registry write (temp file + `os.replace`); idempotent.

### 1c. Retrieval / select — `imagegen/select.py`
Flow: `spec (per-axis asks) → tag filter → caption-embedding cosine rank → coherence
check → ordered ref list`.
- `pick_refs(spec, k_per_axis=1) -> SelectedRefs`: per axis, filter records matching
  `axes[axis]`, rank by numpy cosine vs the spec query embedding.
- **Identity mandatory and first**; only `rights.usable_as_identity=True` eligible as anchor.
- `check_compatibility(selected) -> [warnings]`: cross-check `lighting`/`camera_film` of
  background vs identity vs makeup donor against `LIGHTING_COMPATIBILITY` — **warn, don't
  block** (incoherent light is a top "AI-composite" tell).
- Enforce `MAX_REFS=4`; over-budget drops lowest priority (identity > background > makeup
  > pose; film-look never takes a slot).

### 1d. Prompt assembly — `imagegen/assemble.py`
Flow: `SelectedRefs + realism_preamble + spec → (ordered image list, assembled prompt,
recommended post-filter)`.
- `assemble(selected, spec, preamble_path) -> AssembledJob`. Structure, identity first:
  `<realism_preamble.txt>` → role-labeled blocks (`Reference 1 = IDENTITY (keep exact
  face/bone/skin)`, `Reference 2 = BACKGROUND only (no face)`, `Reference 3 = MAKEUP STYLE
  only (no face/hair)`) → `TARGET / PRESERVE / CHANGE ONLY / CONSTRAINTS` lines.
- Reuse proven phrasing from `prompts/same_person_edit.txt` (preserve-list + "CHANGE ONLY"
  + CONSTRAINTS) and `prompts/realism_preamble.txt`.
- **Critical invariant:** `images=[...]` order must exactly match the label order.
- When `spec.camera_film == iphone_lofi`, emit
  `recommended_post = "python3 scripts/iphone7_filter.py <out> <out_lofi> --strength …"`
  — film-look as POST, never a ref slot.

### 1e. Tag-driven runner — `scripts/render.py` (thin wrapper)
Flow: `specs/*.json → select → assemble → run_job → image + sidecar`.
- `python3 scripts/render.py --spec specs/glowup_makeup.json [--dry-run]`. Spec declares
  per-axis asks + scene/preserve/delta text. `--dry-run` prints the assembled prompt,
  chosen ref ids, and coherence warnings with **zero API spend**.
- Calls `imagegen/run.py:run_job` (shared with `generate.py`).
- **Sidecar logging:** for each `gen_<stamp>_<i>.png`, write `…png.meta.json` with spec,
  chosen ref ids+axes, full assembled prompt, model/size/quality/moderation, coherence
  warnings, recommended post-filter.

### Phase-1 files
- ADD: `imagegen/{__init__,env,paths,vocab,select,assemble,run}.py`, `scripts/ingest.py`,
  `scripts/render.py`, `images/library/registry.json` (seeded `[]`), `specs/` + one
  example spec.
- MODIFY: `generate.py` (import shared `load_env`/`run_job`; CLI unchanged),
  `.env.example` (note vision uses existing `OPENAI_API_KEY`), `.gitignore` (carve-out so
  `images/library/registry.json` is trackable despite `*.png`/`output/` ignores),
  `CLAUDE.md` + `IMAGE_REALISM_GUIDE.md` (document the flow + the honest API-lane limits).

---

## Phase 2 — A/B/C evaluation harness — `scripts/eval_abc.py`
Prove (or disprove) the idea with data. Flow: `one spec → render 3 arms → composite →
score → report`.
- Arms from the SAME spec: **(a) text-only** (`images.generate`, no images);
  **(b) single identity ref**; **(c) full multi-ref injection**.
- `python3 scripts/eval_abc.py --spec specs/glowup_makeup.json --runs 3`.
- Vision-judge scoring (OpenAI vision): `score_generic(img) -> {symmetry,
  even_studio_light, glossy_skin, centered_frontal_pose, score 0-10}` (higher = more
  generic) and `identity_drift(identity_ref, out) -> 0-1`.
- Output: `scripts/composite.py --labels "text-only|1-ref|multi-ref"` board +
  `eval/<stamp>/report.json` + sidecars. Decides whether multi-ref **reduces generic
  tells without increasing identity drift** — the honest failure mode.
- ADD: `scripts/eval_abc.py`, `eval/`. Reuses `run.py`, `select.py`, `composite.py`.

---

## Phase 3 (optional, data-gated) — open-model "power lane"
Only the route to TRUE isolation; build only if Phase 2 shows the API lane plateaus.
**FLUX.1-dev or Qwen-Image in ComfyUI, hosted on fal.ai or Replicate** (no local GPU):
ControlNet (OpenPose/Depth)=pose, IP-Adapter=style/background, PuLID/InstantID=identity
lock, regional prompting=makeup confined to face. Consumes the **same** `specs/*.json` and
registry — per-axis tags map directly onto ControlNet/IP-Adapter/region slots (this is the
payoff of tagging per-axis now). ADD later: `powerlane/fal_driver.py`,
`powerlane/comfy_workflow.json`; lib `fal-client` or `replicate`.

---

## Libraries
MVP needs **no new heavy deps**: `openai` (vision + embeddings, installed), `pillow`,
`numpy` (cosine; all installed). No `chromadb` (JSON + numpy is enough at this scale); no
`anthropic`; no local CLIP. Upgrade to local `open_clip` image embeddings later only if
caption-embedding retrieval feels weak.

## Rollout (cheapest first)
1. Phase 0 + 1a/1b — schema + ingest a handful; eyeball the auto-tags.
2. 1c/1d + `--dry-run` — select+assemble; verify prompts/coherence at **zero API spend**.
3. 1e — wire runner + sidecars; render real jobs.
4. Phase 2 — A/B/C harness; decide with data.
5. Phase 3 — only if data says so.

## Verification (end-to-end)
- **Ingest:** run `scripts/ingest.py` on 5–10 self-shot images → inspect `registry.json`
  for sane captions/tags/embeddings; re-run to confirm sha256 dedupe (no dupes added).
- **Select+assemble (no spend):** `scripts/render.py --spec … --dry-run` → confirm
  identity is Reference 1, image order matches labels, coherence warnings fire on a
  deliberately incoherent spec (e.g. `lighting=studio` bg + `lighting=warm_window` identity).
- **Render:** drop `--dry-run` → confirm output PNG + sidecar `.meta.json` with full
  provenance; eyeball that background/makeup tracked the chosen refs.
- **Eval:** `scripts/eval_abc.py --spec … --runs 3` → open the composite board + read
  `report.json`; success = arm (c) shows **lower generic score** than (a)/(b) **without**
  higher identity-drift. If not, that's the signal to invest in Phase 3.
- **Regression:** existing `generate.py` CLI still works unchanged after the Phase 0
  refactor (run a prior command, e.g. the `prompts/same_person_edit.txt` edit).
