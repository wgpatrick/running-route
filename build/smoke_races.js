// Browser regressions from the review: request races, taps during startup, tiny routes, hilltop + grade + distance.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const out = process.argv[2];
const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0">' +
  fs.readFileSync(path.join(__dirname, '../dist/sf-morning-runs.html'), 'utf8') + '</body></html>';
fs.writeFileSync(path.join(out, 'page.html'), html);
let fails = 0;
const report = (ok, label, info) => { if (!ok) fails++; console.log(`${ok ? 'PASS' : 'FAIL'} ${label}\n   ${info}`); };
async function open(browser, { claude, slowWorker } = {}) {
  const page = await (await browser.newContext({ viewport: { width: 1300, height: 900 } })).newPage();
  page.on('pageerror', e => { fails++; console.log('pageerror', e.message); });
  await page.addInitScript(({ claude, slowWorker }) => {
    // Claude replies slowly to "long and fast", quickly to anything else
    window.claude = { use: async (n) => n === 'sample' && claude ? Object.assign(async () => ({ text: '' }), { limits: async () => ({}), json: async (prompt) => {
      const long = /long and fast/.test(prompt);
      await new Promise(r => setTimeout(r, long ? 2500 : 200));
      return long ? { distance_miles: 9, terrain: 'flat', fast: true, destinations: [], summary: '' } : { duration_minutes: 30, terrain: 'flat', fast: false, destinations: [], summary: '' };
    } }) : null };
    if (slowWorker) { const W = window.Worker; window.Worker = function (u) { const w = new W(u); const post = w.postMessage.bind(w); w.postMessage = (m) => m && m.type === 'init' ? setTimeout(() => post(m), 2500) : post(m); return w; }; }
  }, { claude, slowWorker });
  await page.route('**/leaflet.min.js', r => r.fulfill({ contentType: 'text/javascript', body: fs.readFileSync(path.join(__dirname, 'vendor/package/dist/leaflet.js')) }));
  await page.route('https://fonts.googleapis.com/**', r => r.fulfill({ contentType: 'text/css', body: '' }));
  await page.goto('file://' + path.join(out, 'page.html'));
  return page;
}
const settle = async (page, ms = 600) => { await page.waitForTimeout(ms); await page.waitForFunction(() => !document.getElementById('planBtn').disabled, null, { timeout: 60000 }); };
const state = (page) => page.evaluate(() => ({ understood: document.getElementById('understood').textContent, status: document.getElementById('status').textContent,
  miles: [...document.querySelectorAll('.card .stats')].map(e => parseFloat(e.textContent)), hint: document.getElementById('aiHint').textContent }));
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  { // 1. two prompts in a row: the slow Claude reply to the first must not win
    const page = await open(browser, { claude: true });
    await page.waitForFunction(() => document.querySelectorAll('.card').length > 0, null, { timeout: 60000 });
    await page.click('#examples button:has-text("long and fast route")');
    await page.waitForTimeout(150);
    await page.click('#examples button:has-text("easy flat 30 minutes")');
    await page.waitForTimeout(3500); await settle(page);
    const s = await state(page);
    report(/30 min/.test(s.understood) && !/9 mi/.test(s.understood) && s.miles.every(m => Math.abs(m - 30 / 8.5) / (30 / 8.5) < 0.08), 'later prompt wins over a slow Claude reply to an earlier one', `${s.understood} | ${s.miles.join(', ')}`);
    // 2. a setting changed while Claude is thinking is kept
    await page.fill('#prompt', 'long and fast route'); await page.click('#planBtn');
    await page.waitForTimeout(300); await page.click('#tSteps');
    await page.waitForTimeout(3200); await settle(page);
    const s2 = await state(page); const stepsOn = await page.getAttribute('#tSteps', 'aria-pressed');
    report(stepsOn === 'true', 'setting changed while Claude is thinking survives the reply', `avoid stairs pressed=${stepsOn} | ${s2.understood}`);
    // 3. tiny route: start and finish at the same corner, no distance
    await page.fill('#startIn', 'Cortland & Elsie'); await page.fill('#endIn', 'Elsie & Cortland'); await page.fill('#amountIn', ''); await page.click('#updateBtn');
    const t0 = Date.now(); await settle(page); const s3 = await state(page);
    report(Date.now() - t0 < 10000, 'same start and finish, no distance: no freeze', `${s3.status}`);
    // 4. hilltop + 8% + 7 mi respects the distance
    await page.fill('#startIn', '339 Elsie St'); await page.fill('#endIn', '');
    await page.fill('#prompt', 'cool hilltop, 7 miles, nothing over 8%'); await page.click('#planBtn'); await page.waitForTimeout(800); await settle(page);
    const s4 = await state(page);
    report(s4.miles.length && s4.miles.every(m => Math.abs(m - 7) / 7 <= 0.08) || /closest|longest/.test(s4.status), 'hilltop + 8% + 7 mi stays near 7 mi', `${s4.understood} | ${s4.status} | ${s4.miles.join(', ')}`);
    // 5. unknown place clears old routes
    await page.fill('#startIn', 'Narnia'); await page.click('#updateBtn'); await settle(page, 300);
    const s5 = await state(page);
    report(!s5.miles.length && /Couldn't find/.test(s5.status), 'unknown start clears old routes', s5.status);
  }
  { // 6. tap a setting before the background worker is ready
    const page = await open(browser, { slowWorker: true });
    await page.waitForFunction(() => !document.getElementById('mapLoading') || document.getElementById('mapLoading').hidden, null, { timeout: 60000 });
    await page.click('#hillSeg button[data-v=hilly]'); await page.click('#updateBtn');
    await page.waitForFunction(() => document.querySelectorAll('.card').length > 0, null, { timeout: 60000 }); await settle(page);
    const s = await state(page);
    report(/hilly/.test(s.understood) && s.miles.length > 0 && !/failed/i.test(s.status), 'tap during startup still plans', `${s.understood} | ${s.status}`);
    await page.fill('#prompt', 'flat 4 miles'); await page.click('#planBtn'); await settle(page);
    const s2 = await state(page);
    report(/4 mi/.test(s2.understood) && s2.miles.length > 0, 'Plan works after an early tap', `${s2.understood} | ${s2.miles.join(', ')}`);
  }
  await browser.close();
  console.log(fails ? `${fails} failures` : 'all race cases passed');
})();
