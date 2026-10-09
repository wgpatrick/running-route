// Exports: GPX text, a stored (uncompressed) ZIP so the file can leave the viewer, base64, and a cue sheet.
function ExportLib() {
  const MI = 1609.344;
  const CRC = new Int32Array(256);
  for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; CRC[n] = c; }
  function crc32(bytes) { let c = -1; for (let i = 0; i < bytes.length; i++) c = CRC[(c ^ bytes[i]) & 0xff] ^ (c >>> 8); return (c ^ -1) >>> 0; }
  const enc = new TextEncoder();

  // ZIP with "stored" entries: [{name, text}] -> Uint8Array. Readable by every unzipper, including the iOS Files app.
  function zipStore(files, when = new Date()) {
    const dosTime = ((when.getHours() << 11) | (when.getMinutes() << 5) | (when.getSeconds() >> 1)) & 0xffff;
    const dosDate = (((when.getFullYear() - 1980) << 9) | ((when.getMonth() + 1) << 5) | when.getDate()) & 0xffff;
    const parts = [], central = []; let offset = 0;
    const u16 = (v) => [v & 0xff, (v >>> 8) & 0xff], u32 = (v) => [v & 0xff, (v >>> 8) & 0xff, (v >>> 16) & 0xff, (v >>> 24) & 0xff];
    for (const f of files) {
      const name = enc.encode(f.name), data = typeof f.text === 'string' ? enc.encode(f.text) : f.text, crc = crc32(data);
      const common = [...u16(20), ...u16(0x0800), ...u16(0), ...u16(dosTime), ...u16(dosDate), ...u32(crc), ...u32(data.length), ...u32(data.length), ...u16(name.length), ...u16(0)];
      const local = new Uint8Array([...u32(0x04034b50), ...common, ...name]);
      parts.push(local, data);
      central.push(new Uint8Array([...u32(0x02014b50), ...u16(20), ...common, ...u16(0), ...u16(0), ...u16(0), ...u32(0), ...u32(offset), ...name]));
      offset += local.length + data.length;
    }
    const cdSize = central.reduce((s, c) => s + c.length, 0);
    const eocd = new Uint8Array([...u32(0x06054b50), ...u16(0), ...u16(0), ...u16(files.length), ...u16(files.length), ...u32(cdSize), ...u32(offset), ...u16(0)]);
    const out = new Uint8Array(offset + cdSize + eocd.length); let p = 0;
    for (const b of [...parts, ...central, eocd]) { out.set(b, p); p += b.length; }
    return out;
  }

  function toBase64(bytesOrText) {
    const bytes = typeof bytesOrText === 'string' ? enc.encode(bytesOrText) : bytesOrText;
    let s = ''; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(s);
  }

  const xml = (s) => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  // GPX 1.1 track (what WorkOutDoors, Footpath, Komoot, Strava and Garmin all import)
  function gpxText({ name, desc, lat, lon, el }) {
    const pts = []; for (let i = 0; i < lat.length; i++) pts.push(`<trkpt lat="${lat[i].toFixed(6)}" lon="${lon[i].toFixed(6)}"><ele>${(el ? el[i] : 0).toFixed(1)}</ele></trkpt>`);
    return `<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="SF Morning Runs" xmlns="http://www.topografix.com/GPX/1/1">\n<metadata><name>${xml(name)}</name>${desc ? `<desc>${xml(desc)}</desc>` : ''}</metadata>\n<trk><name>${xml(name)}</name><trkseg>\n${pts.join('\n')}\n</trkseg></trk>\n</gpx>\n`;
  }
  const safeName = (name) => (name || 'run').replace(/[^\w\- +.]/g, '').replace(/\s+/g, '-').slice(0, 60) || 'run';

  // Turn-by-turn cues from the street sequence and the line's headings at each change
  function cueSheet(r) {
    const g = r.geom, n = g.lat.length;
    const at = (d) => { let i = 0; while (i < n - 1 && g.cum[i] < d) i++; return i; };
    const heading = (d0, d1) => { const a = at(d0), b = at(d1); if (a === b) return null; const dx = (g.lon[b] - g.lon[a]) * 88000, dy = (g.lat[b] - g.lat[a]) * 111320; return (Math.atan2(dx, dy) * 180 / Math.PI + 360) % 360; };
    const compass = (h) => ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][Math.round(h / 45) % 8];
    // drop hops under 25 m (a crosswalk, a corner cut) so the sheet lists real turns; their length joins the previous street
    const streets = [];
    for (const s of r.streets) { if (!s.name || s.name === 'sidewalks') { if (streets.length) streets[streets.length - 1].len += s.len; continue; } if (s.len < 25 && streets.length) { streets[streets.length - 1].len += s.len; continue; } streets.push({ name: s.name === 'path' ? 'the path' : s.name === 'stairs' ? 'the stairs' : s.name, len: s.len }); }
    const cues = []; let cum = 0;
    for (let i = 0; i < streets.length; i++) {
      const s = streets[i];
      if (i === 0) { const h = heading(0, Math.min(40, s.len)); cues.push({ at: 0, text: `Start ${h == null ? 'on' : compass(h) + ' on'} ${s.name}`, len: s.len }); cum += s.len; continue; }
      const before = heading(Math.max(0, cum - 30), cum), after = heading(cum, Math.min(cum + 30, r.length));
      let turn = 'Continue onto';
      if (before != null && after != null) {
        let d = after - before; while (d > 180) d -= 360; while (d < -180) d += 360;
        const a = Math.abs(d);
        turn = a < 20 ? 'Continue onto' : a < 60 ? (d > 0 ? 'Bear right onto' : 'Bear left onto') : a < 150 ? (d > 0 ? 'Right onto' : 'Left onto') : 'Turn around onto';
      }
      cues.push({ at: cum, text: `${turn} ${s.name}`, len: s.len }); cum += s.len;
    }
    // fold trivial "continue" hops on paths into the previous cue's length
    const out = [];
    for (const c of cues) { const last = out[out.length - 1]; if (last && /^Continue onto the (path|stairs)$/.test(c.text)) { last.len += c.len; continue; } out.push(c); }
    out.push({ at: r.length, text: 'Finish', len: 0 });
    return out;
  }
  const cueText = (cues) => cues.map(c => `${(c.at / MI).toFixed(1).padStart(4)} mi  ${c.text}${c.len > 0 ? `  (${(c.len / MI).toFixed(2)} mi)` : ''}`).join('\n');

  return { zipStore, crc32, toBase64, gpxText, safeName, cueSheet, cueText };
}
if (typeof module !== 'undefined') module.exports = ExportLib;
