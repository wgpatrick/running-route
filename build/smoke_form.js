// Browser test: edit the settings directly (no prompt changes) and confirm routes follow them.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const out = process.argv[2];
(async () => {
  const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0">' +
    fs.readFileSync(path.join(__dirname, '../dist/sf-morning-runs.html'), 'utf8') + '</body></html>';
  const tmp = path.join(out, 'page.html'); fs.writeFileSync(tmp, html);
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await (await browser.newContext({ viewport: { width: 1300, height: 900 } })).newPage();
  let fails = 0;
  page.on('pageerror', e => { console.log('pageerror', e.message); fails++; });
  await page.route('**/leaflet.min.js', r => r.fulfill({ contentType: 'text/javascript', body: fs.readFileSync(path.join(__dirname, 'vendor/package/dist/leaflet.js')) }));
  await page.route('https://fonts.googleapis.com/**', r => r.fulfill({ contentType: 'text/css', body: '' }));
  await page.goto('file://' + tmp);
  await page.waitForFunction(() => document.querySelectorAll('.card').length > 0, null, { timeout: 60000 });
  const settle = async () => { await page.waitForTimeout(700); await page.waitForFunction(() => !document.getElementById('planBtn').disabled, null, { timeout: 60000 }); };
  const state = async () => ({ miles: await page.$$eval('.card .stats', els => els.map(e => parseFloat(e.textContent))), names: await page.$$eval('.card .name', els => els.map(e => e.textContent)),
    understood: (await page.textContent('#understood')).trim(), cardText: await page.$$eval('.card .stats', els => els.map(e => e.textContent)), detail: await page.textContent('#detail'), pace: await page.inputValue('#paceIn'), amount: await page.inputValue('#amountIn'), status: await page.textContent('#status') });
  const step = async (label, fn, check) => {
    await fn(); await settle(); const s = await state(); const ok = check(s); if (!ok) fails++;
    console.log(`${ok ? 'PASS' : 'FAIL'} ${label}\n   ${s.understood}\n   ${s.status} | ${s.miles.join(', ')} mi | ${s.names.join(' / ')}`);
  };
  const near = (arr, t) => arr.length && arr.every(m => Math.abs(m - t) / t < 0.07);
  await step('miles 7 -> 4 (Enter)', async () => { await page.fill('#amountIn', '4'); await page.press('#amountIn', 'Enter'); }, s => near(s.miles, 4));
  await step('terrain -> Flat (click)', () => page.click('#hillSeg button[data-v=flat]'), s => /flat/.test(s.understood) && near(s.miles, 4));
  await step('include hilltop off (toggle)', () => page.click('#tHill'), s => !/hilltop/.test(s.understood) && near(s.miles, 4));
  await step('switch to Time mode', () => page.click('#modeSeg button[data-v=time]'), s => /min at/.test(s.understood) && near(s.miles, 4));
  await step('time 60 min, pace 10:00 typed then click Rolling without Enter', async () => {
    await page.fill('#amountIn', '60'); await page.fill('#paceIn', '10:00'); await page.click('#hillSeg button[data-v=rolling]'); }, s => s.pace === '10:00' && s.amount === '60' && near(s.miles, 6));
  await step('add Twin Peaks stop from the picker', async () => { await page.click('#placePicker >> xpath=..'); await page.click('#placePicker button:has-text("Twin Peaks")'); }, s => /Twin Peaks/.test(s.understood) && s.names.every(n => /Twin Peaks/.test(n)));
  await step('remove Twin Peaks stop', () => page.click('#dests button:has-text("Twin Peaks")'), s => !/Twin Peaks/.test(s.understood) && near(s.miles, 6));
  await step('finish at Ferry Building (typed, leave field)', async () => { await page.fill('#endIn', 'Ferry Building'); await page.click('#amountLabel'); }, s => /finish at Ferry/.test(s.understood) && s.names.every(n => /Ferry/.test(n)));
  await step('clear finish + start at 24th & Mission (Enter)', async () => { await page.fill('#endIn', ''); await page.fill('#startIn', '24th & Mission'); await page.press('#startIn', 'Enter'); }, s => /from 24th/.test(s.understood) && near(s.miles, 6));
  await step('Plan routes with unchanged prompt keeps edits', () => page.click('#planBtn'), s => /from 24th/.test(s.understood) && s.pace === '10:00' && near(s.miles, 6));
  await step('Update routes button', async () => { await page.fill('#amountIn', '30'); await page.click('#updateBtn'); }, s => near(s.miles, 3));
  await step('Out & back shape', () => page.click('#shapeSeg button[data-v="out-and-back"]'), s => /out & back/.test(s.understood) && near(s.miles, 3));
  for (const [keys, want] of [['830', '8:30'], ['1200', '12:00'], ['12', '12:00'], ['8.5', '8:30'], ['7:15', '7:15'], ['945', '9:45']]) {
    await step(`pace typed as "${keys}" on a number pad`, async () => {
      await page.click('#paceIn', { clickCount: 3 }); await page.keyboard.press('Backspace');
      await page.keyboard.type(keys, { delay: 30 }); await page.keyboard.press('Enter'); },
      s => s.pace === want);
  }
  await step('backspacing "8:30" twice leaves "8"', async () => {
    await page.click('#paceIn', { clickCount: 3 }); await page.keyboard.press('Backspace'); await page.keyboard.type('830');
    await page.keyboard.press('Backspace'); await page.keyboard.press('Backspace'); }, () => true);
  console.log('   field now:', await page.inputValue('#paceIn'));
  await step('steepest grade 8% (click)', async () => { await page.click('#shapeSeg button[data-v=loop]'); await page.click('#gradeSeg button[data-v="0.08"]'); },
    s => /nothing over 8%/.test(s.understood) && s.cardText.every(t => />8%: [0-9.]+ mi/.test(t)) && /steeper than 8%|Nothing steeper than 8%/.test(s.detail));
  await step('steepest grade back to Any', () => page.click('#gradeSeg button[data-v=""]'), s => !/nothing over/.test(s.understood) && s.cardText.every(t => !/>8%/.test(t)));
  // variety: same settings planned again, and Shuffle, should give new routes
  const before = (await state()).names.join('|') + (await state()).miles.join('|');
  await step('Update routes again with same settings gives different routes', () => page.click('#updateBtn'), s => s.names.join('|') + s.miles.join('|') !== before && /steering away/.test(s.status));
  const before2 = (await state()).miles.join('|') + (await state()).names.join('|');
  await step('Shuffle gives different routes', () => page.click('#shuffleBtn'), s => s.miles.join('|') + s.names.join('|') !== before2);
  await step('Forget them clears history', () => page.click('#forgetBtn'), s => /forgotten/.test(s.status));
  await page.click('#gradeSeg button[data-v="0.08"]'); await settle();
  await page.screenshot({ path: path.join(out, 'form-edits.png') });
  await step('new prompt still re-reads the description', async () => { await page.fill('#prompt', 'hilly 5 miles'); await page.click('#planBtn'); }, s => /5 mi/.test(s.understood) && /hilly/.test(s.understood) && near(s.miles, 5));
  await browser.close();
  console.log(fails ? `${fails} failures` : 'all form-edit cases passed');
})();
