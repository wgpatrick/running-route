// Route variety: overlap between the options in one plan, and how many distinct routes repeated Shuffles produce.
const fs = require('fs'), zlib = require('zlib');
const R = require('../app/router.js')();
const buf = zlib.gunzipSync(Buffer.from(fs.readFileSync(__dirname + '/data/blob.b64', 'utf8'), 'base64'));
const g = R.decode(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.length));
const HOME = { lat: 37.7387, lon: -122.41984 }, MI = 1609.344;
// streets-as-run signature: set of named streets with >200 m on the route
const sig = (r) => r.streets.filter(s => s.len > 200 && s.name !== 'path').map(s => s.name);
// geometric overlap: share of route A within 25 m of route B (grid-hashed)
function overlap(a, b) {
  const cell = (la, lo) => Math.round(la * 111320 / 25) + ':' + Math.round(lo * 88000 / 25);
  const B = new Set(); for (let i = 0; i < b.geom.lat.length; i++) B.add(cell(b.geom.lat[i], b.geom.lon[i]));
  let hit = 0, n = 0;
  for (let i = 0; i < a.geom.lat.length; i++) { n++; const [la, lo] = [a.geom.lat[i], a.geom.lon[i]]; let h = false;
    for (const dy of [-1, 0, 1]) for (const dx of [-1, 0, 1]) if (B.has((Math.round(la * 111320 / 25) + dy) + ':' + (Math.round(lo * 88000 / 25) + dx))) h = true; if (h) hit++; }
  return hit / n;
}
const cases = [['5 mi rolling', { targetM: 5 * MI, hill: 'rolling' }], ['7 mi hilly', { targetM: 7 * MI, hill: 'hilly' }], ['4 mi flat', { targetM: 4 * MI, hill: 'flat' }], ['6.67 mi flat (80 min @12)', { targetM: 6.67 * MI, hill: 'flat' }]];
const MODE = process.argv[2] || 'app';
let fail = 0;
for (const [label, base] of cases) {
  const seen = []; const within = []; const hist = []; let current = [];
  for (let k = 0; k < 5; k++) {
    // 'old' = previous behaviour (fixed seeds, no memory); 'app' = random seed + history; Shuffle on k>0 also avoids what's on screen
    const P = Object.assign({ start: HOME }, base);
    if (MODE === 'old') P.seed = undefined, P._oldSeed = k;
    else {
      P.seed = (k * 7919 + 13) % 100000;
      const edges = [], weights = [];
      for (const h of hist.slice(-20)) for (const e of h) { edges.push(e); weights.push(0.6); }
      for (const r of current) for (const e of r.edges) { edges.push(e); weights.push(1.5); }
      P.avoid = { edges, weights };
    }
    const res = R.plan(g, P);
    const rs = res.routes; current = rs;
    for (let i = 0; i < rs.length; i++) for (let j = i + 1; j < rs.length; j++) within.push(overlap(rs[i], rs[j]));
    for (const r of rs) { seen.push(r); hist.push(r.edges); }
    for (const r of rs) if (base.targetM && Math.abs(r.length - base.targetM) / base.targetM > 0.08) { fail++; console.log('   FAIL distance', (r.length / MI).toFixed(2)); }
  }
  const distinct = []; for (const r of seen) if (!distinct.some(d => overlap(r, d) > 0.7)) distinct.push(r);
  const avgW = within.reduce((a, b) => a + b, 0) / within.length;
  console.log(`${label}: within-plan overlap avg ${(avgW * 100).toFixed(0)}% | 5 plans = ${seen.length} routes, ${distinct.length} distinct`);
  if (MODE === 'app' && distinct.length < 12) { fail++; console.log('   FAIL: too many repeats'); }
  const freq = {}; for (const r of seen) for (const s of new Set(sig(r))) freq[s] = (freq[s] || 0) + 1;
  console.log('   most repeated streets:', Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, v]) => `${k} ${v}/${seen.length}`).join(', '));
}
console.log(fail ? fail + ' failures' : 'variety checks passed');
