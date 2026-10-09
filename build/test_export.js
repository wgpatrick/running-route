// Exports: the zip unpacks with a standard tool, GPX parses, cue sheet reads sensibly.
const fs = require('fs'), zlib = require('zlib'), { execSync } = require('child_process');
const R = require('../app/router.js')(), EX = require('../app/export.js')();
const buf = zlib.gunzipSync(Buffer.from(fs.readFileSync(__dirname + '/data/blob.b64', 'utf8'), 'base64'));
const g = R.decode(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.length));
const HOME = { lat: 37.7387, lon: -122.41984 }, MI = 1609.344;
const r = R.plan(g, { start: HOME, targetM: 5 * MI, hill: 'rolling', seed: 4 }).routes[0];
let fail = 0;
const gpx = EX.gpxText({ name: 'Test loop', desc: 'five miles', lat: r.geom.lat, lon: r.geom.lon, el: r.geom.el });
const zip = EX.zipStore([{ name: 'Test-loop.gpx', text: gpx }]);
const out = process.argv[2] || '/tmp'; fs.writeFileSync(out + '/t.zip', zip);
const listing = execSync(`python3 -I -c "import zipfile,sys; z=zipfile.ZipFile(sys.argv[1]); print(z.testzip()); i=z.infolist()[0]; d=z.read(i); print(i.filename, len(d), d[:38])" ${out}/t.zip`).toString();
console.log('zip:', listing.trim().replace(/\n/g, ' | '));
if (!/^None\nTest-loop\.gpx \d+ b'<\?xml version="1\.0" encoding="UTF-8"\?>/.test(listing)) { fail++; console.log('  FAIL zip'); }
const pts = (gpx.match(/<trkpt /g) || []).length;
if (pts !== r.geom.lat.length || !/<name>Test loop<\/name>/.test(gpx)) { fail++; console.log('  FAIL gpx'); }
if (EX.toBase64('hello') !== 'aGVsbG8=') { fail++; console.log('  FAIL base64'); }
const cues = EX.cueSheet(r);
console.log(EX.cueText(cues).split('\n').slice(0, 6).join('\n'), '\n   …', cues.length, 'cues');
if (!(cues.length >= 4 && /^Start/.test(cues[0].text) && cues[cues.length - 1].text === 'Finish' && cues.some(c => /^(Left|Right) onto/.test(c.text)))) { fail++; console.log('  FAIL cues'); }
console.log(fail ? fail + ' failures' : 'export checks passed');
process.exit(fail ? 1 : 0);
