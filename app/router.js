// SF run router: decodes the packed street graph and plans running routes.
// Runs both on the page (for drawing + geocoding) and in a Web Worker (for routing).
function RouterLib() {
  const LAT0 = 37.76, M_LAT = 111320, M_LON = 111320 * Math.cos(LAT0 * Math.PI / 180);
  const LON0 = -122.44;
  const MI = 1609.344;

  // ---------- decoding ----------
  function decode(buf) {
    const dv = new DataView(buf);
    const hlen = dv.getUint32(0, true);
    const header = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, hlen)));
    const base = 4 + hlen;
    const T = { i4: Int32Array, u4: Uint32Array, i2: Int16Array, u2: Uint16Array, u1: Uint8Array };
    const f = {};
    for (const x of header.fields) {
      const C = T[x.dt];
      f[x.k] = new C(buf.slice(base + x.off, base + x.off + x.len));
    }
    const nN = f.nodeLon.length, nE = f.eU.length;
    const g = {
      classes: header.classes, names: header.names, addr: header.addr, places: header.places,
      nN, nE,
      lat: new Float64Array(nN), lon: new Float64Array(nN), el: new Float32Array(nN),
      x: new Float64Array(nN), y: new Float64Array(nN),
      eU: f.eU, eV: f.eV, eCls: f.eCls, eName: f.eName,
      eLen: new Float32Array(nE), eUp: new Float32Array(nE), eDn: new Float32Array(nE),
      eOff: f.eOff, eN: f.eN,
    };
    for (let i = 0; i < nN; i++) {
      g.lat[i] = f.nodeLat[i] / 1e5; g.lon[i] = f.nodeLon[i] / 1e5; g.el[i] = f.nodeEl[i] / 10;
      g.x[i] = (g.lon[i] - LON0) * M_LON; g.y[i] = (g.lat[i] - LAT0) * M_LAT;
    }
    for (let e = 0; e < nE; e++) { g.eLen[e] = f.eLen[e] / 10; g.eUp[e] = f.eUp[e] / 10; g.eDn[e] = f.eDn[e] / 10; }
    // vertex arrays: edge e owns vertices [vOff[e], vOff[e]+eN[e]) running u -> v
    let nv = 0; const vOff = new Uint32Array(nE);
    for (let e = 0; e < nE; e++) { vOff[e] = nv; nv += f.eN[e]; }
    const vLat = new Float64Array(nv), vLon = new Float64Array(nv), vEl = new Float32Array(nv);
    const G = f.geom;
    for (let e = 0; e < nE; e++) {
      const u = f.eU[e];
      let lo = f.nodeLon[u], la = f.nodeLat[u], z = f.nodeEl[u];
      let k = vOff[e], p = f.eOff[e] * 3;
      vLat[k] = la / 1e5; vLon[k] = lo / 1e5; vEl[k] = z / 10; k++;
      for (let j = 1; j < f.eN[e]; j++, k++) {
        lo += G[p++]; la += G[p++]; z += G[p++];
        vLat[k] = la / 1e5; vLon[k] = lo / 1e5; vEl[k] = z / 10;
      }
    }
    Object.assign(g, { vOff, vLat, vLon, vEl });
    g.steepCache = new Map(); g.STEPS = header.classes.indexOf('steps');
    // CSR adjacency (directed half-edges)
    const deg = new Uint32Array(nN + 1);
    for (let e = 0; e < nE; e++) { deg[f.eU[e] + 1]++; deg[f.eV[e] + 1]++; }
    for (let i = 0; i < nN; i++) deg[i + 1] += deg[i];
    const adjTo = new Int32Array(2 * nE), adjE = new Int32Array(2 * nE), fill = deg.slice(0, nN);
    for (let e = 0; e < nE; e++) {
      const u = f.eU[e], v = f.eV[e];
      adjTo[fill[u]] = v; adjE[fill[u]++] = e;          // forward: e >= 0
      adjTo[fill[v]] = u; adjE[fill[v]++] = ~e;         // backward: ~e < 0
    }
    Object.assign(g, { adjStart: deg, adjTo, adjE });
    // spatial grid for snapping
    const CELL = 150, gx0 = -9000, gy0 = -7000, GW = 120;
    const cells = new Map();
    for (let i = 0; i < nN; i++) {
      const cx = Math.floor((g.x[i] - gx0) / CELL), cy = Math.floor((g.y[i] - gy0) / CELL), key = cy * GW + cx;
      let a = cells.get(key); if (!a) cells.set(key, a = []); a.push(i);
    }
    g.grid = { CELL, gx0, gy0, GW, cells };
    // which nodes are touched by "real" ways (not only sidewalks/crosswalks) — nicer snap targets
    const ci = (n) => header.classes.indexOf(n);
    const SW = ci('sidewalk'), CW = ci('crosswalk');
    g.goodNode = new Uint8Array(nN);
    for (let e = 0; e < nE; e++) if (f.eCls[e] !== SW && f.eCls[e] !== CW) { g.goodNode[f.eU[e]] = 1; g.goodNode[f.eV[e]] = 1; }
    g.streetIndex = buildStreetIndex(g);
    return g;
  }

  async function decodeBase64Gz(b64) {
    const bin = atob(b64.trim()); const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    return decode(await new Response(stream).arrayBuffer());
  }

  const toXY = (lat, lon) => [(lon - LON0) * M_LON, (lat - LAT0) * M_LAT];

  function nearestNode(g, lat, lon, opts = {}) {
    const [x, y] = toXY(lat, lon), G = g.grid;
    const cx = Math.floor((x - G.gx0) / G.CELL), cy = Math.floor((y - G.gy0) / G.CELL);
    let best = -1, bd = Infinity;
    for (let r = 0; r <= 8 && (best < 0 || r <= 2); r++) {
      for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
        if (Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
        const a = G.cells.get((cy + dy) * G.GW + cx + dx); if (!a) continue;
        for (const i of a) {
          if (opts.good && !g.goodNode[i]) continue;
          const d = (g.x[i] - x) ** 2 + (g.y[i] - y) ** 2;
          if (d < bd) { bd = d; best = i; }
        }
      }
    }
    return best;
  }
  // nodes within radius (m)
  function nodesNear(g, x, y, rad) {
    const G = g.grid, out = [];
    const c0x = Math.floor((x - rad - G.gx0) / G.CELL), c1x = Math.floor((x + rad - G.gx0) / G.CELL);
    const c0y = Math.floor((y - rad - G.gy0) / G.CELL), c1y = Math.floor((y + rad - G.gy0) / G.CELL);
    for (let cy = c0y; cy <= c1y; cy++) for (let cx = c0x; cx <= c1x; cx++) {
      const a = G.cells.get(cy * G.GW + cx); if (!a) continue;
      for (const i of a) if ((g.x[i] - x) ** 2 + (g.y[i] - y) ** 2 <= rad * rad && g.goodNode[i]) out.push(i);
    }
    return out;
  }

  // ---------- geocoding ----------
  const SUFFIX = { street: 'st', st: 'st', avenue: 'ave', ave: 'ave', av: 'ave', boulevard: 'blvd', blvd: 'blvd', drive: 'dr', dr: 'dr',
    road: 'rd', rd: 'rd', lane: 'ln', ln: 'ln', place: 'pl', pl: 'pl', court: 'ct', ct: 'ct', terrace: 'ter', ter: 'ter', way: 'way',
    alley: 'aly', aly: 'aly', highway: 'hwy', hwy: 'hwy', circle: 'cir', cir: 'cir', plaza: 'plz', parkway: 'pkwy' };
  const ORD = { first: '1st', second: '2nd', third: '3rd', fourth: '4th', fifth: '5th', sixth: '6th', seventh: '7th', eighth: '8th', ninth: '9th', tenth: '10th' };
  function normStreet(s) {
    let w = s.toLowerCase().replace(/[.,']/g, ' ').replace(/\bsaint\b/g, 'st').split(/\s+/).filter(Boolean).map(t => ORD[t] || t);
    if (w[0] === 'st' && w.length > 2) w[0] = 'saint';
    let suf = '';
    if (w.length > 1 && SUFFIX[w[w.length - 1]]) suf = SUFFIX[w.pop()];
    return { core: w.join(' '), suf };
  }
  function buildStreetIndex(g) {
    // core name -> list of {suf, edges[]}
    const m = new Map();
    for (let e = 0; e < g.nE; e++) {
      const nm = g.names[g.eName[e]]; if (!nm) continue;
      const { core, suf } = normStreet(nm);
      const key = core + '|' + suf;
      let a = m.get(key); if (!a) m.set(key, a = []); a.push(e);
    }
    return m;
  }
  function streetEdges(g, q) {
    const { core, suf } = normStreet(q);
    const out = [];
    for (const [key, edges] of g.streetIndex) {
      const [c, s] = key.split('|');
      if (c === core && (!suf || !s || s === suf)) out.push(...edges);
    }
    return out;
  }
  function placeMatch(g, q) {
    const s = q.toLowerCase().trim();
    if (!s) return null;
    let best = null;
    for (const p of g.places) {
      const n = p.name.toLowerCase();
      const aliases = [n, n.replace(/ \(.*\)/, ''), ...(p.aliases || [])];
      for (const a of aliases) if (a === s || (s.length >= 4 && (a.includes(s) || s.includes(a)))) {
        const sc = a === s ? 3 : (s.includes(a) ? 2 : 1);
        if (!best || sc > best.sc) best = { sc, p };
      }
    }
    return best && best.p;
  }
  function geocode(g, text, home) {
    const raw = (text || '').trim();
    const s = raw.toLowerCase();
    if (!s || /^(home|my place|my house|my home|start|same|same as start)$/.test(s) || s.startsWith('339 elsie')) return home;
    let m = s.match(/^\s*(-?\d{2}\.\d+)\s*,\s*(-?\d{3}\.\d+)\s*$/);
    if (m) return { lat: +m[1], lon: +m[2], label: raw };
    // intersection
    m = raw.match(/^(.+?)\s+(?:&|and|at|\/|@|x)\s+(.+)$/i);
    if (m) {
      const A = streetEdges(g, m[1]), B = streetEdges(g, m[2]);
      if (A.length && B.length) {
        const na = new Set(); for (const e of A) { na.add(g.eU[e]); na.add(g.eV[e]); }
        let bestN = -1, bd = Infinity;
        for (const e of B) for (const n of [g.eU[e], g.eV[e]]) if (na.has(n)) { bestN = n; bd = 0; }
        if (bestN < 0) { // closest pair of endpoints
          for (const e of B) for (const n of [g.eU[e], g.eV[e]]) for (const a of na) {
            const d = (g.x[n] - g.x[a]) ** 2 + (g.y[n] - g.y[a]) ** 2; if (d < bd) { bd = d; bestN = n; }
          }
          if (bd > 120 * 120) bestN = -1;
        }
        if (bestN >= 0) return { lat: g.lat[bestN], lon: g.lon[bestN], label: titleCase(m[1]) + ' & ' + titleCase(m[2]) };
      }
    }
    // house number + street
    m = raw.match(/^\s*(\d+)[a-z]?\s+(.+?)(?:,.*)?$/i);
    if (m) {
      const num = +m[1]; const q = normStreet(m[2].replace(/\b(san francisco|sf|ca|california|\d{5})\b/gi, '').trim());
      let cands = [];
      for (const key in g.addr) {
        const { core, suf } = normStreet(key);
        if (core === q.core && (!q.suf || !suf || q.suf === suf)) cands.push(key);
      }
      let best = null;
      for (const key of cands) {
        const a = g.addr[key];
        let lo = null, hi = null;
        for (let i = 0; i < a.length; i += 3) {
          if (a[i] <= num && (!lo || a[i] >= lo[0])) lo = [a[i], a[i + 1], a[i + 2]];
          if (a[i] >= num && (!hi || a[i] <= hi[0])) hi = [a[i], a[i + 1], a[i + 2]];
        }
        const pick = lo && hi ? (lo[0] === hi[0] ? lo : null) : (lo || hi);
        let lat, lon, gap;
        if (pick) { lon = pick[1] / 1e5; lat = pick[2] / 1e5; gap = Math.abs(pick[0] - num); }
        else { const t = (num - lo[0]) / (hi[0] - lo[0]); lon = (lo[1] + t * (hi[1] - lo[1])) / 1e5; lat = (lo[2] + t * (hi[2] - lo[2])) / 1e5; gap = 0; }
        if (!best || gap < best.gap) best = { lat, lon, gap, key };
      }
      if (best && best.gap < 400) return { lat: best.lat, lon: best.lon, label: num + ' ' + titleCase(best.key) };
    }
    const p = placeMatch(g, raw);
    if (p) return { lat: p.lat, lon: p.lon, label: p.name };
    // bare street name: middle of the street
    const E = streetEdges(g, raw);
    if (E.length) { const e = E[Math.floor(E.length / 2)]; return { lat: g.lat[g.eU[e]], lon: g.lon[g.eU[e]], label: titleCase(raw) }; }
    return null;
  }
  const titleCase = (s) => s.toLowerCase().replace(/\b[a-z]/g, c => c.toUpperCase());

  // ---------- routing ----------
  class Heap {
    constructor(n) { this.k = new Float64Array(n); this.v = new Int32Array(n); this.n = 0; }
    push(k, v) {
      if (this.n >= this.k.length) { const k2 = new Float64Array(this.k.length * 2); k2.set(this.k); this.k = k2; const v2 = new Int32Array(this.v.length * 2); v2.set(this.v); this.v = v2; }
      let i = this.n++; const K = this.k, V = this.v;
      while (i > 0) { const p = (i - 1) >> 1; if (K[p] <= k) break; K[i] = K[p]; V[i] = V[p]; i = p; }
      K[i] = k; V[i] = v;
    }
    pop() {
      const K = this.k, V = this.v, top = V[0]; const k = K[--this.n], v = V[this.n];
      let i = 0;
      for (;;) { let c = 2 * i + 1; if (c >= this.n) break; if (c + 1 < this.n && K[c + 1] < K[c]) c++; if (K[c] >= k) break; K[i] = K[c]; V[i] = V[c]; i = c; }
      K[i] = k; V[i] = v; return top;
    }
  }

  const BASE_F = { residential: 1, tertiary: 1.05, secondary: 1.15, primary: 1.3, trunk: 1.7, service: 1.1, footway: 0.95, sidewalk: 1, crosswalk: 1,
    path: 0.9, steps: 1.6, cycleway: 0.92, pedestrian: 0.95, track: 0.95, living_street: 0.95, unclassified: 1.05, bridleway: 1 };

  function makeCost(g, prefs) {
    const F = new Float32Array(g.classes.length);
    g.classes.forEach((c, i) => {
      let f = BASE_F[c] ?? 1;
      if (prefs.trails && (c === 'path' || c === 'track' || c === 'footway' || c === 'bridleway')) f *= 0.7;
      if (prefs.fast) { if (c === 'steps') f = 5; if (c === 'cycleway' || c === 'path') f *= 0.9; if (c === 'primary' || c === 'secondary') f *= 0.95; }
      if (prefs.avoidSteps && c === 'steps') f = 20;
      if (prefs.hill === 'flat' && c === 'steps') f *= 4;
      F[i] = f;
    });
    // metres of extra distance each metre of climb/descent is worth; 'flat' (Flattest) minimises total climbing
    const W = { flat: [25, 8], rolling: [1.5, 0.6], hilly: [-1.0, 0.3], max: [-2.4, 0] }[prefs.hill || 'rolling'];
    const floor = prefs.hill === 'hilly' || prefs.hill === 'max' ? 0.25 : 0.6;
    const SM = prefs.maxGrade ? steepMetres(g, prefs.maxGrade) : null;
    const cost = new Float32Array(2 * g.nE); // [2e] forward, [2e+1] backward
    for (let e = 0; e < g.nE; e++) {
      const L = g.eLen[e], base = L * F[g.eCls[e]];
      for (let d = 0; d < 2; d++) {
        const up = d ? g.eDn[e] : g.eUp[e], dn = d ? g.eUp[e] : g.eDn[e];
        let c = base + W[0] * up + W[1] * dn;
        if (SM) { // steer around anything steeper than the runner's limit, up or down
          const [u, w] = steepDir(SM, d ? ~e : e);
          c += u * 90 + w * 70;
        }
        if (prefs.fast && L > 5) { const gr = up / L; if (gr > 0.05) c += L * (gr - 0.05) * 25; const gd = dn / L; if (gd > 0.08) c += L * (gd - 0.08) * 10; }
        cost[2 * e + d] = Math.max(c, L * floor);
      }
    }
    return { cost, hMin: Math.min(floor, ...F) };
  }

  function makeSearch(g) {
    const dist = new Float64Array(g.nN).fill(Infinity), prevE = new Int32Array(g.nN), stamp = new Uint32Array(g.nN);
    let gen = 0; const heap = new Heap(1 << 16);
    // A* from s to t, edge cost * mult(e)
    return function search(s, t, C, used) {
      gen++; heap.n = 0;
      const tx = g.x[t], ty = g.y[t], h = (i) => Math.hypot(g.x[i] - tx, g.y[i] - ty) * C.hMin;
      dist[s] = 0; stamp[s] = gen; prevE[s] = 0x7fffffff; heap.push(h(s), s);
      while (heap.n) {
        const u = heap.pop();
        if (u === t) break;
        const du = dist[u];
        for (let k = g.adjStart[u], ke = g.adjStart[u + 1]; k < ke; k++) {
          const ae = g.adjE[k], e = ae >= 0 ? ae : ~ae, v = g.adjTo[k];
          let c = C.cost[2 * e + (ae >= 0 ? 0 : 1)];
          if (used) { const r = used[e]; if (r) c *= 1 + 2.5 * r; }
          const nd = du + c;
          if (stamp[v] !== gen || nd < dist[v]) { stamp[v] = gen; dist[v] = nd; prevE[v] = ae; heap.push(nd + h(v), v); }
        }
      }
      if (stamp[t] !== gen) return null;
      const path = []; let v = t;
      while (v !== s) { const ae = prevE[v]; path.push(ae); const e = ae >= 0 ? ae : ~ae; v = ae >= 0 ? g.eU[e] : g.eV[e]; }
      path.reverse(); return path;
    };
  }

  // route through a sequence of nodes, discouraging re-use of edges already run
  function routeVia(g, search, C, nodes) {
    const used = new Uint8Array(g.nE); const all = [];
    for (let i = 0; i + 1 < nodes.length; i++) {
      if (nodes[i] === nodes[i + 1]) continue;
      const p = search(nodes[i], nodes[i + 1], C, used);
      if (!p) return null;
      for (const ae of p) { const e = ae >= 0 ? ae : ~ae; used[e] = Math.min(255, used[e] + 1); all.push(ae); }
    }
    return all;
  }

  // Least distance steeper than `lim` needed to get `rad` metres away from node s
  // (some doorsteps sit on a hill, so a little steepness can be unavoidable).
  function steepEscape(g, s, lim, rad = 700) {
    const SM = steepMetres(g, lim), N = g.nN, d = new Float64Array(N).fill(Infinity), over = new Float32Array(N), heap = new Heap(4096);
    d[s] = 0; heap.push(0, s); let best = Infinity;
    while (heap.n) {
      const u = heap.pop(); const du = d[u];
      if (du > (best === Infinity ? Infinity : best * 1000 + rad * 3)) break;
      if (Math.hypot(g.x[u] - g.x[s], g.y[u] - g.y[s]) > rad) { best = Math.min(best, over[u]); continue; }
      for (let k = g.adjStart[u]; k < g.adjStart[u + 1]; k++) {
        const ae = g.adjE[k], e = ae >= 0 ? ae : ~ae, v = g.adjTo[k];
        const [a, b] = steepDir(SM, ae), sm = a + b, c = g.eLen[e] + sm * 1000;
        if (du + c < d[v]) { d[v] = du + c; over[v] = over[u] + sm; heap.push(d[v], v); }
      }
    }
    return best === Infinity ? 0 : best;
  }

  // For a grade limit, metres of each edge that are steeper than it (40 m windows),
  // split into uphill and downhill when the edge is run forward. Stairs always count.
  function steepMetres(g, lim) {
    const key = Math.round(lim * 1000);
    if (g.steepCache.has(key)) return g.steepCache.get(key);
    const upF = new Float32Array(g.nE), dnF = new Float32Array(g.nE);
    for (let e = 0; e < g.nE; e++) {
      const o = g.vOff[e], n = g.eN[e];
      if (g.eCls[e] === g.STEPS && lim < 0.25) { const net = g.vEl[o + n - 1] - g.vEl[o]; if (net >= 0) upF[e] = g.eLen[e]; else dnF[e] = g.eLen[e]; continue; }
      const cum = [0];
      for (let j = 1; j < n; j++) cum.push(cum[j - 1] + Math.hypot((g.vLon[o + j] - g.vLon[o + j - 1]) * M_LON, (g.vLat[o + j] - g.vLat[o + j - 1]) * M_LAT));
      const L = cum[n - 1];
      if (L < 40) { const gr = (g.vEl[o + n - 1] - g.vEl[o]) / Math.max(L, 15); if (gr > lim) upF[e] = L; else if (-gr > lim) dnF[e] = L; continue; }
      for (let k = 0; k + 1 < n; k++) {
        let a = k, b = k + 1;
        while (cum[b] - cum[a] < 40 && (a > 0 || b < n - 1)) { if (a > 0) a--; if (cum[b] - cum[a] < 40 && b < n - 1) b++; }
        const gr = (g.vEl[o + b] - g.vEl[o + a]) / Math.max(cum[b] - cum[a], 1), seg = cum[k + 1] - cum[k];
        if (gr > lim) upF[e] += seg; else if (-gr > lim) dnF[e] += seg;
      }
    }
    const r = { upF, dnF }; g.steepCache.set(key, r); return r;
  }
  const steepDir = (sm, ae) => ae >= 0 ? [sm.upF[ae], sm.dnF[ae]] : [sm.dnF[~ae], sm.upF[~ae]]; // [uphill m, downhill m] as run

  function pathLength(g, path) { let L = 0; for (const ae of path) L += g.eLen[ae >= 0 ? ae : ~ae]; return L; }

  // ---------- analysis ----------
  function analyze(g, path, P = {}) {
    const lat = [], lon = [], el = [], cum = [], edgeAt = [];
    let L = 0;
    for (const ae of path) {
      const e = ae >= 0 ? ae : ~ae, o = g.vOff[e], n = g.eN[e];
      for (let j = 0; j < n; j++) {
        const k = ae >= 0 ? o + j : o + n - 1 - j;
        if (lat.length && j === 0) continue;
        if (lat.length) { L += Math.hypot((g.vLon[k] - lon[lon.length - 1]) * M_LON, (g.vLat[k] - lat[lat.length - 1]) * M_LAT); }
        lat.push(g.vLat[k]); lon.push(g.vLon[k]); el.push(g.vEl[k]); cum.push(L); edgeAt.push(e);
      }
    }
    // resample elevation every 25 m for grades
    const step = 25, rs = [];
    for (let d = 0, i = 0; d <= L; d += step) {
      while (i < cum.length - 2 && cum[i + 1] < d) i++;
      const t = cum[i + 1] > cum[i] ? (d - cum[i]) / (cum[i + 1] - cum[i]) : 0;
      rs.push(el[i] + Math.max(0, Math.min(1, t)) * ((el[i + 1] ?? el[i]) - el[i]));
    }
    let gain = 0, loss = 0;
    for (let i = 1; i < rs.length; i++) { const d = rs[i] - rs[i - 1]; if (d > 0) gain += d; else loss -= d; }
    // grade over 100 m windows
    const W = 4; let maxUp = 0, maxDn = 0; const bins = [0, 0, 0, 0]; // <3, 3-6, 6-10, 10+
    const gradeAt = [];
    for (let i = 0; i < rs.length; i++) {
      const a = Math.max(0, i - W / 2), b = Math.min(rs.length - 1, i + W / 2);
      const gr = b > a ? (rs[b] - rs[a]) / ((b - a) * step) : 0;
      gradeAt.push(gr);
      maxUp = Math.max(maxUp, gr); maxDn = Math.min(maxDn, gr);
      const ag = Math.abs(gr); bins[ag < 0.03 ? 0 : ag < 0.06 ? 1 : ag < 0.10 ? 2 : 3] += step;
    }
    // distance steeper than the runner's limit (same measure the router uses)
    let overUp = 0, overDn = 0, steep50 = 0;
    for (let i = 0; i + 2 < rs.length; i++) steep50 = Math.max(steep50, Math.abs((rs[i + 2] - rs[i]) / (2 * step)));
    const steepRanges = [];
    if (P.maxGrade) {
      const SM = steepMetres(g, P.maxGrade); let at = 0;
      for (const ae of path) {
        const [u, w] = steepDir(SM, ae), L = g.eLen[ae >= 0 ? ae : ~ae]; overUp += u; overDn += w;
        if (u + w > 0) { const last = steepRanges[steepRanges.length - 1]; if (last && at - last[1] < 15) last[1] = at + L; else steepRanges.push([at, at + L]); }
        at += L;
      }
    }
    // climbs: stretches where the 100 m grade stays above 2.5%, bridging short flat bits (<=100 m, <5 m drop),
    // so a long gentle rise isn't reported as one "climb" and a steep pitch isn't hidden inside it
    const climbs = [];
    {
      let a = -1, lastUp = -1;
      const close = (endI) => {
        let s0 = a, e0 = endI;
        for (let k = Math.max(0, a - 2); k <= a; k++) if (rs[k] < rs[s0]) s0 = k;
        for (let k = endI; k <= Math.min(rs.length - 1, endI + 2); k++) if (rs[k] > rs[e0]) e0 = k;
        const gainC = rs[e0] - rs[s0];
        if (gainC >= 12 && e0 > s0) climbs.push({ from: s0 * step, to: e0 * step, gain: gainC, grade: gainC / ((e0 - s0) * step) });
      };
      for (let i = 0; i < rs.length; i++) {
        if (gradeAt[i] > 0.025) { if (a < 0) a = i; lastUp = i; }
        else if (a >= 0 && (i - lastUp > 4 || rs[lastUp] - rs[i] > 5)) { close(lastUp); a = -1; }
      }
      if (a >= 0) close(lastUp);
    }
    for (const c of climbs) c.street = dominantName(g, path, cum, edgeAt, c.from, c.to);
    climbs.sort((a, b) => b.gain - a.gain);
    // street sequence
    const seq = [];
    for (const ae of path) {
      const e = ae >= 0 ? ae : ~ae, cls = g.classes[g.eCls[e]];
      let nm = cleanName(g.names[g.eName[e]]);
      if (!nm) nm = cls === 'steps' ? 'stairs' : (cls === 'path' || cls === 'track' || cls === 'footway' || cls === 'bridleway' || cls === 'pedestrian') ? 'path' : '';
      const last = seq[seq.length - 1];
      if (last && (last.name === nm || !nm)) last.len += g.eLen[e];
      else if (last && !last.name) { last.name = nm; last.len += g.eLen[e]; }
      else seq.push({ name: nm, len: g.eLen[e] });
    }
    const seq2 = [];
    for (const s of seq) {
      const last = seq2[seq2.length - 1];
      if (last && s.len < 60 && (s.name === 'path' || !s.name)) { last.len += s.len; continue; }
      if (last && last.name === s.name) { last.len += s.len; continue; }
      seq2.push({ ...s, name: s.name || 'path' });
    }
    // overlap: fraction of distance on edges run more than once
    const cnt = new Map(); for (const ae of path) { const e = ae >= 0 ? ae : ~ae; cnt.set(e, (cnt.get(e) || 0) + 1); }
    let rep = 0; for (const [e, c] of cnt) if (c > 1) rep += g.eLen[e] * c;
    let stepsN = 0; for (const ae of path) if (g.classes[g.eCls[ae >= 0 ? ae : ~ae]] === 'steps') stepsN++;
    // places passed
    const passed = [];
    for (const p of g.places) {
      const [px, py] = toXY(p.lat, p.lon); let bd = Infinity, bi = 0;
      for (let i = 0; i < lat.length; i += 2) { const d = (lon[i] - p.lon) ** 2 * M_LON * M_LON + (lat[i] - p.lat) ** 2 * M_LAT * M_LAT; if (d < bd) { bd = d; bi = i; } }
      if (bd < 160 * 160) passed.push({ name: p.name, kind: p.kind, at: cum[bi] });
    }
    passed.sort((a, b) => a.at - b.at);
    let hiI = 0; for (let i = 0; i < el.length; i++) if (el[i] > el[hiI]) hiI = i;
    return {
      length: L, gain, loss, maxUp, maxDn, bins, climbs: climbs.slice(0, 5), streets: seq2, overlap: rep / Math.max(L, 1),
      steps: stepsN, passed, overUp, overDn, steep50, steepRanges, maxGrade: P.maxGrade || null, high: { el: el[hiI], at: cum[hiI], lat: lat[hiI], lon: lon[hiI] },
      colorGrades: gradeAt.map((_, i) => { let s = 0, n = 0; for (let j = Math.max(0, i - 3); j <= Math.min(gradeAt.length - 1, i + 3); j++) { s += gradeAt[j]; n++; } return s / n; }),
      lowEl: Math.min(...el), geom: { lat, lon, el, cum }, gradeStep: step, grades: gradeAt, profile: rs,
    };
  }
  // "Mission Street, W. Sidewalk" -> "Mission Street"
  const cleanName = (n) => (n || '').replace(/,?\s*(?:[NSEW]\.?|North|South|East|West)?\s*Sidewalk$/i, '').trim();
  function dominantName(g, path, cum, edgeAt, from, to) {
    const tally = new Map();
    for (let i = 1; i < cum.length; i++) {
      if (cum[i] < from || cum[i - 1] > to) continue;
      const e = edgeAt[i]; const cls = g.classes[g.eCls[e]];
      const nm = cleanName(g.names[g.eName[e]]) || (cls === 'steps' ? 'stairs' : (cls === 'sidewalk' || cls === 'crosswalk') ? '' : 'park paths');
      tally.set(nm, (tally.get(nm) || 0) + (nm ? 1 : 0.3) * (cum[i] - cum[i - 1]));
    }
    let best = '', bl = 0; for (const [n, l] of tally) if (l > bl) { bl = l; best = n; }
    return best || 'sidewalks';
  }

  // Grade-adjusted pace multiplier (damped Minetti cost of running on slopes)
  function gapFactor(gr) {
    const i = Math.max(-0.3, Math.min(0.3, gr));
    const C = 155.4 * i ** 5 - 30.4 * i ** 4 - 43.3 * i ** 3 + 46.3 * i ** 2 + 19.5 * i + 3.6;
    return Math.max(0.86, 1 + 0.55 * (C / 3.6 - 1));
  }
  function estimateSeconds(a, paceSecPerMile) {
    let t = 0; const per = paceSecPerMile / MI;
    for (const gr of a.grades) t += a.gradeStep * per * gapFactor(gr);
    return t * (a.length / Math.max(1, a.grades.length * a.gradeStep));
  }

  // ---------- planning ----------
  function scoreRoute(a, P) {
    const T = P.targetM;
    let s = 0;
    if (T) s += ((a.length - T) / T / 0.05) ** 2;
    const gpk = a.gain / (a.length / 1000);
    const hill = P.hill || 'rolling';
    if (hill === 'flat') s += gpk * 1.4;
    else if (hill === 'rolling') s += Math.abs(gpk - 14) / 8;
    else if (hill === 'hilly') s += Math.max(0, 28 - gpk) / 6;
    else s += Math.max(0, 60 - gpk) / 8;
    if (P.shape !== 'out-and-back') s += a.overlap / 0.12;
    if (P.fast) s += (a.bins[2] + 2 * a.bins[3]) / a.length / 0.04 + a.steps * 0.5;
    if (P.avoidSteps) s += a.steps * 2;
    if (P.maxGrade) s += Math.max(0, a.overUp + 0.8 * a.overDn - (P._unavoidable || 0)) / (0.005 * a.length);
    return s;
  }

  function plan(g, P, progress) {
    const t0 = Date.now();
    const S = nearestNode(g, P.start.lat, P.start.lon, { good: true });
    const E = P.end ? nearestNode(g, P.end.lat, P.end.lon, { good: true }) : S;
    const C = makeCost(g, P);
    // --- variety ---
    // Streets right around the start/finish are shared by every route, so they're exempt from repeat penalties.
    const DOOR = 350, nearDoor = (n) => Math.hypot(g.x[n] - g.x[S], g.y[n] - g.y[S]) < DOOR || Math.hypot(g.x[n] - g.x[E], g.y[n] - g.y[E]) < DOOR;
    const doorEdge = (e) => nearDoor(g.eU[e]) && nearDoor(g.eV[e]);
    // Small per-edge noise so near-equal grid streets take turns instead of the same one always winning.
    if (P.seed != null) {
      let lo = 1;
      for (let e = 0; e < g.nE; e++) {
        let h = Math.imul(e ^ 0x9e3779b9, 0x85ebca6b) ^ Math.imul(P.seed + 1, 0xc2b2ae35); h ^= h >>> 13; h = Math.imul(h, 0x27d4eb2d); h ^= h >>> 15;
        const m = 0.82 + 0.36 * ((h >>> 0) / 4294967296); lo = Math.min(lo, m);
        C.cost[2 * e] *= m; C.cost[2 * e + 1] *= m;
      }
      C.hMin *= lo;
    }
    // Recently shown routes: make their streets cost more so new plans explore elsewhere.
    const seenW = new Float32Array(g.nE);
    if (P.avoid && P.avoid.edges) {
      P.avoid.edges.forEach((e, i) => { if (e >= 0 && e < g.nE && !doorEdge(e)) seenW[e] += P.avoid.weights ? P.avoid.weights[i] : 1; });
      for (let e = 0; e < g.nE; e++) if (seenW[e]) { const m = 1 + Math.min(2.5, seenW[e]); C.cost[2 * e] *= m; C.cost[2 * e + 1] *= m; }
    }
    const search = makeSearch(g);
    const T = P.targetM || null;
    const dests = (P.destinations || []).map(d => nearestNode(g, d.lat, d.lon, { good: true }));
    // a loop crosses the doorstep twice (out and home); a one-way run once at each end
    const unavoidable = P._unavoidable = P.maxGrade ? (E === S ? 2 * steepEscape(g, S, P.maxGrade) : steepEscape(g, S, P.maxGrade) + steepEscape(g, E, P.maxGrade)) : 0;
    // with a grade limit, turnaround points should sit in gentle terrain
    let nodeSteep = null;
    if (P.maxGrade) {
      const SM = steepMetres(g, P.maxGrade); nodeSteep = new Float32Array(g.nN);
      for (let e = 0; e < g.nE; e++) { const m = SM.upF[e] + SM.dnF[e]; if (m) { nodeSteep[g.eU[e]] += m; nodeSteep[g.eV[e]] += m; } }
    }
    const cands = [];
    const tryRoute = (nodes, meta) => {
      const p = routeVia(g, search, C, nodes);
      if (!p || !p.length) return null;
      const L = pathLength(g, p);
      const c = { path: p, L, nodes, meta };
      return c;
    };
    const finish = (c) => {
      if (!c) return; c.a = analyze(g, c.path, P); c.score = scoreRoute(c.a, P);
      let rep = 0; for (const ae of c.path) { const e = ae >= 0 ? ae : ~ae; if (seenW[e]) rep += g.eLen[e] * Math.min(1, seenW[e]); }
      c.a.repeatFrac = rep / c.L; c.score += 4 * c.a.repeatFrac;
      cands.push(c);
    };
    const pick = (x, y, rad, bias) => {
      // node near (x, y); terrain bias pulls toward high or low ground
      let ns = nodesNear(g, x, y, rad);
      if (!ns.length) ns = nodesNear(g, x, y, rad * 2.5);
      if (!ns.length) return -1;
      let best = ns[0], bv = -Infinity;
      for (const n of ns) {
        const d = Math.hypot(g.x[n] - x, g.y[n] - y);
        const v = (bias === 'high' ? g.el[n] : bias === 'low' ? -g.el[n] : 0) - d * 0.05 * (bias ? 1 : 20) - (nodeSteep ? nodeSteep[n] * 5 : 0);
        if (v > bv) { bv = v; best = n; }
      }
      return best;
    };
    // hilltops are ringed by steep streets, so with a grade limit 'hilly' means long gradual climbs instead
    const pickRad = P.hill === 'flat' ? 450 : 220; // look wider for low ground when minimising climbing
    const bias = P.hill === 'flat' ? 'low' : (P.hill === 'hilly' || P.hill === 'max') && !P.maxGrade ? 'high' : null;
    const sx = g.x[S], sy = g.y[S], ex = g.x[E], ey = g.y[E];
    const seed = P.seed || 0;

    // order destinations greedily
    let order = dests.slice();
    if (order.length > 1) {
      const rest = order.slice(); order = []; let cx = sx, cy = sy;
      while (rest.length) { let bi = 0, bd = Infinity; rest.forEach((n, i) => { const d = Math.hypot(g.x[n] - cx, g.y[n] - cy); if (d < bd) { bd = d; bi = i; } }); const n = rest.splice(bi, 1)[0]; order.push(n); cx = g.x[n]; cy = g.y[n]; }
    }

    // more directions when loops are hard to fit: grade limits, or Flattest (only some directions lead to flat ground)
    const bearings = P.hill === 'flat' ? 28 : P.maxGrade ? 16 : 10;
    if (order.length) {
      const base = tryRoute([S, ...order, E], { kind: 'direct' });
      if (base) {
        if (!T || base.L >= T * 0.93) finish(base);
        if (T && base.L < T * 1.0) {
          // add a detour point to stretch toward the target distance
          for (let b = 0; b < bearings; b++) {
            const th = (b / bearings + seed * 0.37) * 2 * Math.PI;
            const pos = b % (order.length + 1); // insert position
            const before = pos === 0 ? S : order[pos - 1], after = pos === order.length ? E : order[pos];
            const mx = (g.x[before] + g.x[after]) / 2, my = (g.y[before] + g.y[after]) / 2;
            let r = Math.max(300, (T - base.L) / 2.4);
            let c = null;
            for (let it = 0; it < 5; it++) {
              const v = pick(mx + r * Math.cos(th), my + r * Math.sin(th), pickRad, bias);
              if (v < 0) break;
              const seq = [S, ...order.slice(0, pos), v, ...order.slice(pos), E];
              c = tryRoute(seq, { kind: 'detour', th });
              if (!c) break;
              if (Math.abs(c.L - T) / T < 0.025) break;
              r *= Math.max(0.4, Math.min(2.2, 1 + (T - c.L) / Math.max(c.L - base.L, 200)));
            }
            finish(c);
            progress && progress((b + 1) / bearings);
          }
        }
      }
    } else if (!T) {
      finish(tryRoute([S, E], { kind: 'direct' }));
    } else if (S === E && P.shape === 'out-and-back') {
      for (let b = 0; b < bearings; b++) {
        const th = (b / bearings + seed * 0.37) * 2 * Math.PI; let r = T / 2 / 1.25, c = null;
        for (let it = 0; it < 5; it++) {
          const v = pick(sx + r * Math.cos(th), sy + r * Math.sin(th), pickRad, bias); if (v < 0) break;
          const p1 = search(S, v, C, null); if (!p1) break;
          const p = p1.concat(p1.slice().reverse().map(ae => ~ae));
          c = { path: p, L: pathLength(g, p), nodes: [S, v, S], meta: { kind: 'oab', th } };
          if (Math.abs(c.L - T) / T < 0.025) break;
          r *= T / c.L;
        }
        finish(c); progress && progress((b + 1) / bearings);
      }
    } else {
      // loops (or stretched point-to-point) through two via points
      const direct = S === E ? 0 : Math.hypot(ex - sx, ey - sy) * 1.25;
      if (S !== E && direct >= T * 0.93) finish(tryRoute([S, E], { kind: 'direct' }));
      for (let b = 0; b < bearings; b++) {
        const th = (b / bearings + seed * 0.37) * 2 * Math.PI;
        const spread = 0.55 + 0.25 * ((b * 7 + seed) % 3) / 2; // vary triangle shape
        let r = S === E ? T / 4.1 : Math.max(250, (T - direct) / 3.2), c = null;
        for (let it = 0; it < 5; it++) {
          let ax, ay, bx, by;
          if (S === E) {
            ax = sx + r * Math.cos(th - spread); ay = sy + r * Math.sin(th - spread);
            bx = sx + r * Math.cos(th + spread); by = sy + r * Math.sin(th + spread);
          } else {
            const mx = (sx + ex) / 2, my = (sy + ey) / 2;
            ax = sx + (mx - sx) * 0.5 + r * Math.cos(th); ay = sy + (my - sy) * 0.5 + r * Math.sin(th);
            bx = ex + (mx - ex) * 0.5 + r * Math.cos(th); by = ey + (my - ey) * 0.5 + r * Math.sin(th);
          }
          const A = pick(ax, ay, pickRad, bias), B = pick(bx, by, pickRad, bias);
          if (A < 0 || B < 0) break;
          c = tryRoute([S, A, B, E], { kind: 'loop', th });
          if (!c) break;
          if (Math.abs(c.L - T) / T < 0.025) break;
          r = S === E ? r * Math.max(0.5, Math.min(1.8, T / c.L)) : Math.max(120, r + (T - c.L) * 0.45);
        }
        finish(c); progress && progress((b + 1) / bearings);
      }
    }
    // rank and keep a diverse top set
    // when enough candidates hit the distance, drop the ones that miss it
    if (T) {
      const ok = cands.filter(c => Math.abs(c.a.length - T) / T <= 0.05), near = cands.filter(c => Math.abs(c.a.length - T) / T <= 0.08);
      if (ok.length >= Math.min(3, P.count || 3)) cands.splice(0, cands.length, ...ok);
      else if (near.length) cands.splice(0, cands.length, ...near); // fewer options beats a wrong distance
    }
    cands.sort((a, b) => a.score - b.score);
    const out = [];
    for (const c of cands) {
      // options must differ: at most 45% shared distance, not counting the doorstep
      const set = new Set(c.path.map(ae => ae >= 0 ? ae : ~ae).filter(e => !doorEdge(e)));
      let mine = 0; for (const e of set) mine += g.eLen[e];
      let tooClose = false;
      for (const o of out) {
        let inter = 0, lo = 0; for (const e of new Set(o.path.map(ae => ae >= 0 ? ae : ~ae))) { if (doorEdge(e)) continue; if (set.has(e)) inter += g.eLen[e]; lo += g.eLen[e]; }
        if (inter / Math.max(1, Math.min(lo, mine)) > 0.45) { tooClose = true; break; }
      }
      if (!tooClose) out.push(c);
      if (out.length >= (P.count || 3)) break;
    }
    return { routes: out.map(c => ({ ...c.a, edges: [...new Set(c.path.map(ae => ae >= 0 ? ae : ~ae))], score: c.score, kind: c.meta.kind, unavoidable: Math.min(unavoidable, c.a.overUp + c.a.overDn) })), ms: Date.now() - t0, snapped: { start: S, end: E } };
  }

  return { decode, decodeBase64Gz, geocode, plan, nearestNode, estimateSeconds, gapFactor, normStreet, MI, M_LAT, M_LON };
}
if (typeof module !== 'undefined') module.exports = RouterLib;
