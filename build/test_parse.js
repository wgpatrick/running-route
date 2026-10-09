// Prompt test suite: parse -> resolve -> plan, checking numbers and the planned mileage.
const fs = require('fs'), zlib = require('zlib');
const Router = require('../app/router.js')(), ParseLib = require('../app/parse.js');
const b64 = fs.readFileSync(__dirname + '/data/blob.b64', 'utf8');
const buf = zlib.gunzipSync(Buffer.from(b64, 'base64'));
const g = Router.decode(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.length));
const P = ParseLib(g.places);
const HOME = { lat: 37.7387, lon: -122.41984, label: '339 Elsie St' };
const MI = 1609.344;
// [prompt, expectations]; miles = expected target miles
const CASES = [
  ['i want to go on a pretty flat run for a hour and 20 minutes at 12 min pace', { miles: 80 / 12, pace: '12:00', hill: 'flat', dests: [] }],
  ['i want to go on a pretty flat run for an hour and 20 minutes at 12 min pace', { miles: 80 / 12, pace: '12:00', hill: 'flat', dests: [] }],
  ['go to a cool hilltop with a 7 mile long route', { miles: 7, hillTop: true, dests: [] }],
  ['long and fast route', { miles: 9, fast: true }],
  ['easy flat 30 minutes', { miles: 30 / 8.5, hill: 'flat' }],
  ['45 min tempo at 7:15 pace, trails if possible', { miles: 45 / 7.25, pace: '7:15', fast: true, trails: true }],
  ['run for 1 hour at 9:00 pace', { miles: 60 / 9, pace: '9:00' }],
  ['60 minutes at 10 minute miles', { miles: 6, pace: '10:00' }],
  ['90 min easy at 11:30/mi', { miles: 90 / 11.5, pace: '11:30', hill: 'flat' }],
  ['an hour and a half at 10 min/mi', { miles: 9, pace: '10:00' }],
  ['1.5 hours at a 9 minute pace', { miles: 10, pace: '9:00' }],
  ['1h15 at 8:00 pace', { miles: 75 / 8, pace: '8:00' }],
  ['2 hours, 10:00 pace, flat', { miles: 12, pace: '10:00', hill: 'flat' }],
  ['half an hour shakeout at 10:30', { miles: 30 / 10.5, pace: '10:30' }],
  ['forty five minutes at nine minute pace', { miles: 5, pace: '9:00' }],
  ['12 min pace for 40 minutes', { miles: 40 / 12, pace: '12:00' }],
  ['run 50 minutes, pace of 8:45', { miles: 50 / 8.75, pace: '8:45' }],
  ['thirty minutes at 12-minute miles', { miles: 2.5, pace: '12:00' }],
  ['75 minutes at 9:30s, some hills', { miles: 75 / 9.5, pace: '9:30', hill: 'rolling' }],
  ['5 miles in 40 minutes', { miles: 5, pace: '8:00' }],
  ['10k at 8:00 pace', { miles: 6.21, pace: '8:00' }],
  ['5k', { miles: 3.11 }],
  ['half marathon training run, flat', { miles: 13.1, hill: 'flat' }],
  ['3 miles easy', { miles: 3, hill: 'flat' }],
  ['a short run', { miles: 3 }],
  ['4 mile out and back', { miles: 4, shape: 'out-and-back' }],
  ['hilly 10k through Bernal and Holly Park', { miles: 6.21, hill: 'hilly', dests: ['Bernal Heights Summit', 'Holly Park'] }],
  ['Twin Peaks and back, max climbing', { miles: null, hill: 'max', dests: ['Twin Peaks'], shape: 'out-and-back' }],
  ['6 miles ending at the Ferry Building', { miles: 6, end: 'Ferry Building', dests: [] }],
  ['8 miles to Ocean Beach', { miles: 8, dests: ['Ocean Beach'] }],
  ['7 miles via Mount Davidson and Glen Canyon', { miles: 7, dests: ['Mount Davidson', 'Glen Canyon Park'] }],
  ['run up to Coit Tower, 10 miles', { miles: 10, dests: ['Coit Tower'] }],
  ['5 miles no stairs, flat', { miles: 5, avoidSteps: true, hill: 'flat' }],
  ['start at 24th and Mission, 4 miles flat', { miles: 4, start: '24th and Mission', hill: 'flat' }],
  ['6 miles from Dolores Park ending at home', { miles: 6, start: 'Dolores Park (top)', end: 'home', dests: [] }],
  ['run to Bernal Heights', { miles: null, dests: ['Bernal Heights Summit'] }],
  ['go to Stow Lake and end at Ocean Beach', { miles: null, dests: ['Stow Lake'], end: 'Ocean Beach' }],
  ['1 hour hill workout', { miles: 60 / 8.5, hill: 'hilly' }],
  ['steep 5 mile run with a view', { miles: 5, hill: 'hilly', hillTop: true }],
  ['quick 20 minute jog', { miles: 20 / 8.5 }],
  ['tempo 8 miles at 7:30', { miles: 8, pace: '7:30', fast: true }],
  ['easy 40 min recovery run', { miles: 40 / 8.5, hill: 'flat' }],
  ['three miles', { miles: 3 }],
  ['an hour at 10:00 pace through Golden Gate Park', { miles: 6, pace: '10:00', dests: ['Stow Lake'] }],
  ['55 minutes rolling at 9 min/mile', { miles: 55 / 9, pace: '9:00', hill: 'rolling' }],
  ['run 70 minutes at 12 min pace', { miles: 70 / 12, pace: '12:00' }],
  ['flat 1:10:00 at 10 min pace', { miles: 7, pace: '10:00', hill: 'flat' }],
  ['avoid steep hills, 5 miles', { miles: 5, maxGrade: 0.08 }],
  ['6 miles nothing over 8%', { miles: 6, maxGrade: 0.08 }],
  ['flat run under 10% grade, 45 min at 9:00', { miles: 5, pace: '9:00', maxGrade: 0.1, hill: 'flat' }],
  ['7 miles, 12% max', { miles: 7, maxGrade: 0.12 }],
  ['hilly 6 miles but no steep climbs', { miles: 6, maxGrade: 0.08, hill: 'hilly' }],
  ['hilly 10k', { miles: 6.21, maxGrade: null, hill: 'hilly' }],
  // review regressions
  ['10 miles at marathon pace', { miles: 10 }],
  ['half marathon pace 7 miles', { miles: 7 }],
  ['a 7 miler', { miles: 7 }],
  ['a long 14 miler', { miles: 14 }],
  ['6 miles finishing at Cortland and Mission', { miles: 6, end: 'Cortland and Mission' }],
  ['leave at 6:15, easy 5 miles', { miles: 5, pace: '8:30', hill: 'flat' }],
  ['5 miles at 6:45 this morning', { miles: 5, pace: '8:30' }],
  ['run home from the Ferry Building', { miles: null, start: 'Ferry Building', end: 'home', dests: [] }],
  ['from 24th and Mission run 4 miles', { miles: 4, start: '24th and Mission' }],
  ['not too hilly 5 miles', { miles: 5, hill: 'flat' }],
  ['skip the hills, 4 miles', { miles: 4, hill: 'flat' }],
  ['minimal climbing 6 miles', { miles: 6, hill: 'flat' }],
  ['easy 6', { miles: 6, hill: 'flat' }],
  ['run 1:30 at 10:00 pace', { miles: 9, pace: '10:00' }],
  ['6 mi @ 9:15', { miles: 6, pace: '9:15' }],
  ['out the door at 6, 40 min easy', { miles: 40 / 8.5, pace: '8:30' }],
  ['100 minutes at 12:00 pace, lake merced', { miles: 100 / 12, pace: '12:00', dests: ['Lake Merced'] }],
];
// What we saw Claude return for the first case: invented stops and a wrong distance
const BAD_CLAUDE = { distance_miles: 9.3, duration_minutes: 80, pace: '12:00', terrain: 'flat', fast: false, trails: false, avoid_stairs: false, shape: 'loop',
  destinations: ['Ferry Building', 'Crissy Field', 'Palace of Fine Arts'], hilltop: false, start: null, end: 'Ferry Building', summary: 'Flat waterfront loop' };

