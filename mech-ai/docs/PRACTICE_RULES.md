# Practical engineering rules: catalogue, mapping to mechloop, first audit of printer_v8, verifier proposal

Research and specification, 2026-11-15. Nothing under `mechloop/`, `tests/` or `designs/` was changed. Nothing here has
been built or tested on hardware.

The owner looked at `designs/printer_v8.py` (0 errors in all 12 verifiers) and saw at once what no check had: no
washers under screw heads, unbroken edges on the metal parts. This document collects that kind of knowledge, the habits
an experienced designer applies without thinking, as checkable rules; says which of them mechloop already checks; runs a
first read-only audit of v8 against the rest; and proposes a thirteenth verifier, `practice`.

Files:

| File | What |
|---|---|
| `research_notes/practice/rules.yaml` | the 135 rules, machine-readable (`rules.json` is the same data for a Python without PyYAML: the project venv has none) |
| `research_notes/practice/sources.yaml` | every source with its URL, access date, evidence level and the verbatim text relied on |
| `tools/practice_audit.py` | read-only audit script (37 s on v8): `.venv/bin/python tools/practice_audit.py designs/printer_v8.py` |
| `research_notes/practice/v8_audit.json` | its output: the full fastener schedule (172 screws), belts, bearings, edges, T-nuts |

## 1. How to read the evidence

Each rule states the level of the evidence behind its **number**:

- **fetched**: the document was downloaded today and the quoted sentence read (NASA RP-1228, Bolt Science, SDP/SI,
  Hubs CNC and FDM guides, Protolabs sheet guide, SendCutSend bending page, CNC Kitchen, ISO 7089 table).
- **repo**: a document or vendor record already in this repository (Gates Light Power and Precision manual in
  `vendor_docs/`, Hiwin MG tables in `mechloop/parts/vendor/hiwin_mgn12.json`, ISO 4762 table).
- **snippet**: seen only through a web-search summary of the named page. The wording is not verified against the page.
- **recalled**: from memory. 75 of the 135 rules rest on a recalled number. They are standard practice, but none of
  them is presented as sourced, and each should be confirmed against a document before it becomes an error-level check.

Two thresholds used by the audit are recalled and matter to its findings: the class 8.8 tightening torques used to
estimate preload (M3 1.3, M4 2.9, M5 5.7 N.m) and the sustained bearing limit taken for printed plastic (0.3 x yield).

## 2. Rule catalogue

135 rules. By evidence behind the number: recalled 75, fetched 35, repo 13, snippet 12. By mechloop status: not 58, partly 44, checked 23, human 10.

| Category | Rules | fetched / repo | snippet | recalled | already checked | partly | not checked | human |
|---|---|---|---|---|---|---|---|---|
| threaded fasteners (FST) | 37 | 16 | 3 | 18 | 4 | 12 | 19 | 2 |
| locating and constraint (LOC) | 11 | 2 | 2 | 7 | 3 | 5 | 2 | 1 |
| bearings and shafts (BRG) | 10 | 1 | 2 | 7 | 1 | 3 | 6 | 0 |
| belts (BLT) | 12 | 11 | 0 | 1 | 2 | 3 | 7 | 0 |
| lead screws (LSC) | 5 | 0 | 0 | 5 | 0 | 0 | 4 | 1 |
| linear guides (LIN) | 7 | 1 | 3 | 3 | 1 | 2 | 3 | 1 |
| structure (STR) | 5 | 1 | 0 | 4 | 0 | 3 | 1 | 1 |
| sheet metal (SHT) | 8 | 4 | 0 | 4 | 2 | 3 | 3 | 0 |
| machining (MCH) | 6 | 5 | 0 | 1 | 4 | 1 | 1 | 0 |
| 3D-printed parts (PRT) | 10 | 5 | 1 | 4 | 3 | 3 | 3 | 1 |
| assembly and service (ASM) | 10 | 0 | 0 | 10 | 2 | 3 | 4 | 1 |
| wiring (ELE) | 4 | 0 | 1 | 3 | 1 | 3 | 0 | 0 |
| safety and ergonomics (SAF) | 6 | 0 | 0 | 6 | 0 | 1 | 3 | 2 |
| documentation (DOC) | 4 | 2 | 0 | 2 | 0 | 2 | 2 | 0 |
| **all** | **135** | 48 | 12 | 75 | 23 | 44 | 58 | 10 |


