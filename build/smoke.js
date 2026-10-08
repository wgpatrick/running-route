// Local smoke test: wraps the page in the artifact skeleton, serves Leaflet locally, screenshots.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const out = process.argv[2];
(async () => {
  const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body style="margin:0">' +
    fs.readFileSync(path.join(__dirname, '../dist/sf-morning-runs.html'), 'utf8') + '</body></html>';
  const tmp = path.join(out, 'page.html'); fs.writeFileSync(tmp, html);
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' }).catch(() => chromium.launch());
  for (const [name, vp, scheme] of [['desktop', { width: 1400, height: 900 }, 'light'], ['phone', { width: 400, height: 860 }, 'dark']]) {
    const ctx = await browser.newContext({ viewport: vp, colorScheme: scheme });
    const page = await ctx.newPage();
    page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log(name, 'console', m.type(), m.text()); });
    page.on('pageerror', e => console.log(name, 'pageerror', e.message));
    await page.route('**/leaflet.min.js', r => r.fulfill({ contentType: 'text/javascript', body: fs.readFileSync(path.join(__dirname, 'vendor/package/dist/leaflet.js')) }));
    await page.route('https://fonts.googleapis.com/**', r => r.fulfill({ contentType: 'text/css', body: '' }));
    const t0 = Date.now();
    await page.goto('file://' + tmp);
    await page.waitForFunction(() => document.querySelectorAll('.card').length > 0 || /fail|Couldn/.test(document.getElementById('status').textContent), null, { timeout: 60000 });
    console.log(name, 'ready in', Date.now() - t0, 'ms;', await page.textContent('#status'));
    console.log(name, 'understood:', await page.textContent('#understood'));
    console.log(name, 'cards:', (await page.$$eval('.card', els => els.map(e => e.innerText.replace(/\s+/g, ' ')))).join('\n   '));
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(out, name + '.png'), fullPage: name === 'phone' });
    const sw = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth); console.log(name, 'horizontal overflow px', sw);
    if (name === 'desktop') {
      for (const ex of ['long and fast route', 'easy flat 30 minutes', 'hilly 10k through Bernal and Holly Park', '6 miles ending at the Ferry Building']) {
        await page.fill('#prompt', ex); await page.click('#planBtn');
        await page.waitForFunction(() => !document.getElementById('planBtn').disabled, null, { timeout: 60000 });
        console.log('\n>>', ex, '|', await page.textContent('#understood'), '|', await page.textContent('#status'));
        console.log('   ', (await page.$$eval('.card', els => els.map(e => e.innerText.replace(/\s+/g, ' ')))).join('\n    '));
      }
      await page.hover('#profile', { position: { x: 300, y: 60 } });
      await page.screenshot({ path: path.join(out, 'desktop2.png') });
    }
    await ctx.close();
  }
  await browser.close();
})();
