// Edge cases from the review: long runs, water, out & back with stops, open distance, outside SF.
const fs = require('fs'), zlib = require('zlib');
const R = require('../app/router.js')();
const buf = zlib.gunzipSync(Buffer.from(fs.readFileSync(__dirname + '/data/blob.b64', 'utf8'), 'base64'));
const g = R.decode(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.length));
const HOME = { lat: 37.7387, lon: -122.41984 }, MI = 1609.344;
const place = (n) => g.places.find(p => p.name === n);
let fail = 0;
const check = (label, ok, info) => { console.log(`${ok ? 'PASS' : 'FAIL'} ${label}: ${info}`); if (!ok) fail++; };
for (const mi of [1, 13.1, 16, 20, 22, 26.2]) for (const shape of ['loop', 'out-and-back']) {
  const res = R.plan(g, { start: HOME, targetM: mi * MI, hill: 'rolling', shape, seed: 7 });
  const L = res.routes.map(r => r.length / MI);
  // SF only allows out & backs of about 13 mi from Elsie St; beyond that we just need a route back
  const feasible = shape === 'loop' || mi <= 13.1;
  check(`${mi} mi ${shape}`, L.length > 0 && (!feasible || Math.abs(L[0] - mi) / mi < 0.1), `${L.map(x => x.toFixed(2)).join(', ') || 'none'} (${res.ms} ms)`);
}
{ const res = R.plan(g, { start: HOME, destinations: [place('Twin Peaks')], shape: 'out-and-back', hill: 'rolling', seed: 1 });
  const r = res.routes[0]; check('Twin Peaks out & back', r && r.overlap > 0.9, r ? `${(r.length / MI).toFixed(2)} mi, overlap ${(r.overlap * 100).toFixed(0)}%, ${res.routes.length} options` : 'none'); }
{ const res = R.plan(g, { start: HOME, hill: 'rolling' }); check('loop with no distance', !res.routes.length && /distance/.test(res.error || ''), res.error); }
{ const res = R.plan(g, { start: { lat: 37.80, lon: -122.27 }, targetM: 5 * MI }); check('start in Oakland', !res.routes.length && !!res.error, res.error); }
{ const res = R.plan(g, { start: HOME, end: place('Golden Gate Bridge'), targetM: 9 * MI, seed: 2 }); check('to Golden Gate Bridge 9 mi', res.routes.length > 0, res.routes.map(r => (r.length / MI).toFixed(2)).join(', ')); }
console.log(fail ? fail + ' failures' : 'edge checks passed');
process.exit(fail ? 1 : 0);