### threaded fasteners (FST)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| FST-001 | **Declare the property class of every screw and nut; do not design to 12.9 strength when commodity 8.8 / A2-70 will be bought.** each fastener SKU carries a class (8.8, 10.9, 12.9, A2-70); ratings use that class's proof load | all screws. warning: catalogue proof loads are class 12.9 while the SKU names no class | RECALLED (recalled, high) | **not checked** | catalogue field; compare required preload with the class; needs: class on shcs()/add_screw; false alarms L; effort S |
| FST-002 | **Size the screw to the joint: preload must exceed the working load with margin; prefer a longer clamp length.** 0.75 x proof load x n >= 2 x separating load; clamped length >= 3 d where vibration matters (longer bolts keep preload after embedding) | loaded joints. info: few printer joints are strength-limited | RECALLED, BOSSARD (recalled, med) | **not checked**: AGENT.md: 'Bolt preload and contact' not checked | joint force from FEA reactions / load cases against n x preload; needs: loads per joint; false alarms M; effort L |
| FST-010 | **Minimum thread engagement by tapped material.** steel >= 1.0 d; aluminium >= 2.0 d (Nord-Lock; Tameson 2.0-2.5 d; mechloop uses 1.5 d); brass / cast iron 1.5-2.0 d; plastic >= 2 d or use an insert; a standard nut = full strength *SOURCES DISAGREE on aluminium: 1.5 d (mechloop, common shop rule) vs 2 d (Nord-Lock) vs 2-2.5 d (Tameson)* | screws into tapped holes; T-nuts and catalogue tapped holes exempt. error: stripped threads | NORDLOCK, TAMESON, HUBSCNC (snippet, high) | **already checked**: interference: thread_engagement, thread_bottoms_out (1 d steel, 1.5 d aluminium, 2 d plastic) | already; consider 2 d for aluminium and 1.5 d for brass; false alarms L; effort S |
| FST-011 | **Do not thread deeper than the thread can use.** engagement <= 3 d | tapped holes. warning: cost, broken taps | HUBSCNC (fetched, high) | **already checked**: manufacture: cnc.thread_depth_ratio |  |
| FST-012 | **Blind tapped holes need run-out below the thread; the screw must not bottom.** unthreaded depth >= 1.5 d below the last full thread (taps under M6); screw tip >= 1 pitch short of the bottom | blind tapped holes. error if the screw bottoms (no clamp), warning for run-out | HUBSCNC (fetched, high) | **already checked**: manufacture: cnc.blind_tap_runout_d_ratio; interference: thread_bottoms_out (catalogue holes) |  |
| FST-013 | **Use a threaded insert or a nut where a soft material is assembled repeatedly.** plastic or soft aluminium + a screw that is removed in service (wear part, cover) => insert or through-bolt with nut | threads in plastic, cast plate, 5052. warning: thread wears out | RP1228, CNCK (fetched, high) | partly: manufacture: fdm.thread_wall_d_ratio (insert guidance text) | threads_into plastic and screw on a declared service item; needs: service list (ASM-040); false alarms L; effort S |
| FST-020 | **Clearance holes to ISO 273; choose the class deliberately.** fine / medium / coarse: M2.5 2.7/2.9/3.1, M3 3.2/3.4/3.6, M4 4.3/4.5/4.8, M5 5.3/5.5/5.8, M6 6.4/6.6/7.0, M8 8.4/9.0/10.0; larger than coarse needs a washer (FST-031); patterns of 4+ screws or printed parts: medium or coarse | clearance holes in made parts. info (class), warning (under fine, or over coarse without a washer) | ISO273, RECALLED (recalled, high) | partly: tolerance: pattern start (p_all_start); parts.clearance_hole() gives one 'close' value, unverified | measure each hole around each screw (tools/practice_audit.py does); false alarms L; effort S |
| FST-030 | **Keep the pressure under the head and the nut below what the clamped material can carry.** preload / bearing area <= limiting surface pressure (use yield of the clamped part if no figure); bearing area = pi/4 (dw^2 - dh^2) *limit values per material are recalled / assumed* | all clamped parts. warning: embedding and preload loss | PLASTCREEP, BOSSARD (snippet, med) | **not checked** | preload from class torque, area from head and measured hole; needs: torque or class; false alarms M; effort M |
| FST-031 | **Plain washer under any head or nut that sits on a slot, an oversize hole, a soft or painted surface.** slot or hole > ISO 273 coarse, or head face supported < 80 % => ISO 7089 washer (M3 3.2x7x0.5, M4 4.3x9x0.8, M5 5.3x10x1.0); large slots: ISO 7093 wide series | slots, oversize holes, printed and thin parts. warning: head digs in, adjustment creeps, joint loosens | ISO7089, RECALLED (recalled, high) | **not checked** | supported fraction of the head annulus on the first clamped part; needs: washer catalogue part; false alarms L; effort S |
| FST-032 | **Washer under the element that is turned on aluminium (anodised or bare) and on coated parts.** nut or head rotated against aluminium / paint => washer, to keep friction repeatable and the coating intact | aluminium, anodised, painted. info | RECALLED (recalled, med) | **not checked** | material of the bearing part + which end is turned (the one with tool access); false alarms M; effort S |
| FST-033 | **Countersinks only in sheet thick enough to keep a cylindrical land.** sheet >= 3.18 mm for a countersink (SendCutSend); head height <= 60 % of t (recalled) | sheet parts. warning | SCS (repo, med) | **already checked**: manufacture: sheet.countersink_min_thickness_mm |  |
| FST-034 | **Leave enough floor under a counterbored head.** floor under the head >= 0.6 d in aluminium (recalled); check FST-030 on the floor | counterbores. warning | RECALLED (recalled, low) | partly: manufacture: cnc floor / wall minimums (0.5-0.8 mm only) | thickness of the first clamped interval when the head is recessed; false alarms M; effort S |
| FST-040 | **State a tightening torque for every structural joint; derive it from class, friction and the weakest clamped material.** reference: 90 % of yield at mu 0.14 (Bossard F.047 basis); class 8.8 about M3 1.3, M4 2.9, M5 5.7 N.m (recalled); reduce to the FST-030 limit on soft parts | all screws. info: documentation | BOSSARD, RECALLED (recalled, med) | **not checked** | generate a torque table per screw group into BUILD.md; false alarms L; effort M |
| FST-041 | **Do not design a joint that only works at an exact preload.** hand torque scatter +/-35 % (feel), +/-25 % (torque wrench): a joint must work between 0.65 and 1.35 of nominal preload | friction joints. info | RP1228 (fetched, high) | human review | could bracket friction-joint checks (STR-014) with 0.65x preload; effort M; review checklist |
| FST-050 | **Edge distance and pitch of fastener holes.** hole centre to edge: nominal 2 d, minimum 1.5 d; pitch nominal 4 d | metal parts; plastics want more (>= 2 d, recalled). warning: tear-out, bulged edge | RP1228 (fetched, high) | partly: manufacture: sheet.hole_to_edge_t_ratio (1 t of web: a cutting rule, not a strength rule), fdm.thread_wall_d_ratio | distance from each screw axis to the nearest boundary of each clamped part; false alarms M; effort S |
| FST-051 | **A joint needs two fasteners, or one fastener plus a feature that stops rotation.** parts joined by one screw must also share a pin, key, shoulder, rib-in-slot or a second screw | all joints except pivots / axles. warning: the part swings on its screw under vibration | RECALLED, BOLTSCI (recalled, high) | **not checked** | screws per part pair; then look for a second contact that blocks rotation about the screw axis (or a declared join); needs: 'axle' / 'keyed' join kinds exist; false alarms M; effort M |
| FST-052 | **Do not carry a sustained or alternating shear load on screw friction through clearance holes or slots when a shoulder, pin or hook can carry it.** service load across a slotted / clearance joint <= mu (0.15) x preload x 0.65 / 2; otherwise add a positive stop (jack screw, pin) | belt tension anchors, motor mounts on slots, sliding mounts. warning: slip is what loosens screws | BOLTSCI, RP1228 (fetched, med) | **not checked** | belt tension and declared loads against friction capacity of the screws in slots; credit a jack screw that touches the part; needs: load per sliding joint; false alarms M; effort M |
| FST-060 | **Nuts and tapped parts must sit on the threaded part of a partially threaded screw; the plain shank must be shorter than the grip.** ISO 4762 thread length b = 2 d + 12 (M3 18, M4 20, M5 22, M6 24 mm); screws up to about M3x20, M4x25, M5x25, M6x30 are threaded to the head; every nut / tapped interval must start >= (L - b) below the head | long cap screws, studs made from screws. error: cannot be assembled as drawn | ISO4762, RECALLED (repo, high) | **not checked** | thread zone per screw against each threaded target's interval along the axis; needs: b per size in the catalogue (already in vendor_docs CSV); false alarms L; effort S |
| FST-061 | **Use stocked lengths and sizes.** length in the preferred series (4 5 6 8 10 12 16 20 25 30 35 40 45 50 60 ...) and inside the product standard's range for the diameter (ISO 4762: M3 5-30, M5 8-50); otherwise confirm a supplier | all screws. warning: lead time, substitution | ISO4762 (repo, med) | partly: interference STANDARD_LENGTHS_MM (used for bottoming only); ratings BOM | table lookup; false alarms L; effort S |
| FST-062 | **Thread should show past a nut, but not far.** protrusion >= 1 pitch (2 pitches in aerospace practice, recalled) and <= about 3 d unless it is an adjuster | screw + nut joints. info / warning (flush or short: nut not fully engaged) | RECALLED (recalled, med) | partly: interference: nut counted full strength once the screw passes through | tip position against the nut's far face; false alarms L; effort S |
| FST-063 | **Threads out of the shear plane.** in a joint loaded in shear the plain shank, not the thread, crosses the interface | shear joints with loads near capacity. info | RP1228 (fetched, high) | human review | needs FST-060 data plus a load; low value for a printer; effort M; review checklist |
| FST-070 | **Every fastener on a vibrating or moving assembly has a declared locking provision.** one of: prevailing-torque nut (nyloc), thread adhesive (medium strength, removable), serrated-flange screw / nut, or a joint shown not to slip (FST-052); plain nut + plain screw alone is not a provision | screws on moving bodies, motors, pulleys, bed, anything that sets an adjustment. warning: a printer vibrates for thousands of hours | BOLTSCI, BOLTSCI, RP1228 (fetched, high) | **not checked** | per screw: body is moving or a motor is in the joint, and no locking attribute; needs: add_screw(..., locking='nyloc'\|'adhesive'\|'serrated'\|None) and nyloc / serrated catalogue parts; false alarms M; effort S |
| FST-071 | **Do not specify split (helical spring) lock washers as a locking device.** no split lock washers in the BOM | all. warning | RP1228, BOLTSCI (fetched, high) | **not checked** | BOM scan; false alarms L; effort S |
| FST-072 | **Nylon-insert nuts: temperature and reuse limits.** nylon locking element <= about 120 degC (250 degF); replace after a few reassemblies; near the hotend or under the bed use all-metal locknuts or adhesive rated for the temperature | locknuts near heat (bed 80-100 degC, hotend). warning | RP1228 (fetched, high) | **not checked** | distance to el.hot_parts and the thermal estimate; needs: locking attribute (FST-070); false alarms L; effort M |
| FST-073 | **Thread adhesives (anaerobic) attack some plastics; keep them off ABS, PC, PETG parts.** adhesive locking only where the screw touches metal alone; for screws through plastic use nylocs or serrated flanges | screws through printed parts. info | RECALLED (recalled, med) | **not checked** | locking='adhesive' and a plastic in the stack; needs: locking attribute; false alarms L; effort S |
| FST-074 | **Tooth / star washers scratch the seat: use them for earth bonding, not as a general lock on finished or highly stressed parts.** star washers only at protective-earth points | all. info | RP1228 (fetched, high) | partly: electrical: earth_point product text (ring terminals and star washer) | BOM scan; false alarms L; effort S |
| FST-080 | **Standardise fasteners and tools.** target <= 2 thread sizes and <= 3 lengths per size on the main assembly; one drive type; count distinct SKUs and tools and report | whole machine. info: build time and mistakes | RECALLED (recalled, med) | partly: assemble / score: fastener_types, tool_changes (reported, no threshold) | count; suggest merges (a length only used <= 4 times with a neighbour that fits); false alarms L; effort S |
| FST-081 | **Avoid look-alike fasteners that are not interchangeable in the same area.** two lengths of one size differing by <= 2 mm where the shorter one is needed to avoid bottoming (e.g. M3x6 next to M3x8 into 3.5 mm-deep block threads) => warn, key or segregate | catalogue tapped holes with a maximum depth. warning: the wrong screw jams a guide block or cracks a motor end bell | RECALLED (recalled, med) | **not checked** | per sub-assembly: would the next longer SKU in the BOM bottom out here?; false alarms L; effort S |
| FST-090 | **Screws driven straight into printed plastic are for one-time, low-load joints.** no machine screw threaded directly into a printed part where the joint is structural or re-opened; use insert, captive nut or through-bolt | printed parts. warning | CNCK, CNCK (fetched, high) | partly: interference thread_engagement (2 d in plastic); manufacture fdm.thread_wall_d_ratio | threads_into a plastic part; false alarms L; effort S |
| FST-091 | **Heat-set inserts: hole, depth and wall.** straight (not tapered) hole to the insert maker's diameter (M3 brass insert: 4.0 mm, test-print 4.0-4.4); blind hole about 1 mm deeper than the insert; wall around the hole >= 0.5 x insert OD (>= 1.6-2.0 mm for M2-M3); no chamfer needed | inserts in printed parts. warning | CNCK, INSERTS (snippet, med) | **not checked** | insert catalogue part with hole / wall data; measure the boss; needs: heat_set_insert() part; false alarms L; effort M |
| FST-092 | **Put the insert or captive nut on the side where the load pulls it INTO the part.** screw tension must seat the insert / nut against plastic, not draw it out of its hole | inserts. warning: pull-out | RECALLED (recalled, high) | **not checked** | insert on the far side of the clamped stack from the screw head = good; same side = pull-out; needs: insert part; false alarms L; effort S |
| FST-093 | **Captive nut pockets: closed against rotation, open for insertion, with plastic behind the nut.** pocket across flats = nut AF + 0.2 to 0.4 mm; >= 2 mm (or 0.6 d) of plastic between nut face and the clamped interface; nut insertable in the assembled state or retained | printed parts with nut pockets. info | RECALLED (recalled, med) | partly: interference (nut overlap), assemblability (nut has a path in) | measure the pocket around each nut inside a printed part; false alarms M; effort M |
| FST-100 | **Say which T-nut: slide-in nuts must be in the slot before the slot end is closed; drop-in / roll-in nuts for anything added later.** each T-nut SKU names its type; a slide-in nut in a slot whose both ends are blocked at that assembly step is an error | T-slot extrusions. error for trapped slide-in nuts, else info | RECALLED (recalled, high) | **not checked**: T-nuts are BOM lines, not geometry (AGENT.md) | slot ends blocked at the step where the screw is fitted (assembly order exists); needs: T-nut type + position; false alarms M; effort M |
| FST-101 | **A part on T-nuts wants two of them (or a key in the slot); a single T-nut pivots and slides.** parts held to an extrusion by one T-nut screw need a second constraint; loads along the slot are carried by friction only (FST-052) | T-slot joints. warning | RECALLED (recalled, high) | **not checked** | T-nut screws per part; false alarms L; effort S |
| FST-102 | **Tapped extrusion ends: tap the core hole to depth, deburr, and back the joint with a bracket where it carries moment.** end tap M5 in the 2020 core hole, engagement >= 2 d in 6063; a blind butt joint on one screw also needs an anti-rotation feature (bracket, plate) | extrusion butt joints. info | RECALLED (recalled, med) | partly: interference thread_engagement; fea AssemblyCase lower bound | FST-051 on extrusion ends; false alarms L; effort S |
| FST-110 | **Mind galvanic pairs where moisture can stand.** indoors dry: stainless or zinc-plated steel in aluminium is accepted; avoid bare carbon steel sheet against aluminium without a finish; give laser-cut mild steel a finish (paint, zinc, oil) | mixed-metal joints. info | RP1228, SCS (fetched, med) | **not checked** | material pairs in contact + declared finish; needs: finish attribute; false alarms M; effort S |
| FST-111 | **An earth bond through anodised or painted metal must break the coating.** serrated washer or scraped seat at every protective-earth joint; anodised extrusions are not bonded to each other by their brackets unless shown | PE joints. error if a PE path relies on anodised contact | RECALLED, IEC60204 (recalled, high) | partly: electrical: earth_point; builder_work text | PE continuity graph over metal parts with joint conductivity flags; needs: finish per part; false alarms M; effort L |

