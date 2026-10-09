"""Assemble the single-file app: template + router + Leaflet CSS + packed data."""
import json, re, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
t = (root/'app/template.html').read_text()
router = (root/'app/router.js').read_text()
parse = (root/'app/parse.js').read_text()
export = (root/'app/export.js').read_text()
css = (root/'build/vendor/package/dist/leaflet.css').read_text()
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
terrain = json.loads((root/'build/data/terrain.json').read_text())
blob = (root/'build/data/blob.b64').read_text().strip()
out = (t.replace('/*LEAFLET_CSS*/', css).replace('/*ROUTER*/', router).replace('/*PARSE*/', parse).replace('/*EXPORT*/', export)
        .replace('%%BLOB%%', blob).replace('%%TERRAIN%%', terrain['png'])
        .replace('%%TERRAIN_BOUNDS%%', json.dumps(terrain['bounds'])))
(root/'dist').mkdir(exist_ok=True)
(root/'dist/sf-morning-runs.html').write_text(out)
print('wrote dist/sf-morning-runs.html', round(len(out)/1e6, 2), 'MB')
