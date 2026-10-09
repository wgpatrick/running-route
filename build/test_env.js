// Scenic and tempo preferences: fewer industrial/major-road metres and more park/water with Scenic; fewer lights with Fast.
const fs = require('fs'), zlib = require('zlib');
const R = require('../app/router.js')();
const buf = zlib.gunzipSync(Buffer.from(fs.readFileSync(__dirname + '/data/blob.b64', 'utf8'), 'base64'));
const g = R.decode(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.length));
const HOME = { lat: 37.7387, lon: -122.41984 }, MI = 1609.344;
console.log('graph version', g.version, 'amenities', g.amenities.length);
let fail = 0;
const avg = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length;
for (const [label, base] of [['6.67 mi flattest', { targetM: 6.67 * MI, hill: 'flat' }], ['5 mi rolling', { targetM: 5 * MI, hill: 'rolling' }], ['8 mi rolling', { targetM: 8 * MI, hill: 'rolling' }]]) {
  const run = (extra) => { const rs = []; for (let seed = 0; seed < 4; seed++) rs.push(...R.plan(g, Object.assign({ start: HOME, seed }, base, extra)).routes); return rs; };
  const plain = run({}), scenic = run({ scenic: true }), fast = run({ fast: true }), plainFast = run({ fast: false });
  const nice = (rs) => avg(rs.map(r => (r.greenM + r.waterM) / r.length)), bad = (rs) => avg(rs.map(r => (r.industrialM + r.majorM) / r.length));
  const lpm = (rs) => avg(rs.map(r => r.lights / (r.length / MI)));
  const err = (rs) => avg(rs.map(r => Math.abs(r.length - base.targetM) / base.targetM));
  console.log(`${label}: plain nice ${(nice(plain) * 100).toFixed(0)}% bad ${(bad(plain) * 100).toFixed(0)}% | scenic nice ${(nice(scenic) * 100).toFixed(0)}% bad ${(bad(scenic) * 100).toFixed(0)}% (dist err ${(err(scenic) * 100).toFixed(1)}%) | lights/mi plain ${lpm(plain).toFixed(1)} fast ${lpm(fast).toFixed(1)} (dist err ${(err(fast) * 100).toFixed(1)}%)`);
  if (!(nice(scenic) > nice(plain) && bad(scenic) < bad(plain))) { fail++; console.log('  FAIL scenic'); }
  if (!(lpm(fast) < lpm(plain))) { fail++; console.log('  FAIL fast lights'); }
  if (err(scenic) > 0.05 || err(fast) > 0.05) { fail++; console.log('  FAIL distance'); }
}
// saved-run retrace (used after a street-data rebuild): same length, and the new line hugs the old one
for (const seed of [3, 5, 8]) {
  const r = R.plan(g, { start: HOME, targetM: 5 * MI, hill: 'rolling', seed }).routes[0];
  const coords = r.geom.lat.map((la, i) => [la, r.geom.lon[i]]).filter((_, i) => i % 4 === 0);
  const p2 = R.pathFromCoords(g, coords); const a2 = R.reanalyze(g, p2, {});
  let close = 0; const n = a2.geom.lat.length;
  for (let i = 0; i < n; i++) { let bd = Infinity; for (let j = 0; j < r.geom.lat.length; j += 2) { const d = ((r.geom.lon[j] - a2.geom.lon[i]) * 88000) ** 2 + ((r.geom.lat[j] - a2.geom.lat[i]) * 111320) ** 2; if (d < bd) bd = d; } if (bd < 30 * 30) close++; }
  const ok = p2 && Math.abs(a2.length - r.length) / r.length < 0.03 && close / n > 0.95;
  console.log(`retrace seed ${seed}: ${(r.length / MI).toFixed(2)} mi -> ${(a2.length / MI).toFixed(2)} mi, ${(close / n * 100).toFixed(0)}% within 30 m; amenities ${r.amenities.length}, lights ${r.lights}, longest gap ${(r.longestGap / MI).toFixed(2)} mi`);
  if (!ok) { fail++; console.log('  FAIL retrace'); }
}
console.log(fail ? fail + ' failures' : 'env checks passed');
process.exit(fail ? 1 : 0);