### locating and constraint (LOC)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| LOC-001 | **Exact constraint: count what holds each body; make every redundant constraint compliant, floating or adjusted.** per moving body: constraints from guides, screws, nuts = 6 - DOF; each extra one needs a declared float / flexure / adjustment | axes. warning: binding, wear | SLOCUM, RECALLED (recalled, high) | partly: fea.bed_support constraint / z_over_constrained; tolerance two-rail and screw-to-rail checks | generalise the bed-support constraint count to X and Y; false alarms M; effort L |
| LOC-002 | **Two parallel rails: one is the master against a reference edge, the other is set parallel to it at assembly and then locked.** allowable non-parallelism MGN12: 9 um (ZF / Z0), 5 um (Z1): only reachable by setting the slave rail with the carriage as gauge | two-rail axes. warning | HIWIN, HIWIN_SNIP (repo, high) | **already checked**: tolerance: two rails parallel; Adjustment rail_align |  |
| LOC-003 | **A lead screw must not also be a guide: float the nut or the far end.** nut radial float >= 99.7 % misalignment of screw to rails; do not fix both screw ends rigidly AND the nut | screw-driven axes. warning | RECALLED (recalled, high) | **already checked**: tolerance lead_screws; Adjustment float |  |
| LOC-004 | **Screws clamp, they do not locate: use dowels, shoulders, ribs-in-slots or a tight pattern where position matters.** a position requirement tighter than the hole clearance (M3 medium: +/-0.2 mm) across a screwed joint needs a locating feature or an adjustment | joints in a tolerance chain. info | RECALLED (recalled, high) | partly: tolerance: joint play of screws is simulated; adjustments credited | list joints whose play dominates a failed stack-up and that have no locating feature; false alarms M; effort M |
| LOC-005 | **Two-pin location: one round hole and one slot aimed at it.** a part located by two pins / tight screws: second feature is a slot along the line of centres, never two tight round holes more than a few d apart | pinned parts. info | RECALLED (recalled, high) | **not checked** | needs pins as parts; needs: dowel_pin() part and 'pin' join; false alarms L; effort M |
| LOC-006 | **Every adjustment has (a) a controlled way to move it, (b) a lock that does not disturb it, (c) tool access in the finished machine.** Adjustment declares mover (jack screw, nut pair, slot by hand), lock (screws, jam nut, adhesive) and is reachable at the assembled pose | all declared adjustments. warning: an adjustment that drifts or cannot be reached is not one | RECALLED (recalled, high) | **not checked**: Adjustment has name, kind, range only | Adjustment(lock=[screw names], mover=...): locks must exist, be FST-070-locked, and pass driver access in the FINAL assembly, not only at their own step; needs: two fields on Adjustment; false alarms L; effort M |
| LOC-007 | **Allow thermal growth: one fixed point, the rest free to slide or flex.** alpha dT L (aluminium 23.6e-6: 0.3 mm on 220 mm at 60 K) must be taken by slots / flexures, not by clamped screws | heated beds. warning | RECALLED (recalled, high) | partly: fea ThermalCase (bow, gap); AGENT.md 'fixed at one point and free to grow at the others' | bed held at more than one rigid point without a declared flexure; false alarms M; effort M |
| LOC-008 | **Abbe: keep the working point close to the guide and the drive in line with the mass centre and friction.** offset nozzle-to-rail and belt-to-centre-of-mass as small as layout allows; report the arms | carriages. info | SLOCUM (snippet, high) | partly: twin: toolhead tilt spring from block spacing and nozzle distance; fea.bed_support screw offset | report arms; no threshold; effort S |
| LOC-009 | **Bearing spacing against overhang (Saint-Venant / 'golden' proportion).** spacing of guide points along the travel / distance to the load >= 1 (jam risk below), about 1.6 good, 3 ideal; for plain bushings 2:1 minimum | carriages on one rail. warning below 1 | SLOCUM (snippet, med) | partly: ratings: cantilever_on_guide_blocks; fea z_guides_bind | ratio from block positions and tool point; false alarms M; effort S |
| LOC-010 | **Short, closed structural loop between tool and work.** human review of the path nozzle - gantry - frame - Z - bed | machine. info | RECALLED (recalled, med) | human review | review checklist |
| LOC-011 | **Locate both members of a critical pair from the same part / the same set-up.** shortest chain between two features that must align | tolerance chains. info | HUBSCNC (fetched, high) | **already checked**: tolerance: chains; hints 'locate both parts from one part' |  |

### bearings and shafts (BRG)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| BRG-010 | **Fit by load direction: the ring that sees a rotating load gets the tight fit.** inner ring rotating under a fixed-direction load: shaft j5-k5 (light press), housing H7 (slide); state the fit of both seats | rolling bearings. info | RECALLED (recalled, high) | partly: tolerance: shaft_bore_pairs, design.join(a, b, 'press') | require a declared fit for each ring; false alarms L; effort S |
| BRG-011 | **A printed bearing seat is a locating pocket, not a press fit that lasts.** bearing in plastic: retain axially by shoulder + cover / screw / circlip; do not count on interference (creep) and expect 0.1-0.3 mm radial play in a 'sliding' printed seat | bearings in printed parts. warning | RECALLED, PLASTCREEP (recalled, med) | **not checked** | bearing whose seat part is plastic: BRG-020 on both sides + radial clearance drawn; false alarms L; effort S |
| BRG-020 | **Retain the locating bearing axially in BOTH directions, on both rings.** each ring of the locating bearing has a shoulder, sleeve, circlip, cover or collar on both faces; the load path for axial force in each direction is drawn | shafts carrying axial load. warning (error when a declared axial load has no path) | BEARARR, RECALLED (snippet, high) | **not checked**: AGENT.md 'axial retention of bearings' not checked | probe the annulus above / below each ring for an abutting part (tools/practice_audit.py does); false alarms M; effort S |
| BRG-021 | **One locating bearing per shaft; the other floats.** exactly one bearing constrained axially both ways; the other free on one ring (thermal growth, no fight) | two-bearing shafts. info | BEARARR (snippet, high) | **not checked** | from BRG-020 results per shaft; false alarms M; effort S |
| BRG-022 | **Axial load on a deep-groove ball bearing stays a fraction of its static rating.** Fa <= 0.5 C0 (<= 0.25 C0 for small / light-series bearings); 608: C0 1370 N -> about 340 N *the 0.5 / 0.25 C0 figures were searched for and not confirmed today* | ball bearings used as thrust. info | RECALLED (recalled, med) | partly: ratings: guide loads against catalogue ratings ('typical') | axial share of the joint load per bearing; false alarms L; effort S |
| BRG-023 | **Axial load goes through a shoulder, collar or circlip, not through set-screw friction or a press fit.** every axial load path element is a positive stop; a set-screwed hub in the path is a warning | lead screws. warning: slips in service, slowly | RECALLED, MDSET (recalled, high) | **not checked** | axial path from nut to frame: joins of kind set_screw / press on it; false alarms L; effort M |
| SHF-010 | **Set screws bear on a flat (or dimple), two at 90 degrees, and are locked.** hub on a shaft by set screws: flat or spot on the shaft under at least one screw; two screws at 90 deg (Gates stock pulleys: 2 above 16 grooves); thread adhesive *Machine Design (snippet): a flat adds only about 6 % torsional holding power; its value is repeatable seating and no burr locking the hub on* | pulleys. warning: the classic printer failure (layer shift) | GATES, MDSET, MDSET (repo, high) | **not checked**: v8 docstring: 'pulley set screws' not modelled | set_screw joins: does the shaft have a flat (catalogue attribute)?; needs: shaft flat on nema17(); set screw count on gt2_pulley; false alarms L; effort S |
| SHF-011 | **Never seat a set screw or a bearing on a thread.** bearing bores and hub set screws need a plain turned journal; a T8 thread crest is not a journal (undersize, 4 line contacts, set screw ruins the thread) | lead screws. warning: runout and a hub that cannot hold | RECALLED (recalled, high) | **not checked** | bearing or set-screw hub whose shaft part is a lead screw without a 'journal' interface; needs: leadscrew end-machining option; false alarms L; effort S |
| SHF-012 | **Keep overhung loads close to the bearing.** belt pull x overhang within the motor's radial limit; pulley as close to the face as possible | motor pulleys. warning | RECALLED (recalled, high) | **already checked**: ratings: motor_shaft_radial_load |  |
| SHF-013 | **Flexible couplings carry torque, not weight or thrust.** no axial load path through an elastomer / helical coupling | couplings. warning | RECALLED (recalled, high) | partly: interference: shaft_too_deep_in_coupler; v8 requirement 6 | BRG-023 path test; effort M |

### belts (BLT)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| BLT-010 | **At least 6 teeth in mesh on every load-carrying sprocket.** teeth in mesh = wrap/360 x teeth >= 6; for each tooth fewer (minimum 2) the torque rating falls 20 % | all loaded pulleys (not idlers). warning with the derated rating; error under 2 teeth or when the derated rating is below the load | GATES, SDPSI (repo, high) | partly: motion: belt_low_wrap, but only for the pulley named in a joint's drive | apply to every non-idler pulley on the path; compare derated rating with the pulley's torque; false alarms L; effort S |
| BLT-011 | **At least 60 degrees of wrap on every loaded sprocket.** wrap >= 60 deg | loaded pulleys. warning | GATES (repo, high) | **not checked** | route() already returns wraps; false alarms L; effort S |
| BLT-020 | **Sprockets no smaller than the pitch's minimum.** 2MGT: check zmin in the maker's table (inside idler minimum 12 grooves); MXL: 10 teeth | pulleys. warning | GATES, GATESMEC, SDPSI (repo, med) | partly: catalogue offers fixed tooth counts | table; false alarms L; effort S |
| BLT-030 | **Idler type: tooth side gets a sprocket (or a flat idler >= 40-groove pitch diameter), the back gets a FLAT, uncrowned idler.** backside idler: smooth, uncrowned; inside flat idler OD >= 25.4 mm (2MGT) | idlers. warning: teeth on the belt's back wear the backing and make noise | GATES, GATES, SDPSI (repo, high) | **not checked** | wrap sense of each idler against the belt's tooth side; idler SKU toothed or smooth; needs: smooth idler catalogue part; tooth side on Belt; false alarms L; effort S |
| BLT-031 | **Idler diameters.** 2MGT: backside idler OD >= 12.7 mm (0.50 in), and at least 30 % larger than the minimum inside sprocket; inside idler >= 12 grooves; SDP/SI: idler diameter must exceed the smallest drive pulley *Gates' two statements differ: table 9 gives 0.50 in; '30 % larger than the minimum inside sprocket' (12 grooves, 7.6 mm PD) gives about 10 mm. SDP/SI is stricter (larger than the smallest drive pulley).* | idlers. warning | GATES, GATES, SDPSI (repo, high) | **not checked** | idler OD from the catalogue; false alarms L; effort S |
| BLT-032 | **Idlers and tensioners on the slack side, locked after tensioning; no spring idler on the tight side.** tensioner on the span leaving the driver in the unloaded direction; lock declared (LOC-006) | closed loops. info | GATES, SDPSI (repo, high) | **not checked** | for a reversing drive both spans are tight in turn: report only; effort S |
| BLT-040 | **Pulley diameter not smaller than the belt width.** pulley OD >= belt width | all pulleys. warning: tracking, edge wear | SDPSI (fetched, med) | **not checked** | catalogue OD against Belt.width; false alarms L; effort S |
| BLT-041 | **Flanges.** at least one flanged pulley per belt; both flanged when centre distance >= 8 x small pulley diameter or the shafts are vertical; open-ended belts: clamp alignment replaces a flange | belt drives. warning | SDPSI, GATES (fetched, high) | **not checked** | flange attribute of catalogue pulleys; axis direction against gravity; needs: flanged flag (pulley solids already have flanges); false alarms L; effort S |
| BLT-050 | **Belt tension is set to a number, with adjustment travel to fit and re-tension.** installation tension declared (Gates minimum per width; fixed-centre positioning Ti = 1.0-1.2 Te); centre-distance adjustment >= what fitting over flanges needs | belts. info | SDPSI, SDPSI, GATESMEC (fetched, high) | **already checked**: ratings: Belt.tension default from Gates; motion: belt_wrong_length against Belt.adjust |  |
| BLT-051 | **Pulleys in one plane, shafts parallel.** in-plane within 0.5 mm as drawn; under tolerance per the tolerance verifier | belts. error | SDPSI (fetched, high) | **already checked**: motion: belt_misaligned; tolerance: belts in plane |  |
| BLT-052 | **Open belt ends: clamp enough teeth, positively.** >= 6 teeth held in a toothed clamp or folded-back grip; no reliance on a zip tie alone | belt anchors. info | RECALLED (recalled, med) | **not checked**: Belt anchors are points | needs clamp geometry; needs: anchor length on Belt; false alarms M; effort M |
| BLT-053 | **Belt drive brackets must be rigid: centre distance must not change under load.** deflection of motor / idler mounts under 2 x tension small against tooth height (0.76 mm for 2 mm pitch): aim < 0.1 mm | motor and idler mounts. info | GATES, SDPSI (repo, med) | partly: fea load cases if written | auto-generate an AssemblyCase per belt mount; false alarms M; effort L |

