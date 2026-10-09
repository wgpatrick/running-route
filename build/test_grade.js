// Steepness limit: routes planned with a max grade should spend (almost) no distance above it.
const fs = require('fs'), zlib = require('zlib');
const R = require('../app/router.js')();
const buf = zlib.gunzipSync(Buffer.from(fs.readFileSync(__dirname + '/data/blob.b64', 'utf8'), 'base64'));
const g = R.decode(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.length));
const HOME = { lat: 37.7387, lon: -122.41984 }, MI = 1609.344;
const tw = g.places.find(p => p.name === 'Twin Peaks'), fb = g.places.find(p => p.name === 'Ferry Building');
let fail = 0;
for (const [label, base] of [['6 mi rolling loop', { targetM: 6 * MI, hill: 'rolling' }], ['5 mi hilly loop', { targetM: 5 * MI, hill: 'hilly' }],
  ['8 mi via Twin Peaks', { targetM: 8 * MI, hill: 'hilly', destinations: [tw] }], ['to Ferry Building', { end: fb, hill: 'rolling' }], ['4 mi flat', { targetM: 4 * MI, hill: 'flat' }]]) {
  console.log('##', label);
  for (const mg of [null, 0.12, 0.10, 0.08, 0.06]) {
    const res = R.plan(g, Object.assign({ start: HOME, maxGrade: mg }, base));
    const r = res.routes[0];
    const over = r.overUp + r.overDn, avoidable = Math.max(0, over - (r.unavoidable || 0));
    console.log(`  limit ${mg ? (mg * 100) + '%' : 'any'}: ${(r.length / MI).toFixed(2)} mi, +${Math.round(r.gain * 3.28)} ft, steepest(50m) ${(r.steep50 * 100).toFixed(1)}%, over limit ${(over / MI).toFixed(2)} mi, unavoidable ${((r.unavoidable || 0) / MI).toFixed(2)} mi, avoidable ${(avoidable / MI).toFixed(2)} mi (${(avoidable / r.length * 100).toFixed(1)}%)  [${res.ms} ms]`);
    // with no required stops, steepness the runner could have avoided should be (nearly) gone
    if (mg && !base.destinations && avoidable / r.length > (mg >= 0.08 ? 0.025 : 0.04)) { fail++; console.log('    FAIL: too much avoidable steep distance'); }
    if (mg && base.targetM && !base.destinations && Math.abs(r.length - base.targetM) / base.targetM > 0.08) { fail++; console.log('    FAIL: distance off target'); }
  }
}
console.log(fail ? fail + ' failures' : 'grade checks passed');
