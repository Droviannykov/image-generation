import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require('/Users/droviannykov.mykola/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');

// High-signal threads for transferable photorealism technique
const PATHS = [
  '/r/FluxAI/comments/1p8t8m4/want_realistic_looking_images_use_json',
  '/r/comfyui/comments/1oxv8f1/next_level_realism_with_qwen_image_is_now',
  '/r/StableDiffusion/comments/1ll3yat/yet_another_attempt_at_realism_7_images',
  '/r/comfyui/comments/1qxtmlc/the_complete_ai_upscaling_handbook_all_in_comfyui',
  '/r/StableDiffusion/comments/1qt5vdw/qwenimage2512_is_a_severely_underrated_model',
  '/r/comfyui/comments/1purl16/ultimate_promptbuilder_for_zimagefluxnanobanana',
];

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({
  userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  viewport: { width: 1280, height: 900 }, locale: 'en-US',
});
const page = await ctx.newPage();
await page.goto('https://www.reddit.com/', { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
await page.waitForTimeout(1200);

for (const p of PATHS) {
  const url = `https://www.reddit.com${p}.json?limit=40&sort=top`;
  try {
    const data = await page.evaluate(async (u) => {
      const r = await fetch(u, { headers: { Accept: 'application/json' } });
      return { status: r.status, text: await r.text() };
    }, url);
    const j = JSON.parse(data.text);
    const post = j[0].data.children[0].data;
    console.log(`\n\n######## ${post.title} (score ${post.score}) ########`);
    if (post.selftext) console.log('SELFTEXT:\n' + post.selftext.slice(0, 2500));
    const comments = j[1].data.children
      .filter(c => c.kind === 't1' && c.data.body)
      .sort((a, b) => b.data.score - a.data.score)
      .slice(0, 8);
    for (const c of comments) {
      console.log(`\n--- comment (score ${c.data.score}) ---\n` + c.data.body.slice(0, 1200));
    }
  } catch (e) {
    console.log(`\n${p} ERROR`, String(e).slice(0, 150));
  }
}
await browser.close();