### lead screws (LSC)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| LSC-010 | **Stay below the screw's critical (whirl) speed.** n <= 0.8 x n_crit; n_crit grows with root diameter / L^2 and end fixity (fixed-free lowest) | lead screws. info at printer Z speeds (12 mm/s on 2 mm lead = 360 rpm) | RECALLED (recalled, med) | **not checked** | formula with catalogue root diameter and declared end fixity; needs: end fixity; false alarms L; effort S |
| LSC-011 | **Check the screw as a column when it is in compression.** Euler load with end fixity >= 3 x axial load | screws pushing a load. info | RECALLED (recalled, high) | **not checked**: AGENT.md: buckling not checked | formula; needs: end fixity; false alarms L; effort S |
| LSC-012 | **Support the driven end of a screw so that it cannot whip or lift; a free far end is acceptable for short Z screws.** driven end: two bearings spaced >= 3 x shaft diameter (or one double-row), retained per BRG-020; free length / diameter reported | lead screws. warning | RECALLED (recalled, med) | **not checked** | bearing spacing on the screw / diameter; false alarms L; effort S |
| LSC-013 | **Know where backlash goes: gravity-loaded nuts are fine until something lifts the bed.** nut preloaded by weight only: upward force (crash, sticking print removal) must not unseat nut, screw or bearing | Z axes. info | RECALLED (recalled, med) | human review | BRG-020 in the upward direction covers the mechanical part; review checklist |
| LSC-014 | **A vertical axis must not fall at power-off.** self-locking screw (efficiency < 0.5, i.e. lead angle below the friction angle) or a brake | vertical axes. warning | RECALLED (recalled, high) | **not checked** | catalogue efficiency of the screw; false alarms L; effort S |

### linear guides (LIN)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| LIN-010 | **Mounting shoulders and corner reliefs to the maker's table.** MGN12: rail-side shoulder H1 <= 1.7 mm with fillet r1 <= 0.3; block-side shoulder H2 <= 4 mm, r2 <= 0.4 | rails / blocks against shoulders. warning | HIWIN (repo, high) | **not checked** | geometry of the part beside the rail foot; false alarms M; effort M |
| LIN-011 | **Mounting surface flat and stiff enough for the rail.** flatness about 0.05 / 200 mm for MG12 (snippet); an extrusion face is not catalogued for straightness | rail seats. info | HIWIN_SNIP (snippet, low) | **not checked**: AGENT.md: extrusion straightness not catalogued | process flatness class of the seat part; needs: straightness of extrusions; false alarms M; effort M |
| LIN-012 | **Bolt the rail at the maker's pitch; do not leave holes empty on a loaded rail.** every hole (MGNR12: 25 mm pitch, 10 mm end distance) for rated load and accuracy; every second hole only on lightly loaded axes, said explicitly | rails. info | HIWIN, RECALLED (recalled, med) | **not checked** | screws threading through the rail / holes in the rail; false alarms L; effort S |
| LIN-013 | **Rail and block bolts torqued to the maker's figure.** M3: about 1.9 N.m in iron, 1.0 N.m in aluminium (snippet, row not confirmed for MGN12); block threads 3.5 mm deep: screw length = plate + 3 mm | guides. info | HIWIN_SNIP, HIWIN (snippet, low) | partly: interference: thread_bottoms_out on the block | torque table (FST-040); effort S |
| LIN-014 | **A block must never run off its rail; fit end stops, and keep the block on a rail (or its plastic keeper) during assembly.** mechanical stop inside the rail end at both ends of every rail; assembly order never slides a block off | recirculating blocks. warning: balls drop out | RECALLED (recalled, high) | partly: motion: guide run-off over mechanical travel | a part that blocks the block within the rail length beyond mechanical travel; false alarms M; effort M |
| LIN-015 | **Use the rail's reference edge.** master rail's datum edge against a shoulder, pins or a straightedge at assembly | rails. info | HIWIN_SNIP (snippet, med) | human review | review checklist |
| LIN-016 | **Moment loads: one block is a pivot.** a single block carries roll / pitch / yaw moments on its own rating and stiffness; prefer two blocks or two rails when the load is off the block | carriages. warning | RECALLED (recalled, high) | **already checked**: ratings: guide loads and moments; twin: toolhead tilt |  |

### structure (STR)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| STR-010 | **Close and triangulate frames; a rectangle of extrusions with corner cubes racks.** each frame face has a diagonal, a panel or gusseted corners; report racking stiffness | frames. info | RECALLED (recalled, high) | partly: fea AssemblyCase (screwed lower bound) | auto racking load case; effort L |
| STR-011 | **Carry loads in tension / compression and shear, not bending of thin sections; keep load paths short.** review | brackets. info | RECALLED (recalled, high) | human review | review checklist |
| STR-012 | **Radius loaded inside corners.** inside corner radius >= 0.25 t on loaded sheet and printed parts; machined pockets >= 1/3 depth | loaded parts. info | HUBSCNC, RECALLED (recalled, med) | partly: manufacture: corner radii (for the cutter, not for stress); fea FoS | sharp concave edges on parts in a load case; false alarms M; effort M |
| STR-013 | **Friction joints: check slip.** n x 0.65 x preload x mu (0.15 dry steel / aluminium) >= 1.5 x shear load | slotted and T-nut joints carrying load. warning | BOLTSCI, RP1228 (fetched, med) | **not checked** | same as FST-052; effort M |
| STR-014 | **Thin sheet brackets: bend a flange or add a return where they carry out-of-plane load.** flat sheet cantilever length / t <= 10 under belt or motor load, else flange / gusset | sheet mounts. info | RECALLED (recalled, low) | partly: fea | auto load case per motor mount (BLT-053); effort L |

### sheet metal (SHT)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| SHT-010 | **Hole size and web.** hole >= 0.5 t (laser), recommended >= t; hole edge to part edge >= t (Protolabs: >= 3.2 mm above 0.9 mm sheet) | cut sheet. error / warning | SCS, PROTOSHEET (fetched, high) | **already checked**: manufacture: sheet.hole_min_t_ratio, sheet.hole_recommended_t_ratio, sheet.hole_to_edge_t_ratio, sheet.hole_spacing_t_ratio |  |
| SHT-011 | **Features clear of bends; flanges long enough; relief at bend ends.** hole to bend >= 2 t + r; flange >= 4 t (Protolabs) / shop table; relief notch where a bend meets an edge *flange minimum differs: mechloop 2 t + r, Protolabs 4 t* | bent sheet. error / warning | PROTOSHEET, SCS, SCS (fetched, high) | partly: manufacture: sheet.flange_min_t_ratio (2 t + r), sheet.hole_to_bend_t_ratio; bend relief NOT checked | bend line ending inside material without a notch; false alarms M; effort M |
| SHT-012 | **One bend radius per part, the shop's tooling radius.** all bends same inside radius = shop table | bent sheet. info | PROTOSHEET, SCS (fetched, high) | partly: manufacture: sheet.bend_radius_t_ratio | compare radii across bends; effort S |
| SHT-013 | **Round the outside corners of sheet profiles.** outside profile corners R >= 1 mm (R >= t preferred, R 3 mm on parts handled in service) | cut sheet. warning: sharp points cut hands and cables | RECALLED (recalled, high) | **not checked**: manufacture checks INSIDE corners only | convex profile edges parallel to the thickness with no radius; false alarms L; effort S |
| SHT-014 | **Order the deburr / edge finish; laser and waterjet edges are sharp and carry dross on the exit side.** every sheet part has an edge-finish note (deburr both sides / tumble) and a corrosion finish for mild steel | cut sheet. warning: cut fingers, cut wire insulation | SCS, RECALLED (recalled, high) | **not checked** | meta edge_break / finish present; needs: finish + edge_break fields; false alarms L; effort S |
| SHT-015 | **Self-fixturing: tab-and-slot or locating ribs so sheet parts find their place.** slot = t + 0.1 to 0.2 mm; review | sheet assemblies. info | RECALLED (recalled, med) | partly: assemble: needs_holding | ; effort M |
| SHT-016 | **Pressed-in hardware clear of edges and bends.** PEM-type hardware: centre to edge per the maker's table; not near bends | sheet with inserted hardware. warning | PROTOSHEET (fetched, med) | **not checked** | needs hardware parts; needs: press-in nut / stud parts; effort M |
| SHT-017 | **Tapping thin sheet.** tapped sheet >= 1.5 mm and >= 3 pitches of thread (M3 in 1.5 mm, M5 in 2.5 mm); else rivet nut / PEM / nut | tapped sheet. warning | RECALLED (recalled, med) | **already checked**: manufacture: sheet.tap_min_thickness_mm; interference thread_engagement |  |

### machining (MCH)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| MCH-010 | **Inside corner radius and pocket depth.** radius >= 1/3 depth; depth <= 4 x width | milled parts. warning | HUBSCNC, HUBSCNC (fetched, high) | **already checked**: manufacture: cnc.corner_radius_min_mm, cnc.corner_depth_ratio, cnc.pocket_depth_ratio |  |
| MCH-011 | **Standard drills and taps; holes no deeper than needed.** standard drill sizes; depth <= 4 d recommended, 10 d typical; threads M6+ preferred, <= 3 d | machined holes. warning | HUBSCNC, HUBSCNC (fetched, high) | **already checked**: manufacture: cnc.drill_tolerance_mm, cnc.hole_depth_ratio, cnc.thread_depth_ratio |  |
| MCH-012 | **Wall thickness.** metal >= 0.8 mm (0.5 feasible), plastic >= 1.5 (1.0) | machined parts. error / warning | HUBSCNC (fetched, high) | **already checked**: manufacture: cnc.wall_* |  |
| MCH-013 | **Few set-ups; related features in one set-up.** <= 3-4 set-ups; features that must align share a set-up | machined parts. warning | HUBSCNC (fetched, high) | **already checked**: manufacture: cnc.setups_max |  |
| MCH-014 | **Tolerance only what needs it; everything else to a general tolerance.** general tolerance ISO 2768-m (f where needed) stated; tight tolerances listed individually | machined parts. info | HUBSCNC, HUBSCNC (fetched, high) | partly: tolerance: process classes | DOC-011; effort S |
| MCH-015 | **Break all machined edges.** edge break 0.2-0.5 mm chamfer or radius on all outside edges (ISO 13715 indication), stated on the drawing; chamfer hole entries that take screws or pins | machined parts. warning | ISO13715, RECALLED (recalled, high) | **not checked** | sharp convex edge length per part (tools/practice_audit.py does) or a declared edge note; needs: edge_break field; false alarms L; effort S |

