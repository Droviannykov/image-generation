# image-generation

A toolkit for generating **photorealistic** images with OpenAI's `gpt-image-2` — text-to-image, image-to-image (edit/identity-preserving), and a tag-driven multi-reference pipeline. Built for recreating clinical before-and-after aesthetic portraits and similar high-realism work.

The core philosophy: anchor on a real reference image, push resolution high, trigger photorealism, and demand imperfection ("visible pores, no retouching") rather than the plastic "flawless" look. See **[`IMAGE_REALISM_GUIDE.md`](./IMAGE_REALISM_GUIDE.md)** for the full recipe — it's the source of truth.

## Setup

Requires Python 3.10+.

```bash
# Install dependencies
pip install openai pillow numpy

# Configure your API key
cp .env.example .env
# then edit .env and set OPENAI_API_KEY=sk-...
```

`.env` is git-ignored — your key never leaves your machine.

## Usage

### Text-to-image
```bash
python3 generate.py "your prompt here"

# with the reusable realism preamble, large and high quality
python3 generate.py --prompt-file prompts/before_after.txt \
  --preamble prompts/realism_preamble.txt --size 1536x1024 --quality high
```

### Image-to-image (edit / identity-preserving)
Whenever a reference exists, prefer edit mode — it preserves identity far better than text alone.

```bash
python3 generate.py --prompt-file prompts/same_person_edit.txt \
  --image images/<ref>.png --quality high --moderation low
```

`--image` is repeatable to blend multiple references. `--moderation low` is useful for clinical/medical imagery.

Generated PNGs land in `output/` (git-ignored) with timestamped filenames.

### Key flags

| Flag | Default | Notes |
|------|---------|-------|
| `--prompt-file` | — | Read the prompt from a file instead of the CLI arg |
| `--image` | — | Reference image(s); repeatable, enables edit mode |
| `--preamble` | — | File prepended to the prompt (e.g. `prompts/realism_preamble.txt`) |
| `--size` | `1024x1024` | `1536x1024` (landscape), `1024x1536` (portrait), or `auto` |
| `--quality` | `high` | `low` / `medium` / `high` / `auto` |
| `--moderation` | `auto` | `low` = less restrictive filtering |
| `--n` | `1` | Number of images |
| `--out` | `output` | Output directory |

## Layout

```
generate.py        gpt-image-2 driver (text-to-image + --image edit mode)
imagegen/          shared library
  run.py             gpt-image-2 call + save logic
  env.py             minimal .env loader (no extra deps)
  paths.py           canonical project paths
  select.py          reference selection: tag filter → embedding rank → coherence check
  assemble.py        role-labeled multi-reference prompt assembly
  vocab.py           controlled tag vocabulary + compatibility rules
prompts/           prompt files; realism_preamble.txt is the reusable realism block
scripts/
  render.py          tag-driven renderer: spec → select refs → assemble → render
  ingest.py          ingest real references into the tagged library (vision caption + embed)
  composite.py       composite N images side by side with captions
  iphone7_filter.py  post-process to mimic an old iPhone 7 snapshot look
  reddit_*.mjs       scrape photorealism technique threads (Playwright)
images/            reference inputs (library/ + incoming/)
output/            generated results (git-ignored)
```

## Tag-driven pipeline

For repeatable, multi-reference renders, `scripts/render.py` drives a spec → selection → assembly flow against a tagged reference library (`images/library/`). Build the library with `scripts/ingest.py`, then:

```bash
python3 scripts/render.py --spec specs/glowup_makeup.json --dry-run  # zero API spend
python3 scripts/render.py --spec specs/glowup_makeup.json            # render
```

See [`REFERENCE_LIBRARY_PLAN.md`](./REFERENCE_LIBRARY_PLAN.md) and [`QUALITY_AND_MODELS_RESEARCH.md`](./QUALITY_AND_MODELS_RESEARCH.md) for design notes.

## Notes

- **DO** prefer image-to-image over text-to-image whenever a reference exists.
- **DO** use `--quality high` and large `--size`.
- **DON'T** use adjectives like *flawless / perfect / smooth* — they cause the plastic look.
- **DON'T** reproduce a real person's likeness without confirmed rights/consent.
