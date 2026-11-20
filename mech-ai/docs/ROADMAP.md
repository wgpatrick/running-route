# Roadmap: owner's priorities (2026-11-19)

## The overarching goal (owner, 2026-11-20)

Recursive hardware self-improvement: a system that loops around making physical parts, testing them and improving them to
create great hardware, and that uses what it learns to improve the loop itself. The 3D printer is both an output and part
of the loop: it is the loop's first fabrication tool, and redesigning the fabrication equipment (and later other tools:
measurement, cutting, machining) is how the loop gets faster and better.

What this means in practice:
- Measure the loop, not just the parts: loop time (design change to measured part), fidelity (prediction vs measurement
  error for each check and the twin), and autonomy (human touches per iteration). Each should improve over time.
- Every real-world result updates the system with provenance: a rule, an allowance, a twin parameter, a supplier figure.
  Keep a ledger of these learnings and of the prediction error before and after.
- Design the fabrication tools for the loop: instrumented (cameras, accelerometer, sensors), easy to modify, and able to
  make their own test pieces, fixtures and upgrade parts.
- Get to a physical loop early: learning compounds only once parts are being made and measured.

## Next milestone: Build 1 (agreed 2026-11-20)

Build 1 means every part can be ordered and the machine assembled from our build package. One merged build-candidate
revision (v11.1 + v12, including the camera and sensor hardware), a single buildability gate (zero errors, zero
placeholders, every purchased part real with maker CAD and live price, stock and lead time, every fabricated part clean
against its shop's rules, assembly plan checked), then freeze, order (long-lead parts first), build, and run the first
closed loops (coupons, flow, pressure advance, resonance) with each result recorded as a learning.

Owner's caution: design work is much faster and cheaper than building, so do not start the build too early. Use the
design phase to remove risk; prefer cheap, targeted physical tests (a few sheet parts, coupons) over committing to the
whole machine before the gate passes.

The owner set three priorities for the system beyond the printer design itself. Each closes a loop between
the design and the real world, so the system keeps learning from evidence rather than from its own models.

## 1. Supplier APIs: real price, stock, datasheets and CAD

Status:
- Working (keys in the `mech-ai-engineering` environment as environment variables): Digi-Key v4 (price, stock,
  datasheets, and supplier 3D CAD links via the media endpoint), Mouser (widest coverage, few datasheet links),
  element14 / Newark / Farnell (price, stock, datasheets). Nexar / Octopart: free tier of about 10 part lookups,
  kept for one-off lookups.
- Requested by email (owner's agent): McMaster (client-certificate API), TraceParts, CADENAS, Misumi, Volition,
  Xometry, SendCutSend, JLCCNC, PCBWay, CADEX (MTK evaluation), OSH Cut.
- No API exists: SendCutSend, OSH Cut, Fabworks, most fastener houses. Their data comes through the owner's
  agent in a browser, at customer pace, after reading each site's terms.

Next: a `mechloop` sourcing module that prices every purchased electrical part from Digi-Key, Mouser and
element14, records stock and datasheet links, pulls supplier STEP files into `vendor_cad/inbox/` where the
API links them, and reports parts with no distributor source.

## 2. Our own DFM checks and quoting for each core process

Processes: 2D laser cutting, sheet-metal bending, CNC machining, FDM printing.

Approach: build the checks and quote models ourselves, and use the suppliers' own output as the answer key.
- Every rule records its supplier and source page (SendCutSend, OSH Cut, Protolabs, Xometry, Fictiv); a part is
  checked against the rules of the shop it is going to.
- A reference set of parts (real printer parts plus deliberately flawed variants) is quoted on the suppliers'
  sites by the owner's agent (batch upload, never order). Prices, lead times and every DFM warning are recorded.
- A scoring test reports agreement with each supplier's warnings and price error, and runs with the other checks.

Order: sheet-metal and laser rules (in progress), sheet-metal quoting, press-brake bend feasibility (tooling and
bend-order collision), FDM (orientation, slicer warnings as findings, cost from the real slicer), CNC last (tool
reach from six directions, setups, corner radii, depth ratios, time and cost). Independent checks where offered:
CADEX MTK (local SDK), Toolpath (CNC API).

## 3. Cameras and sensors: continuous feedback from real prints

Goal: the whole system learns continuously from the printer: live, per layer, per print and per revision.

| Loop | Speed | Runs on |
|---|---|---|
| Live control (flow, pressure advance, speed, Z offset, temperature, within hard limits) | 2-10 s steps | Raspberry Pi |
| Print watch (spaghetti, layer shift, warping; pause or cancel one object) | per frame / per layer | Pi detects, agent decides |
| Part check (coupons, calipers, calibrated photos, scans) | per print | agent |
| Machine and twin (resonance, ringing, measured vs predicted) | per revision | agent |

Phase 1 (proven): overview camera, lighting, toolhead accelerometer, filament motion sensor, measuring tools; Obico
on the Pi; a photo at every layer change; the Pi pushes images and telemetry to cloud storage and fetches
approved commands (outbound only); coupon set generated by the design system.
Phase 2: fixed top-down camera with a calibration target, nozzle camera; each layer compared with the twin's
rendered layer; a labelled nozzle-camera dataset built by deliberate parameter sweeps.
Phase 3: a CAXTON-style model on the Pi making small capped changes; optional eddy or load-cell probe, line laser.

Safety: Klipper's thermal protection is never touched; every command passes local limits (flow 90-110 %,
speed 50-110 %, Z +/-0.1 mm in total, temperature +/-10 degC); resuming after an auto-pause needs the owner;
if the link drops the printer continues in a conservative mode.

Design consequence: from v12 the printer carries the camera mounts, lighting, accelerometer, nozzle-camera
bracket, filament sensor and Pi wiring, checked like every other part.
