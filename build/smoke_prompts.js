// Browser test: type prompts into the real page with a mocked Claude reply, check the planned mileage.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const out = process.argv[2];
const BAD = { distance_miles: 9.3, duration_minutes: 80, pace: '12:00', terrain: 'flat', fast: false, trails: false, avoid_stairs: false, shape: 'loop',
  destinations: ['Ferry Building', 'Crissy Field', 'Palace of Fine Arts'], hilltop: false, start: null, end: null, summary: 'Flat waterfront loop from home, 80 minutes at 12-minute pace' };
const CASES = [
  ['i want to go on a pretty flat run for a hour and 20 minutes at 12 min pace', 80 / 12, BAD],
  ['45 min tempo at 7:15 pace, trails if possible', 45 / 7.25, { duration_minutes: 45, distance_miles: 7, pace: '7:15', terrain: 'flat', fast: true, trails: true, destinations: ['Glen Canyon Park'], hilltop: false, summary: 'Tempo' }],
  ['an hour and a half at 10 min/mi', 9, null],
  ['5 miles in 40 minutes', 5, null],
  ['go to a cool hilltop with a 7 mile long route', 7, { distance_miles: 7, terrain: 'hilly', hilltop: true, destinations: [], summary: 'Hilltop loop' }],
];
(async () => {
  const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0">' +
    fs.readFileSync(path.join(__dirname, '../dist/sf-morning-runs.html'), 'utf8') + '</body></html>';
  const tmp = path.join(out, 'page.html'); fs.writeFileSync(tmp, html);
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  let fails = 0;
  for (const [prompt, miles, claude] of CASES) {
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 900 } });
    const page = await ctx.newPage();
    page.on('pageerror', e => { console.log('pageerror', e.message); fails++; });
    await page.addInitScript((reply) => {
      window.claude = { use: async (n) => n === 'sample' && reply ? Object.assign(async () => ({ text: '' }), { json: async () => reply, limits: async () => ({}) }) : null };
    }, claude);
    await page.route('**/leaflet.min.js', r => r.fulfill({ contentType: 'text/javascript', body: fs.readFileSync(path.join(__dirname, 'vendor/package/dist/leaflet.js')) }));
    await page.route('https://fonts.googleapis.com/**', r => r.fulfill({ contentType: 'text/css', body: '' }));
    await page.goto('file://' + tmp);
    await page.waitForFunction(() => document.querySelectorAll('.card').length > 0, null, { timeout: 60000 });
    await page.fill('#prompt', prompt); await page.click('#planBtn');
    await page.waitForTimeout(300);
    await page.waitForFunction(() => !document.getElementById('planBtn').disabled, null, { timeout: 60000 });
    const understood = await page.textContent('#understood'), status = await page.textContent('#status');
    const lens = await page.$$eval('.card .stats', els => els.map(e => parseFloat(e.textContent)));
    const ok = lens.length && lens.every(l => Math.abs(l - miles) / miles < 0.06) && !/Ferry|Crissy|Glen Canyon/.test(understood);
    if (!ok) fails++;
    console.log(`${ok ? 'PASS' : 'FAIL'} "${prompt}"\n   ${understood}\n   ${status} | cards ${lens.join(', ')} mi (want ${miles.toFixed(2)})`);
    if (prompt.startsWith('i want')) await page.screenshot({ path: path.join(out, 'user-prompt.png') });
    await ctx.close();
  }
  await browser.close();
  console.log(fails ? `${fails} failures` : 'all browser cases passed');
})();
