// Turns a runner's plain-English request into planner settings.
// The local parser is deterministic and owns the numbers (distance, time, pace);
// Claude's reading is merged in for nuance but never invents stops, endpoints or mileage.
function ParseLib(places) {
  const KM = 1.609344;
  const ALIASES = {
    'bernal': 'Bernal Heights Summit', 'bernal hill': 'Bernal Heights Summit', 'bernal heights': 'Bernal Heights Summit', 'twin peaks': 'Twin Peaks',
    'christmas tree point': 'Twin Peaks', 'coit': 'Coit Tower', 'telegraph hill': 'Coit Tower', 'mt sutro': 'Mount Sutro', 'mount sutro': 'Mount Sutro', 'sutro forest': 'Mount Sutro',
    'mt davidson': 'Mount Davidson', 'davidson': 'Mount Davidson',
    'golden gate park': 'Stow Lake', 'gg park': 'Stow Lake', 'ocean beach': 'Ocean Beach', 'the beach': 'Ocean Beach', 'great highway': 'Ocean Beach', 'embarcadero': 'Ferry Building', 'ferry building': 'Ferry Building',
    'presidio': 'Crissy Field', 'crissy': 'Crissy Field', 'the marina': 'Palace of Fine Arts', 'palace of fine arts': 'Palace of Fine Arts', 'mclaren': 'McLaren Park Summit', 'glen canyon': 'Glen Canyon Park', 'glen park': 'Glen Canyon Park',
    'dolores': 'Dolores Park (top)', 'potrero hill': 'McKinley Square', 'mckinley': 'McKinley Square', 'buena vista': 'Buena Vista Park', 'corona heights': 'Corona Heights',
    'tank hill': 'Tank Hill', 'grand view': 'Grand View Park', 'grandview': 'Grand View Park', 'turtle hill': 'Grand View Park', 'tiled steps': '16th Ave Tiled Steps', 'mosaic steps': '16th Ave Tiled Steps', '16th ave steps': '16th Ave Tiled Steps',
    'holly park': 'Holly Park', 'billy goat': 'Billy Goat Hill', 'kite hill': 'Kite Hill', 'nob hill': 'Huntington Park', 'huntington park': 'Huntington Park', 'russian hill': 'Russian Hill Park', 'alta plaza': 'Alta Plaza',
    'lafayette': 'Lafayette Park', 'lake merced': 'Lake Merced', 'stern grove': 'Stern Grove', 'stow lake': 'Stow Lake', 'panhandle': 'Panhandle', 'precita': 'Precita Park',
    'alamo square': 'Alamo Square', 'painted ladies': 'Alamo Square', 'lone mountain': 'Lone Mountain', 'strawberry hill': 'Strawberry Hill', 'bayview hill': 'Bayview Hill',
    'mission bay': 'Mission Bay', 'oracle park': 'Oracle Park', 'ballpark': 'Oracle Park', 'ball park': 'Oracle Park', 'aquatic park': 'Alcatraz View: Aquatic Park', 'sutro heights': 'Sutro Heights', 'sutro baths': 'Sutro Heights',
    "heron's head": "Heron's Head Park", 'herons head': "Heron's Head Park", 'mount olympus': 'Mount Olympus', 'duboce': 'Duboce Park', 'starr king': 'Starr King Open Space', 'diamond heights': 'Walter Haas Playground',
    'walter haas': 'Walter Haas Playground',
  };
  const WORDS = { a: 1, an: 1, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12, thirteen: 13,
    fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, ninety: 90 };

  // the planner offers 12/10/8/6%; round a stated limit to the nearest of those, preferring the stricter one
  const snapGrade = (x) => [0.06, 0.08, 0.1, 0.12].reduce((b, o) => (Math.abs(o - x) < Math.abs(b - x) - 1e-9 ? o : b), 0.06);
  const paceToSec = (p) => { const m = String(p ?? '').trim().match(/^(\d{1,2})(?::(\d{1,2}))?$/); if (!m) return null; const s = (+m[1]) * 60 + (+(m[2] || 0)); return s >= 180 && s <= 1800 ? s : null; };
  const secToPace = (s) => { s = Math.round(s); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };

  // "forty five" -> "45", "twenty-five" -> "25", "a half" stays for later rules
  function wordsToDigits(t) {
    t = t.replace(/\b(twenty|thirty|forty|fifty)[ -](one|two|three|four|five|six|seven|eight|nine)\b/g, (_, a, b) => String(WORDS[a] + WORDS[b]));
    return t.replace(/\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|ninety)\b/g, (w) => String(WORDS[w]));
  }

  function mentionedPlaces(text) {
    const t = ' ' + text.toLowerCase().replace(/[^a-z0-9' ]+/g, ' ').replace(/\s+/g, ' ') + ' ';
    const out = []; const used = [];
    const keys = Object.keys(ALIASES).concat(places.map(p => p.name.toLowerCase().replace(/ \(.*\)/, '').replace(/[^a-z0-9' ]+/g, ' ').trim()));
    for (const k of [...new Set(keys)].sort((a, b) => b.length - a.length)) {
      const i = t.indexOf(' ' + k + ' ');
      if (i < 0 || used.some(([a, b]) => i + 1 < b && i + 1 + k.length > a)) continue;
      used.push([i + 1, i + 1 + k.length]);
      const name = ALIASES[k] || places.find(p => p.name.toLowerCase().replace(/ \(.*\)/, '').replace(/[^a-z0-9' ]+/g, ' ').trim() === k)?.name;
      if (name && !out.some(o => o.name === name)) out.push({ name, at: i });
    }
    return out.sort((a, b) => a.at - b.at).map(o => o.name);
  }

  function localParse(text) {
    const r = { distanceMi: null, minutes: null, pace: null, hill: null, maxGrade: null, fast: false, trails: false, avoidSteps: false, shape: null, dests: [], hillTop: false, start: null, end: null };
    let t = ' ' + wordsToDigits(text.toLowerCase().replace(/[–—]/g, '-')).replace(/\s+/g, ' ') + ' ';
    let m;
    // --- pace first, then remove it so "12 min pace" is never read as a 12 minute run ---
    const PACE_CUE = String.raw`(?:\s*(?:min(?:ute)?s?|mins?)?\s*(?:\/\s*mi(?:le)?|per mi(?:le)?|pace|min(?:ute)?s? ?\/ ?mi|[- ]?min(?:ute)?s? miles?|[- ]?min(?:ute)? mile pace|miles?\b(?= pace)))`;
    const paceRes = [
      new RegExp(String.raw`\b(\d{1,2}):(\d{2})s?` + PACE_CUE, 'g'),                       // 8:30 pace, 8:30/mi, 8:30 min miles
      new RegExp(String.raw`\b(\d{1,2}(?:\.\d+)?)[- ]?(?:min(?:ute)?s?)\s*(?:\/\s*mi(?:le)?|per mi(?:le)?|pace|miles?|mile pace)`, 'g'), // 12 min pace, 12-minute miles
      /\bpace (?:of |around |about |at )?(\d{1,2})(?::(\d{2}))?\b(?!\s*(?:mi\b|miles?|milers?|k\b|km|min|minutes?|hours?))/g, // pace of 9:30 / pace 9 (not "pace 7 miles")
      /(?:\bat|@) ?(?:an? |about |around )?(\d{1,2}):(\d{2})s?\b(?!\s*(?:am|pm|a\.m|p\.m|hours?|hrs?))/g,     // at 7:15 / @ 7:15 (bare)
    ];
    // "leave at 6:15", "at 6:45 this morning", "6am" are times of day, not paces
    const isClock = (m) => /\b(?:leave|leaving|left|start|starting|head(?:ing)? out|out the door|wake|waking|up|alarm|by|before|after|until|meet|meeting|back by|done by)\s+(?:at\s+|by\s+|around\s+)?$/.test(t.slice(Math.max(0, m.index - 24), m.index + (m[0].startsWith('at') ? 3 : 0)).replace(/at\s*$/, '')) ||
      /^\s*(?:am|pm|a\.m|p\.m|o'?clock|this morning|tomorrow|tonight|sharp)\b/.test(t.slice(m.index + m[0].length));
    for (const re of paceRes) {
      re.lastIndex = 0; m = re.exec(t);
      while (m && isClock(m)) m = re.exec(t);
      if (m) {
        let sec;
        if (m[2] !== undefined && /:/.test(m[0])) sec = (+m[1]) * 60 + (+m[2]);
        else if (m[2] !== undefined) sec = (+m[1]) * 60 + (+m[2]);
        else sec = Math.round(parseFloat(m[1]) * 60);
        if (sec >= 180 && sec <= 1800) { r.pace = secToPace(sec); t = t.slice(0, m.index) + ' ' + t.slice(m.index + m[0].length); break; }
      }
    }
    t = t.replace(/\b(?:leave|leaving|start|starting|head(?:ing)? out|out the door|by|before|after)\s+(?:at\s+|by\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.?|p\.m\.?)?\b/g, ' ')
         .replace(/\b\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.?|p\.m\.?|o'?clock)\b|\bat \d{1,2}:\d{2} (?:this morning|tomorrow|tonight)\b/g, ' ');
    // --- duration ---
    let mins = null;
    if ((m = t.match(/\b(\d{1,2}):(\d{2}):(\d{2})\b/))) { mins = (+m[1]) * 60 + (+m[2]) + (+m[3]) / 60; t = t.replace(m[0], ' '); }
    else if ((m = t.match(/\b(?:for|run|jog|go)\s+(\d):([0-5]\d)\b/))) { mins = (+m[1]) * 60 + (+m[2]); t = t.replace(m[0], ' '); } // "run 1:30" = 90 min
    if (mins == null) {
      let h = 0, found = false;
      if ((m = t.match(/\b(\d+(?:\.\d+)?)\s*(?:-\s*)?(?:h|hr|hrs|hours?)\b(?:\s*(?:and\s+)?(?:a\s+)?(half|quarter|3 quarters))?/))) {
        h = parseFloat(m[1]) + (m[2] === 'half' ? 0.5 : m[2] === 'quarter' ? 0.25 : m[2] ? 0.75 : 0); found = true; t = t.replace(m[0], ' ');
      } else if ((m = t.match(/\b(\d+)h(\d{1,2})\b/))) { h = +m[1] + (+m[2]) / 60; found = true; t = t.replace(m[0], ' '); }
      else if ((m = t.match(/\bhalf (?:an )?hour\b/))) { h = 0.5; found = true; t = t.replace(m[0], ' '); }
      else if ((m = t.match(/\b(?:an?|1) (half|quarter)?\s*hour(?: and an? (half|quarter))?\b/))) {
        h = m[1] === 'half' ? 0.5 : m[1] === 'quarter' ? 0.25 : 1; if (m[2] === 'half') h += 0.5; if (m[2] === 'quarter') h += 0.25; found = true; t = t.replace(m[0], ' ');
      } else if ((m = t.match(/\bhalf (?:an )?hour\b/))) { h = 0.5; found = true; t = t.replace(m[0], ' '); }
      if ((m = t.match(/\b(\d+(?:\.\d+)?)\s*(?:-\s*)?(?:m|min|mins|minutes?)\b(?!\s*(?:\/|per|pace|miles?))/))) { mins = h * 60 + parseFloat(m[1]); t = t.replace(m[0], ' '); }
      else if (found) mins = h * 60;
    }
    if (mins != null && mins > 0) r.minutes = Math.round(mins);
    // --- distance ---
    if ((m = t.match(/\b(\d+(?:\.\d+)?)\s*(?:-\s*)?(?:k|km|kms|kilometers?|kilometres?)\b/))) r.distanceMi = +(parseFloat(m[1]) / KM).toFixed(2);
    else if ((m = t.match(/\b(\d+(?:\.\d+)?)\s*(?:-\s*)?(?:mi|miles?|mile|milers?)\b/))) r.distanceMi = parseFloat(m[1]);
    else if (/\bhalf[- ]marathon\b(?!\s*(?:pace|effort|race pace))/.test(t)) r.distanceMi = 13.1;
    else if (/\bmarathon\b(?!\s*(?:pace|effort|race pace))/.test(t) && !/\bhalf[- ]marathon\b/.test(t)) r.distanceMi = 26.2;
    else if ((m = t.match(/\b(\d+(?:\.\d+)?) and a half (?:mi|miles?)\b/))) r.distanceMi = parseFloat(m[1]) + 0.5;
    else if (/\b(?:a|1) mile\b/.test(t)) r.distanceMi = 1;
    // bare number after a run word: "easy 6", "run 4" (miles), when nothing else gave a length
    if (r.distanceMi == null && r.minutes == null && (m = t.match(/\b(?:easy|run|jog|quick|short|long|do|go|steady|tempo|recovery)\s+(?:an?\s+)?(\d{1,2}(?:\.\d)?)\b(?!\s*(?:%|:|percent|min|minutes?|am|pm))/)) && +m[1] >= 1 && +m[1] <= 30) r.distanceMi = parseFloat(m[1]);
    // --- steepness limit (before distance/time so "8%" isn't misread) ---
    if ((m = t.match(/\b(?:under|below|less than|max(?:imum)?|no more than|nothing (?:over|above|steeper than|more than)|not (?:over|above|steeper than)|at most|up to|limit(?: of)?|cap(?: of)?)\s*(?:of\s*|a\s*)?(\d{1,2}(?:\.\d)?)\s*(?:%|percent|pc)(?:\s*(?:grade|slope|incline|gradient))?/)) ||
        (m = t.match(/\b(\d{1,2}(?:\.\d)?)\s*(?:%|percent)\s*(?:grade|slope|incline|gradient)?\s*(?:max(?:imum)?|or less|limit|cap|tops)\b/)) ||
        (m = t.match(/\b(?:max(?:imum)?|steepest)\s*(?:grade|slope|incline|gradient)\s*(?:of\s*)?(\d{1,2}(?:\.\d)?)\s*(?:%|percent)?/))) {
      r.maxGrade = snapGrade(parseFloat(m[1]) / 100); t = t.replace(m[0], ' ');
    } else if (/\b(no|avoid(?:ing)?|without|skip|nothing|not too|minimal|minimi[sz]e)\s+(?:the\s+|any\s+|really\s+|super\s+|too\s+)?(steep|steepest|steep hills|big hills|steep climbs|steep streets|crazy hills)\b/.test(t) || /\bgentle (?:grades?|slopes?|hills)\b/.test(t)) r.maxGrade = 0.08;
    // --- character of the run ---
    const NOT_HILLY = /\b(no hills|avoid (?:the )?hills|not (?:too |very |that |super )?hilly|without hills|skip (?:the )?hills|minimal (?:climbing|elevation|hills|vert)|low elevation|little climbing|less climbing|no climbing|not much climbing|minimi[sz]e (?:climbing|elevation|incline|hills))\b/;
    if (/\b(flat|flatish|flattest|recovery|easy|gentle|level)\b/.test(t) || NOT_HILLY.test(t)) r.hill = 'flat';
    if (/\b(rolling|some hills|a few hills|moderate|a little climbing|bit of climbing)\b/.test(t)) r.hill = 'rolling';
    if (!NOT_HILLY.test(t) && !(r.maxGrade && !/\b(hilly|climb|climbing|vert)\b/.test(t)) && /\b(hilly|hills|climb|climbing|climbs|vert|steep|elevation|uphill|hill (?:workout|repeats|run|training|session))\b/.test(t) && !/\b(a few hills|some hills|a little climbing|bit of climbing)\b/.test(t)) r.hill = 'hilly';
    if (/\b(max(imum)? (climb|climbing|hills|vert)|brutal|all the hills|as much climbing|hill repeats|lots of climbing|most climbing|as hilly as)\b/.test(t)) r.hill = 'max';
    if (/\b(fast|tempo|speed|speedy|race pace|pr|threshold|workout|intervals|quick pace)\b/.test(t)) { r.fast = true; if (!r.hill) r.hill = 'flat'; }
    if (/\b(trails?|dirt|nature|woods|forest|unpaved|off[- ]road|through the parks?|in the park)\b/.test(t)) r.trails = true;
    if (/\b(no stairs|avoid stairs|no steps|avoid steps|without stairs|skip the stairs)\b/.test(t)) r.avoidSteps = true;
    if (/\b(out[- ]and[- ]back|out & back|there and back|and back|turn around)\b/.test(t)) r.shape = 'out-and-back';
    if (/\b(hill ?tops?|summit|summits|peaks?|views?|viewpoint|overlook|lookout|vista|top of a hill|up a hill)\b/.test(t)) r.hillTop = true;
    // --- places, start, end ---
    if ((m = text.match(/\b(?:end(?:ing)?|finish(?:ing)?|stop(?:ping)?)\s+(?:up\s+)?(?:at|on|near|by)\s+(?:the\s+)?([^,.;]+)/i)))
      r.end = m[1].replace(/\s+(?:with|via|through|then|after|for)\b.*$/i, '').replace(/\s+and\s+(?:then|run|go|come|do|back|get|grab|\d).*$/i, '').replace(/\s+\d+(?:\.\d+)?\s*(?:mi|miles?|k|km|min|minutes?)\b.*$/i, '').trim();
    if ((m = text.match(/\b(?:start(?:ing)?|begin(?:ning)?)\s+(?:at|on|near|from)\s+(?:the\s+)?([^,.;]+?)(?=\s+(?:to|then|ending|end|finish|run|for|with|going)\b|\s+\d+(?:\.\d+)?\s*(?:mi|miles?|k|km|min|minutes?)\b|[,.;]|$)/i)) ||
        (m = text.match(/\bfrom\s+(?:the\s+)?(\d+\s+[a-z0-9 ]+?(?:st|street|ave|avenue|blvd|way|rd|road|dr|drive|pl|place|ter|terrace)\b|[a-z0-9 ]+?\s*(?:&|and)\s*[a-z0-9 ]+?(?=\s+(?:to|then|ending|end|finish|run|jog|for|go|going|back)\b|\s+\d|[,.;]|$))/i))) r.start = m[1].trim();
    if (!r.start && (m = text.match(/\bfrom\s+(?:the\s+)?([^,.;]+)/i))) { // "from <known place>"
      const pl = mentionedPlaces(m[1].split(/\s+(?:to|then|and|ending|end|finish|run|for|with|via|through)\b/i)[0]);
      if (pl.length) r.start = pl[0];
    }
    const HOMEW = /^(home|my (?:house|place|home|apartment)|the house)$/i;
    const homeFinish = /\b(?:run|running|jog|jogging|head|heading|go|going|come|coming|get|back)\s+(?:back\s+)?home\b|\b(?:end|ending|finish|finishing)\s+(?:up\s+)?(?:at\s+)?home\b/i.test(text);
    if (r.start && homeFinish && !r.end) r.end = 'home';
    if (r.start && HOMEW.test(r.start)) r.start = null;
    if (r.end && HOMEW.test(r.end)) r.end = r.start ? 'home' : null; // finishing at home only matters when starting elsewhere
    const endPlaces = r.end ? mentionedPlaces(r.end) : [], startPlaces = r.start ? mentionedPlaces(r.start) : [];
    r.dests = mentionedPlaces(text).filter(n => !endPlaces.includes(n) && !startPlaces.includes(n));
    if (r.dests.length) r.hillTop = false;
    if (r.distanceMi == null && r.minutes == null) {
      if (/\b(long|longer|longish)\b/.test(t)) r.distanceMi = 9;
      else if (/\b(short|quick|shakeout|shake out)\b/.test(t)) r.distanceMi = 3;
    }
    return r;
  }

  // Merge Claude's JSON reading with the local parse. Claude can refine terrain and flags;
  // numbers come from the text whenever the text states them, and places must be named in the text.
  function mergeClaude(text, local, c) {
    if (!c || typeof c !== 'object') return local;
    const num = (v) => (typeof v === 'number' && isFinite(v) && v > 0 ? v : null);
    const r = { ...local, summary: typeof c.summary === 'string' ? c.summary.slice(0, 120) : null };
    // numbers: trust the text first
    if (local.minutes == null && local.distanceMi == null) {
      const cm = num(c.duration_minutes), cd = num(c.distance_miles);
      if (cm) r.minutes = Math.round(cm);
      else if (cd) r.distanceMi = Math.round(cd * 100) / 100;
    }
    if (!local.pace && paceToSec(c.pace)) r.pace = secToPace(paceToSec(c.pace));
    // flags
    if (['flat', 'rolling', 'hilly', 'max'].includes(c.terrain)) r.hill = c.terrain;
    if (!local.maxGrade && num(c.max_grade_percent) && /\b(steep|grade|incline|slope|gradient|%|percent|gentle)\b/i.test(text)) r.maxGrade = snapGrade(c.max_grade_percent / 100);
    for (const [k, ck] of [['fast', 'fast'], ['trails', 'trails'], ['avoidSteps', 'avoid_stairs']]) if (typeof c[ck] === 'boolean') r[k] = c[ck] || local[k];
    if (c.shape === 'out-and-back' || c.shape === 'loop') r.shape = local.shape || c.shape;
    // places: only ones the runner actually named
    const named = mentionedPlaces(text);
    const cd = Array.isArray(c.destinations) ? c.destinations.filter(n => named.includes(n)) : [];
    const endPl = r.end ? mentionedPlaces(r.end) : [];
    r.dests = (cd.length ? cd.concat(local.dests.filter(n => !cd.includes(n))) : local.dests).filter(n => !endPl.includes(n));
    const hillWords = /\b(hill ?tops?|summit|peaks?|views?|viewpoint|overlook|lookout|vista|hill)\b/i.test(text);
    r.hillTop = !r.dests.length && (local.hillTop || (c.hilltop === true && hillWords));
    // endpoints: only when the runner signalled one
    if (!local.end && typeof c.end === 'string' && c.end.trim() && /\b(end|ending|finish|finishing|stop|stopping|to)\b/i.test(text) && (!/^home$/i.test(c.end.trim()) || r.start)) {
      const e = c.end.trim();
      if (text.toLowerCase().includes(e.toLowerCase().split(/[ ,]/)[0])) r.end = e;
    }
    if (!local.start && typeof c.start === 'string' && c.start.trim() && /\b(start|starting|from|begin)\b/i.test(text) && !/^home$/i.test(c.start.trim())) {
      const s = c.start.trim();
      if (text.toLowerCase().includes(s.toLowerCase().split(/[ ,]/)[0])) r.start = s;
    }
    return r;
  }

  // Decide distance vs time mode and the target mileage.
  function resolve(r, currentPace) {
    let pace = r.pace && paceToSec(r.pace) ? r.pace : currentPace;
    let mode, amount;
    if (r.minutes && r.distanceMi) { // both given: plan the distance, derive the pace
      mode = 'distance'; amount = r.distanceMi;
      if (!r.pace) { const s = r.minutes * 60 / r.distanceMi; if (s >= 180 && s <= 1800) pace = secToPace(s); }
    } else if (r.minutes) { mode = 'time'; amount = r.minutes; }
    else if (r.distanceMi) { mode = 'distance'; amount = Math.round(r.distanceMi * 100) / 100; }
    else if (r.dests.length || r.end) { mode = 'distance'; amount = null; } // no length asked: just go there
    else { mode = 'distance'; amount = 5; }
    const miles = amount == null ? null : mode === 'distance' ? amount : amount * 60 / paceToSec(pace);
    return { mode, amount, pace, miles };
  }

  return { localParse, mergeClaude, resolve, mentionedPlaces, paceToSec, secToPace, aliases: ALIASES };
}
if (typeof module !== 'undefined') module.exports = ParseLib;
