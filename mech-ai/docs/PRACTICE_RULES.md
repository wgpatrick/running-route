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
| `research_notes/practice/rules.yaml` | the 138 rules, machine-readable, with a `corrections` list (`rules.json` is the same data for a Python without PyYAML: the project venv has none) |
| `research_notes/practice/sources.yaml` | every source with its URL, access date, evidence level and the verbatim text relied on |
| `tools/practice_audit.py` | read-only audit script (37 s on v8): `.venv/bin/python tools/practice_audit.py designs/printer_v8.py` |
| `research_notes/practice/v8_audit.json` | its output: the full fastener schedule (172 screws), belts, bearings, edges, T-nuts |

## 1. How to read the evidence

Version 2 of this document (later on 2026-11-15). Version 1 rested 75 of 135 numbers on memory. The owner's other agent
then delivered 41 reference documents (`vendor_cad/staging/practice_refs/`, index in `README_INDEX.txt`, declared gaps
in `MISSING.txt`); every recalled rule was checked against them, and section 7 lists every value that changed and what
that did to the v8 audit.

Each rule states the level of the evidence behind its **number**:

- **document**: one of the delivered reference files, quoted with file name and PDF page in `sources.yaml` (Bossard
  torque, surface-pressure and engagement tables, ISO 273 / 4762 / 7089 / 7093 tables, ruthex and SPIROL insert data,
  SKF 608 data, axial-load rule and fit tables, Hiwin installation manual, Holo-Krome and Unbrako set-screw tables,
  legacy Gates GT2 manual, Elesa and igus lead-screw data, PETG / ABS data sheets and creep papers, Stratasys FDM guide,
  ISO 13715 and IEC 60204-1 summaries, Slocum, NASA-STD-5020B). The ISO 273 table is a scan with no text layer; it was
  rendered to an image and read.
- **fetched**: a web document downloaded in the first pass and its sentence read (NASA RP-1228, Bolt Science, SDP/SI,
  Hubs, Protolabs, SendCutSend, CNC Kitchen, ISO 7089 CSV).
- **repo**: a document or vendor record already in this repository. Note: `vendor_docs/Gates_GT2_design_manual.pdf` is
  the CURRENT Gates Light Power and Precision manual (2MGT GT3 belts on GT2 sprockets), not the legacy GT2 manual; its
  rules are now cross-checked against the legacy manual (`12_Gates_GT2_drive_design.pdf`).
- **derived**: our own derivation from documents, labelled as such. One rule: the sustained bearing pressure allowed on
  printed plastic (PRT-030), because no validated allowable exists in the documents.
- **snippet**: a web-search summary only. None remain.
- **recalled**: memory. 52 rules, nearly all in topics the documents do not cover (assembly and service, safety and
  ergonomics, sheet-metal edge finish, structure, T-nut types, tool access): see section 7.3.

The audit's preload is now Bossard's maximum preload for class 8.8 at a friction coefficient of 0.14 (the lower end of
zinc-plated 0.14 to 0.24, which Bossard tells the user to assume when in doubt). The design declares neither class nor
finish. Metal seats are judged against VDI 2230:2015 limiting surface pressures; 6061 and MIC-6 are not in that table and
are mapped to the nearest tabulated alloy by tensile strength (labelled).

## 2. Rule catalogue

138 rules. By evidence behind the number: recalled 52, document 47, fetched 33, repo 5, derived 1. By mechloop status: not 61, partly 44, checked 23, human 10.

| Category | Rules | document | fetched / repo | derived | snippet | recalled | already checked | partly | not checked | human |
|---|---|---|---|---|---|---|---|---|---|---|
| threaded fasteners (FST) | 38 | 17 | 13 | 0 | 0 | 8 | 4 | 12 | 20 | 2 |
| locating and constraint (LOC) | 11 | 4 | 3 | 0 | 0 | 4 | 3 | 5 | 2 | 1 |
| bearings and shafts (BRG) | 11 | 8 | 0 | 0 | 0 | 3 | 1 | 3 | 7 | 0 |
| belts (BLT) | 12 | 5 | 6 | 0 | 0 | 1 | 2 | 3 | 7 | 0 |
| lead screws (LSC) | 6 | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 5 | 1 |
| linear guides (LIN) | 7 | 4 | 0 | 0 | 0 | 3 | 1 | 2 | 3 | 1 |
| structure (STR) | 5 | 0 | 1 | 0 | 0 | 4 | 0 | 3 | 1 | 1 |
| sheet metal (SHT) | 8 | 0 | 4 | 0 | 0 | 4 | 2 | 3 | 3 | 0 |
| machining (MCH) | 6 | 0 | 5 | 0 | 0 | 1 | 4 | 1 | 1 | 0 |
| 3D-printed parts (PRT) | 10 | 3 | 4 | 1 | 0 | 2 | 3 | 3 | 3 | 1 |
| assembly and service (ASM) | 10 | 0 | 0 | 0 | 0 | 10 | 2 | 3 | 4 | 1 |
| wiring (ELE) | 4 | 2 | 0 | 0 | 0 | 2 | 1 | 3 | 0 | 0 |
| safety and ergonomics (SAF) | 6 | 0 | 0 | 0 | 0 | 6 | 0 | 1 | 3 | 2 |
| documentation (DOC) | 4 | 1 | 2 | 0 | 0 | 1 | 0 | 2 | 2 | 0 |
| **all** | **138** | 47 | 38 | 1 | 0 | 52 | 23 | 44 | 61 | 10 |