### 3D-printed parts (PRT)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| PRT-010 | **Orient layers so the load does not peel them.** principal tension not along the build direction *v8 checker note 5: it also fires on compression* | loaded prints. warning | HUBSFDM (fetched, high) | **already checked**: manufacture: fdm.layer_load_fraction (load_across_layers) |  |
| PRT-011 | **Holes print small: compensate, and ream or drill the ones that matter.** vertical holes about 0.15-0.4 mm under; critical bores (bearing seats, shafts, pins) get a 'ream / drill after printing' note | printed holes. info | HUBSFDM (fetched, high) | partly: tolerance: printed holes 0.15 mm small | bearing / pin / axle bores in printed parts without a finishing note; needs: note field; false alarms L; effort S |
| PRT-012 | **Chamfer, not fillet, the edges on the build plate.** 45 deg chamfer 0.4-0.6 mm on bed-contact edges of mating faces (elephant's foot) | printed mating faces. info | HUBSFDM (fetched, high) | **not checked** | sharp convex edges lying on the print_up base plane of a part that mates on that face; false alarms M; effort M |
| PRT-013 | **Small printed pins and bosses are weak: use bought pins.** pins < 5 mm diameter: fillet at the base or replace with a dowel / screw | printed pins. warning | HUBSFDM (fetched, high) | partly: manufacture: fdm.feature_min_mm (2 mm) | ; effort S |
| PRT-014 | **Overhangs, bridges, horizontal holes.** overhang <= 45 deg; bridges clean to 5 mm; horizontal holes teardrop or <= 10 mm | prints. warning | HUBSFDM, HUBSFDM (fetched, high) | **already checked**: manufacture: fdm.overhang_angle_deg, fdm.bridge_*, fdm.horizontal_hole_max_mm |  |
| PRT-020 | **Enough plastic around holes, inserts and nuts.** wall around a screw hole or insert >= 1 d (>= 2 perimeters + infill anchoring); >= 3 perimeters around bearing seats | prints. warning | CNCK, RECALLED (recalled, med) | **already checked**: manufacture: fdm.thread_wall_d_ratio, wall_too_thin_to_print |  |
| PRT-030 | **Plastic creeps under a clamped screw: spread the load and do not rely on preload.** screw head / nut on printed plastic => washer (ISO 7089, wide series on PETG / PLA) or metal sleeve (compression limiter) through the plastic; sustained bearing pressure <= about 0.3 x yield (recalled); or reduce the torque and lock the screw (FST-070) | every screw through a printed part. warning: joints go slack over weeks, faster when warm | PLASTCREEP, PLASTCREEP (snippet, high) | **not checked** | first clamped part under head / nut is plastic and no washer or sleeve part (tools/practice_audit.py does); needs: washer part; optional 'limiter' sleeve; false alarms L; effort S |
| PRT-031 | **Keep sustained load and heat off low-temperature plastics.** part temperature <= HDT - 15 K under load (PLA about 55, PETG about 70, ABS about 95 degC: recalled); motor mounts, bed parts, hotend parts not in PLA | prints near heat. warning | RECALLED (recalled, med) | partly: electrical thermal estimates (probe); v8 chose PETG / ABS by hand | material table with HDT against el.hot_parts and motor case temperature; needs: HDT per material; false alarms M; effort M |
| PRT-032 | **Consolidate parts only as far as each still prints without support and in a strong orientation.** report; no threshold | prints. info | HUBSFDM, RECALLED (recalled, med) | human review | review checklist |
| PRT-033 | **Functional bores print roundest with their axis vertical.** bearing seats and shaft bores: axis along print_up | printed seats. info | RECALLED (recalled, med) | **not checked** | bore axis against print_up; false alarms L; effort S |

### assembly and service (ASM)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| ASM-010 | **Tool access for every screw.** driver envelope clear when the screw is fitted | screws. error | RECALLED (recalled, high) | **already checked**: assemblability: driver access (at installation step, home pose) |  |
| ASM-011 | **A nut needs a spanner or a trap; someone must hold it.** each loose nut: spanner swing >= 60 deg or socket access, or a captive pocket; else it spins | screw + nut joints. warning: two-handed, blind work | RECALLED (recalled, high) | **not checked**: assemblability checks the screw's driver only | clear annular sector around each nut that is not in a pocket; false alarms M; effort M |
| ASM-012 | **Assemble from one direction, onto a base, with gravity.** report from_below, turns; target zero from-below fasteners on bench sub-assemblies | assembly. info | RECALLED (recalled, high) | **already checked**: assemble: from_below, times_assembly_is_turned, needs_holding |  |
| ASM-013 | **Poka-yoke: a part that fits two ways will be fitted the wrong way.** hole patterns of non-symmetric parts are not symmetric under 180 deg rotation / mirroring; left / right parts are identical or cannot be swapped | custom parts. info | RECALLED (recalled, med) | **not checked** | symmetry test of each part's interface pattern against its full shape; false alarms M; effort M |
| ASM-020 | **Adjustments and their locks reachable in the finished machine.** see LOC-006 | adjustments. warning | RECALLED (recalled, high) | **not checked** | driver access test at the final assembly for named screws; needs: LOC-006 fields; false alarms L; effort S |
| ASM-030 | **Wear and service parts come out without tearing the machine down.** declared service items (nozzle, belts, bed sheet, fans, hotend, board) each have a removal path that disturbs no alignment (rails, belt planes, bed level) | printers. warning | RECALLED (recalled, high) | **not checked** | run the disassembly search for each service item on the finished assembly; list what must come off first; needs: design.service = [...]; false alarms M; effort M |
| ASM-040 | **Strain relief at both ends of every moving cable; fixed clamp before each connector.** every flexing span is clamped to a part at both ends, then >= 30 mm of slack to the connector; no flexing at a crimp or solder joint | cables on moving bodies. warning | RECALLED (recalled, high) | partly: subsystems: cable_clamp_in_air; electrical looms (waypoints with clamp=) | last clamp to connector distance; false alarms M; effort S |
| ASM-041 | **Bend radius of flexing cables and chains.** continuous-flex cable: bend radius >= 7.5-10 x cable OD (maker's figure); loom / chain radius >= largest member's | flexing looms. warning | RECALLED (recalled, med) | partly: electrical: bend_too_tight; Cable.min_bend_radius (15 mm default) | derive the minimum from the largest wire OD; effort S |
| ASM-042 | **Cables clear of sharp edges, hot parts and moving parts; grommet or edge trim where a loom crosses sheet.** loom path >= 3 mm from unbroken sheet edges, or the edge is trimmed / the hole grommeted | looms. warning | RECALLED (recalled, high) | partly: electrical: flex_span_crosses_part; AGENT.md 'cable paths (only lengths)' | distance from loom polyline to sharp edges found by MCH-015 / SHT-014; false alarms M; effort M |
| ASM-050 | **Label connectors, wires and fasteners groups; mark adjustment directions.** review | machine. info | RECALLED (recalled, med) | human review: electrical: wiring.md labels | review checklist |

### wiring (ELE)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| ELE-010 | **Protective bonding of every exposed conductive part that can become live.** PE from the inlet to supply case, frame and each separately anodised metal sub-assembly near mains; continuity verified (test current 0.2-10 A, older edition); green-yellow, own terminal | mains-powered machines. error | IEC60204, RECALLED (snippet, med) | partly: electrical: earth wires to supply and earth_point | FST-111 continuity graph; effort L |
| ELE-011 | **Ferrules on stranded wire in screw terminals; ring terminals under screws; no tinned ends.** each stranded conductor in a screw terminal has a ferrule sized to the wire | screw terminals. warning | RECALLED (recalled, high) | partly: electrical: connectors / terminals per wire (twin ferrule text) | terminal kind per port; effort S |
| ELE-012 | **Segregate mains from low voltage; cover live terminals.** mains conductors routed apart from signal looms, double insulation or barrier; finger-safe covers on supply terminals | mains wiring. error | RECALLED (recalled, high) | partly: electrical: mains safety checks | ; effort M |
| ELE-013 | **Derate connectors and wires.** continuous current <= 80 % of connector rating; heater circuits on screw terminals or rated connectors, not signal headers | power wiring. warning | RECALLED (recalled, med) | **already checked**: electrical: connector and gauge checks, 80 % limits |  |

### safety and ergonomics (SAF)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| SAF-010 | **No sharp edges or corners where hands or cables go.** all accessible metal edges broken (MCH-015, SHT-013, SHT-014); extrusion cut ends deburred and capped | machine. warning | ISO13715, RECALLED (recalled, high) | **not checked** | sum of sharp convex edge length on parts with no edge note; false alarms L; effort S |
| SAF-011 | **Pinch and crush points of moving axes.** gaps that close between moving and fixed parts: either < 4 mm (finger cannot enter) or > 25 mm at the end of travel (recalled ISO 13854 finger values), or guarded / low force | axes with drive force > about 75 N. info | RECALLED (recalled, low) | **not checked** | closing gaps from the motion sweep with the joint's available force; false alarms H; effort M |
| SAF-012 | **Hot surfaces marked and out of casual reach.** bare metal above about 60 degC that can be touched: warning label; bed and hotend unavoidable, state it | heaters. info | RECALLED (recalled, med) | human review: electrical el.hot_parts | review checklist |
| SAF-013 | **Guard or enclose belt run-ins that fingers and hair can reach.** review; open-frame printers accept it | belts. info | RECALLED (recalled, med) | human review | review checklist |
| SAF-014 | **Stability: the machine does not tip or walk.** centre of mass projection inside the foot polygon with margin at a 10 deg tilt; feet declared; reaction of the heaviest axis at max accel < static friction | bench machines. info | RECALLED (recalled, med) | **not checked** | mass properties + feet positions; needs: feet; false alarms L; effort S |
| SAF-015 | **Liftable by one person, with somewhere to grip.** mass <= about 20-25 kg for a one-person lift; grips that are not the gantry or the bed | machine. info | RECALLED (recalled, med) | partly: geometry: mass | threshold on total mass; effort S |

### documentation (DOC)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| DOC-010 | **Edge-break note on every made metal part.** 'break all sharp edges 0.2-0.5' or ISO 13715 symbol; deburr note on sheet DXF orders | made parts. warning | ISO13715, RECALLED (recalled, high) | **not checked** | field present; written into the part's fabrication sheet; needs: edge_break; effort S |
| DOC-011 | **General tolerance block.** ISO 2768-m (or the process class used by the tolerance verifier) stated per part; only tighter features called out | made parts. info | HUBSCNC, HUBSCNC (fetched, high) | partly: tolerance process classes exist but are not exported to a drawing / order sheet | ; effort M |
| DOC-012 | **Torque and threadlocker call-outs in the build instructions.** BUILD.md step for each screw group gives torque (FST-040) and locking (FST-070) | build docs. info | RP1228, RECALLED (recalled, high) | **not checked**: assemble writes BUILD.md without torques | ; effort M |
| DOC-013 | **Threads, fits and finishes called out.** tapped holes, press / slide fits and surface finish listed per part (a STEP file does not carry them) | made parts. info | HUBSCNC (fetched, high) | partly: manufacture knows the threads each screw needs | ; effort M |

### Sources

| Key | Document | Level | Where |
|---|---|---|---|
| RP1228 | NASA Reference Publication 1228, Fastener Design Manual (R. T. Barrett, 1990) | fetched | https://ntrs.nasa.gov/api/citations/19900009424/downloads/19900009424.pdf |
| BOLTSCI | Bolt Science, Self-Loosening of Bolts and Nuts (vibration loosening) | fetched | https://www.boltscience.com/pages/vibloose.htm |
| GATES | Gates, Light Power and Precision Drive Design Manual (PowerGrip GT3 / 2MGT), section 'V. Idler Usage' and belt drive design notes | repo | repo: vendor_docs/Gates_GT2_design_manual.pdf (record mechloop/parts/vendor/gates_gt2.json; origin https://www.gates.com/drivedesign) |
| SDPSI | SDP/SI, Timing Belt Design and Installation Suggestions: General Guide Lines | fetched | https://www.sdp-si.com/resources/beltdesignsuggestions.php |
| GATESMEC | Gates Mectrol, Belt Sizing Guide (polyurethane timing belts) | fetched | https://www.gates.com/content/dam/documents-library/installation-guides/BeltSizingGuide.pdf |
| HIWIN | Hiwin MG series catalogue, tables 3.86 to 3.91 (as recorded in mechloop/parts/vendor/hiwin_mgn12.json; PDF vendor_docs/Hiwin_MG_catalogue.pdf) | repo | repo: mechloop/parts/vendor/hiwin_mgn12.json |
| HIWIN_SNIP | Hiwin MG catalogue / assembly manual, via search summary (torque table row and flatness not verified) | snippet | https://motioncontrolsystems.hiwin.com/Asset/Linear-Guideway-Assembly-Manual-HIWIN-Corp.pdf |
| HUBSCNC | Hubs (Protolabs Network), How to design parts for CNC machining | fetched | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| HUBSFDM | Hubs (Protolabs Network), How to design parts for FDM 3D printing | fetched | https://www.hubs.com/knowledge-base/how-design-parts-fdm-3d-printing/ |
| PROTOSHEET | Protolabs, Sheet metal fabrication design guidelines | fetched | https://www.protolabs.com/services/sheet-metal-fabrication/design-guidelines/ |
| SCS | SendCutSend, Bending guidelines | fetched | https://sendcutsend.com/guidelines/bending/ |
| CNCK | CNC Kitchen, Threaded inserts in 3D prints: tips and tricks | fetched | https://www.cnckitchen.com/blog/tipps-amp-tricks-fr-gewindeeinstze-im-3d-druck-3awey |
| ISO7089 | ISO 7089 plain washer dimensions as tabulated in FreeCAD Fasteners Workbench (iso7089def.csv) | fetched | https://raw.githubusercontent.com/shaise/FreeCAD_FastenersWB/master/FsData/iso7089def.csv |
| ISO4762 | ISO 4762 socket head cap screw dimensions as tabulated in FreeCAD Fasteners Workbench (iso4762def.csv) | repo | repo: vendor_docs/FastenersWB_iso4762def.csv |
| NORDLOCK | Nord-Lock, The Experts: Thread engagement in a tapped hole | snippet | https://www.nord-lock.com/insights/bolting-tips/2015/the-experts-thread-engagement-in-a-tapped-hole/ |
| TAMESON | Tameson, Thread Engagement Chart | snippet | https://tameson.com/pages/thread-engagement-chart |
| BOSSARD | Bossard technical information F.047, Preload and tightening torques (reference values, VDI 2230:2015 basis) | snippet | https://media.bossard.com/en/assembly-technology-expert/technical-information-and-tools/technical-resources/preload-and-tightening-torques/how-to-use-reference-values/ |
| MDSET | Machine Design, Setscrews | snippet | https://www.machinedesign.com/fastening-joining/article/21834719/setscrews |
| SLOCUM | A. Slocum, FUNdaMENTALS of Design, Topic 3 Fundamental Principles (MIT 2.75 / OCW) | snippet | https://ocw.mit.edu/courses/2-75-precision-machine-design-fall-2001/78ed54010cbeebb5a27af05d734a26ad_topic3fundamentalprinciples.pdf |
| BEARARR | NSK, Choosing bearing and arrangement (technical insight); Schaeffler medias, Design of bearing arrangements | snippet | https://www.nsk.com/content/dam/nsk/eu/en_gb/documents/bearings-europe/P_TI-0104_EN.pdf |
| PLASTCREEP | Fastener + Fixing Magazine technical article (bolted joints in polymers); hexagon.de review of VDI 2230; mechanicalc bolted joint analysis | snippet | https://fastenerandfixing.com/media/31886/ffm-technical-ffm981603-128.pdf |
| INSERTS | Heat-set insert hole charts (Accu, vendor brochures), via search summary | snippet | https://accu-components.com/p/488-threaded-insert-hole-size-charts-for-3d-printing-pla-petg-resin |
| ISO13715 | ISO 13715:2017 Technical product documentation, Edges of undefined shape, Indication and dimensioning (catalogue entry only) | snippet | https://www.iso.org/standard/61328.html |
| ISO273 | ISO 273:1979 Fasteners, Clearance holes for bolts and screws (catalogue entry only; table values recalled) | snippet | https://www.iso.org/standard/4183.html |
| IEC60204 | IEC 60204-1 Safety of machinery, Electrical equipment of machines (preview / contents only) | snippet | https://webstore.iec.ch/p-preview/info_iec60204-1%7Bed5.0%7Db.pdf |
| RECALLED | Recalled engineering practice (Machinery's Handbook, Shigley, Slocum, Blanding 'Exact Constraint', Gelbart's prototyping talks, VDI 2230, ISO 898-1, SKF catalogue, igus, Thomson, ISO 12100 / 13857 / 13732-1): no document consulted | recalled | none |

## 3. The ten unchecked rules worth most

Ranked by (how often it bites a real machine) x (how cheaply it can be checked from what a design already declares).

| # | Rule | Why it is first-rank | Check from existing data? |
|---|---|---|---|
| 1 | PRT-030 with FST-031: washer or sleeve where a head or nut sits on plastic, a slot or an oversize hole | creep slackens every such joint; the owner's first observation | yes: stack under each head (done in the audit) |
| 2 | FST-070: declared locking on fasteners of moving and vibrating assemblies | loosening is the commonest long-run printer fault | needs one attribute on `add_screw` |
| 3 | FST-060: nuts and tapped parts on the threaded part of a partially threaded screw | a drawn joint that cannot be assembled | yes: thread length table already in `vendor_docs` |
| 4 | BRG-020 / BRG-023: axial retention of bearings both ways; no axial load through set screws | AGENT.md lists it as not checked; v8 depends on it three times | yes: probe around each ring (done in the audit) |
| 5 | SHF-010 / SHF-011: set screws on a flat, never on a thread | pulley slip is the classic layer-shift cause | needs a shaft-flat attribute |
| 6 | MCH-015 / SHT-013 / SHT-014 / DOC-010: broken edges, rounded profile corners, deburr note | the owner's second observation; cuts hands and looms | yes: sharp convex edges per part (done in the audit) |
| 7 | BLT-010 / BLT-011 on every loaded pulley, BLT-030 / BLT-031 for idlers | today only the joint's drive pulley is checked; idler rules not at all | yes: `route()` already returns every wrap |
| 8 | LOC-006: every adjustment has a mover, a lock and access in the finished machine | an adjustment without a lock is a drift source | needs two fields on `Adjustment` |
| 9 | FST-051 / FST-101: two fasteners or one plus an anti-rotation feature; two T-nuts per part | single-screw parts swing loose | yes: screws per part pair |
| 10 | FST-081: look-alike screw lengths where the longer one bottoms in a catalogue thread | M3x8 where M3x6 belongs wrecks a guide block | yes: BOM and `thread_depth` |

## 4. First audit of printer_v8

### 4.1 Method and limits

`tools/practice_audit.py` loads the design with `mechloop.runner.load_design` and probes the B-rep (point-in-solid)
along and around every screw at the home pose: what the screw passes through, each hole's diameter (0.05 mm steps) and
whether it is a slot, the nearest edge, where each nut and tapped part sits on the screw, what the head and each nut bear
on. Belts come from `mechloop.verifiers.belts.route`. Bearings are probed above and below each ring. Sharp edges are
convex edges whose faces meet at 60 degrees or more.

Computed: everything in 4.2 not marked "reading". **From reading the design file, not computed**: set screws (they are
not modelled; only the `set_screw` joins are), what locks each adjustment, the T-nut type, the rails' empty holes, the
T8 screw's fit in the 608 bore. Not examined at all: cable routing against edges, wrench access to nuts, service
removal paths, poka-yoke, pinch points.

Preload is an estimate (class 8.8 torque by feel, +/-35 % per NASA RP-1228); the design names no class and no torque.

### 4.2 Findings, most serious first

**Would stop the build or fail in service**

| # | Rule | Finding | Parts and numbers |
|---|---|---|---|
| 1 | FST-060, FST-061 | The four bed posts cannot be assembled with the screw the BOM names. An ISO 4762 M5 is threaded over its last 22 mm only (b, a reference length); the posts need thread at three places along 76 mm. M5 x 90 is also outside ISO 4762's M5 range (8 to 50 mm). | `bed_post_0..3` (SHCS-M5x90): `bed_post_i_nut_top` sits 2.0 to 6.8 mm under the head, on plain shank (thread starts at 68 mm); `bed_post_i_nut_arm` at 65.8 to 70.5 mm is already 2.3 mm onto the plain shank at the nominal position, so the tab cannot be set at nominal or higher and the declared +/-4 mm of levelling is not there. Needs fully threaded M5 (threaded rod with a nut and adhesive at the plate, or a full-thread screw from a named supplier). |
| 2 | BRG-023, SHF-011, SHF-010 (reading + computed) | The bed's weight goes through pulley set screws that bite on a trapezoidal thread. Each screw's 608 inner ring also sits on the thread crests. | `z_pulley`, `z_pulley_fl`, `z_pulley_fr` on `leadscrew*` (T8x2, `set_screw` joins): the axial path is nut, screw, set screws, hub, upper bearing's inner ring. No journal, shoulder or collar. PRINTER_V8.md lists this as unverified; by practice it is a slip and runout source, not a detail. |
| 3 | BRG-020 (computed) | Nothing holds the three screws, their pulleys or the upper bearings down. | `z_bearing_hi`, `z_bearing_fl_hi`, `z_bearing_fr_hi`: outer ring has nothing above it, inner ring nothing below it; lower bearings' inner rings are free both ways. An upward force on the bed (print removal, a nozzle crash on retract, a nut that sticks) lifts screw, pulley and bearing out of the pocket; the belt then rides off its plane. The nuts are also held down by weight only (design comment). |
| 4 | PRT-030 (computed) | The extruder and hotend are clamped through printed ABS, next to the heater. | `extruder_screw_0/1` (SHCS-M3x50): head on `probe_mount` (4.5 mm ABS), then the Roto, then 7 mm in `tool_plate`. Estimated 346 MPa under the bare head at a normal M3 torque against about 12 MPa sustained; bare-head torque that respects the limit: 0.05 N.m (0.18 with an ISO 7089 washer). The toolhead's clamp load will relax; nozzle and probe offset move with it. |
| 5 | PRT-030, FST-031 (computed) | 34 more head or nut seats (13 heads, 21 nuts) bear directly on printed plastic with no washer. | Heads on `z_drive_mount` (2 x M5 to the rail, 4 x M3 motor screws: the Z motor hangs from PETG at a 41 degC case), `z_pedestal_fl/fr` (2 x M5 each, the bed's weight path), `x_tension_anchor`, `y_tension_anchor`, `y_tension_anchor_l` (belt tension path); nuts on `nut_block`, `nut_block_fl`, `nut_block_fr` (12 x M3, ABS). M5 heads: 289 MPa at normal torque, limit about 14; with an ISO 7089 washer the M5 can take 0.68 N.m, so these joints also need locking (FST-070) or a metal sleeve. |
| 6 | FST-070 (computed + BOM) | No locking provision on 91 screws that ride on moving bodies, nor on any motor, pulley or bed fastener. | Moving bodies: zbody 47, ybody 32, xbody 12 screws. BOM locking items: 3 x NYLOC-M3 (the nut pins). No thread adhesive, no serrated flanges. Plain M3 nuts: 36, plain M5: 22. |
| 7 | FST-030, FST-034 (computed) | The bed posts' heads sit on a 2 mm floor of soft cast plate. | `bed_plate` (MIC-6, yield 105 MPa): 6 mm counterbore in 8 mm leaves 2.0 mm under each M5 head; 235 MPa at normal torque. The two `bed_tie_screw` M3 heads: 196 MPa. The joint is thermally cycled 60 K. Torque limit about 2.5 N.m for M5 there, or a washer in a wider counterbore. |

**Would annoy the builder**

| # | Rule | Finding | Parts and numbers |
|---|---|---|---|
| 8 | FST-031 (computed) | Heads on slots without washers. | `beam_bolt_left`, `beam_bolt_right` and their second bolts (4 x SHCS-M5x8 through `y_plate_left/right`, slot 5.5 x 8.5 mm): 38 % of the head face is supported. These four screws hang the X beam. |
| 9 | SHT-014, SHT-013, MCH-015, DOC-010 (computed) | Every edge of every metal part is unbroken and no part carries an edge note. | 22 parts, 21.5 m of sharp convex edge, 107 sharp outside profile corners. Largest: `electronics_tray` 2.8 m, `front_plate` 2.6 m, `bed_plate` 2.4 m (machined, no chamfer), `back_plate` 1.9 m, `tool_plate` 1.1 m. `y_plate_left/right`, `x_motor_mount` and `tool_plate` move beside the toolhead loom. The 17 laser-cut mild steel parts also have no finish. |
| 10 | BLT-030, BLT-031 (computed) | The Z tensioner is a toothed idler on the belt's smooth back, under Gates' size. | `z_idler` (GT2-IDLER-20T-B5): OD 12.0 mm; Gates table 9 asks a flat, uncrowned back-side idler of at least 12.7 mm for 2MGT. Its bolt sits in a slot of the printed `z_drive_mount` tab, moved by hand, locked by one M5 on plastic (reading): finding 5 applies to the belt's tension. |
| 11 | BLT-010, BLT-011 (computed) | The rear Z screw's pulley has 3.4 teeth in mesh at 60.3 degrees. | `z_pulley`: Gates: rating x 0.4 at 3 teeth, 60 degrees is the stated minimum wrap. Load is small (about 0.013 N.m per screw by hand estimate, against a derated rating near 0.4 N.m), so it works when tensioned; with a slack belt it is the pulley that skips, and a skipped rear screw tilts the bed. `z_pulley_fl/fr` 6.6 and 6.7 teeth, `z_pulley_m` 7.7. mechloop's `belt_low_wrap` does not look at it (it is not the joint's drive pulley). |
| 12 | FST-081 (reading + BOM) | M3x6 (24) and M3x8 (39) are used side by side into guide blocks whose threads are 3.5 mm deep. | Y plates (3 mm steel) and the tool plate (counterbored) need M3x6; the back plate (5 mm) needs M3x8. An M3x8 in a Y plate goes 5 mm into a 3.5 mm thread. |
| 13 | FST-051, FST-101 (computed) | 22 joints hang on one screw. | On one T-nut: `x_rail_stop_left/right` (they stop the X block), `x_tension_anchor`, `y_tension_anchor`, `y_tension_anchor_l` (they take the jack-screw force, about 37 N per Y belt, beside the bolt). On one screw each: both idler axles, each arm end to each plate (backed by one bracket screw), each bed post tab to its post. |
| 14 | FST-100 (reading) | 123 T-nuts (96 M5, 27 M3) with no type. | SKU `TNUT-2020-M3/-M5` only. If slide-in, each must be in its slot before the frame closes; the assembly simulation does not know. |
| 15 | FST-080 (computed) | 15 screw SKUs, 25 fastener SKUs, four hex keys, four spanners. | M2.5, M3, M4, M5 threads; keys 2, 2.5, 3, 4 mm; spanners 5, 5.5, 8, 17 mm. Used once or seldom: M5x10 (1), M5x25 (1), M5x30 (3), M3x25 (3), M3x12 (4), M5x12 (4). |
| 16 | LOC-006 (reading) | Ten declared adjustments; none names its lock. | Mover and lock exist for the X and Y belts (M3 jack screws, T-nut screws) and the bed posts (nut pair). Moved by hand and locked by friction only: Z belt idler (printed slot), X switch (slots), Y switch mount and all rails (sliding T-nuts). Access in the finished machine not checked. |

**Good practice**

| # | Rule | Finding | Parts and numbers |
|---|---|---|---|
| 17 | FST-050 (computed) | 22 holes closer than 1.5 d to an edge or cut-out. | `bed_post_tab_0..3` 1.31 d (post) and 1.41 d (bolts), `x_rail_stop_*` 1.21 d, `y_plate_*` 1.35 d (beside the belt slots: the manufacture verifier's `holes_too_close` is the same place), `tool_plate` 1.33 d, `y_endstop_mount` 1.3 d; printed: `probe_mount`, `part_duct` 1.05 d. |
| 18 | BLT-040 (computed) | 12 mm Y belts on pulleys of 12.0 mm outside diameter. | `y_pulley`, `y_pulley_l`, `y_idler`, `y_idler_l`: SDP/SI: "The pulley diameter should never be smaller than the width of the belt." At the limit. |
| 19 | FST-062 (computed) | Four screws end flush with their nuts. | `bed_tie_screw_0/1`, `part_fan_screw_0/1` (M3x16): 0.0 mm past the nut; one pitch wanted. |
| 20 | FST-020 (computed) | Hole classes are mixed without a stated reason. | Of 218 classified holes: M3 fine 11, medium 47, coarse 57, larger than coarse 23 (all 4.2 mm, printed); M5 medium 49, larger than coarse 9 (6.0 mm, printed); M2.5 fine 4, medium 2; M4 medium 4. The oversize ones are deliberate (printed holes come out small) and are exactly where FST-031 and PRT-030 want washers. The four 3.1 mm holes found are the control board's own (a catalogue part). |
| 21 | FST-001 (computed) | No property class on any screw; the catalogue's proof loads are class 12.9. | all 172 |
| 22 | LIN-012 (reading) | Rails are bolted at every second hole. | `RAIL_SCREW_STEP = 2`: X rail 5, Y rails 6 each, Z rails 5 each, all into M3 T-nuts. Acceptable at these loads; say so. |
| 23 | FST-010 (computed) | Anti-rotation pins have 1.17 d of thread in brass. | `nut_pin`, `nut_pin_fl`, `nut_pin_fr` in the T8 nut flange (3.5 mm). Not a clamping joint. |

What the audit found in order: no thread engagement short of mechloop's own rule (its check holds), no screw in a metal hole
under ISO 273 fine other than the idlers and spacers on their axle screws, all X and Y pulleys at 10 teeth in mesh and 180 degrees,
the Z belt's four toothed pulleys and the idler all flanged on vertical shafts (BLT-041), the protective-earth stud
with ring terminals and a star washer (FST-111).

### 4.3 Fastener schedule in brief

The full schedule is in `v8_audit.json` under `fasteners` (per screw: stack with thickness, hole, slot, edge distance,
ISO 273 class; engagement in diameters against the rule; thread start; thread past the nut; head seat with pressure
estimate and torque limits with and without washer; flags).

| | Count |
|---|---|
| Screws drawn / on moving bodies | 172 / 91 |
| Further M5x8 and T-nuts as BOM lines only (corner brackets) | 52 screws, 123 T-nuts |
| Joints (distinct part sets): with 1 / 2 / 3 / 4 / 5 / 6 screws | 22 / 27 / 1 / 14 / 3 / 2 |
| Heads bearing on printed plastic / on slots / with a washer | 15 / 4 / 0 |
| Nuts bearing on printed plastic | 21 |
| Screws with a declared locking provision / class / torque | 3 (nyloc) / 0 / 0 |
| Flags: PRT-030 36, FST-050 22, FST-060 8, FST-061 6, FST-030 6, FST-031 4, FST-062 4, FST-010 3 | |

## 5. Proposed verifier: `practice`

### 5.1 Structure

- **Thirteenth verifier `practice`**, run after `manufacture` and before `requirements`. Cheap: the audit's probing of
  all 172 screws takes 34 s, of which the fastener stack is the reusable core.
- **Rule registry** in the style of `mechloop/verifiers/dfm_rules.py`: `Rule(id, category, limit, unit, severity,
  source, what, note)`, ids as in this catalogue (`FST-031`), with the source key, URL and evidence level. A rule whose
  number is `recalled` may not be registered at `error` severity; that is a test in `tests/`.
- **Per-rule control**: `d.practice = {"disable": ["SAF-011"], "severity": {"FST-050": "info"}, "limits":
  {"FST-050.min_edge_d": 1.2}}`. Changing a limit is reported in the metrics, as DFM limits are.
- **Waivers**: `d.waive("FST-070", parts=["nut_pin*"], reason="nyloc, left 0.2 mm slack as a slide")`. A waiver without
  a reason of at least 20 characters is itself an error (`waiver_without_reason`). Every waiver in force is listed in
  the report under `practice.waivers` with rule, parts, reason and the finding it suppressed; a waiver that suppresses
  nothing is a warning (`waiver_unused`), so stale ones do not pile up.
- **Findings** carry `rule`, `part`, `at`, `value`, `limit`, `source`, `evidence` and a `hint`, like DFM findings.
- **Shared measurement**: one `fastener_stack(design)` function (stack, hole, slot, seat, thread zone) used by
  `practice`, by `interference.thread_engagement` and by the tolerance verifier's pattern check, so the three agree.
- **Human checklist**: rules with status `human` are written to `out/<name>/practice_review.md` as a checklist with
  the design's own numbers filled in (arms, ratios, hot parts), not silently skipped. The report counts them as
  `not checked`.
- **Declarations to add** (all optional; absence is what the rules flag):
  `add_screw(..., washer=True|"wide", locking="nyloc"|"adhesive"|"serrated", property_class="8.8", torque_nm=...)`;
  `add_nut(..., kind="nyloc"|"flange"|"plain", washer=...)`; `Adjustment(..., mover=..., lock=[...])`;
  `Component.meta["edge_break"]`, `["finish"]`; `design.service = ["nozzle", "x_belt", ...]`;
  `tnut="slide_in"|"drop_in"`; a `flat` interface on motor shafts, a `journal` option on lead screws.

### 5.2 First 25 rules to implement, by value over effort

Each has a known-answer pair: the bad case must raise the finding, the good case must not.

| # | Rule | Effort | Known-answer test: bad -> good |
|---|---|---|---|
| 1 | FST-031 washer on slots and oversize holes | S | M5 cap screw over a 5.5 x 9 slot in a 3 mm plate -> same with a washer part |
| 2 | PRT-030 head or nut on printed plastic | S | M3 through a 5 mm PETG block into a nut -> washer both sides, or an aluminium sleeve through the block |
| 3 | FST-060 nut on the plain shank | S | M5x60 with a nut 10 mm under the head -> M5x20 (threaded to the head) or the nut at 45 mm |
| 4 | FST-070 locking on moving bodies | S | plain M3 + plain nut on a body with a Joint -> `locking="nyloc"`; a waived case appears in the report |
| 5 | BLT-010 / BLT-011 on every loaded pulley | S | three-pulley loop with one driven pulley at 50 degrees -> idler moved to give 90 degrees |
| 6 | BLT-030 / BLT-031 idlers | S | toothed 20T idler on the belt's back -> smooth 18 mm idler |
| 7 | BRG-020 axial retention | S | bearing in an open bore with a shaft through it -> shoulder below, cover above, collar on the shaft |
| 8 | MCH-015 / SHT-014 / DOC-010 edge break | S | plain `Box` plate in steel, no note -> chamfered edges, or `meta["edge_break"]="0.3"` |
| 9 | SHT-013 outside profile corners | S | rectangular sheet tab -> R2 corners |
| 10 | FST-051 single-screw joint | S | bracket on one screw -> second screw, or a rib in a slot declared as a join |
| 11 | FST-101 single T-nut | S | stop plate on one T-nut -> two |
| 12 | FST-050 edge distance | S | M5 hole 6 mm from a steel edge -> 10 mm |
| 13 | FST-020 hole class | S | 5.1 mm hole for an M5 clamp screw -> 5.5; an `axle` join is exempt |
| 14 | FST-061 non-standard length or range | S | M3x50 ISO 4762 -> M3x30; a vendor part number recorded -> info only |
| 15 | FST-062 thread past the nut | S | screw flush with its nut -> next length up |
| 16 | FST-081 look-alike bottoming length | S | BOM with M3x6 and M3x8 around an MGN12H -> one length, or different head style |
| 17 | SHF-010 / SHF-011 set screws | S | `set_screw` join on a T8 screw -> journal end; on a motor shaft with `flat` |
| 18 | BRG-023 axial path through a set screw | M | lead screw whose only downward stop is a set-screwed pulley -> collar or shoulder on a bearing |
| 19 | FST-030 seat pressure | M | M5 on a 2 mm floor of MIC-6 at class torque -> washer in a wider counterbore, or declared torque 2 N.m |
| 20 | LOC-006 adjustment lock and access | M | `Adjustment` with no lock -> lock screws named, reachable with the machine assembled |
| 21 | FST-052 / STR-013 friction joint | M | motor mount on two slotted M5 with 40 N belt pull and no stop -> jack screw touching the mount |
| 22 | BLT-040 / BLT-041 width and flanges | S | 12 mm belt on a 12 mm pulley; unflanged pair on vertical shafts -> 9 mm belt; flanged |
| 23 | FST-100 T-nut type against assembly order | M | slide-in T-nut in a slot closed at both ends at that step -> drop-in, or earlier step |
| 24 | ASM-030 service removal | M | nozzle behind a duct that must come off with the fan -> removal path free |
| 25 | FST-040 / DOC-012 torque and locking table in BUILD.md | M | generated table matches a hand-computed row for M5 on aluminium and on PETG |

Then: LSC-010/011/014 (formulas), LIN-010 shoulders, PRT-012 bed-edge chamfers, ASM-011 spanner access, ASM-042
looms against sharp edges, SAF-014 tip-over.

### 5.3 Existing checks to move or cross-reference

| Existing check | Proposal |
|---|---|
| `interference.thread_engagement`, `thread_bottoms_out` | stay where they are (they are errors every design must clear early); register them as FST-010 / FST-012 so findings carry the rule id and source; use the shared stack. Decide the aluminium factor (1.5 d today against 2 d in the sources) |
| `motion.belt_low_wrap` | move under `practice` as BLT-010 and widen from the joint's drive pulley to every loaded pulley; keep the code name as an alias |
| `motion.belt_misaligned`, `belt_wrong_length`; `ratings.motor_shaft_radial_load` | cross-reference (BLT-051, BLT-050, SHF-012) |
| `manufacture` rules `sheet.hole_to_edge_t_ratio`, `sheet.countersink_min_thickness_mm`, `sheet.tap_min_thickness_mm`, `fdm.thread_wall_d_ratio`, `cnc.thread_depth_ratio`, `cnc.blind_tap_runout_d_ratio` | stay in `manufacture` (can it be made); `practice` adds the in-service rule beside each (FST-050 strength edge distance, FST-013 / FST-091 inserts) and cites the DFM id |
| `ratings.cantilever_on_guide_blocks`, `fea.z_guides_bind`, `fea.bed_support.constraint` | cross-reference from LOC-001 / LOC-009; v8's checker note 2 (three screws judged as a cantilever) belongs to the same clean-up |
| `assemble` metrics `fastener_types`, `tool_changes`, `from_below` | reported by `practice` as FST-080 / ASM-012 with the SKU merge suggestions |
| `subsystems.cable_clamp_in_air`, `electrical.bend_too_tight`, `flex_span_crosses_part` | cross-reference from ASM-040..042 |
| `tolerance` pattern start (`p_all_start`) | shares the measured holes with FST-020 |

### 5.4 Catalogue additions

| Part | Standard / data needed | Used by |
|---|---|---|
| Plain washers M2.5 to M8, normal and wide | ISO 7089 (table fetched: M3 3.2 x 7 x 0.5, M4 4.3 x 9 x 0.8, M5 5.3 x 10 x 1.0), ISO 7093-1 (not fetched) | FST-031, PRT-030, FST-030 |
| Nylon-insert nuts, all-metal locknuts, serrated flange nuts and screws | ISO 10511 / 7040, ISO 7042, ISO 4161, ISO 4162 (none fetched) | FST-070, FST-072 |
| Thread adhesive as a BOM consumable with temperature limit and plastics warning | maker's sheet | FST-070, FST-073 |
| Dowel pins, shoulder screws | ISO 8734 / 2338, ISO 7379 | LOC-004, LOC-005, idler axles |
| Circlips, shaft collars, shim washers 8 x 14 | DIN 471 / 472, DIN 988 | BRG-020, BRG-023 |
| Heat-set inserts M2 to M5 with hole, depth, minimum wall | one maker's table (CNC Kitchen's is an image; not read) | FST-091, FST-092 |
| Smooth idlers, 2MGT | Gates part with OD and bearing data | BLT-030, BLT-031 |
| T-nuts by type (slide-in, drop-in, roll-in, spring), M3 to M5 for 2020 | one maker's drawing with thickness (thread length) | FST-100, FST-101, FST-010 |
| Button and countersunk screws, fully threaded studs / threaded rod | ISO 7380, ISO 10642, DIN 976 | head clearance choices, FST-060 |
| Lead screw with machined journal ends; thrust or support block | a maker's drawing | SHF-011, BRG-023 |
| Rail end stops | maker's part or a made part flagged as such | LIN-014 |
| Tables | ISO 273 clearance holes (confirm the recalled values), ISO 4762 `b` and length ranges (in `vendor_docs`), head sizes for ISO 7380 / 10642, tightening torques by class and friction (Bossard F.047 or ISO 898-1 with VDI 2230), limiting surface pressures by material, HDT by plastic, ISO 2768-m | FST-020, FST-060, FST-040, FST-030, PRT-031, DOC-011 |

## 6. Sources: unreachable, and where they disagree

### 6.1 Not reached today

The session's network allow-list was extended once, with the owner's approval, by 18 reference hosts. Of the sources
the brief names, these were **not read**:

| Source | Why | Effect |
|---|---|---|
| SKF catalogue pages (fits, arrangements, axial load limits) | the pages returned no text to a plain download (script-rendered) | BRG-010, BRG-022 recalled; BRG-020/021 on a search summary of NSK / Schaeffler |
| NASA-STD-5020 | not attempted beyond search; no direct file URL found | thread-protrusion figure in FST-062 recalled |
| VDI 2230, ISO 898-1, ISO 273, ISO 286, ISO 2768, ISO 13715, IEC 60204-1 | paywalled standards; only catalogue entries and previews | hole classes, torques, edge sizes, bonding details recalled or on summaries |
| Bossard F.047 torque tables, Unbrako engineering guide, Fastenal engineering | hosts not fetched after the bulk download was refused by the session's safety classifier; single downloads worked but were spent on NASA, SDP/SI, Bolt Science, CNC Kitchen | FST-040 torques recalled |
| Hiwin assembly manual (bolt torques), Hiwin's own site | file URLs not found; repo's catalogue record used instead | LIN-013 torque on a search summary, row uncertain |
| Thomson (critical speed), igus (bend radius), PEM (edge distances) | not fetched | LSC-010/011, ASM-041, SHT-016 recalled |
| Slocum FUNdaMENTALS, Blanding, Gelbart | Slocum only through a search summary of the MIT notes; Blanding is a book; Gelbart's series is video | LOC rules mostly recalled |
| Xometry, Fictiv, Stratasys, Prusa, Ruthex | not fetched (Hubs / Protolabs and CNC Kitchen covered the same ground) | none |
| SendCutSend general guidelines and deburring pages | downloaded; the rule text is script-rendered and did not extract (the bending page did) | SHT-014 partly recalled |
| Machinery's Handbook | no figure was taken from it, directly or quoted | set-screw figures are Machine Design's, via summary |
| Wikipedia (ISO 13715 page) | 404 | none |

`WebFetch` could not resolve any host in this session; documents were fetched with `curl` through the session proxy.

### 6.2 Disagreements

| Topic | Positions | Used |
|---|---|---|
| Thread engagement in aluminium | mechloop and common shop rule 1.5 d; Nord-Lock 2 d; Tameson 2 to 2.5 d | catalogue states 2 d; the existing check keeps 1.5 d until the owner decides |
| Minimum flange on bent sheet | mechloop 2 t + r (shop tables); Protolabs 4 t | noted in SHT-011 |
| Back-side idler size, 2 mm pitch | Gates table 9: 12.7 mm; Gates text: 30 % over the minimum inside sprocket (about 10 mm); SDP/SI: larger than the smallest drive pulley | table 9 |
| Idlers at all | SDP/SI: "not recommended and should not be used except for power takeoff or functional use"; Gates: "commonly used with good success" | Gates, with its size and side rules |
| Value of a flat under a set screw | Machine Design (summary): about 6 % more torsional holding, axial unchanged; practitioner rule: always use a flat | rule kept for seating and removability, said so in SHF-010 |
| Split lock washers | NASA RP-1228: "useless for locking"; Bolt Science: "actually aid self loosening" | both say do not use; they differ only in how bad |
| Friction for torque tables | Bossard 0.14; SEW (summary) 0.09 for 10.9 / 12.9 | 0.14, recalled torques flagged |
| Hole to edge in sheet | mechloop 1 t of web; Protolabs 3.2 mm from the edge above 0.9 mm sheet; NASA 1.5 d to 2 d from the centre | manufacture keeps the cutting rule, FST-050 adds the strength rule |

### 6.3 Limits of this work

- 75 of 135 rules have a recalled number. The fetched and repo-backed ones are concentrated in fasteners (locking,
  edge distance, preload scatter), belts (all of Gates' and SDP/SI's rules) and the DFM guides.
- The audit's pressure and torque figures rest on recalled torques and an assumed plastic limit; the ranking does not
  depend on their exact values (bare heads on plastic exceed any plausible limit by a factor of ten or more).
- The audit script is not tested beyond this one design. Its hole and edge measurements were spot-checked against the
  design's constants (M5 5.5, printed M5 6.0, printed M3 4.2, sheet M3 3.6 and 3.5: read as drawn after the hole wall is refined by bisection).
- The script measures at the home pose and treats every solid as drawn: T-nuts, set screws and washers that are BOM
  lines or notes are invisible to it, which is itself finding 14.
