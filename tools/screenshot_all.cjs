// Screenshot every built page at 1280px and 390px; report horizontal scroll and broken images.
// Usage: (serve _site on :8080) node tools/screenshot_all.cjs <outDir>
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const out = process.argv[2] || 'screenshots';
const base = process.env.BASE || 'http://localhost:8080';
const pages = [];
(function walk(d) {
  for (const f of fs.readdirSync(d)) {
    const p = path.join(d, f);
    if (fs.statSync(p).isDirectory()) { if (!['images', 'wp-content', 'assets', 'embedded-tools'].includes(f)) walk(p); }
    else if (f === 'index.html') pages.push('/' + path.relative('_site', d).split(path.sep).join('/') + (d === '_site' ? '' : '/'));
  }
})('_site');
pages.sort();
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const results = [];
  for (const width of [1280, 390]) {
    const ctx = await b.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
    await ctx.route('**/*', (r) => (r.request().url().startsWith(base) ? r.continue() : r.abort()));
    const p = await ctx.newPage();
    for (const u of pages.map((x) => x.replace('//', '/'))) {
      await p.goto(base + u, { waitUntil: 'load' });
      await p.evaluate(async () => {
        document.querySelectorAll('img[loading="lazy"]').forEach((i) => { i.loading = 'eager'; });
        await Promise.all([...document.images].map((i) => (i.complete ? null : new Promise((r) => { i.onload = i.onerror = r; setTimeout(r, 8000); }))));
      });
      await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 500) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 40)); } window.scrollTo(0, 0); });
      await p.waitForTimeout(300);
      const r = await p.evaluate(() => {
        const sw = document.documentElement.scrollWidth, cw = document.documentElement.clientWidth;
        const wide = sw > cw + 1 ? [...document.querySelectorAll('body *')].filter((e) => e.getBoundingClientRect().right > cw + 1).slice(0, 5).map((e) => e.tagName + '.' + e.className) : [];
        const broken = [...document.images].filter((i) => i.getAttribute('src') && i.getAttribute('src').startsWith('/') && i.complete && i.naturalWidth === 0).map((i) => i.getAttribute('src'));
        return { scrollWidth: sw, clientWidth: cw, hscroll: sw > cw + 1, wide, broken };
      });
      const name = (u === '/' ? 'home' : u.replace(/^\/|\/$/g, '').replace(/\//g, '--')) + '-' + width + '.jpg';
      await p.screenshot({ path: path.join(out, name), fullPage: true, type: 'jpeg', quality: 60 });
      results.push({ url: u, width, ...r });
      if (r.hscroll || r.broken.length) console.log('ISSUE', width, u, JSON.stringify(r));
    }
    await ctx.close();
  }
  await b.close();
  fs.writeFileSync('reports/screenshot-check.json', JSON.stringify(results, null, 1));
  const bad = results.filter((r) => r.hscroll || r.broken.length);
  console.log('pages:', pages.length, 'shots:', results.length, 'with issues:', bad.length);
})();