let fail = 0, n = 0;
const check = (name, cond, msg) => { n++; if (!cond) { fail++; console.log('  FAIL', name, msg); } };
const close = (a, b, tol) => Math.abs(a - b) <= tol * Math.max(1, Math.abs(b));
for (const [prompt, exp] of CASES) {
  let r = P.localParse(prompt);
  if (prompt.includes('12 min pace') && prompt.includes('20 minutes')) r = P.mergeClaude(prompt, r, BAD_CLAUDE);
  const s = P.resolve(r, '8:30');
  const tag = `"${prompt}"`;
  console.log(`${tag}\n   -> ${s.mode} ${s.amount} @ ${s.pace} = ${s.miles == null ? 'open' : s.miles.toFixed(2)} mi | hill ${r.hill} fast ${r.fast} trails ${r.trails} steps ${r.avoidSteps} shape ${r.shape} hillTop ${r.hillTop} dests [${r.dests}] start ${r.start} end ${r.end}`);
  if (exp.miles === null) check(tag, s.miles === null, `miles ${s.miles} should be open`);
  else if (exp.miles != null) check(tag, close(s.miles, exp.miles, 0.02), `miles ${s.miles.toFixed(2)} != ${exp.miles.toFixed(2)}`);
  if (exp.pace) check(tag, s.pace === exp.pace, `pace ${s.pace} != ${exp.pace}`);
  for (const k of ['hill', 'fast', 'trails', 'avoidSteps', 'shape', 'hillTop', 'maxGrade']) if (k in exp) check(tag, r[k] === exp[k], `${k} ${r[k]} != ${exp[k]}`);
  if (exp.dests) check(tag, JSON.stringify(r.dests) === JSON.stringify(exp.dests), `dests [${r.dests}] != [${exp.dests}]`);
  if ('end' in exp) check(tag, (r.end || '').toLowerCase().includes(exp.end.toLowerCase()), `end ${r.end}`);
  if ('start' in exp) check(tag, (r.start || '').toLowerCase() === exp.start.toLowerCase(), `start ${r.start}`);
  // plan it and confirm the routes land on the target
  const start = r.start ? Router.geocode(g, r.start, HOME) : HOME;
  const end = r.end ? Router.geocode(g, r.end, HOME) : null;
  check(tag, !!start && (!r.end || !!end), `geocode failed start=${r.start} end=${r.end}`);
  const dests = r.dests.map(d => g.places.find(p => p.name === d));
  const plan = Router.plan(g, { start: start || HOME, end, targetM: s.miles ? s.miles * MI : null, hill: r.hill || (r.hillTop || dests.length ? 'hilly' : 'rolling'), maxGrade: r.maxGrade, fast: r.fast, trails: r.trails, avoidSteps: r.avoidSteps,
    shape: r.end ? 'loop' : (r.shape || 'loop'), destinations: dests });
  const lens = plan.routes.map(x => x.length / MI);
  console.log(`   routes: ${lens.map(l => l.toFixed(2)).join(', ')} mi (target ${s.miles == null ? 'open' : s.miles.toFixed(2)})`);
  check(tag, plan.routes.length > 0, 'no routes');
  // without required stops every route should be within 7%; with stops the first one should be when feasible
  const minPossible = dests.length ? Math.min(...lens) : 0;
  if (s.miles) for (const l of lens) if (!dests.length || minPossible < s.miles) check(tag, Math.abs(l - s.miles) / s.miles < 0.07 || (dests.length && l <= s.miles * 1.07 && l >= s.miles * 0.85), `route ${l.toFixed(2)} vs target ${s.miles.toFixed(2)}`);
}
console.log(`\n${n - fail}/${n} checks passed`);
process.exit(fail ? 1 : 0);
