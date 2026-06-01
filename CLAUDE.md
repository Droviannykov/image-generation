# CLAUDE.md

## Project Overview
Image generation with OpenAI `gpt-image-2`. We recreate / generate photorealistic
images (e.g. clinical before-and-after aesthetic portraits) from prompts and reference
images.

## IMPORTANT — always reference the realism guide
**Before generating any image, read [`IMAGE_REALISM_GUIDE.md`](./IMAGE_REALISM_GUIDE.md)
and follow its recipe and parameter recommendations.** It is the source of truth for how
we get realistic results. Keep it updated when we learn something new.

Core recipe (full detail in the guide): anchor on a real image via edit mode → push
resolution high → trigger words (*photorealistic / real photograph*) → demand
imperfection ("visible pores, no retouching") → on edits, repeat the preserve-list and
end with a constraints line.

## Common Commands
```bash
# Edit / image-to-image (preserves identity from a reference)
python3 generate.py --prompt-file prompts/same_person_edit.txt \
  --image images/<ref>.png --size 3072x2048 --quality high --moderation low

# Text-to-image with the reusable realism preamble
python3 generate.py --prompt-file prompts/<file>.txt \
  --preamble prompts/realism_preamble.txt --size 2048x2048 --quality high
```

## Layout
- `generate.py` — gpt-image-2 driver (text-to-image + `--image` edit mode).
- `prompts/` — prompt files; `realism_preamble.txt` is the reusable realism block.
- `images/` — reference inputs. `output/` — generated results (git-ignored).
- `.env` — holds `OPENAI_API_KEY` (git-ignored).

## Do's and Don'ts
- DO prefer image-to-image (edit) over text-to-image whenever a reference exists.
- DO use `--quality high` and large `--size`; cost is not a constraint here.
- DON'T use adjectives like *flawless / perfect / smooth* — they cause the plastic look.
- DON'T reproduce a real person's likeness without confirmed rights/consent.
