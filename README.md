# SF Morning Runs

A single-page run planner for San Francisco. Describe a run in plain English ("go to a cool hilltop with a 7 mile long route", "long and fast route", "easy flat 30 minutes") and it plans three route options from 339 Elsie St (or any address, intersection, or map point), with grade-colored maps, an elevation profile, climb breakdowns, and grade-adjusted time estimates.

Everything runs in the browser: the SF walkable street network (Overture Maps / OpenStreetMap) and terrain (USGS 3DEP via AWS Terrain Tiles) are packed into the page, and routing is an A* search with terrain-aware costs in a Web Worker. When published as a Claude artifact, requests are interpreted by Claude (`sample` capability), with a local parser as a fallback; GPX export uses the `downloads` capability.

## Layout
- `app/template.html` – UI, map, profile, natural-language parsing
- `app/router.js` – graph decoding, geocoding, route planning and analysis
- `build/` – data pipeline
  - `fetch_overture.py seg|addr` – roads and addresses from Overture (S3)
  - `fetch_dem.py` – terrarium elevation tiles
  - `build_graph.py` – walkable graph with per-vertex elevation
  - `build_places.py` – address index + curated hills/spots
  - `pack.py` – binary blob + terrain image
  - `assemble.py` – writes `dist/sf-morning-runs.html`
  - `test_router.js`, `smoke.js` – Node and headless-browser checks
  - `test_parse.js` – ~50 prompts: parsed numbers, pace/time → miles, and planned mileage vs target
  - `smoke_prompts.js` – types prompts into the real page with a mocked Claude reply
  - `smoke_form.js` – edits each setting directly and checks the routes follow
  - `test_grade.js` – steepness limits: steep distance a route could have avoided, and distance accuracy
  - `test_variety.js` – repeated plans with route memory should keep producing new routes (`old` arg shows the previous behaviour)

## Rebuild
```
cd build
python3 fetch_overture.py seg && python3 fetch_overture.py addr && python3 fetch_dem.py
python3 build_graph.py && python3 build_places.py && python3 pack.py && python3 assemble.py
```
