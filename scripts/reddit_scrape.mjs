import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require('/Users/droviannykov.mykola/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');

const SUBS = ['StableDiffusion', 'FluxAI', 'comfyui'];
const Q = encodeURIComponent('photorealistic OR realism OR "skin texture"');

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({
  userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  viewport: { width: 1280, height: 900 },
  locale: 'en-US',
});
const page = await ctx.newPage();

// warm up cookies
await page.goto('https://www.reddit.com/', { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
await page.waitForTimeout(1500);

for (const sub of SUBS) {
  const url = `https://www.reddit.com/r/${sub}/search.json?q=${Q}&restrict_sr=1&sort=top&t=year&limit=20`;
  try {
    const data = await page.evaluate(async (u) => {
      const r = await fetch(u, { headers: { Accept: 'application/json' } });
      return { status: r.status, text: await r.text() };
    }, url);
    console.log(`\n=== r/${sub} (HTTP ${data.status}) ===`);
    try {
      const j = JSON.parse(data.text);
      for (const c of j.data.children) {
        const p = c.data;
        console.log(`${p.score} | ${p.title} | https://reddit.com${p.permalink}`);
      }
    } catch {
      console.log('NON_JSON', data.text.slice(0, 200));
    }
  } catch (e) {
    console.log(`r/${sub} ERROR`, String(e).slice(0, 200));
  }
}

await browser.close();