### threaded fasteners (FST)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| FST-001 | **Declare the property class of every screw and nut; do not design to 12.9 strength when commodity 8.8 / A2-70 will be bought.** each fastener SKU carries a class; preload and ratings use that class (Bossard, mu 0.14, max: M5 8.8 7.0 kN, 10.9 10.3 kN, 12.9 12.0 kN; M3 8.8 2436 N, 12.9 4111 N): the catalogue's 12.9 proof loads overstate a commodity 8.8 or A2-70 screw by 40 % or more | all screws. warning: catalogue proof loads are class 12.9 while the SKU names no class | RECALLED, BOSS_TQ (document, high) | **not checked** | catalogue field; compare required preload with the class; needs: class on shcs()/add_screw; false alarms L; effort S |
| FST-002 | **Size the screw to the joint: preload must exceed the working load with margin; prefer a longer clamp length.** 0.75 x proof x n >= 2 x separating load; material under the head 1 to 3 d thick and bolt spacing 3 to 5 d (Slocum); self-loosening moment about preload x pitch / 2 (NASA-STD-5020B) **Corrected:** clamped length >= 3 d where vibration matters (recalled) -> material under the head 1 to 3 d (Slocum 9-10). | loaded joints. info: few printer joints are strength-limited | RECALLED, BOSSARD, SLOCUM9, NASA5020 (document, med) | **not checked**: AGENT.md: 'Bolt preload and contact' not checked | joint force from FEA reactions / load cases against n x preload; needs: loads per joint; false alarms M; effort L |
| FST-010 | **Minimum thread engagement by tapped material.** Bossard (coarse thread, 8.8 / 10.9 / 12.9): S235 steel 1.0 / 1.25 / 1.4 d; grey iron GJL 250 1.0 / 1.25 / 1.4 d; AlMgSi1 F32 (Rm > 330) 1.4 / 1.6 d / not tabulated; AlMg3 F18 (Rm > 180) 2 d (VDI formula 3 d); standard nut = full strength. Proposed checks: 6061 / 6082 (Rm about 290 to 310, just under F32's 330): ERROR below 1.5 d, WARNING 1.5 to 2 d on load-bearing or frequently removed joints and for 10.9 / 12.9 screws (no Bossard row for 12.9 in aluminium); soft aluminium (6063 extrusion, cast plate MIC-6 / ATP-5, 5052): ERROR below 2 d; plastic: 2 d or an insert; a catalogue part's own tapped hole follows its maker *Bossard's trials cover M6 to M16 (6g / 6H); not validated for M2.5 to M5 (MISSING.txt 5). Slocum: engagement of 1 d already matches bolt tensile strength in a same-strength section. SOURCES DISAGREE: Nord-Lock 2 d and Tameson 2 to 2.5 d for 'aluminium' (snippets) vs Bossard 1.4 d for strong Al and 2 d for soft Al. The extrusion alloy of the 2020 profile is not in the repo's vendor record.* **Corrected:** aluminium 2.0 d (Nord-Lock snippet; mechloop 1.5 d) -> by alloy strength per Bossard: 6061/6082 error < 1.5 d, warning 1.5 to 2 d; soft Al (6063, MIC-6, 5052) error < 2 d. | screws into tapped holes; T-nuts and catalogue tapped holes exempt. error: stripped threads | NORDLOCK, TAMESON, HUBSCNC, BOSS_TE, SLOCUM9 (document, high) | **already checked**: interference: thread_engagement, thread_bottoms_out (1 d steel, 1.5 d aluminium, 2 d plastic) | already; consider 2 d for aluminium and 1.5 d for brass; false alarms L; effort S |
| FST-011 | **Do not thread deeper than the thread can use.** engagement <= 3 d | tapped holes. warning: cost, broken taps | HUBSCNC (fetched, high) | **already checked**: manufacture: cnc.thread_depth_ratio |  |
| FST-012 | **Blind tapped holes need run-out below the thread; the screw must not bottom.** unthreaded depth >= 1.5 d below the last full thread (taps under M6); screw tip >= 1 pitch short of the bottom | blind tapped holes. error if the screw bottoms (no clamp), warning for run-out | HUBSCNC, SPIROL (fetched, high) | **already checked**: manufacture: cnc.blind_tap_runout_d_ratio; interference: thread_bottoms_out (catalogue holes) |  |
| FST-013 | **Use a threaded insert or a nut where a soft material is assembled repeatedly.** plastic or soft aluminium + a screw that is removed in service (wear part, cover) => insert or through-bolt with nut | threads in plastic, cast plate, 5052. warning: thread wears out | RP1228, CNCK, SPIROL (fetched, high) | partly: manufacture: fdm.thread_wall_d_ratio (insert guidance text) | threads_into plastic and screw on a declared service item; needs: service list (ASM-040); false alarms L; effort S |
| FST-020 | **Clearance holes to ISO 273; choose the class deliberately.** ISO 273 fine / medium / coarse: M2.5 2.7/2.9/3.1, M3 3.2/3.4/3.6, M4 4.3/4.5/4.8, M5 5.3/5.5/5.8, M6 6.4/6.6/7, M8 8.4/9/10 (H12 / H13 / H14); Bossard's torque and pressure tables assume medium; larger than coarse => washer (FST-031); chamfer the hole edge under the head (MMCC note) **Corrected:** table values recalled -> confirmed unchanged from the MMCC ISO 273 table (read from the scan). | clearance holes in made parts. info (class), warning (under fine, or over coarse without a washer) | ISO273, RECALLED, MMCC273, BOSS_TQ (document, high) | partly: tolerance: pattern start (p_all_start); parts.clearance_hole() gives one 'close' value, unverified | measure each hole around each screw (tools/practice_audit.py does); false alarms L; effort S |
| FST-030 | **Keep the pressure under the head and the nut below what the clamped material can carry.** p = FM max / Ap <= pG. pG (VDI 2230:2015, short-term, room temperature): S235 mild steel 490 MPa (1986 table: St 37 260), stainless X5CrNiMo 630, AW-6082 T6 (Rm 290) 360 -> used for 6061-T6 (mapped), AW-5083 325, cast GK-AlSi9Cu3 (Rm 160) 200 -> used for MIC-6 cast plate (mapped, derived), 70 % of pG where no indentation is permitted; power screwdriver up to -25 %, chamfered hole up to +25 % (steels). FM max from Bossard at mu 0.14 for the declared class (8.8 assumed when none: M3 2436 N, M5 7.0 kN) *SOURCES DISAGREE: VDI 2230 1986 (St 37 260) vs 2015 (S235 490): both recorded, 2015 used. MIC-6 and 6061 are not in the table: the mapping to the nearest alloy by tensile strength is ours, labelled derived.* **Corrected:** limit = yield of the clamped part (6061 276, MIC-6 105, steel 250); preload = recalled torque / (0.2 d) (M3 2167 N, M5 5700 N) -> limit = VDI 2230:2015 pG (6061 360 mapped, MIC-6 200 mapped, mild steel 490); preload = Bossard FM max, 8.8, mu 0.14 (M3 2436 N, M5 7000 N). | all clamped parts. warning: embedding and preload loss | PLASTCREEP, BOSSARD, BOSS_SP, BOSS_SP, BOSS_SP, BOSS_SP, BOSS_TQ (document, med) | **not checked** | preload from class torque, area from head and measured hole; needs: torque or class; false alarms M; effort M |
| FST-031 | **Plain washer under any head or nut that sits on a slot, an oversize hole, a soft or painted surface.** slot or hole larger than ISO 273 coarse, or head face supported < 80 % => washer. ISO 7089 (ID min / OD max / t): M3 3.2 / 7 / 0.5, M4 4.3 / 9 / 0.8, M5 5.3 / 10 / 1.0; ISO 7093 large: M3 3.2 / 9 / 0.8, M4 4.3 / 12 / 1.0, M5 5.3 / 15 / 1.2; ISO 7090 starts at M5, ISO 7093-1 at M3 **Corrected:** ISO 7089 dims from FreeCAD CSV; ISO 7093 not fetched -> ISO 7089 confirmed (RC); ISO 7093 added (M3 9 mm, M5 15 mm OD). | slots, oversize holes, printed and thin parts. warning: head digs in, adjustment creeps, joint loosens | ISO7089, RECALLED, RC_WASH, RC_WASH, SLOCUM9 (document, high) | **not checked** | supported fraction of the head annulus on the first clamped part; needs: washer catalogue part; false alarms L; effort S |
| FST-032 | **Washer under the element that is turned on aluminium (anodised or bare) and on coated parts.** nut or head rotated against aluminium / paint => washer, to keep friction repeatable and the coating intact | aluminium, anodised, painted. info | RECALLED (recalled, med) | **not checked** | material of the bearing part + which end is turned (the one with tool access); false alarms M; effort S |
| FST-033 | **Countersinks only in sheet thick enough to keep a cylindrical land.** sheet >= 3.18 mm for a countersink (SendCutSend); head height <= 60 % of t (recalled) | sheet parts. warning | SCS (repo, med) | **already checked**: manufacture: sheet.countersink_min_thickness_mm |  |
| FST-034 | **Leave enough floor under a counterbored head.** material under a head (counterbore floor, thin flange) typically 1 to 3 d thick (Slocum); below 1 d check FST-030 on the floor **Corrected:** floor >= 0.6 d (recalled) -> >= 1 d (Slocum, 'typically'). | counterbores. warning | RECALLED, SLOCUM9 (document, med) | partly: manufacture: cnc floor / wall minimums (0.5-0.8 mm only) | thickness of the first clamped interval when the head is recessed; false alarms M; effort S |
| FST-040 | **State a tightening torque for every structural joint; derive it from class, friction and the weakest clamped material.** torque from Bossard (VDI 2230:2015, 90 % of yield, max, no safety factor) at mu 0.14 (zinc-plated, the lower end of 0.14 to 0.24): class 8.8 M2.5 0.81, M3 1.41, M4 3.3, M5 6.5 N.m; 12.9 M3 2.37, M5 11.2 N.m; at mu 0.10: M3 8.8 1.12, M5 8.8 5.2 N.m; minimum preload = FM max / alphaA, alphaA 1.6 to 2.0 for a hand torque wrench; reduce to the FST-030 / PRT-030 limit on soft parts; rail bolts per Hiwin (M3 0.98 N.m in aluminium) *Friction: the screws' finish is not declared (black-oxide socket screws are not in the Bossard example); 0.14 is used as the lowest practical value Bossard tells the user to assume. SEW (snippet) uses 0.09 for 10.9 / 12.9.* **Corrected:** 8.8 torques M2.5 0.7, M3 1.3, M4 2.9, M5 5.7 N.m (recalled, mu about 0.14) -> M2.5 0.81, M3 1.41, M4 3.3, M5 6.5 N.m (Bossard mu 0.14); preload taken directly from the table, not from T / 0.2 d. | all screws. info: documentation | BOSSARD, RECALLED, BOSS_TQ, BOSS_TQ, BOSS_TQ, HIWIN_INST (document, high) | **not checked** | generate a torque table per screw group into BUILD.md; false alarms L; effort M |
| FST-041 | **Do not design a joint that only works at an exact preload.** hand torque scatter +/-35 % (feel), +/-25 % (torque wrench): a joint must work between 0.65 and 1.35 of nominal preload | friction joints. info | RP1228, BOSS_TQ (fetched, high) | human review | could bracket friction-joint checks (STR-014) with 0.65x preload; effort M; review checklist |
| FST-050 | **Edge distance and pitch of fastener holes.** hole centre to edge: nominal 2 d, minimum 1.5 d (NASA RP-1228); Bossard's recommended minimum edge distance c: M4 6, M5 7.5 mm (= 1.5 d); pitch 4 d nominal (NASA), 3 to 5 d (Slocum) | metal parts; plastics want more (>= 2 d, recalled). warning: tear-out, bulged edge | RP1228, BOSS_SP, SLOCUM9 (fetched, high) | partly: manufacture: sheet.hole_to_edge_t_ratio (1 t of web: a cutting rule, not a strength rule), fdm.thread_wall_d_ratio | distance from each screw axis to the nearest boundary of each clamped part; false alarms M; effort S |
| FST-051 | **A joint needs two fasteners, or one fastener plus a feature that stops rotation.** parts joined by one screw also share a pin, key, shoulder, rib-in-slot or a second screw: 'To resist rotation, a moment, or two forces acting as a couple, is required' (Slocum); one screw is one force on a line | all joints except pivots / axles. warning: the part swings on its screw under vibration | RECALLED, BOLTSCI, SLOCUMFP (document, med) | **not checked** | screws per part pair; then look for a second contact that blocks rotation about the screw axis (or a declared join); needs: 'axle' / 'keyed' join kinds exist; false alarms M; effort M |
| FST-052 | **Do not carry a sustained or alternating shear load on screw friction through clearance holes or slots when a shoulder, pin or hook can carry it.** service load across a slotted / clearance joint <= mu (0.15) x preload x 0.65 / 2; otherwise add a positive stop (jack screw, pin) | belt tension anchors, motor mounts on slots, sliding mounts. warning: slip is what loosens screws | BOLTSCI, RP1228, SLOCUM9 (fetched, med) | **not checked** | belt tension and declared loads against friction capacity of the screws in slots; credit a jack screw that touches the part; needs: load per sliding joint; false alarms M; effort M |
| FST-060 | **Nuts and tapped parts must sit on the threaded part of a partially threaded screw; the plain shank must be shorter than the grip.** ISO 4762 / DIN 912 thread length b: M2.5 17, M3 18, M4 20, M5 22, M6 24, M8 28 mm (Westfield); fully threaded up to M3 x 20, M4 x 25, M5 x 25, M6 x 30, M8 x 35 and partly threaded above, with lg max = l - b (Aramfix DIN 912 matrix); every nut / tapped interval must start at least lg below the head **Corrected:** b and full-thread lengths recalled / from the FreeCAD CSV -> confirmed unchanged (Westfield b; Aramfix full-thread rows). | long cap screws, studs made from screws. error: cannot be assembled as drawn | ISO4762, RECALLED, WESTFIELD, ARAMFIX (document, high) | **not checked** | thread zone per screw against each threaded target's interval along the axis; needs: b per size in the catalogue (already in vendor_docs CSV); false alarms L; effort S |
| FST-061 | **Use stocked lengths and sizes.** length in the preferred series; for lengths beyond the DIN 912 matrix rows (M3 > 30, M5 > 50) name a supplier: Lederer stocks stainless A2 / A4 M3 to 60 and M5 to 100 mm (M3 x 50, M5 x 90 included), in class 70 / 80, not 12.9 *A definitive ISO 4762 length range is not verified (MISSING.txt 3).* **Corrected:** M3 x 50 and M5 x 90 'outside ISO 4762's range (M3 5-30, M5 8-50)': warning -> beyond the DIN 912 matrix but stocked in A2 / A4 (Lederer): info, with the strength class to declare. | all screws. warning: lead time, substitution | ISO4762, ARAMFIX, LEDERER (document, med) | partly: interference STANDARD_LENGTHS_MM (used for bottoming only); ratings BOM | table lookup; false alarms L; effort S |
| FST-062 | **Thread should show past a nut, but not far.** thread through a prevailing-torque (self-locking) nut: at least two threads (NASA-STD-5020B); through a plain nut: at least one pitch (recalled); not more than about 3 d unless an adjuster **Corrected:** 1 pitch (2 in aerospace practice, recalled) -> 2 threads for self-locking nuts (NASA-STD-5020B p.86); 1 pitch for plain nuts stays recalled. | screw + nut joints. info / warning (flush or short: nut not fully engaged) | RECALLED, NASA5020 (document, high) | partly: interference: nut counted full strength once the screw passes through | tip position against the nut's far face; false alarms L; effort S |
| FST-063 | **Threads out of the shear plane.** in a joint loaded in shear the plain shank, not the thread, crosses the interface | shear joints with loads near capacity. info | RP1228 (fetched, high) | human review | needs FST-060 data plus a load; low value for a printer; effort M; review checklist |
| FST-064 | **A screw threads into one part only.** 'Both parts should NEVER have threaded holes because the threads will not be in phase' (Slocum): at most one tapped part (or one nut) per screw | all screws. warning: the joint cannot clamp | SLOCUM9 (document, high) | **not checked** | threads_into lists more than one non-nut part, or the core probe finds material of two parts; false alarms L; effort S |
| FST-070 | **Every fastener on a vibrating or moving assembly has a declared locking provision.** every fastener on a moving or vibrating assembly has a locking feature that does not depend on preload: prevailing-torque nut (nyloc / all-metal) or thread adhesive (NASA-STD-5020B TFSR 16 states it for spaceflight; adopted here as practice). Serrated flanges and jam nuts depend on preload: accepted only where preload is assured (metal seats), never as the only feature on plastic seats **Corrected:** serrated flange listed as a full locking provision -> serrated / free-spinning features depend on preload (NASA): not accepted alone where the seat creeps. | screws on moving bodies, motors, pulleys, bed, anything that sets an adjustment. warning: a printer vibrates for thousands of hours | BOLTSCI, BOLTSCI, RP1228, NASA5020, NASA5020, SLOCUM9 (document, high) | **not checked** | per screw: body is moving or a motor is in the joint, and no locking attribute; needs: add_screw(..., locking='nyloc'\|'adhesive'\|'serrated'\|None) and nyloc / serrated catalogue parts; false alarms M; effort S |
| FST-071 | **Do not specify split (helical spring) lock washers as a locking device.** no split lock washers in the BOM | all. warning | RP1228, BOLTSCI, NASA5020, NASA5020 (fetched, high) | **not checked** | BOM scan; false alarms L; effort S |
| FST-072 | **Nylon-insert nuts: temperature and reuse limits.** nylon locking element <= about 120 degC (250 degF); replace after a few reassemblies; near the hotend or under the bed use all-metal locknuts or adhesive rated for the temperature | locknuts near heat (bed 80-100 degC, hotend). warning | RP1228 (fetched, high) | **checked**: practice FST-072 (service temperature declared on the parts) | distance to el.hot_parts and the thermal estimate; needs: locking attribute (FST-070); false alarms L; effort M |
| FST-073 | **Thread adhesives (anaerobic) attack some plastics; keep them off ABS, PC, PETG parts.** adhesive locking only where the screw touches metal alone; for screws through plastic use nylocs or serrated flanges | screws through printed parts. info | RECALLED (recalled, med) | **not checked** | locking='adhesive' and a plastic in the stack; needs: locking attribute; false alarms L; effort S |
| FST-074 | **Tooth / star washers scratch the seat: use them for earth bonding, not as a general lock on finished or highly stressed parts.** star washers only at protective-earth points | all. info | RP1228, NASA5020 (fetched, high) | partly: electrical: earth_point product text (ring terminals and star washer) | BOM scan; false alarms L; effort S |
| FST-080 | **Standardise fasteners and tools.** target <= 2 thread sizes and <= 3 lengths per size on the main assembly; one drive type; count distinct SKUs and tools and report | whole machine. info: build time and mistakes | RECALLED (recalled, med) | partly: assemble / score: fastener_types, tool_changes (reported, no threshold) | count; suggest merges (a length only used <= 4 times with a neighbour that fits); false alarms L; effort S |
| FST-081 | **Avoid look-alike fasteners that are not interchangeable in the same area.** two lengths of one size differing by <= 2 mm where the shorter one is needed to avoid bottoming (e.g. M3x6 next to M3x8 into 3.5 mm-deep block threads) => warn, key or segregate | catalogue tapped holes with a maximum depth. warning: the wrong screw jams a guide block or cracks a motor end bell | RECALLED (recalled, med) | **not checked** | per sub-assembly: would the next longer SKU in the BOM bottom out here?; false alarms L; effort S |
| FST-090 | **Screws driven straight into printed plastic are for one-time, low-load joints.** no machine screw threaded directly into a printed part where the joint is structural or re-opened; use insert, captive nut or through-bolt | printed parts. warning | CNCK, CNCK (fetched, high) | **checked**: practice DG-04 (owner's rule, stricter); interference thread_engagement (2 d in plastic); manufacture fdm.thread_wall_d_ratio | threads_into a plastic part; false alarms L; effort S |
| FST-091 | **Heat-set inserts: hole, depth and wall.** straight hole to the insert maker's figure (ruthex RX-M3x5,7: 4.0 mm, wall W min 1.6; RX-M5x9,5: 6.4 mm, W 2.6); blind depth insert length + 2 pitches (SPIROL) (CNC Kitchen: about 1 mm deeper); boss 2 to 3 x insert diameter (SPIROL); install flush (subflush = jack-out) *SOURCES DISAGREE on boss size: ruthex's minimum wall (M3: 4.6 + 2 x 1.6 = 7.8 mm boss, 1.7 x d1) vs SPIROL's optimum 2 to 3 x (9.2 to 13.8 mm). SPIROL strength data are for nylon test plastics and its own inserts; not ratings for printed PETG / ABS (MISSING.txt 7).* **Corrected:** M3 hole 4.0 (snippet), wall >= 0.5 x insert OD (snippet), depth +1 mm -> ruthex hole and W min per size; depth +2 pitches (SPIROL). | inserts in printed parts. warning | CNCK, INSERTS, RUTHEX, SPIROL, SPIROL, SPIROL (document, med) | **not checked** | insert catalogue part with hole / wall data; measure the boss; needs: heat_set_insert() part; false alarms L; effort M |
| FST-092 | **Put the insert or captive nut on the side where the load pulls it INTO the part.** screw tension must seat the insert / nut against plastic, not draw it out of its hole | inserts. warning: pull-out | RECALLED, SPIROL, SPIROL (recalled, high) | **not checked** | insert on the far side of the clamped stack from the screw head = good; same side = pull-out; needs: insert part; false alarms L; effort S |
| FST-093 | **Captive nut pockets: closed against rotation, open for insertion, with plastic behind the nut.** pocket across flats = nut AF + 0.2 to 0.4 mm; >= 2 mm (or 0.6 d) of plastic between nut face and the clamped interface; nut insertable in the assembled state or retained | printed parts with nut pockets. info | RECALLED (recalled, med) | partly: interference (nut overlap), assemblability (nut has a path in) | measure the pocket around each nut inside a printed part; false alarms M; effort M |
| FST-100 | **Say which T-nut: slide-in nuts must be in the slot before the slot end is closed; drop-in / roll-in nuts for anything added later.** each T-nut SKU names its type; a slide-in nut in a slot whose both ends are blocked at that assembly step is an error | T-slot extrusions. error for trapped slide-in nuts, else info | RECALLED (recalled, high) | **not checked**: T-nuts are BOM lines, not geometry (AGENT.md) | slot ends blocked at the step where the screw is fitted (assembly order exists); needs: T-nut type + position; false alarms M; effort M |
| FST-101 | **A part on T-nuts wants two of them (or a key in the slot); a single T-nut pivots and slides.** parts held to an extrusion by one T-nut screw need a second constraint; loads along the slot are carried by friction only (FST-052) | T-slot joints. warning | RECALLED (recalled, high) | **not checked** | T-nut screws per part; false alarms L; effort S |
| FST-102 | **Tapped extrusion ends: tap the core hole to depth, deburr, and back the joint with a bracket where it carries moment.** end tap M5 in the 2020 core hole: engagement >= 2 d if the profile is 6063-class (Bossard AlMg3 F18 row, Rm > 180, mapped); a blind butt joint on one screw also needs an anti-rotation feature **Corrected:** 2 d in 6063 (recalled) -> 2 d by Bossard's soft-aluminium row (mapping derived). | extrusion butt joints. info | RECALLED, BOSS_TE (document, med) | partly: interference thread_engagement; fea AssemblyCase lower bound | FST-051 on extrusion ends; false alarms L; effort S |
| FST-110 | **Mind galvanic pairs where moisture can stand.** indoors dry: stainless or zinc-plated steel in aluminium is accepted; avoid bare carbon steel sheet against aluminium without a finish; give laser-cut mild steel a finish (paint, zinc, oil) | mixed-metal joints. info | RP1228, SCS (fetched, med) | **not checked** | material pairs in contact + declared finish; needs: finish attribute; false alarms M; effort S |
| FST-111 | **An earth bond through anodised or painted metal must break the coating.** serrated washer or scraped seat at every protective-earth joint; anodised extrusions are not bonded to each other by their brackets unless shown | PE joints. error if a PE path relies on anodised contact | RECALLED, IEC60204, IEC_JMF (document, med) | partly: electrical: earth_point; builder_work text | PE continuity graph over metal parts with joint conductivity flags; needs: finish per part; false alarms M; effort L |

### locating and constraint (LOC)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| LOC-001 | **Exact constraint: count what holds each body; make every redundant constraint compliant, floating or adjusted.** per body: bearing reaction points = 6 - DOF (Slocum 3-36); each extra one needs a declared float / flexure / adjustment, or deliberate elastic averaging | axes. warning: binding, wear | SLOCUM, RECALLED, SLOCUMFP (document, high) | partly: fea.bed_support constraint / z_over_constrained; tolerance two-rail and screw-to-rail checks | generalise the bed-support constraint count to X and Y; false alarms M; effort L |
| LOC-002 | **Two parallel rails: one is the master against a reference edge, the other is set parallel to it at assembly and then locked.** allowable non-parallelism MGN12: 9 um (ZF / Z0), 5 um (Z1): only reachable by setting the slave rail with the carriage as gauge | two-rail axes. warning | HIWIN, HIWIN_SNIP (repo, high) | **already checked**: tolerance: two rails parallel; Adjustment rail_align |  |
| LOC-003 | **A lead screw must not also be a guide: float the nut or the far end.** nut radial float >= 99.7 % misalignment of screw to rails; do not fix both screw ends rigidly AND the nut | screw-driven axes. warning | RECALLED (recalled, high) | **already checked**: tolerance lead_screws; Adjustment float |  |
| LOC-004 | **Screws clamp, they do not locate: use dowels, shoulders, ribs-in-slots or a tight pattern where position matters.** screws clamp; 'Bolts and screws DO NOT themselves take shear loads, unless you use a shoulder bolt' (Slocum); a position requirement tighter than the clearance (M3 medium 3.4 - 3.0: +/-0.2 mm) needs a locating feature or an adjustment | joints in a tolerance chain. info | RECALLED, SLOCUM9, MMCC273 (document, high) | partly: tolerance: joint play of screws is simulated; adjustments credited | list joints whose play dominates a failed stack-up and that have no locating feature; false alarms M; effort M |
| LOC-005 | **Two-pin location: one round hole and one slot aimed at it.** a part located by two pins / tight screws: second feature is a slot along the line of centres, never two tight round holes more than a few d apart | pinned parts. info | RECALLED (recalled, high) | **not checked** | needs pins as parts; needs: dowel_pin() part and 'pin' join; false alarms L; effort M |
| LOC-006 | **Every adjustment has (a) a controlled way to move it, (b) a lock that does not disturb it, (c) tool access in the finished machine.** Adjustment declares mover (jack screw, nut pair, slot by hand), lock (screws, jam nut, adhesive) and is reachable at the assembled pose | all declared adjustments. warning: an adjustment that drifts or cannot be reached is not one | RECALLED (recalled, high) | **not checked**: Adjustment has name, kind, range only | Adjustment(lock=[screw names], mover=...): locks must exist, be FST-070-locked, and pass driver access in the FINAL assembly, not only at their own step; needs: two fields on Adjustment; false alarms L; effort M |
| LOC-007 | **Allow thermal growth: one fixed point, the rest free to slide or flex.** alpha dT L (aluminium plate 23.6e-6 /K per mechloop/parts/vendor/cast_tooling_plate.json: 0.3 mm on 220 mm at 60 K) taken by slots / flexures; 'an exactly constrained design has no chance of deforming [...] by thermal expansion' (Slocum) | heated beds. warning | RECALLED, SLOCUMFP (repo, high) | partly: fea ThermalCase (bow, gap); AGENT.md 'fixed at one point and free to grow at the others' | bed held at more than one rigid point without a declared flexure; false alarms M; effort M |
| LOC-008 | **Abbe: keep the working point close to the guide and the drive in line with the mass centre and friction.** offset nozzle-to-rail and belt-to-centre-of-mass as small as layout allows; report the arms | carriages. info | SLOCUM, SLOCUMFP (document, high) | partly: twin: toolhead tilt spring from block spacing and nozzle distance; fea.bed_support screw offset | report arms; no threshold; effort S |
| LOC-009 | **Bearing spacing against overhang (Saint-Venant / 'golden' proportion).** linear guides: spacing / width L/D > 1 (below it machines jam), 1.6 very good, 3 'awesome' (Slocum 3-7) **Corrected:** L/D 1 / 1.6 / 3 (snippet) -> same, from the document. | carriages on one rail. warning below 1 | SLOCUM, SLOCUMFP (document, high) | partly: ratings: cantilever_on_guide_blocks; fea z_guides_bind | ratio from block positions and tool point; false alarms M; effort S |
| LOC-010 | **Short, closed structural loop between tool and work.** human review of the path nozzle - gantry - frame - Z - bed | machine. info | RECALLED (recalled, med) | human review | review checklist |
| LOC-011 | **Locate both members of a critical pair from the same part / the same set-up.** shortest chain between two features that must align | tolerance chains. info | HUBSCNC (fetched, high) | **already checked**: tolerance: chains; hints 'locate both parts from one part' |  |

### bearings and shafts (BRG)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| BRG-010 | **Fit by load direction: the ring that sees a rotating load gets the tight fit.** rotating inner ring under a stationary load: inner ring interference fit, outer ring loose (SKF table 1); shaft up to 17 mm under light load js5 (h5), normal load up to 10 mm js5 (SKF table 2); housing H7-class loose **Corrected:** shaft j5-k5, housing H7 (recalled) -> js5 (h5) for an 8 mm shaft under light load (SKF). | rolling bearings. info | RECALLED, SKFINST, SKFINST (document, high) | partly: tolerance: shaft_bore_pairs, design.join(a, b, 'press') | require a declared fit for each ring; false alarms L; effort S |
| BRG-011 | **A printed bearing seat is a locating pocket, not a press fit that lasts.** bearing in plastic: retain axially by shoulder + cover / screw / circlip; do not count on interference (creep) and expect 0.1-0.3 mm radial play in a 'sliding' printed seat | bearings in printed parts. warning | RECALLED, PLASTCREEP, PETGCREEP, SKFINST (recalled, med) | **not checked** | bearing whose seat part is plastic: BRG-020 on both sides + radial clearance drawn; false alarms L; effort S |
| BRG-020 | **Retain the locating bearing axially in BOTH directions, on both rings.** each ring of the locating bearing has a shoulder, sleeve, circlip, cover or collar on both faces; the load path for axial force in each direction is drawn | shafts carrying axial load. warning (error when a declared axial load has no path) | BEARARR, RECALLED, SKFINST, SLOCUMFP (document, high) | **not checked**: AGENT.md 'axial retention of bearings' not checked | probe the annulus above / below each ring for an abutting part (tools/practice_audit.py does); false alarms M; effort S |
| BRG-021 | **One locating bearing per shaft; the other floats.** exactly one bearing constrained axially both ways; the other free on one ring (thermal growth, no fight) | two-bearing shafts. info | BEARARR, SLOCUMFP, SKFINST (document, high) | **not checked** | from BRG-020 results per shaft; false alarms M; effort S |
| BRG-022 | **Axial load on a deep-groove ball bearing stays a fraction of its static rating.** pure axial load <= 0.5 C0; small bearings (bore up to about 12 mm) and light series <= 0.25 C0 (SKF). 608: C0 1.37 kN -> 342 N *SKF's basic ratings are not permissible service loads without life, speed, fit and lubrication checks (README).* **Corrected:** 0.5 / 0.25 C0 recalled, unconfirmed -> confirmed: 608 is a 'small bearing', 0.25 C0 = 342 N. | ball bearings used as thrust. info | RECALLED, SKFCAT, SKF608 (document, high) | partly: ratings: guide loads against catalogue ratings ('typical') | axial share of the joint load per bearing; false alarms L; effort S |
| BRG-023 | **Axial load goes through a shoulder, collar or circlip, not through set-screw friction or a press fit.** axial load through a shoulder, collar, circlip or nut; a set-screwed hub in the path is a warning. Capacity of a cup-point set screw on a plain steel shaft (Rc 15 to 35 / HRB 80 to 100): M3 0.71 kN (Unbrako, 0.87 N.m) to 0.88 kN (Holo-Krome, 1.0 N.m), +/-30 %; on a thread or a soft shaft no data *The capacity on a proper shaft is large against a printer's loads; the objection is the seat (thread, unhardened stainless) and creep of the hub's preload, not the number.* | lead screws. warning: slips in service, slowly | RECALLED, MDSET, HOLO, UNBRAKO (document, med) | **not checked** | axial path from nut to frame: joins of kind set_screw / press on it; false alarms L; effort M |
| BRG-024 | **What abuts a bearing ring stays inside that ring's abutment diameters.** 608: parts on the shaft side abut between da min 10 mm and the inner ring's shoulder d1 about 12.15 mm (ra max 0.3); housing side up to Da max 20 mm (SKF); a pulley hub, collar (Ruland MCL-8 18 mm OD) or nut wider than d1 rubs the shields / cage: put an 8 x 12 shim washer between | anything seated on a bearing ring. warning: rubbing shield, preload on the wrong ring | SKF608, RULAND (document, high) | **not checked** | diameter of the contact annulus between each ring face and the abutting part (practice_audit measures it); needs: abutment data in the bearing catalogue; false alarms L; effort S |
| SHF-010 | **Set screws bear on a flat (or dimple), two at 90 degrees, and are locked.** hub on a shaft by set screws: M3 cup point at 0.87 to 1.0 N.m holds 0.71 to 0.88 kN axially, torsionally that x shaft radius (8 mm shaft: 2.8 N.m, Unbrako); two screws at 90 deg (Gates stock pulleys); flat or spot on the shaft for repeatable seating; thread adhesive *MISSING.txt 10: no controlled with-flat vs without-flat comparison; Machine Design's 6 % (snippet) remains the only figure. A flat-point screw (0.92 x cup) is not a flat on the shaft.* | pulleys. warning: the classic printer failure (layer shift) | GATES, MDSET, MDSET, HOLO, UNBRAKO (document, high) | **not checked**: v8 docstring: 'pulley set screws' not modelled | set_screw joins: does the shaft have a flat (catalogue attribute)?; needs: shaft flat on nema17(); set screw count on gt2_pulley; false alarms L; effort S |
| SHF-011 | **Never seat a set screw or a bearing on a thread.** bearing seats, set screws, circlips and collars need a plain journal: SKF js5 / h5 for an 8 mm seat; a DIN 471 ring needs a 7.6 mm groove 0.9 mm wide (impossible across a trapezoidal thread whose minor diameter is about 6 mm); a thread crest is neither **Corrected:** principle recalled -> document-backed (SKF fit, DIN 471 groove). | lead screws. warning: runout and a hub that cannot hold | RECALLED, SKFINST, DIN471, ELESA (document, high) | **not checked** | bearing or set-screw hub whose shaft part is a lead screw without a 'journal' interface; needs: leadscrew end-machining option; false alarms L; effort S |
| SHF-012 | **Keep overhung loads close to the bearing.** belt pull x overhang within the motor's radial limit; pulley as close to the face as possible | motor pulleys. warning | RECALLED (recalled, high) | **already checked**: ratings: motor_shaft_radial_load |  |
| SHF-013 | **Flexible couplings carry torque, not weight or thrust.** no axial load path through an elastomer / helical coupling | couplings. warning | RECALLED (recalled, high) | partly: interference: shaft_too_deep_in_coupler; v8 requirement 6 | BRG-023 path test; effort M |

### belts (BLT)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| BLT-010 | **At least 6 teeth in mesh on every load-carrying sprocket.** teeth in mesh = wrap/360 x teeth >= 6; for each tooth fewer (minimum 2) the torque rating falls 20 % *Same rule and KTM table in the legacy GT2 manual (document) and the current GT3-era manual (repo).* | all loaded pulleys (not idlers). warning with the derated rating; error under 2 teeth or when the derated rating is below the load | GATES, SDPSI, GATES_GT2L (document, high) | partly: motion: belt_low_wrap, but only for the pulley named in a joint's drive | apply to every non-idler pulley on the path; compare derated rating with the pulley's torque; false alarms L; effort S |
| BLT-011 | **At least 60 degrees of wrap on every loaded sprocket.** wrap >= 60 deg | loaded pulleys. warning | GATES, GATES_GT2L (document, high) | **not checked** | route() already returns wraps; false alarms L; effort S |
| BLT-020 | **Sprockets no smaller than the pitch's minimum.** 2MGT: check zmin in the maker's table (inside idler minimum 12 grooves); MXL: 10 teeth | pulleys. warning | GATES, GATESMEC, SDPSI (repo, med) | partly: catalogue offers fixed tooth counts | table; false alarms L; effort S |
| BLT-030 | **Idler type: tooth side gets a sprocket (or a flat idler >= 40-groove pitch diameter), the back gets a FLAT, uncrowned idler.** backside idler: smooth, uncrowned; inside flat idler OD >= 25.4 mm (2MGT) | idlers. warning: teeth on the belt's back wear the backing and make noise | GATES, GATES, SDPSI, GATES_GT2L (document, high) | **not checked** | wrap sense of each idler against the belt's tooth side; idler SKU toothed or smooth; needs: smooth idler catalogue part; tooth side on Belt; false alarms L; effort S |
| BLT-031 | **Idler diameters.** current GT3-era table 9 (2MGT GT3): backside idler OD >= 12.7 mm (0.50 in), inside idler >= 12 grooves, inside flat >= 25.4 mm; legacy GT2 manual: backside idler not smaller than 1.3 x the smallest recommended inside sprocket (12 grooves, 7.64 mm PD, if the GT3 minimum applies: 9.9 mm); SDP/SI: larger than the smallest drive pulley *SOURCES DISAGREE three ways; the legacy GT2 manual's 2 mm minimum sprocket was not found in its text (MISSING.txt 12), so the 9.9 mm figure borrows the GT3 table's 12 grooves.* **Corrected:** 12.7 mm (GT3 table, labelled as GT2) -> 12.7 mm (current GT3 table) or 9.9 mm (legacy GT2 rule with a 12-groove minimum). | idlers. warning | GATES, GATES, SDPSI, GATES_GT2L (document, med) | **not checked** | idler OD from the catalogue; false alarms L; effort S |
| BLT-032 | **Idlers and tensioners on the slack side, locked after tensioning; no spring idler on the tight side.** tensioner on the span leaving the driver in the unloaded direction; lock declared (LOC-006) | closed loops. info | GATES, SDPSI, GATES_GT2L (document, high) | **not checked** | for a reversing drive both spans are tight in turn: report only; effort S |
| BLT-040 | **Pulley diameter not smaller than the belt width.** pulley OD >= belt width | all pulleys. warning: tracking, edge wear | SDPSI (fetched, med) | **not checked** | catalogue OD against Belt.width; false alarms L; effort S |
| BLT-041 | **Flanges.** at least one flanged pulley per belt; both flanged when centre distance >= 8 x small pulley diameter or the shafts are vertical; open-ended belts: clamp alignment replaces a flange | belt drives. warning | SDPSI, GATES (fetched, high) | **not checked** | flange attribute of catalogue pulleys; axis direction against gravity; needs: flanged flag (pulley solids already have flanges); false alarms L; effort S |
| BLT-050 | **Belt tension is set to a number, with adjustment travel to fit and re-tension.** installation tension declared (Gates minimum per width; fixed-centre positioning Ti = 1.0-1.2 Te); centre-distance adjustment >= what fitting over flanges needs | belts. info | SDPSI, SDPSI, GATESMEC (fetched, high) | **already checked**: ratings: Belt.tension default from Gates; motion: belt_wrong_length against Belt.adjust |  |
| BLT-051 | **Pulleys in one plane, shafts parallel.** in-plane within 0.5 mm as drawn; under tolerance per the tolerance verifier | belts. error | SDPSI (fetched, high) | **already checked**: motion: belt_misaligned; tolerance: belts in plane |  |
| BLT-052 | **Open belt ends: clamp enough teeth, positively.** >= 6 teeth held in a toothed clamp or folded-back grip; no reliance on a zip tie alone | belt anchors. info | RECALLED (recalled, med) | **not checked**: Belt anchors are points | needs clamp geometry; needs: anchor length on Belt; false alarms M; effort M |
| BLT-053 | **Belt drive brackets must be rigid: centre distance must not change under load.** deflection of motor / idler mounts under 2 x tension small against tooth height (0.76 mm for 2 mm pitch): aim < 0.1 mm | motor and idler mounts. info | GATES, SDPSI, GATES_GT2L (repo, med) | partly: fea load cases if written | auto-generate an AssemblyCase per belt mount; false alarms M; effort L |

### lead screws (LSC)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| LSC-010 | **Stay below the screw's critical (whirl) speed.** n <= 0.8 x n_crit; n_crit grows with root diameter / L^2 and end fixity (fixed-free lowest) *Elesa gives n max = nk x fk x safety factor with nk from a diagram that is not readable as text; the formula's constants stay recalled.* | lead screws. info at printer Z speeds (12 mm/s on 2 mm lead = 360 rpm) | RECALLED, ELESA (recalled, med) | **not checked** | formula with catalogue root diameter and declared end fixity; needs: end fixity; false alarms L; effort S |
| LSC-011 | **Check the screw as a column when it is in compression.** Euler load with end fixity >= 3 x axial load | screws pushing a load. info | RECALLED, ELESA (recalled, high) | **not checked**: AGENT.md: buckling not checked | formula; needs: end fixity; false alarms L; effort S |
| LSC-012 | **Support the driven end of a screw so that it cannot whip or lift; a free far end is acceptable for short Z screws.** a screw held only at its driven end (top free) acts as a cantilever: its two bearings need spacing / diameter L/D > 3 (Slocum 3-7: 'L/D > 3 if the bearings are to act to constrain the shaft like a cantilever'), retained per BRG-020 **Corrected:** bearing spacing >= 3 x shaft diameter (recalled) -> L/D > 3 (Slocum). | lead screws. warning | RECALLED, SLOCUMFP (document, high) | **not checked** | bearing spacing on the screw / diameter; false alarms L; effort S |
| LSC-013 | **Know where backlash goes: gravity-loaded nuts are fine until something lifts the bed.** nut preloaded by weight only: upward force (crash, sticking print removal) must not unseat nut, screw or bearing | Z axes. info | RECALLED (recalled, med) | human review | BRG-020 in the upward direction covers the mechanical part; review checklist |
| LSC-014 | **A vertical axis must not fall at power-off.** self-locking screw (efficiency < 0.5, i.e. lead angle below the friction angle) or a brake | vertical axes. warning | RECALLED, ELESA (document, med) | **not checked** | catalogue efficiency of the screw; false alarms L; effort S |
| LSC-015 | **Several screws driving one body: budget their lead difference.** rolled trapezoidal screws: lead deviation up to 0.1 mm / 300 mm, straightness 0.3 mm / 300 mm (Elesa GN 103; igus DryLin TR, same figures). Two screws tied by a belt can differ in height by up to 2 x 0.1 x travel / 300 over the travel; the support must tolerate it (float, compliance) or the firmware must re-level *Maker figures for their own screws; no figure exists for generic T8 screws (MISSING.txt 13), which are unlikely to be better.* | multi-screw Z. warning | ELESA, ELESA, IGUS_DRYLIN (document, med) | **not checked**: fea.bed_support screw_synchronisation assumes 0.02 mm | replace the assumed 0.02 mm by the maker's lead deviation over the declared travel; needs: lead accuracy on leadscrew_t8(); false alarms L; effort S |

### linear guides (LIN)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| LIN-010 | **Mounting shoulders and corner reliefs to the maker's table.** MGN12: rail-side shoulder H1 <= 1.7 mm with fillet r1 <= 0.3; block-side shoulder H2 <= 4 mm, r2 <= 0.4 | rails / blocks against shoulders. warning | HIWIN, HIWIN_INST (document, high) | **not checked** | geometry of the part beside the rail foot; false alarms M; effort M |
| LIN-011 | **Mounting surface flat and stiff enough for the rail.** mounting surface flatness MG_12: 0.050 / 200 mm (ZF, Z0), tighter for Z1 or two rails on one surface (Hiwin table 3.90); an extrusion face's straightness is not catalogued **Corrected:** 0.05 / 200 (snippet) -> confirmed (Hiwin table 3.90). | rail seats. info | HIWIN_SNIP, HIWIN_MGCAT (document, high) | **not checked**: AGENT.md: extrusion straightness not catalogued | process flatness class of the seat part; needs: straightness of extrusions; false alarms M; effort M |
| LIN-012 | **Bolt the rail at the maker's pitch; do not leave holes empty on a loaded rail.** every hole (MGNR12: 25 mm pitch, 10 mm end distance) for rated load and accuracy; every second hole only on lightly loaded axes, said explicitly | rails. info | HIWIN, RECALLED (recalled, med) | **not checked** | screws threading through the rail / holes in the rail; false alarms L; effort S |
| LIN-013 | **Rail and block bolts torqued to the maker's figure.** rail bolts tightened sequentially with a torque wrench: M3 1.86 N.m into iron, 1.27 into castings, 0.98 into aluminium (Hiwin table 11); block-to-carriage torque not verified (MISSING.txt 9); block threads 3.5 mm deep **Corrected:** about 1.9 / 1.0 N.m (snippet, row uncertain) -> 1.86 / 1.27 / 0.98 N.m (Hiwin table 11, rail bolts only). | guides. info | HIWIN_SNIP, HIWIN, HIWIN_INST (document, high) | partly: interference: thread_bottoms_out on the block | torque table (FST-040); effort S |
| LIN-014 | **A block must never run off its rail; fit end stops, and keep the block on a rail (or its plastic keeper) during assembly.** mechanical stop inside the rail end at both ends of every rail; assembly order never slides a block off | recirculating blocks. warning: balls drop out | RECALLED (recalled, high) | partly: motion: guide run-off over mechanical travel | a part that blocks the block within the rail length beyond mechanical travel; false alarms M; effort M |
| LIN-015 | **Use the rail's reference edge.** master rail's datum edge against a shoulder, pins or a straightedge at assembly | rails. info | HIWIN_SNIP, HIWIN_INST (document, med) | human review | review checklist |
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
| MCH-015 | **Break all machined edges.** edge break 0.2-0.5 mm chamfer or radius on all outside edges (ISO 13715 indication), stated on the drawing; chamfer hole entries that take screws or pins *ISO 13715 notation (+ passing, - undercut, +/- with size) is now documented; no universal edge-break size is given, and the maker summary's example B.7 is inconsistent (0.1-0.5 vs 0.1-0.3 mm). The 0.2-0.5 mm figure stays recalled.* | machined parts. warning | ISO13715, RECALLED, ISO13715M, ISO13715M, MMCC273 (recalled, high) | **not checked** | sharp convex edge length per part (tools/practice_audit.py does) or a declared edge note; needs: edge_break field; false alarms L; effort S |

### 3D-printed parts (PRT)

| Id | Rule and criterion | Applies / severity | Source (evidence) | mechloop today | How to check; needs; false alarms; effort |
|---|---|---|---|---|---|
| PRT-010 | **Orient layers so the load does not peel them.** principal tension not along the build direction *v8 checker note 5: it also fires on compression* | loaded prints. warning | HUBSFDM (fetched, high) | **already checked**: manufacture: fdm.layer_load_fraction (load_across_layers) |  |
| PRT-011 | **Holes print small: compensate, and ream or drill the ones that matter.** vertical holes about 0.15-0.4 mm under; critical bores (bearing seats, shafts, pins) get a 'ream / drill after printing' note | printed holes. info | HUBSFDM, STRATFDM (document, high) | partly: tolerance: printed holes 0.15 mm small | bearing / pin / axle bores in printed parts without a finishing note; needs: note field; false alarms L; effort S |
| PRT-012 | **Chamfer, not fillet, the edges on the build plate.** 45 deg chamfer 0.4-0.6 mm on bed-contact edges of mating faces (elephant's foot) | printed mating faces. info | HUBSFDM (fetched, high) | **not checked** | sharp convex edges lying on the print_up base plane of a part that mates on that face; false alarms M; effort M |
| PRT-013 | **Small printed pins and bosses are weak: use bought pins.** pins < 5 mm diameter: fillet at the base or replace with a dowel / screw | printed pins. warning | HUBSFDM (fetched, high) | partly: manufacture: fdm.feature_min_mm (2 mm) | ; effort S |
| PRT-014 | **Overhangs, bridges, horizontal holes.** overhang <= 45 deg; bridges clean to 5 mm; horizontal holes teardrop or <= 10 mm | prints. warning | HUBSFDM, HUBSFDM (fetched, high) | **already checked**: manufacture: fdm.overhang_angle_deg, fdm.bridge_*, fdm.horizontal_hole_max_mm |  |
| PRT-020 | **Enough plastic around holes, inserts and nuts.** minimum wall 4 x layer height (Stratasys: 0.25 mm layers -> 1.0 mm); around inserts the maker's W min (ruthex M3 1.6 mm); bosses supported by ribs / gussets; around screw holes >= 1 d stays recalled | prints. warning | CNCK, RECALLED, STRATFDM, RUTHEX, STRATFDM (document, med) | **already checked**: manufacture: fdm.thread_wall_d_ratio, wall_too_thin_to_print |  |
| PRT-030 | **Plastic creeps under a clamped screw: spread the load and do not rely on preload.** screw head / nut on printed plastic => washer AND, where preload matters, a metal sleeve (compression limiter) so the clamp load goes through metal. DERIVED sustained bearing limit for printed PETG / ABS: 5 MPa at up to 40 degC, 2.5 MPa from 40 to 60 degC, no sustained clamp above 60 degC or above HDT - 15 K. Derivation: PETG's linear viscoelastic region ends at 5.3 to 8.0 MPa (Romeijn, DMA, mean 6.5); the ABS creep study held 5 MPa to stay under 2 % strain; PETG creep compliance rises about 2.5-fold over 10 years at 23 degC; PETG's creep model is valid only to 60 degC *NO VALIDATED ALLOWABLE for printed PETG / ABS was found (Bossard's VDI tables are metals only; MISSING.txt 4 and 14). The 5 MPa figure is ours, labelled derived: it keeps the plastic in the linear range so creep stays predictable; it is not a strength. Test plastics differ: pellet-extruded PETG (not Prusament), Z-ABS (not ABS-M30).* **Corrected:** 0.3 x yield, sustained (recalled): PETG about 14, ABS about 12 MPa -> 5 MPa derived (2.5 MPa between 40 and 60 degC). | every screw through a printed part. warning: joints go slack over weeks, faster when warm | PLASTCREEP, PLASTCREEP, PETGCREEP, PETGCREEP, ABSCREEP, PRUSA_PETG, ABSM30 (derived, med) | **not checked** | first clamped part under head / nut is plastic and no washer or sleeve part (tools/practice_audit.py does); needs: washer part; optional 'limiter' sleeve; false alarms L; effort S |
| PRT-031 | **Keep sustained load and heat off low-temperature plastics.** sustained-load parts at <= HDT - 15 K: Prusament PETG HDT 68 degC at 0.45 and 1.80 MPa -> 53 degC; Stratasys ABS-M30 99.9 (1.82 MPa) to 103.8 degC (0.45 MPa) -> 85 degC; HDT is a short-term deflection temperature, not a creep allowable *Generic ABS filament is not ABS-M30; the design names 'abs'. PLA not covered.* **Corrected:** PETG about 70, ABS about 95 degC (recalled) -> PETG 68 (Prusament), ABS-M30 99.9 to 103.8 (Stratasys). | prints near heat. warning | RECALLED, PRUSA_PETG, ABSM30 (document, high) | partly: electrical thermal estimates (probe); v8 chose PETG / ABS by hand | material table with HDT against el.hot_parts and motor case temperature; needs: HDT per material; false alarms M; effort M |
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
| ELE-010 | **Protective bonding of every exposed conductive part that can become live.** protective bonding of exposed conductive parts; a protective conductor that is not part of a cable and not in a common enclosure with the line conductor >= 2.5 mm2 Cu if mechanically protected, >= 4 mm2 if not; metal frames used as protective conductors need continuity 'assured by construction or by suitable connection' against electrochemical deterioration; continuity verified (18.2.2 Test 1) **Corrected:** no conductor size (recalled continuity test current only) -> 2.5 / 4 mm2 Cu for separate PE conductors (IEC 60204-1 8.2.2 via IDEC). | mains-powered machines. error | IEC60204, RECALLED, IEC_JMF, IEC_JMF (document, med) | partly: electrical: earth wires to supply and earth_point | FST-111 continuity graph; effort L |
| ELE-011 | **Ferrules on stranded wire in screw terminals; ring terminals under screws; no tinned ends.** each stranded conductor in a screw terminal has a ferrule sized to the wire | screw terminals. warning | RECALLED (recalled, high) | partly: electrical: connectors / terminals per wire (twin ferrule text) | terminal kind per port; effort S |
| ELE-012 | **Segregate mains from low voltage; cover live terminals.** mains conductors apart from signal looms; live parts inside enclosures of at least IP2X / IPXXB (IEC 60204-1 6.2.2, web excerpt) | mains wiring. error | RECALLED, IEC_IP2X (document, med) | partly: electrical: mains safety checks | ; effort M |
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
| DOC-010 | **Edge-break note on every made metal part.** edge note on every made metal part in ISO 13715 form: '-' for a required undercut / break (e.g. -0.3 at every external edge), '+' for a permitted burr; the size is the designer's (no universal value in the documents) | made parts. warning | ISO13715, RECALLED, ISO13715M, ISO13715M (document, med) | **not checked** | field present; written into the part's fabrication sheet; needs: edge_break; effort S |
| DOC-011 | **General tolerance block.** ISO 2768-m (or the process class used by the tolerance verifier) stated per part; only tighter features called out | made parts. info | HUBSCNC, HUBSCNC (fetched, high) | partly: tolerance process classes exist but are not exported to a drawing / order sheet | ; effort M |
| DOC-012 | **Torque and threadlocker call-outs in the build instructions.** BUILD.md step for each screw group gives torque (FST-040) and locking (FST-070) | build docs. info | RP1228, RECALLED (recalled, high) | **not checked**: assemble writes BUILD.md without torques | ; effort M |
| DOC-013 | **Threads, fits and finishes called out.** tapped holes, press / slide fits and surface finish listed per part (a STEP file does not carry them) | made parts. info | HUBSCNC (fetched, high) | partly: manufacture knows the threads each screw needs | ; effort M |

### Sources

Levels: document = owner-delivered file in `vendor_cad/staging/practice_refs/` (quoted with page in `sources.yaml`); fetched / repo / snippet as in section 1.

| Key | Document | Level | Where |
|---|---|---|---|
| RP1228 | NASA Reference Publication 1228, Fastener Design Manual (R. T. Barrett, 1990) | fetched | https://ntrs.nasa.gov/api/citations/19900009424/downloads/19900009424.pdf |
| BOLTSCI | Bolt Science, Self-Loosening of Bolts and Nuts (vibration loosening) | fetched | https://www.boltscience.com/pages/vibloose.htm |
| GATES | Gates, Light Power and Precision Drive Design Manual (CURRENT, GT3-era: 2MGT GT3 belts on GT2 sprockets); the repo file vendor_docs/Gates_GT2_design_manual.pdf is this manual, also delivered as 12_Gates_light_power_precision.pdf (idlers p.70 [68], tensions p.67 [65]) | repo | repo: vendor_docs/Gates_GT2_design_manual.pdf (record mechloop/parts/vendor/gates_gt2.json; origin https://www.gates.com/drivedesign) |
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
| BOSS_TQ | Bossard, Preload and tightening torques (VDI 2230:2015 basis), 01-2025 | document | vendor_cad/staging/practice_refs/01_Bossard_preload_torque.pdf |
| MMCC273 | Metric & Multistandard Components Corp., Clearance hole information (ref. ISO 273-1979), page 10-1040 (scan, read visually) | document | vendor_cad/staging/practice_refs/02_MetricMCC_ISO273_clearance.pdf |
| WESTFIELD | Westfield Fasteners, Socket head cap screws (DIN 912 / ISO 4762) dimension table | document | vendor_cad/staging/practice_refs/03_Westfield_socket_head_cap_screw.pdf |
| ARAMFIX | Aramfix ISO 4762 data sheet, table 1 'according to DIN 912' (length matrix with ls / lg) | document | vendor_cad/staging/practice_refs/03_Aramfix_ISO4762_dimensions.pdf |
| LEDERER | Lederer, DIN 912 / ISO 4762 stainless (A2 / A4) availability matrix | document | vendor_cad/staging/practice_refs/03_Lederer_ISO4762.pdf |
| BOSS_SP | Bossard, Surface pressure when mounted (VDI 2230 1986 and 2015 tables), 01-2025 | document | vendor_cad/staging/practice_refs/04_Bossard_surface_pressure.pdf |
| BOSS_TE | Bossard, Length of engaged thread (recommended minimum, trial values M6 to M16) | document | vendor_cad/staging/practice_refs/05_Bossard_thread_engagement.pdf |
| RC_WASH | RC Fasteners, metric flat washers: ISO 7089 (normal), ISO 7093 (large) | document | vendor_cad/staging/practice_refs/06_RC_ISO_washers.pdf |
| STEPHENS7090 | Stephens, ISO 7090 chamfered washer dimensions (from M5) | document | vendor_cad/staging/practice_refs/06_Stephens_ISO7090.pdf |
| RUTHEX | ruthex RX series heat-set inserts, product data sheet (status 15.08.2022) | document | vendor_cad/staging/practice_refs/07_Ruthex_RX_insert_data.pdf |
| SPIROL | SPIROL, Inserts for plastics design guide, 'Design guidelines for the plastic component' | document | vendor_cad/staging/practice_refs/07_SPIROL_inserts_design_guide.pdf |
| SKF608 | SKF 608 product data (generated from skf.com 2023-12-05) | document | vendor_cad/staging/practice_refs/08_SKF_608_product_data.pdf |
| SKFCAT | SKF general catalogue, deep groove ball bearings, axial load carrying capacity | document | vendor_cad/staging/practice_refs/08_SKF_deep_groove_general_catalogue.pdf |
| SKFINST | SKF bearing installation and maintenance guide, selecting fits | document | vendor_cad/staging/practice_refs/08_SKF_installation_maintenance.pdf |
| HIWIN_INST | HIWIN linear guideway installation instructions G99UE02-2506 | document | vendor_cad/staging/practice_refs/09_HIWIN_installation.pdf |
| HIWIN_MGCAT | HIWIN MG series catalogue, table 3.90 | document | vendor_cad/staging/practice_refs/09_HIWIN_MG_catalogue.pdf |
| HOLO | Holo-Krome metric handbook, table 61, axial holding power of cup point set screws | document | vendor_cad/staging/practice_refs/10_HoloKrome_metric_handbook.pdf |
| UNBRAKO | Unbrako metric socket set screws, torsional and axial holding power | document | vendor_cad/staging/practice_refs/10_Unbrako_metric_set_screws.pdf |
| DIN471 | Maedler, DIN 471 external retaining rings | document | vendor_cad/staging/practice_refs/11_Maedler_DIN471.pdf |
| RULAND | Ruland MCL metric one-piece clamp collars (distributor table) | document | vendor_cad/staging/practice_refs/11_Ruland_metric_collars.pdf |
| GATES_GT2L | Gates PowerGrip GT2 drive design manual (legacy GT2), section 'Use of Idlers' and 'Minimum Belt Wrap and Tooth Engagement' | document | vendor_cad/staging/practice_refs/12_Gates_GT2_drive_design.pdf |
| ELESA | Elesa+Ganter, Trapezoidal lead screws GN 103, technical information (4/2024) | document | vendor_cad/staging/practice_refs/13_ElesaGanter_trapezoidal_engineering.pdf |
| IGUS_DRYLIN | igus DryLin TR lead screw drives catalogue | document | vendor_cad/staging/practice_refs/13_Igus_DryLin_leadscrews.pdf |
| PRUSA_PETG | Prusament PETG technical datasheet v1.1 (16-02-2022) | document | vendor_cad/staging/practice_refs/14_Prusament_PETG_TDS.pdf |
| ABSM30 | Stratasys ABS-M30 data sheet | document | vendor_cad/staging/practice_refs/14_Stratasys_ABSM30_TDS.pdf |
| PETGCREEP | T. Romeijn et al., Instantaneous and long-term mechanical properties of PETG additively manufactured by pellet-based material extrusion, Additive Manufacturing 2022 (accepted manuscript) | document | vendor_cad/staging/practice_refs/14_PETG_creep_UTS_research.pdf |
| ABSCREEP | Numerical and Experimental Investigations of Polymer Viscoelastic Materials Obtained by 3D Printing, Polymers 2021, 13, 3276 | document | vendor_cad/staging/practice_refs/14_ABS_creep_MDPI_research.pdf |
| STRATFDM | Stratasys Direct, FDM design guide (July 2025) | document | vendor_cad/staging/practice_refs/15_Stratasys_FDM_design_guide.pdf |
| ISO13715M | Modulus Metal summary of ISO 13715 (maker article snapshot, not the standard) | document | vendor_cad/staging/practice_refs/16_ISO13715_Modulus_maker_summary.pdf |
| IEC_JMF | IDEC presentation on IEC 60204-1:2016 (hosted by JMF), clause 8.2 | document | vendor_cad/staging/practice_refs/17_JMF_IEC60204_summary.pdf |
| IEC_IP2X | GT Engineering excerpt of IEC 60204-1 clause 6.2.2 (web excerpt) | document | vendor_cad/staging/practice_refs/17_IEC60204_IP2X_source_excerpt.pdf |
| SLOCUM9 | A. Slocum, Topic 9 (bolted joints), MIT | document | vendor_cad/staging/practice_refs/18_Slocum_Topic9.pdf |
| SLOCUMFP | A. Slocum, Fundamental principles lecture (MIT, 2022) | document | vendor_cad/staging/practice_refs/18_Slocum_fundamental_principles.pdf |
| NASA5020 | NASA-STD-5020B, Requirements for Threaded Fastening Systems in Spaceflight Hardware (2021, revalidated 2026-01-05) | document | vendor_cad/staging/practice_refs/19_NASA_STD5020B_revalidated2026.pdf |

## 3. The ten unchecked rules worth most

Ranked by (how often it bites a real machine) x (how cheaply it can be checked from what a design already declares).
Two entries changed in version 2 (LSC-015 and BRG-024 are new; FST-081 and FST-051 moved out).

| # | Rule | Why it is first-rank | Check from existing data? |
|---|---|---|---|
| 1 | PRT-030 with FST-031: no preloaded screw seat on printed plastic without a washer and a metal sleeve | creep slackens every such joint; the derived 5 MPa limit leaves an M5 0.23 N.m even with a washer | yes: stack under each head (audit does it) |
| 2 | FST-070: a locking feature that does not depend on preload on moving and vibrating assemblies | loosening is the commonest long-run printer fault (NASA-STD-5020B TFSR 16 states the same for spaceflight) | needs one attribute on `add_screw` |
| 3 | FST-060: nuts and tapped parts on the threaded part of a partially threaded screw | a drawn joint that cannot be assembled | yes: b and full-thread lengths now documented |
| 4 | LSC-015: lead difference between screws that drive one body | maker screws differ up to 0.1 mm / 300 mm; mechloop assumes 0.02 mm | yes: travel and screw list are declared |
| 5 | BRG-020 / BRG-023 / BRG-024: retention, axial path, abutment diameters | AGENT.md lists retention as not checked; v8 has all three problems | yes: probing around each ring (audit does it) |
| 6 | SHF-010 / SHF-011: set screws and bearings on a plain journal (js5 / h5), not on a thread | layer-shift and runout source | needs a journal attribute on lead screws |
| 7 | MCH-015 / SHT-013 / SHT-014 / DOC-010: broken edges, rounded profile corners, an ISO 13715 edge note | the owner's second observation | yes: sharp convex edges per part (audit does it) |
| 8 | BLT-010 / BLT-011 on every loaded pulley; BLT-030 / BLT-031 idlers | only the joint's drive pulley is checked today | yes: `route()` returns every wrap |
| 9 | FST-010 v2: engagement by aluminium strength (Bossard) | extrusion end taps are soft aluminium; the present 1.5 d passes them | yes: the existing check with a material table |
| 10 | LOC-006: every adjustment has a mover, a lock and access in the finished machine | an adjustment without a lock drifts | needs two fields on `Adjustment` |

## 4. Audit of printer_v8 (re-run with version 2 values)

### 4.1 Method and limits

`tools/practice_audit.py` loads the design with `mechloop.runner.load_design` and probes the B-rep (point-in-solid)
along and around every screw at the home pose: what the screw passes through, each hole's diameter and whether it is a
slot, the nearest edge, where each nut and tapped part sits on the screw, what the head and each nut bear on, and now
also whether a head sits in a counterbore and how thick the floor is, and what touches each bearing ring face out to
which diameter. Belts come from `mechloop.verifiers.belts.route`. Sharp edges are convex edges whose faces meet at 60
degrees or more. Re-run: 34 s, 313,803 point tests, output `research_notes/practice/v8_audit.json`.

Computed: everything below not marked "reading" or "hand estimate". **From reading the design or PRINTER_V8.md, not
computed**: set screws (only the `set_screw` joins exist), what locks each adjustment, T-nut type, rail screw pitch, the
earth wire's routing, the Z mount's 41 degC (motor case figure from PRINTER_V8.md), and the lead-difference figures,
which scale PRINTER_V8.md's own trade-study numbers linearly. Not examined: cable routing against edges, spanner access
to nuts, service removal paths, poka-yoke, pinch points.

Preload: Bossard FM max, class 8.8, mu 0.14 (M3 2436 N, M5 7.0 kN); hand torque scatter is +/-25 % to +/-35 % (NASA
RP-1228), so these are upper values, which is what a seat-pressure check needs.

### 4.2 Findings, most serious first

**Would stop the build or fail in service**

| # | Rule | Finding | Parts and numbers |
|---|---|---|---|
| 1 | FST-060 | The four bed posts cannot be assembled with the screw the BOM names. ISO 4762 / DIN 912 M5 is threaded over its last 22 mm only (b, Westfield); the DIN 912 matrix threads M5 fully only up to 25 mm (Aramfix); M5 x 90 has lg max 68 mm. | `bed_post_0..3` (SHCS-M5x90): `bed_post_i_nut_top` at 2.0 to 6.8 mm under the head is on plain shank; `bed_post_i_nut_arm` (65.8 to 70.5 mm) is 2.3 mm onto it at the nominal setting, so the declared +/-4 mm of levelling is not there. Use fully threaded rod (DIN 976) with a nut and adhesive at the plate. M5 x 90 itself is stocked in A2 / A4 (Lederer), so the length is not the problem (version 1 said it was: corrected). |
| 2 | PRT-030 (derived limit), FST-070 | No screw that passes through a printed part can hold a preload in v8. 36 head or nut seats bear on bare PETG / ABS: 354 to 389 MPa at class 8.8 torque against a derived sustained limit of 5 MPa (2.5 MPa for the warm Z mount). Even with washers the allowable preload is a few hundred newtons. | `z_drive_mount` (2 x M5 to the rail: 126 N allowed with an ISO 7089 washer, 0.12 N.m; 4 x M3 Z-motor screws: 62 N, 0.04 N.m), `z_pedestal_fl/fr` (2 x M5 each, the bed's weight path: 251 N, 0.23 N.m; ISO 7093 742 N, 0.69 N.m), `x/y/y_l_tension_anchor` (belt tension path), `probe_mount` under `extruder_screw_0/1` (M3x50 clamping Roto and hotend: 123 N, 0.07 N.m), 12 nuts on `nut_block*` (ABS). Remedy: a metal sleeve (compression limiter) through each printed hole so the clamp load goes through metal, plus a nyloc or adhesive (preload-independent locking). |
| 3 | LSC-015 (hand estimate) | The three belt-tied Z screws can differ in height by six times what the design's trade study assumed. Makers' lead deviation for rolled trapezoidal screws is 0.1 mm / 300 mm (Elesa GN 103, igus DryLin TR); over 184.7 mm of travel two screws can differ by 0.123 mm against mechloop's assumed 0.02 mm. | Scaling PRINTER_V8.md's own figures for layout (d) (0.02 mm -> 0.017 mm tilt, 2.8 N on a nut): 0.105 mm of tilt that changes with height, and 17 N on a nut against the about 14 N of bed weight that seats each floating nut. At maker accuracy a nut can lift, the case the trade study used to reject layouts (b) and (c). The generic T8x2 has no lead figure at all (MISSING.txt 13); measure the three screws, or let Klipper re-level (independent motors + `[z_tilt]`). |
| 4 | BRG-024 (computed) | The two front lower bearings sit with both rings on the electronics tray, and the three pulley hubs bear on the upper inner rings past the rings' shoulders. | `z_bearing_fl_lo`, `z_bearing_fr_lo`: `electronics_tray` touches the faces out to 21 mm (outer ring abutment Da max 20 mm, SKF): the inner ring turns with the screw and drags on the tray. `z_pulley`, `z_pulley_fl`, `z_pulley_fr`: hub contact out to 15.5 mm against the inner ring's shoulder d1 about 12.15 mm: on a shielded 608 the hub rubs the shield. An 8 x 12 shim washer under each hub and a relief in the tray (or a step in the pedestal) under each lower bearing. |
| 5 | BRG-023, SHF-011 (reading + computed) | The bed's weight goes through pulley set screws biting on a trapezoidal thread, and each 608 inner ring sits on thread crests. | Capacity is not the issue: an M3 cup-point set screw holds 0.71 to 0.88 kN on a plain hardened shaft (Unbrako, Holo-Krome, +/-30 %) against 10 to 20 N per screw. The seat is: SKF asks js5 / h5 for an 8 mm seat; a DIN 471 groove (7.6 x 0.9 mm) or a collar cannot be put across a thread whose minor diameter is about 6 mm. Specify screws with turned journal ends. |
| 6 | BRG-020 (computed) | Nothing holds the three screws, pulleys or upper bearings down. | `z_bearing_hi`, `_fl_hi`, `_fr_hi`: nothing above the outer ring, nothing below the inner ring; the lower inner rings are free upwards. An upward force on the bed lifts screw, pulley and bearing. SKF's 0.25 C0 limit for small bearings (342 N on a 608) is not the issue (BRG-022 passes about 20-fold). |
| 7 | FST-070 (computed + BOM) | No preload-independent locking on 91 screws that ride on moving bodies, nor on any motor, pulley or bed fastener. | zbody 47, ybody 32, xbody 12 screws; BOM locking items: 3 x NYLOC-M3. |
| 8 | FST-030, FST-034 (computed) | The bed posts' heads sit on a 2 mm floor of cast plate, over its limiting surface pressure. | `bed_plate` (MIC-6, pG 200 MPa mapped from cast GK-AlSi9Cu3; 140 MPa if no indentation is permitted): 288 MPa under each M5 head at 8.8 torque, floor 0.40 d (Slocum: material under a head typically 1 to 3 d). `bed_tie_screw_0/1` M3: 221 MPa. With an ISO 7089 washer the M5 seat is fine (10.9 kN allowed), but the 6 mm counterbore has no room for one. |
| 9 | ELE-010 (reading, conditional) | The frame's protective-earth wire is 0.82 mm2. | `earth to frame` (inlet PE to the frame stud), AWG 18 single conductor. IEC 60204-1 8.2.2 (IDEC summary): a protective conductor not in a cable or common enclosure with the line conductor needs at least 2.5 mm2 Cu (4 mm2 unprotected). The routing is not modelled; if it is not sheathed with the line conductors it is under size. The frame's anodised extrusions bonded only through cast brackets on T-nuts are also not "continuity assured by construction". |

**Would annoy the builder**

| # | Rule | Finding | Parts and numbers |
|---|---|---|---|
| 10 | FST-010 v2 (computed) | The front arm-end screws have 1.8 d of thread in the 2020 arm ends. | `bed_arm_left_fbolt`, `bed_arm_right_fbolt` (M5x12 through the 3 mm front plate): 9 mm in the tapped core hole. Bossard: 2 d in soft aluminium (Rm > 180, the AlMg3 row) for 8.8; the profile's alloy is not recorded (6063-class assumed). mechloop's 1.5 d passes them. An M5x14 or a thicker plate. The rear ones (M5x16, 2.2 d) pass. |
| 11 | FST-031 (computed) | Heads on slots without washers. | `beam_bolt_left/right` and their second bolts (4 x M5x8 through the Y plates, slot 5.5 x 8.5 mm): 38 % of the head supported, 769 MPa against 490 MPa for mild steel (VDI 2230:2015). They hang the X beam. |
| 12 | SHT-014, SHT-013, MCH-015, DOC-010 (computed) | Every edge of every metal part is unbroken; no part carries an edge note. | 22 parts, 21.5 m of sharp convex edge, 107 sharp outside profile corners (`electronics_tray` 2.8 m, `front_plate` 2.6 m, `bed_plate` 2.4 m, `back_plate` 1.9 m, `tool_plate` 1.1 m). Write the note in ISO 13715 form (e.g. -0.3 on every external edge); 17 mild-steel parts also need a finish. |
| 13 | BLT-030, BLT-031 (computed) | The Z tensioner is a toothed idler on the belt's smooth back. | `z_idler` (GT2-IDLER-20T-B5), OD 12.0 mm. Both Gates manuals: back-side idlers flat and uncrowned. Size: under the current (GT3) table's 12.7 mm, over the legacy GT2 rule (1.3 x a 12-groove sprocket, 9.9 mm): the sources disagree, the tooth objection does not. |
| 14 | BLT-010, BLT-011 (computed) | The rear Z screw's pulley: 3.4 teeth in mesh at 60.3 degrees. | `z_pulley`: legacy GT2 manual: rating x 0.40 at 3 teeth, at least 60 degrees of wrap. Load is small; with a slack belt this is the pulley that skips, and a skipped rear screw tilts the bed. |
| 15 | FST-081 (reading + BOM) | M3x6 (24) and M3x8 (39) side by side into guide blocks with 3.5 mm threads. | Y plates and tool plate need M3x6; the back plate M3x8. |
| 16 | FST-051, FST-101 (computed) | 22 joints hang on one screw ("to resist rotation, a moment, or two forces acting as a couple, is required": Slocum). | One T-nut each: `x_rail_stop_left/right`, `x_tension_anchor`, `y_tension_anchor`, `y_tension_anchor_l`; idler axles; arm ends; post tabs. |
| 17 | FST-100 (reading) | 123 T-nuts with no type. | `TNUT-2020-M3/-M5` only. |
| 18 | FST-080 (computed) | 15 screw SKUs, 25 fastener SKUs, keys 2 / 2.5 / 3 / 4 mm, spanners 5 / 5.5 / 8 / 17 mm. | Used once or seldom: M5x10, M5x25, M5x30, M3x25, M3x12, M5x12. |
| 19 | LOC-006 (reading) | Ten adjustments, none names its lock. | Z belt idler, X switch, Y switch mount and all rails held by friction only. |

**Good practice**

| # | Rule | Finding | Parts and numbers |
|---|---|---|---|
| 20 | FST-050 (computed) | 22 holes closer than 1.5 d to an edge (Bossard's recommended minimum edge distance for M5 is 7.5 mm = 1.5 d). | `bed_post_tab_*` 1.31 d, `x_rail_stop_*` 1.21 d, `y_plate_*` 1.35 d, `tool_plate` 1.33 d, `y_endstop_mount` 1.3 d; printed `probe_mount`, `part_duct` 1.05 d. |
| 21 | BLT-040 (computed) | 12 mm Y belts on 12.0 mm OD pulleys (SDP/SI: never smaller than the belt width). | `y_pulley(_l)`, `y_idler(_l)` |
| 22 | FST-062 (computed) | Four screws end flush with their nuts; with nylocs (FST-070) they need two threads through (NASA-STD-5020B). | `bed_tie_screw_0/1`, `part_fan_screw_0/1` (M3x16): one length up. |
| 23 | FST-020 (computed) | Hole classes mixed without a stated reason (ISO 273 confirmed from the MMCC table). | Of 218: M3 fine 11, medium 47, coarse 57, 4.2 mm printed 23; M5 medium 49, 6.0 mm printed 9. |
| 24 | FST-001, FST-061 (computed) | No property class on any screw; the catalogue's proof loads are 12.9. The M5x90 posts and M3x50 Roto screws are stocked in A2 / A4 (class 70 / 80), not 12.9. | all 172; 6 info flags |
| 25 | LIN-012, LIN-013 (reading) | Rails bolted at every second hole, torque unstated. | Hiwin rail bolts: M3 0.98 N.m into aluminium (into T-nuts in the extrusion), tightened in sequence with a torque wrench. |
| 26 | FST-010 (computed) | Anti-rotation pins have 1.17 d of thread in brass. | `nut_pin*` in the T8 nut flange; not a clamping joint. |

Checked and passing: thread engagement against mechloop's own rule except item 10; SKF axial limit on the 608s
(10 to 20 N against 342 N); the Z screws' bearing pair as a cantilever support (37 mm apart on 8 mm, L/D 4.6 > 3,
Slocum); X / Y pulleys at 10 teeth and 180 degrees; no metal seat on 6061 or steel over its VDI 2230 pressure except the
slotted beam bolts; no PETG part above its HDT (68 degC, Prusament) with 15 K margin (the Z mount at 41 degC has 12 K
to the 53 degC line); the earth stud's ring terminals and star washer.

### 4.3 Fastener schedule in brief

| | Count |
|---|---|
| Screws drawn / on moving bodies | 172 / 91 |
| Further M5x8 and T-nuts as BOM lines only (corner brackets) | 52 screws, 123 T-nuts |
| Joints with 1 / 2 / 3 / 4 / 5 / 6 screws | 22 / 27 / 1 / 14 / 3 / 2 |
| Heads on printed plastic / on slots / with a washer | 15 / 4 / 0 |
| Nuts on printed plastic | 21 |
| Screws with declared locking / class / torque | 3 (nyloc) / 0 / 0 |
| Flags: PRT-030 36, FST-050 22, FST-060 8, FST-030 6, FST-061i 6 (info), FST-010 5, FST-034 4, FST-031 4, FST-062 4 | |

## 5. Proposed verifier: `practice`

### 5.1 Structure

- **Thirteenth verifier `practice`**, run after `manufacture` and before `requirements`. Cheap: the audit's probing of
  all 172 screws takes 34 s, of which the fastener stack is the reusable core.
- **Rule registry** in the style of `mechloop/verifiers/dfm_rules.py`: `Rule(id, category, limit, unit, severity,
  source, what, note)`, ids as in this catalogue (`FST-031`), with the source key, URL and evidence level. A rule whose
  number is `recalled` or `derived` may not be registered at `error` severity; that is a test in `tests/`.
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

Each has a known-answer pair: the bad case must raise the finding, the good case must not. Changed in version 2:
BRG-024 and LSC-015 replace FST-061 and FST-062 (both moved to the next batch; FST-061 is now an info rule).

| # | Rule | Effort | Known-answer test: bad -> good |
|---|---|---|---|
| 1 | FST-031 washer on slots and oversize holes | S | M5 cap screw over a 5.5 x 9 slot in a 3 mm plate -> same with a washer part |
| 2 | PRT-030 seat on printed plastic | S | M3 through a 5 mm PETG block into a nut -> aluminium sleeve through the block, washers both sides |
| 3 | FST-060 nut on the plain shank | S | M5x60 with a nut 10 mm under the head -> M5x20 (full thread to 25) or the nut beyond 38 mm |
| 4 | FST-070 preload-independent locking on moving bodies | S | plain M3 + plain nut on a body with a Joint -> `locking="nyloc"`; a serrated flange on a printed seat still fails |
| 5 | BLT-010 / BLT-011 on every loaded pulley | S | three-pulley loop with one driven pulley at 50 degrees -> idler moved to give 90 degrees |
| 6 | BLT-030 / BLT-031 idlers | S | toothed 20T idler on the belt's back -> smooth 18 mm idler |
| 7 | BRG-020 axial retention | S | bearing in an open bore with a shaft through it -> shoulder below, cover above, collar on the shaft |
| 8 | MCH-015 / SHT-014 / DOC-010 edge break | S | plain steel `Box` plate, no note -> chamfered edges, or `meta["edge_break"]="-0.3"` |
| 9 | SHT-013 outside profile corners | S | rectangular sheet tab -> R2 corners |
| 10 | FST-051 single-screw joint | S | bracket on one screw -> second screw, or a rib in a slot declared as a join |
| 11 | FST-101 single T-nut | S | stop plate on one T-nut -> two |
| 12 | FST-050 edge distance | S | M5 hole 6 mm from a steel edge -> 7.5 mm |
| 13 | FST-020 hole class | S | 5.1 mm hole for an M5 clamp screw -> 5.5; an `axle` join is exempt |
| 14 | BRG-024 abutment diameters | S | 16 mm pulley hub on a 608 inner ring -> 8 x 12 shim; a plate under both rings of a turning bearing -> relieved |
| 15 | LSC-015 lead difference between screws | S | two belt-tied screws, 200 mm travel, support rigid in tilt -> declared float that covers 0.13 mm, or independent motors with `z_tilt` |
| 16 | FST-081 look-alike bottoming length | S | M3x6 and M3x8 around an MGN12H -> one length |
| 17 | SHF-010 / SHF-011 set screws and seats | S | `set_screw` join or bearing on a T8 thread -> journal end; motor shaft with `flat` |
| 18 | BRG-023 axial path through a set screw | M | lead screw whose only downward stop is a set-screwed pulley -> collar or shoulder on a bearing |
| 19 | FST-030 / FST-034 seat pressure and floor | M | M5 on a 2 mm floor of MIC-6 at 8.8 torque -> washer in a wider counterbore and a 5 mm floor |
| 20 | LOC-006 adjustment lock and access | M | `Adjustment` with no lock -> lock screws named, reachable with the machine assembled |
| 21 | FST-052 / STR-013 friction joint | M | motor mount on two slotted M5 with 40 N belt pull and no stop -> jack screw touching the mount |
| 22 | BLT-040 / BLT-041 width and flanges | S | 12 mm belt on a 12 mm pulley; unflanged pair on vertical shafts -> 9 mm belt; flanged |
| 23 | FST-100 T-nut type against assembly order | M | slide-in T-nut in a slot closed at both ends at that step -> drop-in, or earlier step |
| 24 | ASM-030 service removal | M | nozzle behind a duct that must come off with the fan -> removal path free |
| 25 | FST-040 / DOC-012 torque and locking table in BUILD.md | M | generated table matches Bossard's row (M5 8.8, mu 0.14: 6.5 N.m) and is cut to the seat limit on soft parts |

Then: FST-061 (info), FST-062 (two threads through a locknut), FST-064 (one tapped part per screw), ELE-010 (PE
conductor size), LSC-010/011/014, LIN-010 shoulders, PRT-012 bed-edge chamfers, PRT-031 HDT, ASM-011 spanner access,
ASM-042 looms against sharp edges, SAF-014 tip-over.

### 5.3 Existing checks to move or cross-reference

| Existing check | Proposal |
|---|---|
| `interference.thread_engagement`, `thread_bottoms_out` | stay where they are (they are errors every design must clear early); register them as FST-010 / FST-012 so findings carry the rule id and source; use the shared stack. Adopt FST-010 v2 (Bossard): 6061 error below 1.5 d, warning to 2 d; soft aluminium (6063 extrusion, cast plate, 5052) error below 2 d |
| `motion.belt_low_wrap` | move under `practice` as BLT-010 and widen from the joint's drive pulley to every loaded pulley; keep the code name as an alias |
| `motion.belt_misaligned`, `belt_wrong_length`; `ratings.motor_shaft_radial_load` | cross-reference (BLT-051, BLT-050, SHF-012) |
| `manufacture` rules `sheet.hole_to_edge_t_ratio`, `sheet.countersink_min_thickness_mm`, `sheet.tap_min_thickness_mm`, `fdm.thread_wall_d_ratio`, `cnc.thread_depth_ratio`, `cnc.blind_tap_runout_d_ratio` | stay in `manufacture` (can it be made); `practice` adds the in-service rule beside each (FST-050 strength edge distance, FST-013 / FST-091 inserts) and cites the DFM id |
| `fea.bed_support.screw_synchronisation` (assumes 0.02 mm between screws) | replace the assumption by LSC-015 (makers' 0.1 mm / 300 mm lead deviation) |
| `ratings.cantilever_on_guide_blocks`, `fea.z_guides_bind`, `fea.bed_support.constraint` | cross-reference from LOC-001 / LOC-009; v8's checker note 2 (three screws judged as a cantilever) belongs to the same clean-up |
| `assemble` metrics `fastener_types`, `tool_changes`, `from_below` | reported by `practice` as FST-080 / ASM-012 with the SKU merge suggestions |
| `subsystems.cable_clamp_in_air`, `electrical.bend_too_tight`, `flex_span_crosses_part` | cross-reference from ASM-040..042 |
| `tolerance` pattern start (`p_all_start`) | shares the measured holes with FST-020 |

### 5.4 Catalogue additions

| Part | Standard / data needed | Used by |
|---|---|---|
| Plain washers M2.5 to M8, normal and wide | ISO 7089 (M3 3.2 x 7 x 0.5, M4 4.3 x 9 x 0.8, M5 5.3 x 10 x 1.0) and ISO 7093 (M3 3.2 x 9 x 0.8, M5 5.3 x 15 x 1.2): RC Fasteners tables | FST-031, PRT-030, FST-030 |
| Nylon-insert nuts, all-metal locknuts, serrated flange nuts and screws | ISO 10511 / 7040, ISO 7042, ISO 4161, ISO 4162 (none fetched) | FST-070, FST-072 |
| Thread adhesive as a BOM consumable with temperature limit and plastics warning | maker's sheet | FST-070, FST-073 |
| Dowel pins, shoulder screws | ISO 8734 / 2338, ISO 7379 | LOC-004, LOC-005, idler axles |
| Circlips, shaft collars, shim washers 8 x 12 / 8 x 14 | DIN 471 (8 mm: groove 7.6 x 0.9, Maedler), Ruland MCL-8 (18 OD x 9, M3 clamp; no holding rating), DIN 988 | BRG-020, BRG-023 |
| Heat-set inserts M2 to M5 with hole, depth, minimum wall | ruthex RX table (M3x5.7: hole 4.0, W min 1.6; M5x9.5: hole 6.4, W 2.6); SPIROL depth and boss rules | FST-091, FST-092 |
| Smooth idlers, 2MGT | Gates part with OD and bearing data | BLT-030, BLT-031 |
| T-nuts by type (slide-in, drop-in, roll-in, spring), M3 to M5 for 2020 | one maker's drawing with thickness (thread length) | FST-100, FST-101, FST-010 |
| Button and countersunk screws, fully threaded studs / threaded rod | ISO 7380, ISO 10642, DIN 976 | head clearance choices, FST-060 |
| Lead screw with machined journal ends (js5 / h5 seat per SKF); thrust or support block; lead accuracy per screw | a maker's drawing; Elesa / igus give 0.1 mm / 300 mm for their own screws | SHF-011, BRG-023 |
| Rail end stops | maker's part or a made part flagged as such | LIN-014 |
| Tables | ISO 273 clearance holes (confirm the recalled values), ISO 4762 `b` and length ranges (in `vendor_docs`), head sizes for ISO 7380 / 10642, tightening torques by class and friction (Bossard F.047: now in hand), limiting surface pressures by material (VDI 2230:2015 via Bossard: in hand for metals), HDT by plastic (Prusament PETG 68, ABS-M30 100 to 104 degC), SKF abutment diameters per bearing, ISO 2768-m | FST-020, FST-060, FST-040, FST-030, PRT-031, DOC-011 |

## 6. Sources: what is still missing, and where they disagree

### 6.1 Still not covered

Version 1's unreachable list (SKF, Bossard, Hiwin manual, ISO tables, Slocum, NASA-STD-5020B, set-screw data, insert
data) is now covered by the delivered documents. What remains, cross-checked against `MISSING.txt`:

| Gap | Where it bites | MISSING.txt |
|---|---|---|
| A verified ISO 4762 length range (the matrix in hand is DIN 912; Lederer is availability) | FST-061 (info only now) | 3 |
| Any validated allowable bearing pressure or long-term stress for printed PETG / ABS | PRT-030 runs on a derived 5 MPa | 4, 14 |
| Bossard's engagement trials below M6 | FST-010 for M3 to M5 | 5 |
| ISO 7090 below M5, ISO 7093-1 below M3 | washer choice for M2.5 | 6 |
| Insert strength in printed PETG / ABS (SPIROL's data are nylon) | FST-091 strength | 7 |
| A single correct 608 fit and axial service load | BRG-010 / 022 are conditional | 8 |
| MGN block-to-carriage bolt torque | LIN-013 covers rail bolts only | 9 |
| Set-screw holding with vs without a shaft flat | SHF-010 | 10 |
| Collar holding force | BRG-023 remedy | 11 |
| Legacy GT2 2 mm minimum sprocket and tension by width | BLT-020, BLT-031, BLT-050 | 12 |
| Lead accuracy and backlash of generic T8 screws | LSC-015 uses maker figures | 13 |
| ISO 13715 edge sizes (B.7 is self-inconsistent in the summary) | MCH-015 / DOC-010 sizes | 16 |
| Lead-screw critical speed and buckling constants (Elesa's are diagrams) | LSC-010 / 011 | not listed |
| Not requested at all: T-nut types and loads, tool and spanner access, poka-yoke, service access, cable bend radius and strain relief (igus chain data was not in the set), ferrules, connector derating, pinch points, hot surfaces, tip-over, lifting, sheet edge finish and corner radii, anodised-aluminium washers, anaerobic adhesive on plastics | the 52 recalled rules | not listed |

### 6.2 Disagreements (both positions recorded in `rules.yaml`)

| Topic | Positions | Used |
|---|---|---|
| Thread engagement in aluminium | Bossard: 1.4 d (8.8) / 1.6 d (10.9) in AlMgSi1 F32 (Rm > 330); 2 d (VDI formula 3 d) in AlMg3 F18; Nord-Lock 2 d, Tameson 2 to 2.5 d (snippets); mechloop 1.5 d | by alloy: 6061 error < 1.5 d, warning to 2 d; soft aluminium error < 2 d |
| Surface pressure, mild steel | VDI 2230:1986 St 37: 260 MPa; VDI 2230:2015 S235: 490 MPa | 2015 |
| Back-side idler size, 2 mm pitch | current Gates (GT3) table 12.7 mm; legacy GT2: 1.3 x the smallest inside sprocket (9.9 mm if 12 grooves); SDP/SI: larger than the smallest drive pulley | report both; v8's 12.0 mm sits between |
| Idlers at all | SDP/SI and the legacy GT2 manual: only where functionally necessary; current Gates: commonly used with good success | Gates' side and size rules |
| Insert hole depth and boss | CNC Kitchen: about 1 mm deeper than the insert; SPIROL: insert length + 2 pitches; ruthex minimum wall (M3 boss about 7.8 mm) vs SPIROL's optimum 2 to 3 x insert diameter | SPIROL depth, ruthex wall as minimum |
| Lock washers | NASA RP-1228 'useless'; Bolt Science 'aid self loosening'; NASA-STD-5020B 'minimal, if any, locking' | do not use |
| Serrated flanges | Bolt Science lists them as a locking category; NASA-STD-5020B: preload-dependent and they damage bearing surfaces | not accepted alone on creeping seats |
| Torque-table friction | Bossard 0.14 (zinc, lower bound); SEW 0.09 for 10.9 / 12.9 (snippet) | 0.14 |
| Flange length on bent sheet | mechloop 2 t + r; Protolabs 4 t | unchanged |
| Hole to edge | mechloop 1 t of web (cutting); Protolabs 3.2 mm; NASA RP-1228 1.5 to 2 d; Bossard c = 1.5 d for M4 / M5 | strength rule 1.5 d |
| ISO 13715 example B.7 | diagram 0.1 to 0.5 mm, text 0.1 to 0.3 mm (same summary) | no size taken from it |

## 7. Version 2: what changed

### 7.1 Counts

| | Version 1 | Version 2 |
|---|---|---|
| Rules | 135 | 138 (new: BRG-024 abutment diameters, LSC-015 lead difference between screws, FST-064 one tapped part per screw) |
| document (delivered files) | 0 | 47 |
| fetched / repo | 48 | 38 (several moved up to document) |
| derived | 0 | 1 (PRT-030) |
| snippet | 12 | 0 |
| recalled | 75 | 52 |

### 7.2 Every value correction and its effect on the v8 audit

24 rules carry a `correction` field in `rules.yaml`; the list is also under `corrections:` at its end.

| Rule | Old | New | Effect on v8 |
|---|---|---|---|
| FST-002 | clamped length >= 3 d where vibration matters (recalled) | material under the head 1 to 3 d (Slocum 9-10) | none flagged directly; supports FST-034 (v8 has 2 mm under M5 heads in the bed plate, 0.4 d) |
| FST-010 | aluminium 2.0 d (Nord-Lock snippet; mechloop 1.5 d) | by alloy strength per Bossard: 6061/6082 error < 1.5 d, warning 1.5 to 2 d; soft Al (6063, MIC-6, 5052) error < 2 d | v8: bed_arm_left/right_fbolt (M5x12 into the 2020 arm ends) 1.8 d: passes mechloop's 1.5 d, FAILS the soft-aluminium 2 d rule if the profile is 6063 (warning if treated as 6061); tool_plate M3 2.33 d passes |
| FST-020 | table values recalled | confirmed unchanged from the MMCC ISO 273 table (read from the scan) | none: the audit's classes stand |
| FST-030 | limit = yield of the clamped part (6061 276, MIC-6 105, steel 250); preload = recalled torque / (0.2 d) (M3 2167 N, M5 5700 N) | limit = VDI 2230:2015 pG (6061 360 mapped, MIC-6 200 mapped, mild steel 490); preload = Bossard FM max, 8.8, mu 0.14 (M3 2436 N, M5 7000 N) | bed_post heads on MIC-6: 235 MPa vs 105 -> about 290 MPa vs 200 (still over; also over 140 = 70 %); bed_tie M3 heads: 196 vs 105 -> about 220 vs 200 (marginal over). No metal seat on 6061 or steel now exceeds its pG at 8.8 torque |
| FST-031 | ISO 7089 dims from FreeCAD CSV; ISO 7093 not fetched | ISO 7089 confirmed (RC); ISO 7093 added (M3 9 mm, M5 15 mm OD) | torque limits with a washer now also computed for ISO 7093 large washers |
| FST-034 | floor >= 0.6 d (recalled) | >= 1 d (Slocum, 'typically') | bed_plate counterbore floors (2 mm under M5, 0.4 d) fail by either figure |
| FST-040 | 8.8 torques M2.5 0.7, M3 1.3, M4 2.9, M5 5.7 N.m (recalled, mu about 0.14) | M2.5 0.81, M3 1.41, M4 3.3, M5 6.5 N.m (Bossard mu 0.14); preload taken directly from the table, not from T / 0.2 d | preloads used by the audit rise 12 % (M3) and 23 % (M5): every bearing-pressure figure rises by the same share; ranking unchanged |
| FST-060 | b and full-thread lengths recalled / from the FreeCAD CSV | confirmed unchanged (Westfield b; Aramfix full-thread rows) | the bed-post finding stands: M5 x 90 has lg max 68 mm, thread only over the last 22 mm |
| FST-061 | M3 x 50 and M5 x 90 'outside ISO 4762's range (M3 5-30, M5 8-50)': warning | beyond the DIN 912 matrix but stocked in A2 / A4 (Lederer): info, with the strength class to declare | the 6 FST-061 flags (bed posts, extruder screws) drop from warning to info; FST-001 gains them (A2-70 / A4-80 instead of the catalogue's 12.9) |
| FST-062 | 1 pitch (2 in aerospace practice, recalled) | 2 threads for self-locking nuts (NASA-STD-5020B p.86); 1 pitch for plain nuts stays recalled | any nyloc added on the four flush screws (bed_tie_screw_0/1, part_fan_screw_0/1) needs a screw 2 mm longer |
| FST-070 | serrated flange listed as a full locking provision | serrated / free-spinning features depend on preload (NASA): not accepted alone where the seat creeps | no change to v8's count (no serrated parts); matters for the remedy: on printed seats use nylocs or adhesive, not serrated flanges |
| FST-091 | M3 hole 4.0 (snippet), wall >= 0.5 x insert OD (snippet), depth +1 mm | ruthex hole and W min per size; depth +2 pitches (SPIROL) | none in v8 (no inserts) |
| FST-102 | 2 d in 6063 (recalled) | 2 d by Bossard's soft-aluminium row (mapping derived) | bed_arm_*_fbolt 1.8 d: see FST-010 |
| LOC-009 | L/D 1 / 1.6 / 3 (snippet) | same, from the document | none |
| BRG-010 | shaft j5-k5, housing H7 (recalled) | js5 (h5) for an 8 mm shaft under light load (SKF) | sharpens SHF-011: a rolled T8 thread is not a js5 journal |
| BRG-022 | 0.5 / 0.25 C0 recalled, unconfirmed | confirmed: 608 is a 'small bearing', 0.25 C0 = 342 N | v8's Z screws (10 to 20 N axial each) pass by a factor of about 20 |
| SHF-011 | principle recalled | document-backed (SKF fit, DIN 471 groove) | the set-screw / seat finding (section 4.2, item 5) unchanged in kind |
| BLT-031 | 12.7 mm (GT3 table, labelled as GT2) | 12.7 mm (current GT3 table) or 9.9 mm (legacy GT2 rule with a 12-groove minimum) | z_idler OD 12.0 mm: fails the GT3 table, passes the legacy GT2 rule; the toothed-on-back objection (BLT-030) stands in both |
| LSC-012 | bearing spacing >= 3 x shaft diameter (recalled) | L/D > 3 (Slocum) | v8's screws: 608 pair 37 mm apart on 8 mm: L/D 4.6, passes |
| LIN-011 | 0.05 / 200 (snippet) | confirmed (Hiwin table 3.90) | none computed: extrusion straightness still unknown |
| LIN-013 | about 1.9 / 1.0 N.m (snippet, row uncertain) | 1.86 / 1.27 / 0.98 N.m (Hiwin table 11, rail bolts only) | torque table for v8's rail screws: 0.98 N.m (into T-nuts in aluminium extrusion) |
| PRT-030 | 0.3 x yield, sustained (recalled): PETG about 14, ABS about 12 MPa | 5 MPa derived (2.5 MPa between 40 and 60 degC) | all 36 plastic seats exceed it 70- to 160-fold at 8.8 torque; with an ISO 7089 washer an M5 may carry about 250 N (0.23 N.m), with ISO 7093 740 N (0.69 N.m); an M3 with ISO 7089 about 120 N (0.07 N.m); on the 41 degC Z mount half that. Conclusion: screws through printed parts in v8 cannot be preloaded without a metal sleeve |
| PRT-031 | PETG about 70, ABS about 95 degC (recalled) | PETG 68 (Prusament), ABS-M30 99.9 to 103.8 (Stratasys) | v8: no PETG part is near the 80 degC bed; z_drive_mount carries the Z motor at a 41 degC case (12 K under the 53 degC line, and into PRT-030's 40 to 60 degC band); ABS parts near the hotend and bed pass |
| ELE-010 | no conductor size (recalled continuity test current only) | 2.5 / 4 mm2 Cu for separate PE conductors (IEC 60204-1 8.2.2 via IDEC) | v8 (reading): 'earth to frame' is a single AWG 18 (0.82 mm2) wire to the frame stud; unless it runs in a common sheath / enclosure with the line conductors it is under the 2.5 mm2 minimum |

Net effect on the ranking: the bed-post threads stay first; screws through printed parts move up (the derived limit is
a third of version 1's); the lead-difference finding (LSC-015) and the bearing-abutment finding (BRG-024) are new; the
set-screw finding moves down (capacity is ample; the seat is the problem); the post screw's length is no longer a
finding; the extrusion end-tap engagement and the PE conductor size are new; the cast-plate seat pressure stays over its
(now higher) limit.

### 7.3 Rules still recalled

52, mostly topics the delivered set did not cover (section 6.1): FST-032, FST-073, FST-080, FST-081, FST-092, FST-093,
FST-100, FST-101; LOC-003, LOC-005, LOC-006, LOC-010; BRG-011, SHF-012, SHF-013; BLT-052; LSC-010, LSC-011, LSC-013;
LIN-012, LIN-014, LIN-016; STR-010 to STR-012, STR-014; SHT-013 to SHT-015, SHT-017; MCH-015 (size only; notation is
documented); PRT-032, PRT-033; all ten ASM rules; ELE-011, ELE-013; all six SAF rules; DOC-012. None may be registered
at error severity until sourced.

### 7.4 Limits

- The audit script is exercised on v8 only and has no tests. It works at the home pose and sees only drawn solids.
- Mapped values (6061 -> AW-6082, MIC-6 -> GK-AlSi9Cu3, 2020 profile -> soft aluminium) are ours; each finding that
  depends on one says so.
- The PRT-030 limit is a derivation to keep printed plastic in its linear viscoelastic range, not a strength; the
  ranking does not depend on it (bare seats exceed it 70-fold).
- The lead-difference figures are a linear scaling of PRINTER_V8.md's trade-study numbers, not a verifier result.

## 8. Implemented

The thirteenth verifier, `practice` (`mechloop/verifiers/practice.py`), runs after `manufacture` and by default in
`mechloop verify`; `--only practice` runs it alone. The audit's measuring core was promoted to
`mechloop/verifiers/fastener_stack.py` (`Probe`, `fastener_stack`, `bearing_contacts`), which `tools/practice_audit.py`
now imports, so audit and verifier measure alike. The rule registry (`RULES`, with evidence, source and status) is in
the verifier; `metrics.practice.rules` reports each rule's status and finding count; a test keeps every recalled or
derived rule below error. Declarations, control and waivers: AGENT.md, "Practice". Known-answer tests, bad and good case
for every implemented rule: `tests/test_practice.py`.

### 8.1 The first 25 (section 5.2)

| # | Rule | Status | Check / reason |
|---|---|---|---|
| 1 | FST-031 | cross-referenced | `ratings.head_bearing`: `screw_head_seat_too_small` (washers, ISO 7089 / 7093) |
| 2 | PRT-030 | cross-referenced | `ratings.head_bearing`: `screw_head_bearing_pressure` on printed seats (derived 5 / 2.5 MPa) |
| 3 | FST-060 | implemented | `nut_on_plain_shank` (error): nut or tapped part before the thread start of an ISO 4762 screw; T-nut screws and `meta["fully_threaded"]` skipped |
| 4 | FST-070 | implemented | `no_locking_feature` (warning, grouped per body): screws on a moving body or holding a motor without `locking=` on screw or nut, or a join naming a locknut / adhesive; serrated or jam accepted on metal seats only, split washers never |
| 5 | BLT-010 / BLT-011 | implemented | `pulley_few_teeth` (warning; error under 2 teeth), `pulley_low_wrap` on every loaded pulley; a joint's drive pulley stays with `motion.belt_low_wrap` (cross-referenced) |
| 6 | BLT-030 / BLT-031 | implemented | `toothed_backside_idler`, `idler_too_small` (back side 12.7 mm, legacy GT2 rule quoted; inside idlers 12 grooves, flat 25.4 mm) |
| 7 | BRG-020 | implemented | `bearing_not_retained`: a ring face with nothing against it within 0.4 mm; the error for a declared axial load without a path is not implemented (no axial loads are declared) |
| 8 | MCH-015 / SHT-014 / DOC-010 | cross-referenced | `manufacture.edges`: `edges_not_broken`, edge-break declaration (`edge_break_mm`) |
| 9 | SHT-013 | cross-referenced | `manufacture.edges`: `sharp_profile_corners` |
| 10 | FST-051 | implemented | `single_screw_joint`: pairs of parts held by one screw and no other screw, T-nut screw or non-screw join; parts that turn on the screw (idlers, bearings, axle joins) and round standoffs coaxial with it are exempt |
| 11 | FST-101 | implemented | `single_tnut` (recalled: warning): a part whose only fixing is one T-nut screw |
| 12 | FST-050 | implemented | `hole_near_edge`: hole centre to edge or cut-out under 1.5 d (`limits["FST-050.min_edge_d"]`), made parts only |
| 13 | FST-020 | implemented | `hole_under_fine` (warning, metal parts, axle joins exempt); `hole_over_coarse` under a head (info; the seat is FST-031's); class counts in the metrics |
| 14 | BRG-024 | cross-referenced | `ratings.ring_abutment`: `bearing_abutment` |
| 15 | LSC-015 | cross-referenced | `fea.bed_support.nut_seating_and_lead_error`: `z_tilt_over_constrained`, `z_nut_unseats` |
| 16 | FST-081 | implemented | `lookalike_screw_lengths` (recalled: warning): lengths of one size within 2 mm into one catalogue part's blind maker thread |
| 17 | SHF-010 / SHF-011 | implemented | `set_screw_without_flat` (the join kind must say flat and threadlocked); `seat_on_thread`: a set screw or a bearing on a T8 lead screw without `meta["journal"]` |
| 18 | BRG-023 | implemented | `axial_load_through_set_screw`: an inner-ring face whose only abutment is a set-screwed hub |
| 19 | FST-030 / FST-034 | FST-030 cross-referenced, FST-034 implemented | `ratings.head_bearing` (metal seats, VDI 2230); `counterbore_floor_thin`: floor under a counterbored head under 1 d |
| 20 | LOC-006 | implemented (part) | `adjustment_without_lock` (recalled: warning) from `Adjustment(lock=, mover=)`; z_offset and float exempt. Access in the finished machine: deferred (needs a tool-access search for adjustments at the assembled pose) |
| 21 | FST-052 / STR-013 | deferred | needs the service shear across each slotted joint (belt pull on a motor mount), which no design declares |
| 22 | BLT-040 / BLT-041 | BLT-040 implemented, BLT-041 deferred | `pulley_narrower_than_belt`; every catalogue GT2 pulley and idler is drawn double-flanged, so BLT-041 has nothing to find until an unflanged part exists |
| 23 | FST-100 | deferred | T-nuts are BOM lines without a type and without geometry; the check needs both and the assembly sequence |
| 24 | ASM-030 | deferred | needs a `design.service` list and a removal-path search |
| 25 | FST-040 / DOC-012 | implemented (part) | `torque_not_stated` (info) and `metrics.practice.torque_table` (Bossard 8.8 at mu 0.14 for metal joints, the assumed torque for printed seats, locking declared per group); BUILD.md does not yet print it |

Also cross-referenced: FST-010 (`interference.thread_engagement`), FST-012 (`interference.thread_bottoms_out`), BRG-022
(`fea.bed_support`, `bearing_axial_overload`).

### 8.2 The owner's rules (docs/DESIGN_GUIDELINES.md)

| Id | Rule | Severity | How it is found |
|---|---|---|---|
| DG-01 | no printed part in a load path | error, unless `d.waive("DG-01", part, reason=...)` | a printed part sharing a screw (one it is clamped by or threads into, measured or declared), a declared join, or contact with: a guide (rail, block, a part with `guides=`), a bearing, a lead-screw nut or screw, a motor or an extruder, a pulley or idler, a belt end (anchor within 3 mm), the bed, or a part with `meta["load_path"]`; also a jack screw held in the printed part whose tip pushes a part that holds one of those |
| DG-02 | no tapped thread in aluminium we make; no tapped extrusion ends | warning | `tapped_aluminium`: a screw threading into a made aluminium part (sheet or machined) without `insert="pem"` / `"steel"`; `tapped_extrusion_end`: into a 2020 extrusion without a T-nut |
| DG-03 | a machined part with only through-features is a laser-cut candidate | info | `cnc_2d_candidate`: a 2.5D plate with no blind level, countersink or fitted bore (a shaft, pin or bearing of another part coaxial in it, or a press join); `meta["cnc_reason"]` suppresses it and is listed |
| DG-04 | no thread in a printed part: through-bolt, nut and washers; a heat-set insert only with a written reason | warning; error when the joint is in a load path (one of DG-01's load parts in the joint, or the printed part flagged by DG-01) | `thread_in_printed_part`: a screw whose `threads_into` is a printed part (tapped, self-tapped or a heat-set insert); accepted: `add_screw(..., insert=True, insert_reason="...")` (20 characters or more) or a DG-04 waiver. FST-090 is cross-referenced to it |
| DG-05 | printed clearance holes at ISO 273 medium + the FDM allowance | warning | the narrowest closed section of each printed clearance hole (probed every 0.5 mm along the screw): `printed_hole_too_small` under medium + 0.2 mm (vertical in the print, from `meta["print_up"]`) or + 0.3 mm (axis in the build plane); `printed_hole_oversize_no_washer` over coarse + 0.4 mm with a head or nut bearing on the part bare. Limits `DG-05.allowance_vertical_mm` / `DG-05.allowance_in_plane_mm`. FST-020 keeps the metal parts (its `hole_over_coarse` info no longer reports printed parts) |
| DG-06 | every fastener is a drawn part: the BOM and the model list the same hardware | error | `hardware_bom_only`: a screw, nut, washer, T-nut, insert or clinch nut that exists only as a `design.bom_extra` line; `hardware_count_mismatch`: a hardware SKU whose BOM quantity is not the number of parts drawn; `tnut_not_drawn` / `tnut_without_screw`; `joint_without_fasteners`: a declared join whose kind names a fastener (`m5_tnut`, `through_bolt`, `bolted`...) with no drawn fastener holding both parts. Set screws inside a bought pulley's hub are listed in the metrics (`hardware_completeness.set_screw_joins_not_drawn`), not required as parts. The T-slot screw checks themselves (bottoming, thread in the T-nut, T-nut fit and type) are the interference verifier's (`tslot_screws`); FST-100 is now cross-referenced to them |

DG-01 also recognises a compression sleeve: contact between a printed part and a load part is not a load path when the
screws that clamp the load part beside it pass through a metal spacer declared in the printed part (a join between the
two), the head bears on the spacer directly or through washers, and the printed part touches neither the head nor
those washers (the plastic is located on the sleeve, not clamped). The sleeves found are listed under
`metrics.practice.printed_parts_on_metal_sleeves`. FST-072 (nylon-insert nuts at most about 120 degC; a nyloc on a part
whose `meta["service_temp_c"]` is over `FST-072.max_temp_c`, or on a hotend or heater) is implemented as a warning.

### 8.3 Results

`printer_v8` (`verify designs/printer_v8.py --only practice --no-render`, 172 screws and 6 bearings probed, about
30 s): 16 errors, 41 warnings, 2 info. Errors: FST-060 on the four bed posts (each `nut_top` entirely on the plain shank
of the M5 x 90, each `nut_arm` 2.2 mm onto it); DG-01 on twelve printed parts (`nut_block`, `nut_block_fl`,
`nut_block_fr`: lead-screw nuts; `z_drive_mount`: the Z motor, two bearings, the Z idler; `z_sleeve`, `z_pedestal_fl`,
`z_pedestal_fr`: bearings; `probe_mount`: clamps the extruder; `x_belt_block`: the X belt ends; `x_tension_anchor`,
`y_tension_anchor`, `y_tension_anchor_l`: jack screws carrying belt tension). Warnings, in line with the section 4
audit: FST-070 on 103 screws, SHF-011 on the three Z screws (bearings and pulleys on thread), BRG-020 on all six 608s,
BRG-023 on the three upper bearings, SHF-010 on four motor pulleys, BLT-040 on the 12 mm Y belts, BLT-030 / BLT-031 /
BLT-010 on the Z belt, FST-050 on 15 parts, FST-034 on the bed plate, FST-081 (M3 x 6 and x 8 into MGN12H), FST-051
(arm-end bolts), FST-101 (five parts on one T-nut), LOC-006 (8 adjustments), DG-02 (`tool_plate` tapped; four arm-end
taps). Neither machined part is a DG-03 candidate (both have counterbores).

`ref_vminion` (the Rat Rig V-Minion reference model): 8 errors, 14 warnings, 1 info. The eight errors are DG-01 on the
machine's printed motor cages, idler blocks, belt mount, Z cap and carriage: the owner's practice is stricter than the
reference machine's, so these are true by the rule, not false alarms. False alarms found on it and on `z_axis_v2` /
`pan_tilt` were fixed in the checker (each with a test): a T-nut screw was not counted as the second fixing of a block
also held by an end tap; round standoffs and retainers on their own screw were reported as single-screw joints; one
T-nut in each of two extrusions was reported as two single T-nuts; parts merely beside a screw's shank (inside its head
radius, no hole) were counted as held by it.
