"""printer_v12: the Build 1 candidate. printer_v11 merged with the v11.1 and v12 plans (docs/V11_1_PLAN.md, docs/V12_PLAN.md, every owner
decision of 2026-11-19/20). docs/PRINTER_V12.md has the results, what is real, what is a placeholder and the Build 1 readiness.

Every part carries meta["build_stage"]: 1 frame, electronics bay, bed and Z; 2 XY gantry, toolhead and probe; 3 feedback hardware
(cameras, line laser, accelerometer, filament sensor, lights). The DG-07 report, the sourcing report and the schedule are given per
stage (mechloop/verifiers/purchased.py stage_of, python -m mechloop.sourcing --design designs/printer_v12.py).

What v12 changes against v11:
1. Rails: genuine HIWIN MGN12HZ0C sets (rail + MGN12H, preload Z0, accuracy C) from Motion Constrained, HIWIN's own CAD (REQ-005):
   Y 295 mm, Z 295 mm (both sets), X 245 mm (HIWIN rail only: a 295 mm rail does not fit between the Y blocks, see the doc).
2. Belts 9 mm GT2 (Gates 2MGT, LL2MR09) on X and Y; Y pulleys, idlers and belt slots at 9 mm.
3. Spacers at stock lengths only (Harwin R30); the Z motor posts are turned 6061 standoffs (no stocked M5 round spacer at 55 / 58 mm
   with a maker drawing was found).
4. Bed: Keenovo 200 x 200 mm 24 V 200 W stock heater on the 232 mm MIC-6 plate (studs clear of it); Wham Bam 220 PEI plate and 1 mm
   magnetic base (150 degC); Cantherm CS712025Y 120 degC thermostat clamped to the plate; Semitec 104NT-4 bed thermistor; the bed on
   the Octopus HB output with a 10 A blade fuse (no external MOSFET).
5. Limit (b) after a heat soak: probe once the bed has soaked (time from the carrier's thermal time constant); the thermal case
   carries only the warming left after the soak; the start macro holds the soak.
6. Frame corners: MISUMI HBLFSN5-SEP (30 x 30, cast 383.0) with CBM5-10 and HNTP5-5 spring nuts, every one drawn.
7. Electronics (V12_PLAN): Raspberry Pi 5 8 GB + Active Cooler + own 27 W supply; Finder 22.32 contactor + Phoenix 1119897 interface relay
   + PN2222A from a Pi GPIO (Moonraker [power]); Schurter DD11.0114.1111 + 1-pole drawer 4301.1405 + one SPT T8A; 16 AWG earth to the
   frame stud (one conductor per tab); DIN rail; covers.
8. Sensing (stage 2/3): BTT Eddy Duo replaces the OMRON E2B (printed spacer, 2.5 mm above the tip); Arducam B0454 + Commonlands CIL062
   nozzle camera; Quarton VLM-520-56 line laser in an insulating clamp; Pi Camera Module 3 overview and top-down; BTT ADXL345; BTT SFS
   V2; 24 V COB LED strips in printed clips.
9. Printed parts in PETG from a print service (Hubs rules: 0.8 mm wall, 2 mm feature, +/-0.5 mm).
10. Real-part records (mechloop/data/real_parts.json, part real_part), staged maker files moved to vendor_cad/inbox (SOURCES.md).

Below: printer_v11's own description, unchanged.

printer_v11: printer_v10_1 with purchased parts at stock sizes, a bed sized to the smaller print area, a radial-blower part
cooler, an aluminium probe bracket, flat belt brackets and the owner's fastener decisions. docs/PRINTER_V11.md has what
changed, why, and what is assumed.

What v11 changes against v10.1 (owner-approved, 2026-11-19):
A. Stock parts only. X rail: a stock HIWIN MGNR12R 250 mm (v10: cut to 288) -> X travel 191.6 mm; the beam is 276 mm (ends
   inside the front Z screws). Z: the three 17E19S1684AB4-330RA screws used at 330 mm as sold (328 above the motor face):
   the front two moved to x +/-144.5 (inboard of the top side rails, outboard of the beam's ends and the toolhead's reach),
   the rear one outboard of the back wall (y 202.5, inside the Y motors' footprint, so the envelope does not grow); motors on
   posts of stacked stock spacers. Their POM anti-backlash nuts (a labelled stand-in: no dimensions published) hang below the
   nut plates, flange up, captive under a keeper. T-slot extrusion is the one purchased part bought cut (Misumi HFS5-2020).
B. Bed: 220 x 220 PEI sheet (third-party stock size; the print area is 84.9 % of it) on a 232 x 232 x 6.35 mm MIC-6 plate
   (v10: 12.7), three studs moved to the plate's front and rear edges; three achievable flatness limits replace the 0.02 mm
   sag limit (as installed <= 0.3, change after probing <= 0.1, 1 kg at a corner <= 0.2).
C. Toolhead: one Delta BFB0524HH 24 V 5015 radial blower behind the Roto (outlet down; owner's later change from the GDSTIME GDB4010) with a short printed duct whose outlet
   aims the jet just under the nozzle tip (>= 2.5 mm above the tip, >= 4.5 mm from the heater block), E3D silicone sock.
   Probe holder: a one-bend 5052 L, the OMRON E2B-M12KS04-WP-C1 (shielded M12; owner's later change from the E2E-X5ME1)
   clamped in an M12 hole by its two nuts, 15 mm behind its face.
D. Belt brackets: X belt bracket kept bent (the only bent part); Y tension anchors are stock cast corner brackets on the
   rails' outer faces with an M5 tension screw between jam nuts pushing a second bracket under each Y motor plate's front
   M5; Y motor plates flat (304 1.88); X tension anchor deleted (slotted X motor plate, hand tension); X idler plate flat;
   Y switch on standoffs on a flat plate on the rail's top. The Y belt plane moved 0.36 mm towards the motors (Y idler
   plates 304 1.52) so the Y motor shaft load passes.
E. Fasteners: flanged button heads (ISO 7380-2) on every corner-bracket leg; M5 x 8 with one washer for the v10.1 M5 x 10 +
   two washers; beam bolts M5 x 12 with two washers; M2.5 nuts thread-locked; Accu A2 large washers.
F. Supplier CAD folded in: Misumi HFS5-2020 section, KIPP thumb nut, Century spring, Schurter inlet, Delta blower, OMRON E2B probe
   (OMRON's STEP, adopted 2026-11-20).

Below: printer_v10_1's own description, unchanged.

printer_v10_1: printer_v10 with every fastener drawn and every T-slot screw checked for length. docs/PRINTER_V10_1.md has
what changed, what the new checks found and what is assumed.

What v10.1 changes against v10 (frame, envelope, travel, bed, cooling fan and duct, belt tension brackets and probe mount are v10's):
- d.tnut_style = "drop_in": every tnut=True screw and every corner-bracket leg has its own drawn drop-in T-nut (catalogue
  tnut_2020: Misumi HNTAJ5, re-made from the maker's catalogue drawing), and every bracket leg its own M5 x 8 cap screw.
- T-slot screw lengths, so the tip ends at least 0.5 mm above the slot floor (6.0 mm deep, 2.0 mm lip: Misumi's drawing)
  with at least 0.5 d of thread in the nut (3.2 mm of thread, from 1.2 to 4.4 mm below the face): a second washer under the
  M5 x 10 on 3.2 mm and 2.5 mm plates (deck, X motor, idler and tension-anchor plates, Y tension anchors, tray, inlet panel),
  M5 x 12 on the 6.35 mm nut plates, M5 x 8 on the 1.9 mm Y motor and idler mounts, M5 x 6 on the earth stud.
- No BOM-only hardware: the PEM nuts are catalogue parts (stand-in solids), the nut keepers' nylocs are drawn as nylocs, the
  earth stud's toothed washer is drawn, the nut pins' hex nuts are thread-locked instead of swapped for M2.5 nylocs.
- The hardware that is bought: McMaster's washers (0.1 mm thicker), the DIN 934 M5 nut.

Below: printer_v10's own description, unchanged.

printer_v10: printer_v9 with the gantry's ends and the toolhead redrawn for X travel, the bed sized to the nozzle's reach,
and three levelling points instead of four. docs/PRINTER_V10.md has the numbers, every judgement call and the open items.

The frame (every extrusion, the 340 x 373 x 404 mm cube and the 420 mm envelope) is v9's, untouched. What changed:

1. X TRAVEL 229.6 mm (v9 180). The X rail is as long as the 288 mm beam (HIWIN MGNR12R cut to length; v9 a stock 250), so
   the guide block's centre runs +/-116.3 mm with 5 mm of rail left at each end. To let it:
   - the X motor and idler stand outboard of the block's travel, over the Y plates (pulley centres -141.8 / +142.8, belt
     plane 8 mm higher); their mounts keep their bolts on the beam's front face and reach outward above the Y plates;
   - the Y plates end in front of the block's path over the beam; from x 140.8 outward a tab on each is the hard stop for
     the tool plates' edge, 1.5 mm beyond the travel (v9's two rail-stop plates are gone);
   - the toolhead is centred on the block: the Roto (16.2 mm left and 40.9 mm right of its nozzle) and the part fan's plenum
     (46.8 right) sit 15.5 mm to the left, so the 63 mm between Roto and plenum clears the top side rails by 2.0 and 2.4 mm at
     the ends of travel; the HeaterCore's lead sleeve points forward, under the tool plates (their bottom edge 2 mm higher);
   - the X switch moved to the right Y plate's land (worked by a striker tab on the front tool plate; X homes at maximum), the Y
     switch to a bent bracket in the right top rail's top slot (worked by that land's rear edge), the toolhead loom's
     anchor to the top of the back rail.
   Both ends are now set by the beam's length between the Y blocks (5 mm of rail kept beyond the block) with the Roto and
   the plenum 2.0 and 2.4 mm from the top side rails. Y travel is v9's 214.5 mm: confirmed at its limit (front: Y idlers and the 420 mm envelope,
   bolt heads 3.5 mm from the top front rail; rear: fan screws 1.44 mm from the top back rail).
2. BED: 235 x 235 mm PEI sheet (catalogue print_sheet_pei235) on a 241 x 241 x 12.7 mm MIC-6 plate, centred on the nozzle's
   reach (x -15.5, y 4.5): the 229.6 x 214.5 mm print area is 89 % of the sheet (v9: 58 % of a 257 mm sheet). Heater pad
   230 x 207 mm, 180 W: the print area's whole width and all but 3.75 mm of its depth at each end.
3. THREE LEVELLING POINTS: front left (fitted hole), front right (slot), rear centre (oversize hole), each beside a member
   of the square and near a lead screw. Same stack as v9 (M4 countersunk stud locked by washer and nut under the plate, die
   spring, thumb nut under the deck; no tapped aluminium), M4 x 40, spring compressed 8 mm (61 N), +/-1.5 mm. On three points the two
   rear print corners overhang the rear stud by 115 mm, so the plate is 12.7 mm (v9 6.35 on four); the nut plates are 6.35 mm
   (v9 4.75) for the heavier bed.
4. MOTOR TILT: the bed-support checker now works out how far one Z motor may stand out of the plane of the other two before
   a guide block's static rating, a carriage plate's web or a nut seat reaches its limit (requirement and metrics); the web's
   dimensions and the nut seat's play are declared for it.
The carrier's 2020 square and deck outline, the carriage plates, keepers and motor plates, the three Z rails and motors and
the electronics are v9's.

Layout (X = width, Y = depth with the front at -Y, Z = up) is v4's; see designs/printer_v4.py for the history.

Not modelled (flagged): as v9 (Roto envelope, T-nuts, PEM nuts, BAT85, Revo clip are BOM lines or notes; payload is extra
mass on the bed plate; no airflow model; pulley set screws; belt teeth; screw whip by hand in the doc; the springs are tubes
and are left out of the FEA; friction at the sliding levelling points), and: the X motor mount's wing is not in the nozzle
stiffness cases (they hold the Y plates and load the nozzle; the belt path is the twin's).
"""
import math
import re

import numpy as np
from build123d import (Box, Cylinder, GeomType, Location, Plane, Polygon, Pos, RectangleRounded, RegularPolygon, Rot,
                       chamfer, extrude, fillet)

from mechloop import Adjustment, AssemblyCase, Design, Joint, LoadCase, Requirement
from mechloop.electrical import Bay, Device, Electrical, Port, Waypoint
from mechloop.model import MATERIALS, Belt, ModalCase, ThermalCase
from mechloop.parts import (Stock, add_corner_bracket, add_nut, add_screw, add_washer, clearance_hole,
                            endstop_switch, extrusion_2020, gt2_idler, gt2_pulley, leadscrew_nut_t8,
                            mgn12_rail, mgn12h_carriage, nema17, place, printed_clearance_hole)
from mechloop.parts.batch6 import fan_cg3010u24
from mechloop.parts.batch7 import leadscrew_motor_17e19_ab4, leadscrew_screw_17e19_ab4, octopus_v11
from mechloop.parts.batch8 import add_thumb_nut, die_spring_dj8x20
from mechloop.parts.batch10 import blower_bfb0524hh, blower_flow_estimate_pa, leadscrew_nut_pom_ab4, print_sheet_pei220
from mechloop.parts.hardware import washer_toothed
from mechloop.parts.electrical import (THERMISTORS, add_electrical_bom, bed_heater_pad, device_from, embedded_device,
                                       iec_inlet_c14, psu_lrs, raspberry_pi_zero2w, relay_btt_v12, thermal_fuse)
from mechloop.parts import BRACKET_CAD_SLOT, BRACKET_SLOT_LEG, CSK, corner_bracket_2020
from mechloop.parts.hardware import WASHER, spacer_round
from mechloop.parts.probes import add_probe_nuts, probe_omron_e2e
from mechloop.parts.toolhead import extruder_roto, hotend_revo
from mechloop.shops import assign
from mechloop.parts.batch12 import (add_bracket_misumi, adxl345_btt, cam_arducam_b0454, cob_led, contactor_finder_2232, din_endstop_wago,
                                    din_rail_wago, heater_keenovo_200, hiwin_mgn12_rail, hiwin_mgn12h_block, laser_vlm520, lens_cil062,
                                    leadscrew_motor_a4003, leadscrew_nut_pom_a4003, leadscrew_screw_a4003, picam3, pi5_host, probe_eddy_duo,
                                    relay_phoenix_1119897, sfs_v2, spacer_harwin, thermostat_cs7,
                                    whambam_base_220, whambam_plate_220)

# ---- brief ------------------------------------------------------------------------
PRINT_X, PRINT_Y, PRINT_Z = 186.6, 214.5, 180.0     # v12: X from a 245 mm HIWIN rail (v11 191.6 on a 250 mm rail)
_V11_PRINT_X = 191.6     # v11: X is what a stock 250 mm X rail gives (v10 / v10.1: 229.6 on a cut 288 mm rail)
PAYLOAD_KG = 1.0
V_XY, A_XY = 250.0, 4000.0
V_Z, A_Z = 12.0, 200.0
MARGIN = 3.0
ENVELOPE = (420.0, 420.0, 480.0)
MAX_TOOLHEAD_KG, MIN_BELT_IN_PLANE = 0.45, 0.98   # v12 (owner, Q9): toolhead under 0.45 kg with the new sensors

# ---- electrical choices -----------------------------------------------------------
BED_W = 200.0          # v12: the Keenovo stock pad, 200 W (8.3 A at 24 V) on the Octopus HB output, 10 A blade fuse          # 180 W pad on the board's own bed output (7.5 A of 8 A allowed), as v7 / v8
BED_MAX_C = 80.0       # v11 (owner): PLA and PETG only, no enclosure, max bed 80 degC; the magnetic base is to be bought rated 120 degC continuous
PSU_MODEL = "LRS-350-24"
BED_AWG, BED_INS = 16, "silicone"
RUN_CURRENT = {"x": 0.28, "y": 1.20, "z": 0.80, "extruder": 0.40}   # z: per motor, three motors (rated 1.68 A)
BOARD_XY = (94.5, 5.0)  # BTT Octopus V1.1, turned so its motor connectors face +X (the right-hand rail)
HOST_XY = (75.0, -105.0)   # v12: the Pi 5 (85 x 56), between the supply and the front-right Z motor
FUSE_A = 8.0
T_TRAY = 3.175         # v8.1: SendCutSend 6061 .125"
TRAY_Y0, TRAY_Y1 = -140.5, 85.0      # v12: 1.5 mm back (the 30 mm bracket legs end at -143); v11: -142      # v11: front edge 4 mm further forward, under the front Z posts' spacers
Z_TRAY = 20.0 + T_TRAY

# ---- materials and stock (SendCutSend gauges, mm) ----------------------------------
AL, AL_BEND, SS, CAST = "al6061", "al5052", "stainless304", "al_mic6"
G16, G20, G25, G32, G48, G64, G95, G127 = 1.6, 2.032, 2.54, 3.175, 4.75, 6.35, 9.525, 12.7   # 6061-T6 .063 .080 .100 .125 .187 .250 .375 .500
B23, B32 = 2.286, 3.175                                                  # 5052-H32 .090 .125
R_B32, R_B23 = 3.18, 0.81                                                # SendCutSend's only inside bend radius for those gauges
SS15 = 1.524                                                             # 304 .060
R_SS15 = 1.78
HOT = "petg"           # v12: every printed part is PETG from a print service (ROADMAP, Build 1); the duct included (Tg about 80 degC: watch it on the first hot prints)
COOL = "petg"          # printed covers on the cold frame
PRINT_ABS = {"walls": 4, "top_layers": 5, "bottom_layers": 5, "infill": 0.4, "infill_pattern": "gyroid", "layer_height_mm": 0.2,
             "line_width_mm": 0.45}

# ---- frame ------------------------------------------------------------------------
FX, FY, FZ = 340.0, 360.0, 394.0
RAIL_X = FX / 2 - 10
TX, TY = PRINT_X / 2, PRINT_Y / 2
FRONT_EXT = 13.0       # v8.2 (owner review): the frame's front is 13 mm further forward and its top front rail flush with the
                       # other three (v8.1: 30 mm lower, FT_DROP, so the gantry's front parts passed over it). At full -Y
                       # over-travel the gantry's front-most parts below z 407 (the X mounts' M5 bolt heads on the beam's
                       # front face) reach y -169.5; the flush rail's inner face is now at -173.0 (3.5 mm clear). The X idler
                       # mount's and tension anchor's lugs are trimmed to start 4 mm above the rail (z 408). 13 mm keeps the
                       # machine inside its 420 mm envelope (26 mm, lugs untrimmed, made it 431)
FD = FY + FRONT_EXT    # frame depth, outside to outside of the front and back rails
FRONT_Y = -(FY / 2 - 10) - FRONT_EXT   # centre line of the front rails and posts (v8.1 -170)

# ---- toolhead offset (v10) -----------------------------------------------------------
C_NOZ = 15.5           # the nozzle is 15.5 mm to the LEFT of the X guide block's centre: the Roto reaches 16.2 mm left and
                       # 40.9 mm right of its nozzle, and the part fan's plenum 46.8 mm right, so the toolhead (63.0 mm wide
                       # between Roto and plenum) is centred on the block and fits the 300 mm between the top side rails
                       # at both ends of the rail's travel. The nozzle's travel, and so the bed, is centred on x = -15.5
NOZ_X = -C_NOZ         # world x of the nozzle at the home pose (the X block at the beam's centre)
# ---- Z stage (v9 / v10): bed, deck, 2020 square, three rails ------------------------
SHEET = 220.0          # v11: print sheet (catalogue print_sheet_pei220, a third-party stock size): the 191.6 x 214.5 mm reach is 84.9 % of it
BED = 232.0            # v11: MIC-6 plate, square: 6 mm of margin round the sheet (the studs' countersinks sit in that margin's band)
T_BED = G64            # v11: 6.35 mm MIC-6 (v10 12.7): the thinnest stock thickness meeting the three flatness limits (requirements)
MIC6_FLAT_BOUGHT = 0.127   # mm: flatness of the plate as bought, the owner's figure ("MIC-6 ~0.13 mm per McMaster listing"); the
                           # maker's brochure in the repository gives 0.381 mm for 6.35 to 15.9 mm plate (whole cast plate). The
                           # 0.127 is taken as a receiving-inspection limit on the cut 232 mm piece (docs/PRINTER_V11.md)
MIC6_FLAT_MAKER = 0.381
FLAT_AS_INSTALLED, FLAT_AFTER_PROBING, SAG_1KG_CORNER = 0.3, 0.1, 0.2   # v11: the three limits the owner set
BED_CX = NOZ_X         # centre of sheet and plate in X = centre of the nozzle's reach
T_MAG = 1.0  # v12: Wham Bam base, 1 mm (maker page). v11: 1.5 stand-in.            # the sheet's magnetic base: NOT published by any seller read; 1.5 mm from other sellers' kits (stand-in)
T_SHEET = 0.64  # v12: Wham Bam plate, 0.4 steel + 2 x 0.12 PEI. v11:          # spring steel (catalogue; a third-party figure)
BED_CY = 4.5           # centre of sheet and plate in Y = centre of the gantry's (unchanged) nozzle reach, world y -102.75 .. 111.75
BED_Y0, BED_Y1 = BED_CY - BED / 2, BED_CY + BED / 2
BED_X0, BED_X1 = BED_CX - BED / 2, BED_CX + BED / 2
W5 = WASHER["normal"]["M5"][2]
PAD_X, PAD_Y = 200.0, 200.0   # v12: Keenovo's stock 200 x 200 pad, centred on the plate (3.5 mm clear of the studs' washers)   # v11 heater pad (made to size): the print area's full width, and its depth between the front studs' and the rear stud's washers
# guides: one MGN12 rail + one ZF block per wall; a flat plate with a flexure web ties each block to the square
RAIL_FACE = 13.0       # MGN12H: rail base to the block's mounting face
T_CP = G16             # carriage plates: 1.6 mm 6061 (the web is the radial flexure)
CP_W, CP_WEB, L_FLEX = 50.0, 24.0, 30.0      # plate width, web width, web length
CP_BOLT_U = 16.0       # the plate's two M5 into the square, +/- along the wall from the rail (the driver passes the upright)
K_FLEX = MATERIALS[AL].E * CP_WEB * T_CP ** 3 / L_FLEX ** 3        # web as a guided beam: 12 E I / L^3 = 251 N/mm
FLEX_RANGE = 0.35      # mm: web bending stress 3 E t x / L^2 = 129 MPa there (half of 6061-T6's yield)
WEB_TEST_N = 5.0       # FEA beam test of the web (AssemblyCase carriage_plate_web)
WEB_TEST_MM = WEB_TEST_N * (L_FLEX ** 3 / 3 + L_FLEX ** 2 * 23.7 + L_FLEX * 23.7 ** 2) / (MATERIALS[AL].E * CP_WEB * T_CP ** 3 / 12)
WALL_X = FX / 2 - 20   # inner face of the side walls (150)
UP_Y = FY / 2 - 10     # rear upright in the back wall (y 170)
Y_FACE = UP_Y - 10     # inner face of the back wall (160)
UP_R_X = 65.0          # rear upright: beside the rear screw's motor plate
UP_S_Y = -32.0         # side uprights: between the front motor mounts and the mains inlet's hood
SQ_X = WALL_X - RAIL_FACE - T_CP          # the square's outer side faces at +/-135.4
SQ_Y1 = Y_FACE - RAIL_FACE - T_CP         # its rear outer face (145.4)
SQ_Y0 = 2 * BED_CY - SQ_Y1                # its front outer face (-136.4): the rectangle is centred on the bed
T_DECK = G32           # deck: 3.175 mm 6061 (1/8 in)
# bed mount: stud (M4 countersunk) - washer - nut - die spring - seat washer - deck - large washer - thumb nut
W4, W4L, NUT4 = WASHER["normal"]["M4"][2], WASHER["large"]["M4"][2], 3.2
SPRING_H = 12.0        # DJ-8X20YCS installed: 8 mm of its 20 compressed, 60.8 N (range 10.5..13.5 mm: 72..49 N; the maker lists to 10 mm
                       # of deflection). v9: 14 mm, 45.6 N: three studs carry more each, the rear one half the bed
SPRING_K = 7.6
GAP = W4 + NUT4 + SPRING_H + W4           # plate underside to deck top: 16.8 mm
STUD_L = 40.0          # M4 x 40 countersunk: 12 mm in the plate, 16.8 gap, deck, washer, 7 mm into the thumb nut
CSK_SINK = (CSK["M4"][0] - CSK["M4"][1]) / 2      # 0.72 mm: how far an M4 countersunk head sits below the surface
LEVEL_RANGE = 1.5      # +/- at each thumb nut (v9 2.0: the spring's 10 mm and the preload margin leave 1.5; the stack-up needs 0.7)
LEV_X, LEV_Y = 86.0, 108.0                # v11: 108 (v10 109.5): 8 mm inside the 232 mm plate's edges; three studs: front pair at (+/-86, BED_CY - 109.5) beside the square's front member (thumb nuts
                                          # clear of its corner brackets), the rear one on the bed's centre line beside the rear member:
                                          # each 11.4 mm from a member's inner face and within 60 mm of a lead-screw nut
# deck hole per stud (thermal growth of the plate): 0 fitted, 1 slot towards 0, 2 oversize
BED_MOUNTS = [(-LEV_X, BED_CY - LEV_Y), (LEV_X, BED_CY - LEV_Y), (BED_CX, BED_CY + LEV_Y)]
DECK_FIT, DECK_FREE = 4.3, 5.5
# v11: the 330 mm screws (328 above the motor face, as sold) cannot stand under the top rails with their motors on the bottom
# rails (motor body 48 + screw 328 = 376 > the 364 between the rails' faces). So the front two stand INBOARD of the top side
# rails (x +/-144.5: the screw 1.5 mm from the rail's inner face, outboard of the 276 mm beam's ends and the toolhead's reach)
# with their motors on the tray over the bottom side rails, and the rear one OUTBOARD of the back wall (y 202.5, its motor
# beside the bottom back rail inside the Y motors' footprint): the envelope does not grow
LS_Y = 202.5           # v11: rear lead screw outboard of the back wall (v10: 170, on the bottom back rail)
FS_X = 144.5           # v11: front lead screws inboard of the side rails (v10: 160, over them)
FS_Y = -101.0
NUT_OUT_R = LS_Y - SQ_Y1      # 57.1: the rear nut plate reaches out through the back wall
NUT_OUT_F = FS_X - SQ_X       # 9.1
NUT_OUT = NUT_OUT_F
NUT_PIN = (-9.25, 9.25)       # v12: a corner hole of the POM nut's flange (4 x M4 on 18.5, drawing A4003)         # v11: the anti-rotation pin in a corner hole of the POM nut's square flange
KEEP_HOLES = None             # set below: the keeper's two bolts (one each side of the open slot)
NUT_FLOAT = 2.0               # v12: 2.0 (v11 2.8): the A4003 barrel is 18 mm, the keeper's web stays 2.6 mm
NUT_FT = 5.0                  # v12: the POM nut's flange thickness, drawing A4003
KEEP_GAP, T_KEEP, KEEP_BX = 1.0, 3.175, 19.0   # v12: 1.0 mm play: a stock 6 mm Harwin spacer over the 5 mm flange (v11 0.1 on a custom 6.1)   # nut keeper: axial play, thickness (6061), bolts along the member from the nut
KEEP_HOLES = [(-KEEP_BX, 0.0), (KEEP_BX, 16.3)]   # v12: 16.3 (v11 15.5): webs to the pin nut's slot and the plate's edge  # v11: the +x one beside the open slot (local x along the member, y outward)
Z_DN = 3.0
Z_UP = 1.65
Z_RAIL_L = 295.0       # v12: the MGN12HZ0C set's 295 mm rail
Z_RAIL_C_FIXED = 202.05       # v12: 20 mm higher than v11 (179.05): the 295 mm rail's foot clears the Octopus       # v11: the Z rails stay where v9 / v10 had them (the carrier rides 6.35 mm higher on the thinner plate)

# ---- gantry -----------------------------------------------------------------------
Z_RAIL = FZ + 10
Z_PLATE = Z_RAIL + 13
T_YP = G48             # Y plates: 4.75 mm 6061 (v8: 3 mm steel)
Z_BEAM = Z_PLATE - 10.0
PR = 20 * 2.0 / math.pi / 2
BWX, BWY = 9.0, 9.0    # v12: 9 mm GT2 (Gates 2MGT stock width) on X and Y
P_BC = lambda w: 7.0 + (w + 1) / 2
I_H = lambda w: w + 2.5
SS19, R_SS19 = 1.88, 1.9   # 304 .074, SendCutSend's bend radius
MT_Y = SS19            # Y motor mounts: 1.88 mm 304 (v11: flat, the bent fin is gone; owner: keep the gauge)
MT_YI = SS15           # v11: Y idler mounts 1.52 mm 304 (SendCutSend .060; v10.1 1.88): the belt plane, which the idler's stack sets, is
                       # 0.36 mm nearer the Y motors' faces (10.97 mm), so the belt's pull on each motor shaft is within its allowance
MT = G32               # X motor mount (6061) and X idler mount (5052): 3.175 mm
R_TPF = 10.0 + 13.0
T_TPF, T_TPR = G32, G48            # tool plate: front 3.175 (on the guide block), rear 4.75 (counterbore for the block screws)
T_TP = T_TPF + T_TPR
R_TPR = R_TPF + T_TP
_ROTO = extruder_roto().interfaces
ROTO_W = _ROTO["mount_width"]
ROTO_NX, ROTO_NY, ROTO_NZ = _ROTO["nozzle_tip"][0]
ROTO_H2 = _ROTO["mount_holes_m3"][1]
HOT_OFF = R_TPR + ROTO_W / 2 + ROTO_NY
YB0 = BED_CY - HOT_OFF
ROTO_O = (-ROTO_NX + NOZ_X, YB0 + R_TPR + ROTO_W / 2, Z_BEAM)
Z_NOZZLE = ROTO_O[2] + ROTO_NZ
NOZZLE_GAP = 0.1
BEAM_L = 276.0         # v11: ends at +/-138, 2.5 mm inside the front lead screws (v10: 288, between the Y blocks)
X_RAIL_L = 245.0       # v12: HIWIN MGNR12R 245 (standard length, E 10/10); 295 does not fit between the Y blocks       # v11: a STOCK HIWIN MGNR12R 250 mm, not cut (v10: cut to 288)
X_BLOCK_L = 45.4       # MGN12H
ES_OT_X = 1.5          # X over-travel past the working range at each end (the switch's lever spread at the right end)
X_CAR_MAX = X_RAIL_L / 2 - 5.0 - X_BLOCK_L / 2        # 116.3: the X block's centre with 5 mm of rail left beyond it
assert abs(PRINT_X / 2 - (X_CAR_MAX - ES_OT_X)) < 1e-9, 'PRINT_X is the rail-limited working travel'
X_CLAMP_HW = 15.0      # half width of the belt bracket and clamp on the tool plate
XM_X = -(X_CAR_MAX + X_CLAMP_HW + 2.5 + 8.0)          # -141.8: X pulley (flange radius 8) 2.5 mm beyond the clamp at the end of travel
XI_X = X_CAR_MAX + X_CLAMP_HW + 2.5 + 9.0             # 142.8: X idler (flange radius 9)
XD_Z = Z_BEAM + 41.0   # v10: 8 mm higher than v9: the motor and the idler now stand outboard of the beam's ends, over the Y plates,
                       # and must clear the Y plates and the heads of the Y blocks' screws
LUG_Z0 = FZ + 10.0 + 4.0  # v8.2: the X idler mount's lug and the X tension anchor's fin start 4 mm above the flush top front rail
X_PG = 2.75
XB_Y = YB0 - 10.0 + X_PG + P_BC(BWX)
X_SP = XB_Y - I_H(BWX) / 2 - (YB0 - 10.0)
Z_XL = XD_Z - PR
Y_SP = 2 * W5                      # v8.2: two M5 washers between each Y idler and its mount (BLT-061: 2 mm to the plate; v8.1 one)
YB_X = FX / 2 + MT_YI + Y_SP + I_H(BWY) / 2     # v11: from the idler plate's thickness (1.52), 0.36 mm nearer the motor face than v10.1
YM_Y = FY / 2 + 24.0
Z_YA = Z_PLATE + T_YP + 0.7
Z_YC = Z_YA - PR
BELT_ADJ = 3.0
# clearance holes in PRINTED parts (owner's practice, docs/DESIGN_GUIDELINES.md): ISO 273 medium + 0.2 mm FDM allowance for a
# vertical hole (M3 3.6, M5 5.7); every printed clearance hole in v8.1 is vertical in its print orientation
PH3, PH5 = printed_clearance_hole("M3"), printed_clearance_hole("M5")
# captive nut pocket in a printed part: nyloc M3 (ISO 10511, 5.5 across flats, 4.0 high) with an M3 washer (7.0 x 0.5) in front
# tightening torque for an M3 through-bolt that clamps a printed part (stated, not the 0.5 N.m the checker assumes for
# plastic): about 520 N of preload, 18 MPa under an M3 washer, well under the printed yield (ABS 30.8, PETG 47 MPa)
PRINTED_JOINT_TORQUE = 0.3
POCKET_AF, POCKET_NUT, POCKET_WD, POCKET_W, POCKET_WALL = 5.5 + 0.3, 4.0 + 0.2, 7.0 + 0.4, 0.5 + 0.1, 2.0
SH3 = 3.6
YH3 = 3.5
CB_TS = T_TPR
PL_Y0, PL_Y1 = -23.5, 19.5     # v8.2: front edge 0.5 mm back (BLT-061: 2.05 mm from the Y idler at full travel)
BELT_SLOTS = (-15.3, -5.5, 5.5, 15.3)   # v8.1: slots as wide as the sheet is thick, webs >= 4.75
SLOT_W = 4.8
YP_IN = 108.0          # v11: the Y plates reach in to x 108 over the shorter beam (v10: 127), for the beam bolts
YP_NOTCH = (RAIL_X - 15.5, -8.0)

# bed heights follow from the nozzle
Z_SURF = Z_NOZZLE - NOZZLE_GAP - PRINT_Z
Z_BED = Z_SURF - T_SHEET - T_MAG - T_BED          # underside of the bed plate
Z_DECK1 = Z_BED - GAP                             # top of the deck
Z_SQT = Z_DECK1 - T_DECK                          # top of the 2020 square
Z_SQ = Z_SQT - 10.0
Z_SQB = Z_SQ - 10.0
T_NP = G95                                        # v11: nut plates 9.525 mm 6061 (v10 6.35): the rear one reaches 57 mm out through the back wall
Z_TAB = Z_SQB - T_NP                              # underside of the nut plates = top of each nut's flange
ZC = Z_SQB - L_FLEX - 1.0 - 22.7                  # centre of the guide blocks (they hang below the square on the plates' webs)
Z_RAIL_C = Z_RAIL_C_FIXED                            # v11: rails where v9 / v10 had them; the blocks ride 6.35 mm higher (11.5 mm of rail below, 8.5 above)
NP_HOLE = 2 * (4.0 + NUT_FLOAT) + 0.8             # v11: the screw passes the plate with the nut's float (the POM nut's barrel hangs BELOW)
KP_HOLE = 2 * (18.0 / 2 + NUT_FLOAT) + 0.8        # v12: the A4003 barrel, dia 18        # v11: the keeper's hole: the POM barrel (12.7, stand-in) with its float
NP_U, NP_R1 = 27.75, 23.5                         # nut plate: half length along the member (v11: 27.75, clear of the posts' drivers), reach beyond the nut
NP_BOLT_U = 20.0                                  # its two M5 into the member's bottom slot (5.0 mm from the plate's ends)
PIN_SP_D = 5.0                                    # anti-rotation pin: an M2.5 screw through a 5 mm aluminium sleeve
# ---- Z drive: three integrated lead-screw motors, one per screw, no belt (v8.2) ---------------------------------------
Z_BASE_R, Z_BASE_F = 20.0, 20.0 + T_TRAY          # v11: post bases: the bottom back rail's top (rear), the tray on the side rails (front)
POSTS_R, POSTS_F = (40.0, 13.2), (40.0, 9.0)      # v11: each post is two STOCK aluminium spacers (OpenBuilds lengths), stacked
Z_MF_R, Z_MF_F = Z_BASE_R + sum(POSTS_R), Z_BASE_F + sum(POSTS_F)   # 73.2 / 72.175: motor faces = undersides of the plates
Z_MF = Z_MF_F
T_MP = G64                                       # motor plate 6.35 mm 6061
Z_MPT = Z_MF + T_MP
Z_SCREW_ABOVE = 328.0                            # v11: the screw as sold (330 nominal; 328 above the face as the sister model's STEP has it),
                                                 # NOT cut: tops at 401.2 (rear, outside the back wall) and 400.2 (front, inboard of the top rails)
MP_POST_DY = 33.0                                # v11: front posts +/- along the rail from the screw, clear of the nut plate and keeper
MP_POST_DX_R = 28.0                              # rear posts +/- along the back rail (the rear upright's brackets are at 35 to 55)
MP_PILOT_HOLE = 22.3                             # the motor's 22 mm pilot locates in it
PSU_COVER_TOP = 56.04                            # mains cover over the supply's terminals (v8.1: 2.8 mm under its belt plane)
# Y endstop
ES_TRIG, ES_SIDE = 8.3, 9.0
TPX = 23.0             # half width of the tool plates (on the X block)
YP_REAR = 11.0         # v10: over the beam the Y plates end 11 mm behind its centre line, 2 mm in front of the X block's path
X_STOP = X_CAR_MAX + TPX + 1.5    # 140.8: from here outward each Y plate reaches back; its inner edge is the hard stop for the tool
                                  # plates' edge, 1.5 mm beyond the mechanical travel (what the stack-up of sheet parts needs to stay open)
STOP_Y1 = 29.0         # the stop tabs end 1.9 mm in front of the Roto's front face (the Roto is wider than the tool plates)
TAB_X1 = 163.0         # outer edge of the stop tabs and of the land
LAND_X0, LAND_Y1 = X_CAR_MAX + (40.9 - C_NOZ) + 2.0, 50.0     # right Y plate's land behind the stop tab: inner edge 2 mm beyond the Roto's reach;
                                                              # it carries the X switch and its rear edge works the Y switch
ES_SP_XS = 5.0  # v12: Harwin R30-6700594 (stock 5; v11 5.5)         # spacers under the X switch (its M3 x 16 then end 1.3 mm above the right Y rail)
ES_SLOT = 2.0
ES_OT = 1.5
YIM_BOLTS = (-174.0, -126.0)
YEM_BOLTS = (89.0, 101.0)
Y_RAIL_C = -32.0       # v12: the 295 mm rail 3.5 mm further forward (v11 -28.5 on 300): >= 5 mm of rail beyond the block at both ends
ES_SP = 4.0
ES_SP_X = 8.0
RAIL_SCREW_STEP = 2
BEAM_BOLT_X = (116.0, 130.0)     # v11: inside the 276 mm beam's ends (v10: 127, 139)
X_ES_Y = 34.4          # X switch: centre of its board, behind YB0 (lever tip at 25.4, on the front tool plate's striker tab; its front
                       # screw's washer then clears the Y block by 0.7 mm)
# bed probe: OMRON E2B-M12KS04-WP-C1 (v10.1: E2E-X5ME1) 34.5 mm behind the nozzle reading the print sheet's steel
PRB_MODEL = "E2B-M12KS04-WP-C1"       # v11 (owner, 2026-11-19): OMRON E2B shielded M12, 4 mm, NPN NO, Digi-Key (was E2E-X5ME1)
PRB_H = 2.0
PRB_X = NOZ_X          # on the nozzle's X: no X offset
PRB_DY = 34.5
PRB_Y = HOT_OFF + PRB_DY
TY_F = TY                                       # v9: the print area is the whole Y travel; the front PRB_DY of it is beyond the probe
YI_Y = YB0 - 24.0 - (TY_F + ES_OT) - 10.5      # as v8.1 (same place in the frame as v8.2: the home pose moved, the travel did not)
# Klipper [z_tilt]: firmware X = world x - NOZ_X + TX (0 at the left end of the nozzle's travel; X homes at the right end), firmware Y = world y - (nozzle's home y) + TY_F
_FW = lambda x, y: (round(x - NOZ_X + TX, 2), round(y - (YB0 + HOT_OFF) + TY_F, 2))
Z_TILT = {"z_positions": [_FW(0.0, LS_Y), _FW(-FS_X, FS_Y), _FW(FS_X, FS_Y)],       # rear, front-left, front-right screw
          "points": [(TX, 185.0), (10.0, 5.0), (2 * TX - 10.0, 5.0)],                 # nozzle; probe 34.5 mm behind it
          "speed": 100, "horizontal_move_z": 5, "retries": 5, "retry_tolerance": 0.0075}
Z_PRB = Z_NOZZLE + PRB_H
PRB_CLAMP = (15.0, 15.0 + B32)    # v11: the 5052 L's horizontal leg, 15 mm behind the sensing face (kept from the unshielded E2E; the E2B needs 2.4)
PM_T = 4.0                                        # aluminium compression sleeves (4 mm long) through the printed probe holder
PM_TP = PM_T - 0.6                                # the holder plate: 0.6 mm thinner than its sleeves (the printed minimum clearance
                                                  # 0.5, and open in every simulated build), so the screw clamps metal only
PM_Z0, PM_Z1 = Z_PRB + PRB_CLAMP[0] - Z_BEAM, Z_PRB + PRB_CLAMP[1] - Z_BEAM
TP_Z0, TP_Z1 = -16.0, 38.0   # v10: bottom edge 2 mm higher (v9 -18): the HeaterCore's lead sleeve passes 2.2 mm under it
TAB_R = (13.5 + NOZ_X, 38.5 + NOZ_X, -27.0, -14.0)   # the duct flange's tab: -2 .. 23 from the block's centre, inside the plate's width
STRIKER = (TPX + 4.9, 20.75, 27.5)                   # v10: a tab on the FRONT tool plate's right edge (x to 27.9, z from Z_BEAM) that works
                                                     # the X switch: it reaches 2.5 mm beyond the Roto's right side (25.4)
LEAD_RELIEF = (16.0, 18.0)                           # v10: the REAR tool plate's upper right corner (x > 16, z > 18) is cut away for the plug
                                                     # of the Roto's motor lead (at x 22.3, z 21.9, leaving forward and up at 45 degrees)
LEAD_RELIEF_F = (19.5, 27.5)                         # and the FRONT plate's above the striker tab (x > 19.5, z > 27.5): the plug's last 3 mm
FC_X0, FC_X1 = TAB_R[0], TAB_R[1]
FC_FL = 8.5                                       # duct flange: holds two M3 heat-set inserts
FC_Z0, FC_ZF = TAB_R[2], -12.8
DUCT_Z0 = -31.0
DUCT_W = 1.6
FC_LUG_Y = R_TPR + ROTO_W + 1.5
PLEN = 7.0
PFAN = (30.3 + NOZ_X, FC_LUG_Y + PLEN + 5.0, -16.0)
PLEN_X0, PLEN_X1 = PFAN[0] - 16.5, PFAN[0] + 16.5
FC_SCREWS = [(19.0 + NOZ_X, -20.5), (30.5 + NOZ_X, -20.5)]
DUCT_OUT = (40.0, 52.0, -29.0, -23.0)
BLK_SCREWS = [(-9.5, 20.5), (9.5, 20.5)]          # belt bracket -> tool plate (x, z from Z_BEAM)
CLAMP_Y = (-1.8, 12.2)                            # belt clamp screws, from YB0: just in front of and behind the 9 mm belt
NUT_AF3, NUT_T3 = 5.5, 2.4


# =================================================================== helpers
def bx(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))


ycyl = lambda r, h: Rot(90, 0, 0) * Cylinder(r, h)
xcyl = lambda r, h: Rot(0, 90, 0) * Cylinder(r, h)


def zc(x, y, z0, z1, r):
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(r, z1 - z0)


def slot_z(x, y, angle_deg, half_len, width, z0, z1):
    h = z1 - z0
    return Pos(x, y, (z0 + z1) / 2) * Rot(0, 0, angle_deg) * (
        Box(2 * half_len, width, h) + Pos(-half_len, 0, 0) * Cylinder(width / 2, h) + Pos(half_len, 0, 0) * Cylinder(width / 2, h))


def hex_z(x, y, z0, z1, af, turn=0.0):
    """Hexagonal through-hole (across flats af) square to Z: a captive-nut pocket in a laser-cut plate."""
    return Pos(x, y, z0) * extrude(Rot(0, 0, turn) * RegularPolygon(af / 2, 6, major_radius=False), z1 - z0)


def hex_y(x, y0, y1, z, af, turn=0.0):
    return Pos(x, y1, z) * Rot(90, 0, 0) * extrude(Rot(0, 0, turn) * RegularPolygon(af / 2, 6, major_radius=False), y1 - y0)


def fillet_z(x, y, sx, sy, r, z0, z1):
    return (Pos(x + sx * r / 2, y + sy * r / 2, (z0 + z1) / 2) * Box(r, r, z1 - z0)
            - Pos(x + sx * r, y + sy * r, (z0 + z1) / 2) * Cylinder(r, z1 - z0))


def fillet_x(y, z, sy, sz, r, x0, x1):
    return (Pos((x0 + x1) / 2, y + sy * r / 2, z + sz * r / 2) * Box(x1 - x0, r, r)
            - Pos((x0 + x1) / 2, y + sy * r, z + sz * r) * Rot(0, 90, 0) * Cylinder(r, x1 - x0))


def fillet_y(x, z, sx, sz, r, y0, y1):
    return (Pos(x + sx * r / 2, (y0 + y1) / 2, z + sz * r / 2) * Box(r, y1 - y0, r)
            - Pos(x + sx * r, (y0 + y1) / 2, z + sz * r) * Rot(90, 0, 0) * Cylinder(r, y1 - y0))


def round_profile(shape, r=1.0, t=None):
    """Round the convex corners of a cut profile: the straight edges through the sheet's thickness t (an edge of length t
    between two planar faces), where the profile turns outward. Laser cutting makes a radius for nothing
    (DESIGN_GUIDELINES: no sharp corners). t defaults to the part's smallest bounding-box size (a flat part)."""
    if t is None:
        bb = shape.bounding_box()
        t = min(bb.size.X, bb.size.Y, bb.size.Z)

    def candidates(sh):
        out = []
        faces = list(sh.faces())
        for e in sh.edges():
            if e.geom_type != GeomType.LINE or abs(float(e.length) - t) > 0.02:
                continue
            fs = [f for f in faces if any(e.is_same(x) for x in f.edges())]
            if len(fs) != 2 or any(f.geom_type != GeomType.PLANE for f in fs):
                continue
            n1, n2 = (np.array(tuple(f.normal_at(f.center()))) for f in fs)
            if abs(n1 @ n2) > 0.99:
                continue
            p = np.array(tuple(e.position_at(0.5)))
            m = (n1 + n2) / np.linalg.norm(n1 + n2)
            if any(so.is_inside(tuple(p + 0.05 * m)) for so in sh.solids()):
                continue
            out.append(e)
        return out
    es = candidates(shape)
    if not es:
        return shape
    for rr in (r, 0.75 * r, 0.5 * r):
        try:
            return fillet(es, rr)
        except Exception:
            pass
    sh = shape
    for _ in range(len(es)):
        done = False
        for e in candidates(sh):
            for rr in (r, 0.5 * r):
                try:
                    sh = fillet([e], rr)
                    done = True
                    break
                except Exception:
                    continue
            if done:
                break
        if not done:
            break
    return sh


def bent_L(t, r, h_a, l_b, w, holes_a=(), holes_b=()):
    """A 90-degree sheet bend drawn as made (inside radius r, outside r + t), in a local frame: leg A in the YZ plane at
    x 0..t rising to z = h_a; leg B in the XY plane at z 0..t reaching to x = l_b; width w along Y (centred). Holes:
    (y, z, dia) on leg A, (x, y, dia) on leg B."""
    c = t + r
    leg_a = bx(0, t, -w / 2, w / 2, c, h_a)
    leg_b = bx(c, l_b, -w / 2, w / 2, 0, t)
    ring = Pos(c, 0, c) * Rot(90, 0, 0) * (Cylinder(c, w) - Cylinder(r, w))
    ring &= bx(0, c, -w / 2, w / 2, 0, c)
    s = leg_a + leg_b + ring
    for y, z, dia in holes_a:
        s -= Pos(t / 2, y, z) * xcyl(dia / 2, t)
    for x, y, dia in holes_b:
        s -= Pos(x, y, t / 2) * Cylinder(dia / 2, t)
    return s


def sheet(d, name, shape, material, body="world", finish="bare", r=1.0, **meta):
    """A laser-cut part: outside profile corners rounded, the finish declared, process sheet."""
    return d.add(name, round_profile(shape, r), material=material, body=body, process="sheet",
                 meta={"finish": finish, **meta})


def mount_pcb(d, name, comp, holes_key, size, screw_len, sp_len, group, use=None):
    names = []
    for i, (hx, hy, hz) in enumerate(comp.meta["interfaces"][holes_key]):
        if use is not None and i not in use:
            continue
        place(d, f"{name}_spacer_{i}", spacer_harwin(int(sp_len), "nylon") if size == "M3" else spacer_round(size, sp_len), Location((hx, hy, Z_TRAY)))
        pcb_t = 1.5 if size == "M2.5" else 1.6
        add_screw(d, f"{name}_screw_{i}", size, screw_len, at=(hx, hy, Z_TRAY + sp_len + pcb_t),
                  clamps=(name, f"{name}_spacer_{i}", "electronics_tray"))
        add_washer(d, f"{name}_washer_{i}", size, (hx, hy, 20.0), (0, 0, -1), screw=f"{name}_screw_{i}")
        add_nut(d, f"{name}_nut_{i}", size, at=(hx, hy, 20.0 - WASHER["normal"][size][2]), direction=(0, 0, -1), screw=f"{name}_screw_{i}")
        d.join(f"{name}_nut_{i}", "electronics_tray", "clamped through its washer")
        names += [f"{name}_spacer_{i}", f"{name}_screw_{i}", f"{name}_washer_{i}", f"{name}_nut_{i}"]
    group += [name] + names


def place_casting(d, name, corner, u, v, body="world"):
    """v11: a stock cast 2020 corner bracket (the catalogue's casting, Misumi HBLFSN5 class) placed on its own: inside corner
    at `corner`, legs along u and v, drawn as its CAD model has it (3 mm legs, webs, the 6 mm slots), as add_corner_bracket
    draws a bracket whose legs are on T-slots. Its fasteners are added by the caller."""
    import dataclasses

    st = corner_bracket_2020()
    LEG_T, WEB_IN = 3.0, 6.0
    solid = st.shape - extrude(Polygon((LEG_T, LEG_T), (20 - LEG_T, LEG_T), (LEG_T, 20 - LEG_T), align=None), WEB_IN, both=True)
    s0, s1, sr = BRACKET_CAD_SLOT
    solid -= (Pos((s0 + s1) / 2, 0, 0) * Box(s1 - s0, 2 * LEG_T, 2 * sr) + Pos(s0, 0, 0) * Rot(90, 0, 0) * Cylinder(sr, 2 * LEG_T)
              + Pos(s1, 0, 0) * Rot(90, 0, 0) * Cylinder(sr, 2 * LEG_T))
    solid -= (Pos(0, (s0 + s1) / 2, 0) * Box(2 * LEG_T, s1 - s0, 2 * sr) + Pos(0, s0, 0) * Rot(0, 90, 0) * Cylinder(sr, 2 * LEG_T)
              + Pos(0, s1, 0) * Rot(0, 90, 0) * Cylinder(sr, 2 * LEG_T))
    uv, vv = np.array(u, float), np.array(v, float)
    return place(d, name, dataclasses.replace(st, shape=solid), Location(Plane(origin=corner, x_dir=u, z_dir=tuple(np.cross(uv, vv)))), body=body)


BRACKET_KIND = {f"sq_bracket_{e}{s_}": "HBLFSNF5" for e in "fr" for s_ in "lr"}       # v12: brackets where a 30 mm leg does not fit get the HBLFSNF5 (30 x 20); filled from the clearance checks


def cbr(d, name, a, b, corner, u, v, body="world", slot_leg=None):
    """v12 (owner, V11_1_PLAN): every frame / carrier corner is a MISUMI HBLFSN5-SEP reversal tabbed bracket (30 x 30, cast 383.0)
    with its set's two CBM5-10 cap screws into HNTP5-5 post-assembly spring nuts, all drawn (mechloop.parts.batch12). Where a
    30 mm leg does not fit, the HBLFSNF5-SEP (30 x 20; MISUMI's STEP) with its 20 mm leg on part b."""
    kind = BRACKET_KIND.get(name, "HBLFSN5")
    if name.startswith("brkt_up_bot_"):
        # v12: at the uprights' feet a 30 mm leg along the bottom rail reaches the Z motor posts and the tray: HBLFSNF5, its 30 mm leg
        # up the upright and its 20 mm leg along the rail
        a, b, u, v, kind = b, a, v, u, "HBLFSNF5"
    return add_bracket_misumi(d, name, a, b, corner, u, v, body=body, kind=kind, locking=(slot_leg or {}).get("locking"))


def bolt_nut(d, name, size, length, head_at, direction, body, clamps, nut_at=None, washer_head=True, washer_nut=True,
             large=False, threads_into=None, nyloc=False):
    """Through-bolt: screw (washer under the head), what it clamps, washer and nut on the far side. head_at = face the
    head's washer bears on; nut_at = face the nut's washer bears on (along `direction`)."""
    add_screw(d, name, size, length, at=head_at, direction=direction, body=body, clamps=clamps,
              washer=("large" if large else True) if washer_head else False, threads_into=threads_into)
    if nut_at is not None:
        dvec = np.array(direction, float) / np.linalg.norm(direction)
        at = np.array(nut_at, float)
        if washer_nut:
            add_washer(d, f"{name}_nwasher", size, tuple(at), tuple(dvec), body=body, screw=name,
                       series="large" if large else "normal")
            at = at + dvec * WASHER["large" if large else "normal"][size][2]
        # v10.1: a nyloc is drawn as the nyloc it is (ISO 10511, taller), not as a hex nut with a BOM-only upgrade line
        add_nut(d, f"{name}_nut", size, at=tuple(at), direction=tuple(dvec), body=body, screw=name,
                standard="iso10511" if nyloc else "iso4032")
        if washer_nut and clamps:
            d.join(f"{name}_nut", clamps[-1], "clamped through its washer")


def captive_nut(d, screw, at, direction, part, body="world"):
    """Washer and ISO 10511 nyloc nut captured in a printed pocket (nut_pocket) of `part`: at = the pocket face the washer
    bears on, direction = along the screw, away from its head."""
    dvec = np.array(direction, float)
    add_washer(d, f"{screw}_nwasher", "M3", tuple(at), tuple(dvec), body=body, screw=screw)
    add_nut(d, f"{screw}_nut", "M3", at=tuple(np.array(at) + dvec * WASHER["normal"]["M3"][2]), direction=tuple(dvec), body=body,
            screw=screw, standard="iso10511")
    d.join(f"{screw}_nut", part, "captive nut in a printed pocket (flats against the slot's walls), slid in on the bench")
    d.join(f"{screw}_nwasher", part, "washer captured in the printed pocket, under the nut")


def through_bolt_nyloc(d, name, length, head_at, direction, clamps, nut_face, body="world", nyloc=True):
    """M3 through-bolt for a printed part: washer under the head, washer and ISO 10511 nyloc nut on `nut_face` (the face
    the nut's washer bears on, on the side with access)."""
    dvec = np.array(direction, float) / np.linalg.norm(direction)
    sc = add_screw(d, name, "M3", length, at=head_at, direction=tuple(dvec), body=body, clamps=clamps, washer=True)
    sc.meta["torque_nm"] = PRINTED_JOINT_TORQUE
    add_washer(d, f"{name}_nwasher", "M3", tuple(nut_face), tuple(dvec), body=body, screw=name)
    add_nut(d, f"{name}_nut", "M3", at=tuple(np.array(nut_face) + dvec * WASHER["normal"]["M3"][2]), direction=tuple(dvec),
            body=body, screw=name, standard="iso10511" if nyloc else "iso4032")
    if not nyloc:
        sc.meta["locking"] = "adhesive"
    d.join(f"{name}_nut", clamps[-1], "clamped through its washer")
    return [name, f"{name}_washer", f"{name}_nwasher", f"{name}_nut"]


def bolt_length(grip, nut_h=4.0, washers=2, past=1.0):
    """Shortest standard M3 cap screw that passes a grip, two washers and a nyloc nut by at least `past` mm."""
    need = grip + washers * WASHER["normal"]["M3"][2] + nut_h + past
    return next(L for L in (10, 12, 16, 20, 25, 30, 35, 40, 45, 50) if L >= need - 1e-9)


def convex_hull(pts):
    """Andrew's monotone chain; returns the hull counter-clockwise."""
    P = sorted(set((round(x, 4), round(y, 4)) for x, y in pts))
    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, up = half(P), half(reversed(P))
    return lo[:-1] + up[:-1]


def screw_len(stack, nut_h, past=0.5, choices=(6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80)):
    need = stack + nut_h + past
    return next(L for L in choices if L >= need - 1e-6)


# =================================================================== part shapes
def countersink_z(x, y, z_top, depth_total, d_csk, d_hole):
    """A 90-degree countersink from the top face z_top (mouth d_csk) with a through clearance hole d_hole, as a solid to cut."""
    from build123d import Cone
    h = (d_csk - d_hole) / 2.0
    return Pos(x, y, z_top - h / 2) * Cone(d_hole / 2, d_csk / 2, h) + zc(x, y, z_top - depth_total, z_top, d_hole / 2)


def bed_shape_():
    """12.7 mm MIC-6 cast plate, laser cut (faces as cast), no tapped holes: three M4 countersunk screws from the top, in
    90-degree countersinks (8.96 mm; SendCutSend's countersinking service or the builder's countersink bit), heads 0.7 mm
    below the surface: the magnetic base lies flat over them."""
    b = bx(BED_X0, BED_X1, BED_Y0, BED_Y1, Z_BED, Z_BED + T_BED)
    for x, y in BED_MOUNTS:
        b -= countersink_z(x, y, Z_BED + T_BED, T_BED, CSK["M4"][0], clearance_hole("M4"))
    return b


def rz(shape, cx, cy, ang):
    """A shape drawn about the origin, turned `ang` degrees about Z and moved to (cx, cy)."""
    return Pos(cx, cy, 0) * Rot(0, 0, ang) * shape


def rxy(u, r_, cx, cy, ang):
    """Local (u along the member, r_ outward from the square) -> world x, y for a bracket turned `ang` about Z."""
    a = math.radians(ang)
    return (cx + u * math.cos(a) - r_ * math.sin(a), cy + u * math.sin(a) + r_ * math.cos(a))


def nut_plate_local(z0, z1, nut_out=NUT_OUT):
    """One nut plate, about its nut's axis: local x along the square's member, local y outward. It lies under the member
    (y from -nut_out - 20 to -nut_out), two M5 from below into the member's bottom slot, and reaches out to the nut: the
    screw in a round hole with the nut's float (v11: the POM nut's flange is under the plate, its barrel hangs below), the
    pin's sleeve in a radial slot to the flange's corner hole, two holes for the keeper's through-bolts."""
    h = z1 - z0
    yc, ly = (NP_R1 - nut_out - 20.0) / 2, NP_R1 + nut_out + 20.0
    s = Pos(0, yc, z0) * extrude(RectangleRounded(2 * NP_U, ly, 3.0), h)
    s -= zc(0, 0, z0, z1, NP_HOLE / 2)
    rp_ = math.hypot(*NUT_PIN)
    s -= slot_z(NUT_PIN[0] / 2, NUT_PIN[1] / 2, 135.0, rp_ / 2 + NUT_FLOAT, PIN_SP_D + 1.2, z0, z1)     # v12: open into the screw's hole
    # v11: the screw's hole is open along the member (+x) to the plate's end: the plate slides onto the nut sideways (the
    # 330 mm screw cannot be threaded through a closed hole once the motor stands in the frame)
    s -= bx(0.0, NP_U + 1.0, -NP_HOLE / 2, NP_HOLE / 2, z0, z1)
    for u in (-NP_BOLT_U, NP_BOLT_U):
        s -= zc(u, -nut_out - 10.0, z0, z1, clearance_hole("M5") / 2)
    for u, v in KEEP_HOLES:
        s -= zc(u, v, z0, z1, 4.8 / 2)          # keeper bolts (v12 4.8 at y 16.3, v11 4.8: with a large washer; SendCutSend's edge web)
    return s


def nut_keeper_local(z0, z1):
    """The keeper under a nut's flange (v8.2), drawn about the nut's axis: local x along the member."""
    from build123d import Circle, SlotOverall
    s = Pos(0, 4.5, z0) * extrude(RectangleRounded(50.0, 37.0, 3.0), z1 - z0)        # v12: y -14 .. 23     # v11: local y -14 .. 20 (clear of the plate's M5 drivers)
    # the barrel's hole and the slot the pin's nut moves in, as one opening; its four corners rounded (v8.2's were sharp)
    cut = (Circle(KP_HOLE / 2) + Pos(NUT_PIN[0], NUT_PIN[1]) * Rot(0, 0, 135) * SlotOverall(2 * NUT_FLOAT + 7.0, 7.0)
           + Pos(13.0, 0) * RectangleRounded(26.0, KP_HOLE, 0.5)       # v11: open along the member: the keeper slides in under the flange,
           + Pos((NUT_PIN[0] - 3.5 + 26.0) / 2, NUT_PIN[1]) * RectangleRounded(26.0 - NUT_PIN[0] + 3.5, 7.0, 0.5))   # and past the pin's nut
    try:
        cut = fillet(cut.vertices(), 0.8)
    except Exception:
        pass
    s -= Pos(0, 0, z0) * extrude(cut, z1 - z0)
    for u, v in KEEP_HOLES:
        s -= zc(u, v, z0, z1, clearance_hole("M3") / 2)
    return s


def carriage_plate_local(z_blk):
    """One carriage plate in its own frame: x along the wall, y up (0 at the square's centre line), z from the block's
    mounting face (0) towards the square (T_CP). Top 20 mm: on the square's outer face, two M5 into T-nuts. Then the web,
    L_FLEX long and CP_WEB wide: the flexure. Below it the block's face, four M3. z_blk: the block's centre, from the
    square's centre line."""
    y0, y1 = z_blk - 22.7 - 1.0, -10.0 - L_FLEX          # bottom edge; top of the block's zone
    s = Pos(0, 0, 0) * extrude(RectangleRounded(CP_W, 20.0, 2.0), T_CP)                         # on the square
    s += Pos(0, (y0 + y1) / 2, 0) * extrude(RectangleRounded(CP_W, y1 - y0, 2.0), T_CP)          # on the block
    s += bx(-CP_WEB / 2, CP_WEB / 2, y1 - 1.0, -9.0, 0, T_CP)                                    # the web
    for sx in (-1, 1):                               # 3 mm radii where the web meets the two zones
        s += fillet_z(sx * CP_WEB / 2, -10.0, sx, -1, 3.0, 0, T_CP)
        s += fillet_z(sx * CP_WEB / 2, y1, sx, 1, 3.0, 0, T_CP)
    for u in (-CP_BOLT_U, CP_BOLT_U):
        s -= Pos(u, 0, T_CP / 2) * Cylinder(clearance_hole("M5") / 2, T_CP)
    for u in (-10.0, 10.0):
        for v in (-10.0, 10.0):
            s -= Pos(u, z_blk + v, T_CP / 2) * Cylinder(clearance_hole("M3") / 2, T_CP)
    return s


def deck_shape():
    """3.175 mm 6061 deck on the square: flush with its outer faces, twelve M5 holes over the members' top slots (one
    beside each bed stud), and one hole per bed stud: stud 0 a fitted 4.3 mm hole (locates the bed), stud 1 a 4.3 mm slot
    pointing at stud 0, stud 2 oversize (5.5 mm), so the heated plate grows without bending its studs."""
    z0, z1 = Z_SQT, Z_DECK1
    s = Pos(0, BED_CY, z0) * extrude(RectangleRounded(2 * SQ_X, SQ_Y1 - SQ_Y0, 4.0), T_DECK)
    for x, y in DECK_BOLTS:
        s -= zc(x, y, z0, z1, clearance_hole("M5") / 2)
    (x0, y0), (x1, y1) = BED_MOUNTS[0], BED_MOUNTS[1]
    s -= zc(x0, y0, z0, z1, DECK_FIT / 2)
    s -= slot_z(x1, y1, 0.0, 1.0, DECK_FIT, z0, z1)
    for x, y in BED_MOUNTS[2:]:
        s -= zc(x, y, z0, z1, DECK_FREE / 2)
    return s


DECK_BOLTS = ([(sx * (SQ_X - 10.0), BED_CY + dy) for sx in (-1, 1) for dy in (-100.0, 0.0, 100.0)]
              + [(x, SQ_Y0 + 10.0) for x in (-LEV_X, 0.0, LEV_X)]                       # one straight outboard of each front stud
              + [(BED_CX + dx, SQ_Y1 - 10.0) for dx in (-55.0, 0.0, 55.0)])           # one straight outboard of the rear stud
# the three guides: (name, rail-base point on the wall (x, y), inward normal, frame rails the upright stands between)
GUIDES = [("left", (-WALL_X, UP_S_Y), (1.0, 0.0, 0.0), "left"), ("right", (WALL_X, UP_S_Y), (-1.0, 0.0, 0.0), "right"),
          ("rear", (UP_R_X, Y_FACE), (0.0, -1.0, 0.0), "back")]
# the three nuts: (tag, screw x, y, turn of the nut plate about Z (local y = outward), member it bolts under)
NUTS = [("", 0.0, LS_Y, 0.0, "sq_rear"), ("_fl", -FS_X, FS_Y, 90.0, "sq_left"), ("_fr", FS_X, FS_Y, -90.0, "sq_right")]


def tool_plate_outline(y0, y1, striker=True):
    box = lambda x0, x1, z0, z1: bx(x0, x1, y0, y1, Z_BEAM + z0, Z_BEAM + z1)
    # v10: centred on the X block; the Roto, and with it the duct's tab, sit C_NOZ to the left, so the tab ends at the
    # plate's right edge. No notch at the left edge (v9's cleared the X switch) and no lightening window (the Roto's
    # upper screw is there now). FRONT plate: a striker tab on the right edge works the X switch on the right Y plate's
    # land. REAR plate: its upper right corner is cut away instead, where the Roto's motor lead now leaves towards it (the
    # connector, 0.7 mm inside the plate's width, needs 12 mm in front of it for its plug).
    tp = box(-TPX, TPX, TP_Z0, TP_Z1) + box(*TAB_R)
    r = 3.0
    tp += fillet_y(TAB_R[0], Z_BEAM + TP_Z0, -1, -1, r, y0, y1)
    if striker:
        tp += box(TPX - 1.0, STRIKER[0], STRIKER[1], STRIKER[2])
        tp += fillet_y(TPX, Z_BEAM + STRIKER[1], 1, -1, 1.5, y0, y1)
        rel = LEAD_RELIEF_F
    else:
        rel = LEAD_RELIEF
    tp -= box(rel[0], STRIKER[0] + 1.0, rel[1], TP_Z1 + 1.0)
    tp += fillet_y(rel[0], Z_BEAM + rel[1], 1, 1, 2.0, y0, y1)
    return tp


ROTO_HOLES = lambda: [(ROTO_O[0], ROTO_O[2]), (ROTO_O[0] + ROTO_H2[0], ROTO_O[2] + ROTO_H2[2])]
BRK_Z = 28.0                           # belt bracket bolts, from Z_BEAM (v11: 0.25 lower, 6.1 mm from the bend: SendCutSend's die width)


def tool_plate_front_shape():
    """3.175 mm 6061 on the X guide block (four M3x6, heads from the rear). PEM M3 nuts clinched in it take the Roto's
    screws, so those screws clamp the Roto, the rear plate and this plate together; clearance holes for the belt
    bracket and the duct."""
    y0, y1 = YB0 + R_TPF, YB0 + R_TPF + T_TPF
    tp = tool_plate_outline(y0, y1)
    for x in (-10, 10):
        for z in (-10, 10):
            tp -= Pos(x, (y0 + y1) / 2, Z_BEAM + z) * ycyl(clearance_hole("M3") / 2, T_TPF)
    for x, z in ROTO_HOLES():
        tp -= Pos(x, (y0 + y1) / 2, z) * ycyl(4.27 / 2, T_TPF)          # v11: PEM S-M3-0 mounting hole (SendCutSend: 0.168 in +0.003)
    for x, z in BLK_SCREWS:
        tp -= Pos(x, (y0 + y1) / 2, Z_BEAM + BRK_Z) * ycyl(clearance_hole("M3") / 2, T_TPF)
    for x, z in FC_SCREWS:
        tp -= Pos(x, (y0 + y1) / 2, Z_BEAM + z) * ycyl(clearance_hole("M3") / 2, T_TPF)
    return tp


def tool_plate_rear_shape():
    """4.75 mm 6061 behind the front plate: 6.5 mm holes are the counterbores of the block screws' heads; hex pockets hold
    the belt bracket's nuts (they bear on the front plate) and clear the PEM nuts' heads; the Roto's flat side sits on
    its rear face."""
    y0, y1 = YB0 + R_TPF + T_TPF, YB0 + R_TPR
    tp = tool_plate_outline(y0, y1, striker=False)
    for x in (-10, 10):
        for z in (-10, 10):
            tp -= Pos(x, (y0 + y1) / 2, Z_BEAM + z) * ycyl(3.25, T_TPR)
    for x, z in ROTO_HOLES():
        tp -= Location(Plane(origin=(x, y0, z), z_dir=(0, 1, 0))) * extrude(RegularPolygon(5.65 / 2, 6, major_radius=False), T_TPR)
    for x, z in BLK_SCREWS:
        tp -= Location(Plane(origin=(x, y0, Z_BEAM + BRK_Z), z_dir=(0, 1, 0))) * extrude(RegularPolygon(5.65 / 2, 6, major_radius=False), T_TPR)
    for x, z in FC_SCREWS:
        tp -= Pos(x, (y0 + y1) / 2, Z_BEAM + z) * ycyl(4.8 / 2, T_TPR)
    return tp


def nut_pocket(at, axis, up, extra_back=0.0):
    """Captive nut pocket for an M3 nyloc with its washer, as a solid to cut: at = the face the washer bears on (towards
    the screw head), axis = unit vector from that face away from the head, up = the direction the pocket opens (a slot the
    nut and washer slide in along), back / front: how far the slot runs beyond the axis on the closed side (none: it
    opens at `up`'s side). The nut sits flats-on against the slot's walls, so it cannot turn."""
    a, u = np.array(axis, float), np.array(up, float)
    w = np.cross(u, a)
    def slab(y0, y1, width, below):
        # from `below` under the axis (towards -u) to far out along +u (the opening), y0..y1 along the axis
        L = 40.0
        c = np.array(at, float) + a * (y0 + y1) / 2 + u * (L / 2 - below)
        return Location(Plane(origin=tuple(c), x_dir=tuple(w), z_dir=tuple(a))) * Box(width, L, y1 - y0)
    return (slab(0.0, POCKET_W, POCKET_WD, POCKET_WD / 2 + 0.2) +
            slab(POCKET_W - 0.01, POCKET_W + POCKET_NUT + extra_back, POCKET_AF, POCKET_AF / math.sqrt(3) + 0.2))


# ---- v11 part cooling: one BFB0524HH radial blower behind the Roto, outlet down, a short printed duct -----------------------
# v11 (owner, 2026-11-19): Delta BFB0524HH 5015 blower (was GDSTIME GDB4010 4010)
BL_WX, BL_W, BL_T = 52.59, 51.42, 15.34   # the maker's STEP's bounding box: width, height, thickness
BL_X0 = NOZ_X + 23.0                    # x from 23 to 75.6 right of the nozzle: right of the probe bracket and the Roto's screw heads
BL_X1 = BL_X0 + BL_WX                   # (above z 424.5 nothing on the frame reaches in: at the right end it is at x 158.9)
BL_Z0 = Z_NOZZLE + 51.05                # 424.5: its outlet edge, above the Y switch board (z 422.6) and the top back rail: its outlet edge; its lower lugs' nuts pass 1 mm above the top back rail at the rear end
CRADLE_T = 4.0
BL_HOLES = lambda: [((BL_X0 + BL_X1) / 2 - 22.3, BL_Z0 + BL_W / 2 + 18.24), ((BL_X0 + BL_X1) / 2 + 20.9, BL_Z0 + BL_W / 2 - 19.85)]
                                        # the Delta's two 4.5 mm holes (measured on its STEP), as the blower is turned here
DUCT_FLOOR = Z_NOZZLE + 3.05            # 376.5: the duct's lowest face, 3.05 mm above the nozzle tip (owner: >= 2.5)
OUT_D, OUT_W, OUT_H, OUT_L = 24.0, 14.0, 3.0, 6.0     # outlet: 24 mm from the nozzle's axis on the rear-right diagonal, 14 x 3 mm bore
OUT_Z = Z_NOZZLE + 5.5                  # outlet centre height; the jet is aimed at 0.5 mm under the tip
DUCT_K = {"contraction into the outlet tube (area ratio about 0.1)": 0.40, "exit (the jet's kinetic energy)": 1.00,
          "outlet tube friction (6 mm, rectangular 14 x 3)": 0.25, "two 45-degree turns in the chamber, at chamber velocity": 0.20}


def _outlet_frame(y_noz):
    """Outlet centre and unit jet axis (towards the aim point 0.5 mm under the nozzle tip)."""
    o = np.array([NOZ_X + OUT_D / math.sqrt(2), y_noz + OUT_D / math.sqrt(2), OUT_Z])
    t = np.array([NOZ_X, y_noz, Z_NOZZLE - 0.5])
    ax = (t - o) / np.linalg.norm(t - o)
    return o, ax


def _tube(o, ax, w, h, L):
    """A box w (horizontal, square to the axis) x h x L along `ax`, ending at `o`."""
    p_ = np.cross(ax, [0, 0, 1.0])
    p_ /= np.linalg.norm(p_)
    z_ = np.cross(p_, ax)
    c = o - ax * L / 2
    return Location(Plane(origin=tuple(c), x_dir=tuple(p_), z_dir=tuple(z_))) * Box(w, L, h)


def part_duct_shape(y_noz, bl_y0):
    """v11 printed ABS duct for the Delta BFB0524HH blower. A flange on the tool plates' tab (v10's: two M3 through-bolts into nyloc
    nuts captured in printed pockets) and an arm under the Roto's right side carry a chamber under the blower (the blower's
    outlet blows down into it; a cradle behind the blower takes its two M3 through-bolts). From the chamber's front-left
    corner a short tube, 14 x 3 mm inside, points from 24 mm out on the rear-right diagonal down at about 14 degrees to a
    point 0.5 mm under the nozzle tip: the jet passes under the heater block (E3D silicone sock fitted) instead of hitting
    it. The duct stays 3 mm or more above the tip and 4.5 mm or more from the heater block. Walls 1.6 mm, tube 1.2 mm."""
    w = DUCT_W
    yf = YB0 + R_TPR
    z0, zf = Z_BEAM + FC_Z0, Z_BEAM + FC_ZF
    y_c0 = y_noz + 13.5                                 # chamber's front face: 5.15 mm behind the heater block
    by1 = bl_y0 + BL_T                                  # blower's rear face
    yl_back = bl_y0 + 11.0                              # the riser's back below z 406 (it passes the top back rail at the rear end)
    c = bx(FC_X0, FC_X1, yf, yf + FC_FL, z0, zf)        # flange
    c += bx(NOZ_X + 21.5, FC_X1, yf + FC_FL, y_c0, z0, zf)                        # arm under the Roto
    y_rf = YB0 + R_TPR + ROTO_W                         # the Roto's rear face: under the Roto the chamber stays below its underside
    c += bx(NOZ_X + 21.5, NOZ_X + 48.5, y_c0, y_rf, DUCT_FLOOR, Z_NOZZLE + 20.55)   # chamber A, under the Roto
    c += bx(NOZ_X + 21.5, NOZ_X + 48.5, y_rf - 0.01, y_rf + 0.61, DUCT_FLOOR, Z_NOZZLE + 20.55)   # v11: bridges chamber A to the riser (below the Roto)
    c += bx(NOZ_X + 21.5, NOZ_X + 48.5, y_rf + 0.6, yl_back, DUCT_FLOOR, Z_NOZZLE + 32.55)   # and its riser behind the Roto (0.6 mm clear of it),
    c += bx(NOZ_X + 21.5, NOZ_X + 48.5, y_rf + 0.6, by1, Z_NOZZLE + 32.55, BL_Z0)            # deeper above z 406, up to the blower
    c += bx(NOZ_X + 13.0, NOZ_X + 28.0, y_c0, y_noz + 23.0, DUCT_FLOOR, DUCT_FLOOR + 9.5)   # chamber B, its front-left extension
    c += bx(NOZ_X + 41.0, NOZ_X + 48.5, by1, by1 + CRADLE_T, Z_NOZZLE + 32.55, BL_Z0 + BL_W)   # cradle: a 7.5 mm upright from the riser's back
    c += bx(BL_X0, NOZ_X + 48.5, by1, by1 + CRADLE_T, BL_Z0 + BL_W - 14.0, BL_Z0 + BL_W)        # a bar to the blower's upper-left hole
    c += bx(NOZ_X + 41.0, BL_X1, by1, by1 + CRADLE_T, BL_Z0 + 1.0, BL_Z0 + 11.0)                 # and one to its lower-right hole
    o, ax = _outlet_frame(y_noz)
    c += _tube(o, ax, OUT_W + 2.4, OUT_H + 2.4, OUT_L)
    # the air passage
    # v11: the riser keeps a front wall (it was cut open towards the Roto's rear face, leaving a 0.6 mm slit and the duct in
    # two pieces); chamber A's passage runs through the bridge into the riser below the Roto's underside
    c -= bx(NOZ_X + 21.5 + w, NOZ_X + 48.5 - w, y_c0 + w, y_rf + 0.6 + w + 0.01, DUCT_FLOOR + w, Z_NOZZLE + 20.55 - w)
    c -= bx(NOZ_X + 21.5 + w, NOZ_X + 48.5 - w, y_rf + 0.6 + w, yl_back - w, DUCT_FLOOR + w, Z_NOZZLE + 32.55 + 0.01)
    c -= bx(NOZ_X + 21.5 + w, NOZ_X + 48.5 - w, y_rf + 0.6 + w, by1 - w, Z_NOZZLE + 32.55, BL_Z0 - w)
    bc = (BL_X0 + BL_X1) / 2
    # the blower's outlet (Delta drawing: 20 x 12.2) at the -x end of its lower edge, as the blower is turned here
    c -= bx(max(BL_X0, NOZ_X + 21.5 + w), min(BL_X0 + 19.8, NOZ_X + 48.5 - w), bl_y0 + BL_T / 2 - 6.1, bl_y0 + BL_T / 2 + 6.1, BL_Z0 - w - 0.1, BL_Z0 + 0.1)
    c -= bx(NOZ_X + 13.0 + w, NOZ_X + 28.0, y_c0 + w, y_noz + 23.0 - w, DUCT_FLOOR + w, DUCT_FLOOR + 9.5 - w)
    c -= _tube(o + ax * 0.05, ax, OUT_W, OUT_H, OUT_L + 2.0)
    for x, z in FC_SCREWS:
        c -= Pos(x, yf + FC_FL / 2, Z_BEAM + z) * ycyl(PH3 / 2, FC_FL)
        c -= nut_pocket((x, yf + POCKET_WALL, Z_BEAM + z), (0, 1, 0), (0, 0, -1))     # opens at the flange's underside
    for x, z in BL_HOLES():                            # the blower's two holes: M3 clearance through the cradle
        c -= Pos(x, by1 + CRADLE_T / 2, z) * ycyl(printed_clearance_hole("M3") / 2, CRADLE_T)
    return c


EDDY_DX = -8.0                                 # v12: the Eddy's coil 8 mm left of the nozzle (clear of the Roto's lower screw head)
EDDY_H = 2.5                                   # coil face above the nozzle tip (BTT: 2-3 mm; HEIGHT_SENSING 2.5)
EDDY_HOLDER_T = 8.5                            # printed holder on the Eddy's left (its mounting face), PETG
EDDY_LEG_W = 9.0                               # the L's narrow bent strip under the holder
EDDY_PLATE_X = (-40.5, 4.5)                    # the L's vertical leg on the Roto's rear face, world x


def eddy_geometry(yb_pm):
    """World positions of the v12 probe: the Eddy turned 90 degrees (holes along X), its front face 1 mm behind the L's vertical leg;
    the printed holder on its left; the L's narrow strip under the holder."""
    x_e = NOZ_X + EDDY_DX
    y_e = yb_pm + B23 + 1.0 + 18.1 / 2
    z_face = Z_NOZZLE + EDDY_H
    z_eh = z_face + 33.8 - 13.9
    z_leg = Z_NOZZLE + 7.0
    xh1 = x_e - 15.3 / 2                        # the Eddy's left (mounting) face
    xh0 = xh1 - EDDY_HOLDER_T
    return dict(x_e=x_e, y_e=y_e, z_face=z_face, z_eh=z_eh, z_leg=z_leg, xh0=xh0, xh1=xh1, y0=yb_pm + B23, y1=y_e + 18.1 / 2)


EDDY_HB_DY = (-3.8, 3.8)                       # the holder's two vertical bolts, from the Eddy's centre along Y


def eddy_bracket_shape(y_face, g):
    """v12: the 5052 L (SendCutSend .090): a flat vertical leg on the Roto's rear face under its two screws (as v11), with one narrow strip
    bent back at z_leg on the left, under the printed holder (two M3 holes)."""
    roto = ROTO_HOLES()
    z_b = g["z_leg"]
    h_a = Z_BEAM + 36.0 - z_b
    x0s, x1s = g["xh0"] - 1.0, g["xh0"] - 1.0 + EDDY_LEG_W
    x_c = (x0s + x1s) / 2
    l_b = g["y1"] - y_face
    hb = [(g["y_e"] + dy - y_face, 0.0, clearance_hole("M3")) for dy in EDDY_HB_DY]
    brk = bent_L(B23, R_B23, h_a, l_b, EDDY_LEG_W, holes_b=hb)
    s_ = Location(Plane(origin=(x_c, y_face, z_b), x_dir=(0, 1, 0), z_dir=(0, 0, 1))) * brk
    c = B23 + R_B23
    s_ += bx(x1s - 0.5, EDDY_PLATE_X[1], y_face, y_face + B23, z_b + c, Z_BEAM + 36.0)
    s_ += bx(EDDY_PLATE_X[0], x0s + 0.5, y_face, y_face + B23, z_b + c, Z_BEAM + 36.0)
    for x, z in roto:
        s_ -= Pos(x, y_face + B23 / 2, z) * ycyl(clearance_hole("M3") / 2, B23)
    return s_


def eddy_holder_shape(g):
    """Printed PETG holder on the Eddy's left, standing on the L's strip: two vertical M3 from below into nylocs captured in one pocket
    (open to the left, below the Eddy's bolts), and the Eddy's two horizontal M3 (along X, in its own dia 3.15 holes)."""
    z0, z1 = g["z_leg"] + B23, g["z_eh"] + 6.5
    s_ = bx(g["xh0"], g["xh1"], g["y0"] + R_B23, g["y1"], z0, z1)           # clear of the strip's bend
    xc = g["xh0"] + 3.75
    zp0 = z0 + 3.0
    for dy in EDDY_HB_DY:
        s_ -= zc(xc, g["y_e"] + dy, z0, zp0, PH3 / 2)
    s_ -= bx(g["xh0"] - 1.0, g["xh0"] + 7.5, g["y_e"] - 7.0, g["y_e"] + 7.0, zp0, zp0 + 5.2)       # the nuts' pocket, open to the left
    for dy in EDDY_HB_DY:                                                                            # the bolts' tips past the nylocs
        s_ -= zc(xc, g["y_e"] + dy, zp0 + 5.2, zp0 + 6.7, PH3 / 2)
    for dy in (-5.25, 5.25):
        s_ -= Pos(g["xh0"] + EDDY_HOLDER_T / 2, g["y_e"] + dy, g["z_eh"]) * xcyl(3.7 / 2, EDDY_HOLDER_T)
    return s_


def probe_bracket_shape(y_face):
    """v11: the probe holder, a one-bend L of 2.286 mm 5052 (SendCutSend .090; inside radius 0.81). Its upper leg lies on the
    Roto's rear face under the Roto's two screws; at the bottom it bends back into a horizontal leg with the 12.5 mm hole the
    OMRON's M12 barrel passes, clamped by the sensor's two nuts 15 mm behind its face (kept from the unshielded E2E-X5ME1; the
    shielded E2B needs only 2.4). Up to z 396 the leg is 22 mm wide (clear of the blower beside it); above, it widens to 29.5 for the
    Roto's right-hand screw. y_face: the Roto's rear face."""
    z_b = Z_PRB + PRB_CLAMP[0]
    roto = ROTO_HOLES()
    h_a = Z_BEAM + 36.0 - z_b                             # up to z 443: the toolhead loom is clamped to it
    xl0, xl1 = NOZ_X - 13.0, NOZ_X + 12.5       # 25.5 wide at the bend: over half of it clears the probe's hole (SendCutSend)
    w = xl1 - xl0
    x_c = (xl0 + xl1) / 2
    l_b = (YB0 + PRB_Y + 10.5) - y_face
    brk = bent_L(B23, R_B23, h_a, l_b, w, holes_b=[((YB0 + PRB_Y) - y_face, -(PRB_X - x_c), 12.5)])
    s = Location(Plane(origin=(x_c, y_face, z_b), x_dir=(0, 1, 0), z_dir=(0, 0, 1))) * brk
    s += bx(xl1 - 0.5, NOZ_X + 20.0, y_face, y_face + B23, Z_NOZZLE + 22.55, z_b + h_a)       # the wide part (from z 396)
    for x, z in roto:
        s -= Pos(x, y_face + B23 / 2, z) * ycyl(clearance_hole("M3") / 2, B23)
    return s


USE_CUTOFFS = True


def add_thermostat(d):
    """v12: the Cantherm CS712025Y bed thermostat (120 degC NC, 10 A at 24 V DC) under the plate, cap face on the plate's underside,
    in series with the heater; bonded with high-temperature silicone adhesive and thermal paste (the owner asked for a clamp: a
    clamp needs two countersunk M3 through the plate, whose McMaster numbers and STEPs are not in hand: open question)."""
    place(d, "bed_tco", thermostat_cs7(), Location((BED_CX + 107.0, BED_CY + 107.0, Z_BED)), body="zbody")     # the rear-right corner, clear of the pad
    d.join("bed_tco", "bed_plate", "bond")


def build_electrical(d: Design) -> Electrical:
    """v12 (V12_PLAN): Raspberry Pi 5 (own 27 W supply) on the Octopus's UART header without 5 V; Finder 22.32 contactor in L and N,
    its 120 V coil through the Phoenix 1119897 contact, whose 5 V coil a Pi GPIO drives through a PN2222A (Moonraker [power],
    off_when_shutdown); DD11.0114.1111 inlet with one T8A in L; 16 AWG earth inlet PE -> frame stud, stud -> supply FG and -> bed plate;
    bed on the Octopus HB output (10 A blade fuse) through the Cantherm thermostat; Semitec 104NT-4 bed thermistor; BTT Eddy Duo on USB
    to the Pi. v11's text: As v8.1, with the BTT Octopus V1.1 in place of the SKR Mini E3 V3.0: seven drivers used, one motor each (X M0, Y
    M1, Y left M2, Z rear M3, extruder M4, Z front-left M5, Z front-right M6; M7 spare); X and Y switches and the probe on
    STOP0 / STOP1 / STOP2 (their DIAG jumpers removed), the probe still through a BAT85 on an ordinary 3.3 V input; the
    Pi Zero 2 W on the Octopus's Raspberry Pi header (5 V, GND, UART2); Klipper [z_tilt] with the three screw positions."""
    from mechloop.electrical import add_board_5v_port

    el = Electrical(supply_v=24.0, mains_v=(115.0, 230.0))
    d.electrical = el
    for nm in ("control_board", "psu", "inlet", "host", "hotend", "part_fan", "x_endstop", "y_endstop", "bed_probe", "x_motor",
               "z_motor", "z_motor_fl", "z_motor_fr", "extruder", "y_motor", "y_motor_l"):
        device_from(el, d, nm)
    device_from(el, d, "bed_heater", plate="bed_plate")
    # v12: Semitec 104NT-4-R025H42G on the plate (Klipper has its exact table); the Keenovo pad's own NTC is left unconnected
    embedded_device(el, d, "bed_heater", "bed_ntc", "thermistor", "ntc", "thermistor", ratings={"max_temp_c": 300.0},
                    sources={"points": "Klipper 'ATC Semitec 104NT-4-R025H42G' (Semitec NT-4 data sheet, vendor_docs/Semitec_NT-4_thermistor_datasheet.pdf)",
                             "max_temp_c": "Semitec NT-4 data sheet: to 300 degC", "tau_s": "assumed 10 s (bonded to the plate; not a data-sheet figure)"},
                    sensor_type="ATC Semitec 104NT-4-R025H42G", points=THERMISTORS["ATC Semitec 104NT-4-R025H42G"], tau_s=10.0, node="pad")
    embedded_device(el, d, "hotend", "hotend_thermistor", "thermistor", "ntc", "thermistor", **d.get("hotend").ratings["thermistor"])
    rf = d.get("extruder").ratings["fan"]
    embedded_device(el, d, "extruder", "hotend_fan", "fan", "fan", "fan",
                    ratings={"current_a": rf["current_a"], "volts": rf["volts"]},
                    sources={"current_a": "E3D Roto data sheet, 'Fan Specification': 5 V, 0.14 A"})
    add_board_5v_port(el, "control_board")
    device_from(el, d, "bed_tco")
    device_from(el, d, "psu_relay")
    el.add(Device("frame_earth", "earth_point", "earth_stud",
                  {"pe": Port("pe", "pe", "ring-M5", 20.0, at=(-FX / 2 - 6.0, 80.0, 10.0), multi=True, extra={"body": "world"})},
                  params={"bonds": "frame_bot_left"},
                  product={"product": "M5 ring terminals (CONN-RING-M5) stacked under the M5 x 6 earth stud and a DIN 6797 toothed washer in a T-nut",
                           "vendor": "McMaster-Carr (screw 91290A221, washer 91106A126) + ring terminals per mpn_map.json", "part_number": "91290A221",
                           "form": "hardware", "off_the_shelf": True, "custom_pcb": False,
                           "builder_work": "crimp M5 ring terminals: inlet PE, supply FG and bed plate each on their own lug (one conductor per tab)"}))
    zt = Z_TRAY + 8.0
    XL, ZL = -147.0, FZ - 6.0
    # v10: the toolhead now reaches the right top rail's inner face (2.4 mm) and the back rail (as before), so its loom is
    # anchored on TOP of the top back rail and drops down that rail's outer face, not in the frame's inside corner
    P1 = (118.0, 189.0, FZ + 12.0)
    yl = YB0 + R_TPR + ROTO_W + B23 + 2.0      # v11: clamped to the probe bracket's upper leg, at the blower's top
    by_c = YB0 + R_TPR + ROTO_W + B23 + 2 * WASHER["large"]["M3"][2] + 3.0 + 1.5 + BL_T + CRADLE_T     # back of the blower's cradle
    el.loom("toolhead", [Waypoint("xbody", (NOZ_X - 8.0, yl, Z_BEAM + 33.0), clamp="probe_mount"),
                         ("xbody", (NOZ_X - 12.0, yl + 14.0, Z_BEAM + 58.0)),      # v11: up past the blower's left side,
                         ("xbody", (NOZ_X + 12.0, by_c + 5.0, Z_BEAM + 70.0)),     # over its top and behind its cradle
                         Waypoint("xbody", (NOZ_X + 40.0, by_c + 1.5, BL_Z0 + BL_W - 1.0), clamp="part_duct"),   # on the cradle's back
                         Waypoint("world", (118.0, 175.0, FZ + 12.0), clamp="frame_top_back"), Waypoint("world", P1)],
            flex_length={3: 480.0})
    # over the back rail's rear edge on a 30 mm radius (the 10 mm bundle needs 26), down the outside of the back wall (beside the
    # right Y motor), and in again over the bottom back rail on the same radius
    arc = lambda yc, zc_, angs, xs: [("world", (x, yc + 30.0 * math.cos(math.radians(a)), zc_ + 30.0 * math.sin(math.radians(a)))) for a, x in zip(angs, xs)]
    el.loom("drop_right", [("world", P1)] + arc(189.0, FZ - 18.0, (60, 30, 0), (114.0, 110.0, 108.0))
            + [("world", (108.0, 219.0, 64.0))] + arc(189.0, 64.0, (-30, -60, -90), (108.0, 110.0, 114.0))
            + [("world", (118.0, 172.0, 33.5)), ("world", (130.0, 158.0, 33.5)), ("world", (145.0, 150.0, 34.0))])
    el.loom("tray_right", [("world", (145.0, 150.0, 34.0)), ("world", (147.0, 60.0, zt)), ("world", (147.0, -40.0, zt))])   # v9: inboard of the right upright
    el.loom("back", [("world", (140.0, 152.0, 30.0)), ("world", (126.0, 152.0, 26.0)), ("world", (66.0, 152.0, 26.0)),
                     ("world", (10.0, 140.0, 32.0))])
    el.loom("gantry", [Waypoint("ybody", (-142.0, YB0 + PL_Y0 + 5.0, Z_PLATE - 1.5), clamp="y_plate_left"),
                       Waypoint("world", (XL - 2.0, FRONT_Y + 13.0, FZ - 12.0), clamp="frame_top_left"), ("world", (XL, -124.0, ZL))],
            flex_length={0: 270.0})
    # v10: along the left top rail the loom lies IN the rail's inner T-slot (x -152.5): the Roto now passes 2 mm from that face
    el.loom("top_left", [("world", (XL, -122.0, ZL)), ("world", (-152.5, -110.0, FZ)), ("world", (-152.5, 136.0, FZ))])
    # v10: the X switch is on the right Y plate; its lead runs in the X beam's top slot to the left end, where the gantry loom leaves
    zbm = Z_PLATE + T_YP + 2.5
    el.loom("beam", [Waypoint("ybody", (-142.0, YB0 + PL_Y0 + 5.0, Z_PLATE - 1.5), clamp="y_plate_left"),
                     Waypoint("ybody", (-96.0, YB0 - 16.0, Z_BEAM + 6.0), clamp="x_beam"),
                     Waypoint("ybody", (-90.0, YB0, Z_BEAM + 7.5), clamp="x_beam"),
                     Waypoint("ybody", (92.0, YB0, Z_BEAM + 7.5), clamp="x_beam"),
                     ("ybody", (101.0, YB0 + 3.0, zbm)),                 # v11: up past the right Y plate's inner edge (x 108)
                     Waypoint("ybody", (112.0, YB0 + 7.5, zbm), clamp="y_plate_right"),
                     Waypoint("ybody", (142.0, YB0 + 8.0, zbm), clamp="y_plate_right"),
                     Waypoint("ybody", (150.0, YB0 + 24.0, zbm), clamp="y_plate_right")])
    el.loom("drop_left", [("world", (XL, -120.0, ZL)),
                          ("world", (-143.0, -140.0, FZ - 24.0)), ("world", (-143.0, -150.0 - FRONT_EXT, FZ - 60.0)),
                          ("world", (-143.0, FRONT_Y, FZ - 90.0)),
                          ("world", (-143.0, FRONT_Y, 70.0)), ("world", (-140.0, FRONT_Y + 4.0, 26.0))])
    el.loom("front", [("world", (-140.0, FRONT_Y + 4.0, 26.0)), ("world", (60.0, FRONT_Y + 4.0, 26.0)), ("world", (72.0, -142.0, zt))])
    el.loom("bed", [Waypoint("zbody", (-62.0, SQ_Y1 - 21.0, Z_SQ + 5.0), clamp="sq_rear"),
                    Waypoint("zbody", (-62.0, SQ_Y1 - 21.0, Z_SQB - 2.0), clamp="sq_rear"),
                    Waypoint("world", (-40.0, TRAY_Y1 - 1.0, Z_TRAY + 3.0), clamp="electronics_tray")], flex_length={1: 365.0})
    el.loom("mains", [("world", (-115.0, 9.0, zt)), ("world", (-108.0, 44.0, zt)), ("world", (-100.0, 84.0, zt))])
    tool, left = ["tray_right", "drop_right", "toolhead"], ["front", "drop_left"]
    mk = dict(conductors=1, insulation="pvc105")
    el.wire("mains L inlet-contactor", "inlet.L", "psu_relay.LIN", 18, **mk)
    el.wire("mains L contactor-supply", "psu_relay.LOT", "psu.L", 18, via=["mains"], **mk)
    el.wire("mains N inlet-contactor", "inlet.N", "psu_relay.NIN", 18, **mk)
    el.wire("mains N contactor-supply", "psu_relay.NOT", "psu.N", 18, via=["mains"], **mk)
    el.wire("contactor control", "host.PWR", "psu_relay.ctrl", 22, conductors=2,
            note="Pi GPIO26 -> 1 kOhm -> PN2222A base; collector to the Phoenix PLC-RSC-5DC/21 coil (5 V from the Pi's 5 V pin, 38 mA); "
                 "the Phoenix contact switches the Finder's 120 V coil from the inlet's L after its fuse (A1) and N (A2). Moonraker "
                 "[power printer] type gpio, off_when_shutdown True, locked_while_printing True. The coil circuit itself is mains: "
                 "18 AWG in the mains loom; this 2-core lead is the 5 V control side")
    # v12 (COMMODITY_PARTS): 16 AWG green/yellow (LAPP 4160400), one conductor per tab: inlet PE -> frame stud; the supply's FG and
    # the bed plate each bonded from the stud on their own ring lug
    el.wire("earth to frame", "inlet.PE", "frame_earth.pe", 16, connector_b="ring-M5", **mk)
    el.wire("earth stud to supply", "frame_earth.pe", "psu.FG", 16, connector_a="ring-M5", via=["mains"], **mk)
    el.wire("24 V to board", "psu.V+1", "control_board.POWER", 14, insulation="silicone")      # v12: 14 AWG (the bed's 8 A rides it)
    el.wire("bed heater", "control_board.HB", "bed_tco.a", BED_AWG, insulation=BED_INS, via=["bed"])
    el.wire("bed heater tail", "bed_tco.b", "bed_heater.in", BED_AWG, insulation=BED_INS, length=90.0)
    el.wire("bed thermistor", "control_board.THB", "bed_ntc.out", 26, insulation="silicone", via=["bed"])
    el.wire("hotend heater", "control_board.HE0", "hotend.in", 20, insulation="silicone", via=tool, pigtail=(115.0, "fiberglass"))
    el.wire("hotend thermistor", "control_board.TH0", "hotend_thermistor.out", 26, insulation="silicone", via=tool,
            pigtail=(130.0, "fiberglass"))
    el.wire("heat-sink fan 5 V", "control_board.5V", "hotend_fan.out", 26, via=tool,
            note="the Roto's fan is a 5 V part: always on from the board's 5 V pins, never on a 24 V fan output")
    el.wire("part fan", "control_board.FAN0", "part_fan.in", 26, via=tool)
    # v12: the BTT Eddy Duo is on USB to the Pi 5 (its own RP2040 MCU, mainline Klipper [probe_eddy_current]); 5 V from the USB port
    el.wire("bed probe USB", "host.USB", "bed_probe.out", 26, conductors=4, insulation="silicone", via=tool,
            note="high-flex 4-core lead (igus CF130 class) with the Eddy's 1.5 mm-pitch housing; 5 V, D-, D+, GND (BTT manual 4.15)")
    el.devices["bed_probe"].params.update(supply_v=5.0, supply_from="Pi 5 USB port (5 V)")
    el.wire("extruder motor", "control_board.M4", "extruder.coils", 24, conductors=4, via=tool)
    el.wire("X motor", "control_board.M0", "x_motor.coils", 24, conductors=4, via=left + ["gantry"])
    el.wire("X endstop", "control_board.STOP0", "x_endstop.out", 26, conductors=3, via=left + ["gantry", "beam"],
            note="STOP0 (DIAG0) header, its DIAG jumper removed; in the X beam's top slot from the left end to the switch on the right Y plate")
    el.wire("Y endstop", "control_board.STOP1", "y_endstop.out", 26, conductors=3, via=["tray_right", "drop_right"],
            note="STOP1 (DIAG1) header, its DIAG jumper removed")
    el.wire("Y motor left", "control_board.M2", "y_motor_l.coils", 24, conductors=4, via=left + ["top_left"],
            note="mirror-image motor on its own driver ([stepper_y1]): invert its dir_pin (or swap one coil pair) so both turn the belts the same way")
    el.wire("Y motor right", "control_board.M1", "y_motor.coils", 24, conductors=4, via=["tray_right", "drop_right"])
    # v8.2: three Z motors, each on its own driver; their 500 mm leads plug straight into the Octopus (front-right: a short
    # stub; front-left: along the front loom; rear: along the back loom)
    el.wire("Z motor rear", "control_board.M3", "z_motor.coils", 24, conductors=4, via=["tray_right", "back"])
    el.wire("Z motor front left", "control_board.M5", "z_motor_fl.coils", 24, conductors=4, via=["front"])
    el.wire("Z motor front right", "control_board.M6", "z_motor_fr.coils", 24, conductors=4)
    el.wire("host serial", "control_board.RPI", "host.GPIO", 26, conductors=4,
            note="Octopus 'Raspberry Pi' header GND, PD6 RX, PD5 TX (USART2) to the Pi 5's GPIO 6/8/10; the 5 V conductor is cut back and "
                 "insulated at the Pi end (NO 5 V: the Pi has its own 27 W "
                 "supply (V12_PLAN); Klipper serial /dev/ttyAMA0 (enable the UART on the Pi 5)")
    el.firmware = {
        "kind": "klipper",
        "steppers": {"x": {"run_current": RUN_CURRENT["x"]}, "y": {"run_current": RUN_CURRENT["y"]},
                     "z": {"run_current": RUN_CURRENT["z"]},
                     "extruder": {"motors": ["extruder"], "run_current": RUN_CURRENT["extruder"]}},
        # Z_TILT_ADJUST: the three screws in the firmware's XY (nozzle) coordinates, and three probe points (nozzle
        # positions; the probe is 34.5 mm behind the nozzle) as close to each screw as the probe reaches over the plate
        "z_tilt": Z_TILT,
        "heaters": {"extruder": {"heater": "hotend", "sensor": "hotend_thermistor", "control": "pid", "min_temp": 0,
                                 "max_temp": 280, "targets": [250.0], "verify_heater": {}},
                    "heater_bed": {"heater": "bed_heater", "sensor": "bed_ntc", "control": "pid", "min_temp": 0, "max_power": 0.95,
                                   "max_temp": BED_MAX_C + 10.0, "targets": [60.0, BED_MAX_C], "verify_heater": {}}},
        "fans": {"part_fan": {"device": "part_fan", "role": "part"}, "hotend_fan": {"device": "hotend_fan", "role": "heatsink"}},
    }
    hi = d.get("hotend").meta["interfaces"]
    rc = hi["heatercore_dia"] / 2
    hb = (-rc, YB0 + HOT_OFF - rc, hi["heater_block_box"][0][2], rc, YB0 + HOT_OFF + rc, hi["heater_block_box"][1][2])
    el.hot_parts = {"hotend": {"temp": 250.0, "box": hb}, "bed": BED_MAX_C}
    el.bay = Bay(devices=[n for n in ("psu", "control_board", "host", "psu_relay") if n in el.devices],
                 enclosed=False, vent_area_m2=0.02, height_m=0.05)
    el.sync_cables(d)
    add_electrical_bom(el, d)
    d.bom_extra(f"FUSE-5x20-T{FUSE_A:g}A", 2, 1.09, stage=1)       # one in the drawer, one spare (Schurter 0001.2513)
    add_v12_bom_lines(d)
    feedback_firmware(el, d)
    return el


def motor_plate_shape(x0, y0, posts, z_mf=Z_MF):
    """6.35 mm 6061 plate the motor hangs under: the convex hull of discs round the motor's four screws and the two posts
    (a polygon of short straight cuts), the pilot hole (locates the motor), four M3 and two M5 clearance holes."""
    circ = lambda cx, cy, r: [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    z_t = z_mf + T_MP
    pts = []
    for ox in (-15.5, 15.5):
        for oy in (-15.5, 15.5):
            pts += circ(x0 + ox, y0 + oy, 6.5)
    for px, py in posts:
        pts += circ(px, py, 8.0)
    s = Pos(0, 0, z_mf) * extrude(Polygon(*convex_hull(pts), align=None), T_MP)
    s -= zc(x0, y0, z_mf, z_t, MP_PILOT_HOLE / 2)
    for ox in (-15.5, 15.5):
        for oy in (-15.5, 15.5):
            s -= zc(x0 + ox, y0 + oy, z_mf, z_t, clearance_hole("M3") / 2)
    for px, py in posts:
        s -= zc(px, py, z_mf, z_t, clearance_hole("M5") / 2)
    return s


def build_z_mount(d, tag, x0, y0, turn, posts, rail, on_tray):
    """One Z drive: a 17E19S1684AB4-330RA lead-screw motor (body + its integral Tr8x2 screw, 328 mm above the face AS SOLD)
    hanging under a laser-cut motor plate on two aluminium posts. Four M3 x 10 from the plate's top thread 3.65 mm into the
    motor's own M3 holes (4.5 deep: 1.2 d, 0.85 mm short of the bottom), thread-locked. v11: each post is two STOCK
    aluminium spacers stacked (40 + 13.2 at the rear, on the bottom back rail; 40 + 9 at the front, on the tray), an M5 x 65
    with a washer under its head through the plate, the spacers (and the tray at the front) into a T-nut in the bottom rail,
    thread-locked. No top bearing: the screw runs free-ended (docs/PRINTER_V8_2.md: whip, over-constraint).
    Returns its part names."""
    P = lambda n: f"z_mount{tag or '_rear'}_{n}"
    mot, scr, plate = f"z_motor{tag}", f"leadscrew{tag}", f"z_motor_plate{tag}"
    z_mf, z_base, lens = (Z_MF_F, Z_BASE_F, POSTS_F) if on_tray else (Z_MF_R, Z_BASE_R, POSTS_R)
    z_t = z_mf + T_MP
    names = [plate, mot, scr]
    sheet(d, plate, motor_plate_shape(x0, y0, posts, z_mf), AL)
    place(d, mot, leadscrew_motor_a4003(), Location((x0, y0, z_mf), (0, 0, turn)))
    place(d, scr, leadscrew_screw_a4003(Z_SCREW_ABOVE), Location((x0, y0, z_mf)))
    d.join(scr, mot, "integral screw: the motor's shaft")
    d.get(scr).meta["description"] = (f"Tr8x2 lead screw: the shaft of {mot} itself (StepperOnline 17E19S1684AB4-330RA), used as sold: "
                                      f"{Z_SCREW_ABOVE:g} mm above the motor face (330 nominal), not cut; free at its top end (no bearing). "
                                      f"Not a separate part to buy.")
    d.get(mot).meta["description"] = (f"Lead-screw stepper hanging under {plate}: its 22 mm pilot locates in the plate's hole, four M3 x 10 "
                                      f"from above thread into its own housing. Its shaft is the lead screw {scr}.")
    d.allow_overlap(scr, mot)                    # the screw enters the motor through its pilot (the solids meet there)
    d.join(mot, plate, "pilot located in the plate's 22.3 mm hole, face on the plate")
    for i, (ox, oy) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        nm = f"{mot}_screw_{i}"
        add_screw(d, nm, "M3", 10, at=(x0 + ox, y0 + oy, z_t), direction=(0, 0, -1), threads_into=mot, clamps=(plate,),
                  locking="adhesive")
        names.append(nm)
    for i, (px, py) in enumerate(posts):
        # v12: one turned 6061 standoff per post (Xometry), its length the stack's: no stocked M5 round spacer at these
        # lengths with a maker's drawing was found (RAF lists 3 / 5 / 11 / 44 mm, none in stock, drawing not in hand)
        sp = P(f"spacer_{i}")
        L_post = sum(lens)
        d.add(sp, Pos(px, py, z_base + L_post / 2) * (Cylinder(5.0, L_post) - Cylinder(5.3 / 2, L_post)), material=AL, process="machined",
              meta={"cnc_reason": "a 10 x 5.3 mm round post, " + f"{L_post:g}" + " mm long: turned from 10 mm 6061 bar (no stocked M5 spacer of that length with a maker drawing)",
                    "edge_break_mm": 0.3, "form": "turned", "dfm": {"shop": "xometry"},
                    "description": f"Turned 6061 post under {plate}: dia 10 x 5.3 bore x {L_post:g} mm, faces square; the M5 post bolt passes it"})
        sps = [sp]
        b = P(f"bolt_{i}")
        add_screw(d, b, "M5", 65, at=(px, py, z_t), direction=(0, 0, -1), clamps=(plate, *reversed(sps)) + (("electronics_tray",) if on_tray else ()),
                  threads_into=rail, tnut=True, washer=True, locking="adhesive")
        names += sps + [b, f"{b}_washer"]
    return names


def build_frame_z():
    d = Design("printer_v12", envelope=ENVELOPE, base="frame_bot_left")
    d.tnut_style = "drop_in"      # v10.1: T-nuts and bracket screws are drawn parts; T-slot screw lengths are checked
    d.manufacturing = {"shop": "sendcutsend", "sheet": {"method": "laser"},
                       "printer": {"build_volume": (220.0, 220.0, 220.0), "nozzle": 0.4},
                       "print_settings": dict(PRINT_ABS)}
    # ================= frame (v8) ================================================
    # v8.2: the side rails are FRONT_EXT longer, all at the front; the front rails and posts move forward with them and
    # the top front rail is flush with the other three
    yrail = lambda sy: (FY / 2 - 10) if sy > 0 else FRONT_Y
    for sx, n in ((-1, "left"), (1, "right")):
        for z, lvl in ((FZ, "top"), (10, "bot")):
            place(d, f"frame_{lvl}_{n}", extrusion_2020(FD), Location((sx * RAIL_X, -FRONT_EXT / 2, z), (0, 0, 90)))
    for sy, n in ((-1, "front"), (1, "back")):
        for z, lvl in ((FZ, "top"), (10, "bot")):
            place(d, f"frame_{lvl}_{n}", extrusion_2020(FX - 40), Location((0, yrail(sy), z)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            place(d, f"post_{'l' if sx < 0 else 'r'}{'f' if sy < 0 else 'b'}", extrusion_2020(FZ - 30),
                  Location((sx * RAIL_X, yrail(sy), (FZ + 10) / 2), (0, 90, 0)))
    k = 0
    for sx in (-1, 1):
        side = "left" if sx < 0 else "right"
        for sy in (-1, 1):
            post = f"post_{'l' if sx < 0 else 'r'}{'f' if sy < 0 else 'b'}"
            cross = "front" if sy < 0 else "back"
            yi = yrail(sy) - sy * 10.0
            for lvl, zcen, zdir in (("top", FZ - 10, -1), ("bot", 20, 1)):
                cbr(d, f"bracket_{k}", f"frame_{lvl}_{side}", post, (sx * RAIL_X, yi, zcen), (0, -sy, 0), (0, 0, zdir)); k += 1
                if lvl == "top":
                    cbr(d, f"bracket_{k}", f"frame_{lvl}_{cross}", post,
                                       (sx * (RAIL_X - 10), yrail(sy), FZ - 10.0),
                                       (-sx, 0, 0), (0, 0, -1)); k += 1
                else:
                    cbr(d, f"bracket_{k}", f"frame_{lvl}_{cross}", f"frame_{lvl}_{side}",
                                       (sx * (RAIL_X - 10), yi, 10), (-sx, 0, 0), (0, -sy, 0)); k += 1
    # ================= Z guides (v9): three uprights, three rails, one ZF block each ==========
    # Left and right uprights stand in the side walls between the bottom and top side rails, the rear one in the back
    # wall; each rail is on its upright's inner face. One clearance-class (ZF) block per rail: the three screws hold the
    # carrier's tilt, the blocks only locate it across the axis. Each block's plate has a flexure web, soft square to
    # the wall, so left and right hold Y and yaw and the rear holds X: three stiff directions, none redundant.
    up = np.array([0.0, 0.0, 1.0])
    guide_parts = {}
    # v10.1: the carrier's four members are placed before anything is screwed to them (a drawn T-nut goes into its slot)
    for sx, n in ((-1, "left"), (1, "right")):
        place(d, f"sq_{n}", extrusion_2020(SQ_Y1 - SQ_Y0), Location((sx * (SQ_X - 10.0), BED_CY, Z_SQ), (0, 0, 90)), body="zbody")
    for sy, n, yc in ((-1, "front", SQ_Y0 + 10.0), (1, "rear", SQ_Y1 - 10.0)):
        place(d, f"sq_{n}", extrusion_2020(2 * (SQ_X - 20.0)), Location((0, yc, Z_SQ)), body="zbody")
    for nm, (bx_, by_), nrm, wall in GUIDES:
        nv = np.array(nrm)
        tv = np.cross(up, nv)                            # along the wall
        ux, uy = bx_ - 10.0 * nv[0], by_ - 10.0 * nv[1]
        place(d, f"upright_{nm}", extrusion_2020(FZ - 30), Location((ux, uy, (FZ + 10) / 2), (0, 90, 0)))
        for lvl, zcen, zdir in (("bot", 20, 1), ("top", FZ - 10, -1)):
            for s_, tg in ((-1, "a"), (1, "b")):
                cbr(d, f"brkt_up_{lvl}_{tg}_{nm}", f"frame_{lvl}_{wall}", f"upright_{nm}",
                                   (ux + s_ * 10.0 * tv[0], uy + s_ * 10.0 * tv[1], zcen), tuple(s_ * tv), (0, 0, zdir))
        plane = lambda z: Plane(origin=(bx_, by_, z), x_dir=(0, 0, 1), z_dir=tuple(nv))
        rail = place(d, f"z_rail_{nm}", hiwin_mgn12_rail(Z_RAIL_L), Location(plane(Z_RAIL_C)))
        for i, h in enumerate(rail.meta["interfaces"]["mount_holes_m3"][::2]):
            add_screw(d, f"z_rail_{nm}_screw_{i}", "M3", 8, at=tuple(np.array(h) + 3.5 * nv), direction=tuple(-nv),
                      threads_into=f"upright_{nm}", tnut=True)
        car = place(d, f"z_carriage_{nm}", hiwin_mgn12h_block(), Location(plane(ZC)), body="zbody", guides="z")
        # the mount floats along the wall's normal on the plate's web (tolerance verifier: mechloop.tolerance._rail_set)
        E_, G_ = MATERIALS[AL].E, MATERIALS[AL].E / (2 * (1 + MATERIALS[AL].nu))
        car.meta["guide_float"] = {"axis": tuple(nv), "stiffness_n_per_mm": round(K_FLEX, 1), "range_mm": FLEX_RANGE,
                                   # v10: the web itself, for the allowable screw tilt (bed_support.tilt_allowance): its
                                   # stress when the carrier is tilted against the block. kt: a flat bar stepping from
                                   # 50 to 24 mm with 3 mm radii, in bending (Peterson's charts give about 1.7; ASSUMED)
                                   "web": {"length_mm": L_FLEX, "width_mm": CP_WEB, "thickness_mm": T_CP, "material": AL, "kt_in_plane": 1.7},
                                   "by": f"the {L_FLEX:g} x {CP_WEB:g} x {T_CP:g} mm web of carriage_plate_{nm}",
                                   # the web as a beam between block and square, N.mm/rad (E I / L, G J / L): the bed-support
                                   # model puts these in series with the block's own moment stiffness
                                   "rotation_n_mm_per_rad": {"about_float_axis": round(E_ * T_CP * CP_WEB ** 3 / 12 / L_FLEX),
                                                             "about_across": round(E_ * CP_WEB * T_CP ** 3 / 12 / L_FLEX),
                                                             "about_travel": round(G_ * CP_WEB * T_CP ** 3 / 3 / L_FLEX)}}
        face = np.array([bx_, by_, Z_SQ]) + RAIL_FACE * nv          # on the block's mounting plane, at the square's centre line
        cp = Location(Plane(origin=tuple(face), x_dir=tuple(tv), z_dir=tuple(nv))) * carriage_plate_local(ZC - Z_SQ)
        pl = f"carriage_plate_{nm}"
        d.add(pl, cp, material=AL, body="zbody", process="sheet", meta={"finish": "bare", "description": (
            f"Carriage plate ({nm}): one of three identical flat 1.6 mm 6061 plates. Its top 20 mm is bolted to the 2020 square's "
            f"outer face (two M5, T-nuts); its bottom carries the guide block z_carriage_{nm} (four M3 x 5 into the block's own "
            f"threads). The {L_FLEX:g} mm web between them is a flexure: stiff along the wall, soft square to it ({K_FLEX:.0f} N/mm), "
            f"so this block locates the carrier along the wall only and a rail that is not exactly parallel, or a carrier that "
            f"has grown warm, bends the web instead of loading the block.")})
        for i, h in enumerate(car.meta["interfaces"]["mount_holes_m3"]):
            add_screw(d, f"z_carriage_{nm}_screw_{i}", "M3", 5, at=tuple(np.array(h) + T_CP * nv), direction=tuple(-nv), body="zbody",
                      threads_into=f"z_carriage_{nm}", clamps=(pl,), washer=True, locking="adhesive")
        member = "sq_rear" if nm == "rear" else f"sq_{nm}"
        for i, u in enumerate((-CP_BOLT_U, CP_BOLT_U)):
            add_screw(d, f"{pl}_bolt_{i}", "M5", 8, at=tuple(face + u * tv), direction=tuple(nv), body="zbody",
                      threads_into=member, tnut=True, clamps=(pl,), washer=True, locking="adhesive")
        guide_parts[nm] = (nv, np.array([bx_, by_]))

    # ================= carrier (v9): a closed 2020 rectangle, a deck on top =====================
    for sy, n, yc in ((-1, "front", SQ_Y0 + 10.0), (1, "rear", SQ_Y1 - 10.0)):
        for sx, sn in ((-1, "left"), (1, "right")):
            # one cast bracket in each inside corner, both legs on T-nuts
            cbr(d, f"sq_bracket_{n[0]}{sn[0]}", f"sq_{sn}", f"sq_{n}", (sx * (SQ_X - 20.0), yc - sy * 10.0, Z_SQ),
                               (0, -sy, 0), (-sx, 0, 0), body="zbody", slot_leg={"locking": "adhesive"})      # v10.1: on the moving carrier
    d.add("z_deck", deck_shape(), material=AL, body="zbody", process="sheet", meta={"finish": "bare", "description": (
        "Deck: 3.175 mm (1/8 in) 6061 sheet on top of the 2020 square, twelve M5 into T-nuts. It closes the rectangle in shear, "
        "shields the carrier from the heater, and is what the bed is levelled against: the three bed studs pass through it "
        "(one fitted hole, one slot, one oversize) and the thumb nuts bear on its underside.")})
    for i, (x, y) in enumerate(DECK_BOLTS):
        member = ("sq_left" if x < 0 else "sq_right") if abs(abs(x) - (SQ_X - 10.0)) < 1e-6 else ("sq_front" if y < BED_CY else "sq_rear")
        add_screw(d, f"z_deck_bolt_{i}", "M5", 8, at=(x, y, Z_DECK1), body="zbody", threads_into=member, tnut=True,
                  clamps=("z_deck",), washer=True, locking="adhesive")      # v11 (owner): M5 x 8, one washer (v10.1: M5 x 10, two)

    # ================= nut plates and captive floating POM nuts (v11) ==========
    zn0, zn1 = Z_TAB, Z_SQB
    for tg, cx, cy, ang, member in NUTS:
        W = lambda u, r_: rxy(u, r_, cx, cy, ang)
        n_out = NUT_OUT_R if tg == "" else NUT_OUT_F
        d.add(f"nut_plate{tg}", rz(nut_plate_local(zn0, zn1, n_out), cx, cy, ang), material=AL, body="zbody", process="sheet", meta={"finish": "bare"})
        for i, u in enumerate((-NP_BOLT_U, NP_BOLT_U)):
            # v11: M5 x 16 with one washer through the 9.525 mm plate: 5.4 mm into the slot, through the T-nut's whole thread
            add_screw(d, f"nut_plate{tg}_bolt_{i}", "M5", 16, at=(*W(u, -n_out - 10.0), zn0), direction=(0, 0, 1), body="zbody",
                      threads_into=member, tnut=True, clamps=(f"nut_plate{tg}",), washer=True, locking="adhesive")
        px, py = W(*NUT_PIN)
        # the POM anti-backlash nut the motor ships with: flange face up against the plate's underside, barrel hanging below
        place(d, f"z_nut{tg}", leadscrew_nut_pom_a4003(), Location((cx, cy, Z_TAB), (0, 0, ang)), body="zbody")
        place(d, f"nut_pin{tg}_sleeve", spacer_harwin(10, "aluminium"), Location((px, py, Z_TAB)), body="zbody")     # v12: Harwin R30-6201014
        add_screw(d, f"nut_pin{tg}", "M3", 20, at=(px, py, Z_TAB + 10.0), body="zbody", clamps=(f"nut_pin{tg}_sleeve", f"z_nut{tg}"),
                  locking="adhesive")      # v10.1 / v11 (owner): the drawn hex nut, thread-locked
        add_nut(d, f"nut_pin{tg}_nut", "M3", at=(px, py, Z_TAB - NUT_FT), direction=(0, 0, -1), body="zbody", screw=f"nut_pin{tg}")
        d.join(f"z_nut{tg}", f"nut_plate{tg}", "floating: the carrier sits on its flange; the pin in the slot stops it turning")
        # captive: a 3.175 mm 6061 keeper under the flange, 0.1 mm clear of it, on two M3 through-bolts with spacers: the
        # flange floats sideways between plate and keeper but the carrier cannot lift off it; the barrel passes the keeper
        kz1 = Z_TAB - NUT_FT - KEEP_GAP
        kz0 = kz1 - T_KEEP
        d.add(f"nut_keeper{tg}", rz(nut_keeper_local(kz0, kz1), cx, cy, ang), material=AL, body="zbody", process="sheet", meta={"finish": "bare"})
        for k_, (u, v) in enumerate(KEEP_HOLES):
            bx_, by_ = W(u, v)
            spn = f"nut_keeper{tg}_spacer_{k_}"
            place(d, spn, spacer_harwin(int(round(KEEP_GAP + NUT_FT)), "aluminium"), Location((bx_, by_, kz1)), body="zbody")     # v12: Harwin R30-6200614
            bolt_nut(d, f"nut_keeper{tg}_bolt_{k_}", "M3", screw_len(T_NP + KEEP_GAP + NUT_FT + T_KEEP + 1.0, 4.0, 1.0, choices=(20, 25, 30)),
                     (bx_, by_, zn1), (0, 0, -1), "zbody", (f"nut_plate{tg}", spn, f"nut_keeper{tg}"), nut_at=(bx_, by_, kz0),
                     large=True)
            d.get(f"nut_keeper{tg}_bolt_{k_}").meta["locking"] = "adhesive"      # v12: hex nut + Loctite 243 (the nyloc's 120 degC rating has no maker figure)
        d.join(f"z_nut{tg}", f"nut_keeper{tg}", "captive: the flange sits between plate and keeper, 0.1 mm play, free to float sideways")
        how = (f"How the bed is lifted: the POM anti-backlash nut z_nut{tg} (supplied on the motor's screw; dimensions a STAND-IN) rides lead "
               f"screw leadscrew{tg}. Its square flange is under this {T_NP:g} mm plate, which is bolted under the 2020 square's member "
               f"{member} (two M5 from below into T-nuts) and reaches {n_out:.1f} mm out to the screw; the nut's barrel hangs below. "
               f"The carrier's weight rests on the flange, so when the screw turns the nut climbs it and lifts the plate, the square, "
               f"the deck and the bed. The M2.5 pin screw nut_pin{tg} (through a 5 mm aluminium sleeve, fixed in a corner hole of the "
               f"flange) sits in a radial slot in the plate: it stops the nut turning with the screw while letting it float "
               f"{NUT_FLOAT:g} mm sideways. The nut is captive: the laser-cut keeper nut_keeper{tg}, bolted 0.1 mm under the flange "
               f"on two M3 through-bolts and spacers, stops the plate lifting off it.")
        d.get(f"nut_plate{tg}").meta["description"] = "Laser-cut 6061 nut plate under the carrier's square. " + how
        d.get(f"z_nut{tg}").meta["description"] = f"POM anti-backlash nut, floating and captive under nut_plate{tg}. " + how
        d.get(f"nut_keeper{tg}").meta["description"] = (f"Keeper: holds z_nut{tg}'s flange up against nut_plate{tg} (0.1 mm play, free to float "
                                                       f"sideways) so the carrier cannot lift off the nut. " + how)

    # ================= bed (v11): 6.35 mm MIC-6 plate, 220 mm sheet, three sprung levelling studs ==========
    bed_own = BED * BED * T_BED * MATERIALS[CAST].density * 1e-9
    d.add("bed_plate", round_profile(bed_shape_(), 2.0, T_BED), material=CAST, body="zbody", mass_kg=bed_own + PAYLOAD_KG, process="sheet",
          meta={"finish": "bare", "note": "MIC-6 6.35 mm, laser cut at SendCutSend, faces as cast; three 90-degree countersinks for M4 "
                                          "(8.96 mm) from the top face. Receiving inspection: flat within 0.13 mm over the piece "
                                          "(straight edge and feeler), the figure the flatness limit is worked with"})
    mag = whambam_base_220()      # v12: Wham Bam 220 magnetic base, 1 mm, 150 degC (maker page)
    place(d, "bed_magnet", mag, Location((BED_CX, BED_CY, Z_BED + T_BED)), body="zbody")
    place(d, "bed", whambam_plate_220(), Location((BED_CX, BED_CY, Z_BED + T_BED + T_MAG)), body="zbody")
    d.join("bed_magnet", "bed_plate", "bond")
    d.join("bed", "bed_magnet", "magnet")
    place(d, "bed_heater", heater_keenovo_200(), Location((BED_CX, BED_CY, Z_BED), (0, 0, 180)), body="zbody")
    d.join("bed_heater", "bed_plate", "bond")
    add_thermostat(d)
    for nm_, txt in (("bed_heater", f"Silicone heater pad {PAD_X:g} x {PAD_Y:g} mm, adhesive-backed, bonded to bed_plate's underside between the front studs "
                                    "and the rear stud (no fasteners): it covers the print area's whole width and all but 3.75 mm of its depth at each end."),
                     ("bed_magnet", "Magnetic base sheet of the 220 mm PEI plate (rated 120 degC continuous), adhesive-backed, bonded to bed_plate's top face over the studs' heads (no fasteners)."),
                     ("bed", "220 x 220 mm textured PEI spring-steel print sheet, held on bed_magnet by magnetism alone: lift it off to remove prints."),
                     ("bed_tco", "Thermal fuse, bonded to bed_plate's underside with high-temperature adhesive (thermal contact), in series with the heater."),
                     ("bed_plate", f"MIC-6 bed plate, {BED:g} x {BED:g} x {T_BED:g} mm: it floats {GAP:g} mm above the deck on three M4 studs (countersunk screws from "
                                   "its top face, each locked to it by a nut underneath), pushed up by three die springs against three thumb "
                                   "nuts under the deck; the heater pad is bonded under it, the magnetic base on top.")):
        d.get(nm_).meta["description"] = txt
    # each levelling point, top to bottom: M4 x 35 countersunk screw (fully threaded) from the plate's top face; M4 washer
    # and nut under the plate, thread-locked (the screw is now a stud fixed in the plate: it cannot turn with the thumb
    # nut); die spring; M4 washer on the deck (the spring's seat: it slides on the deck as the plate grows); deck; large M4
    # washer; DIN 466 thumb nut. The spring pushes the plate up against the thumb nut: turning the nut sets the height.
    for i, (x, y) in enumerate(BED_MOUNTS):
        p = f"bed_stud_{i}"
        wt, jam, spr, seat, dw, th = f"{p}_washer", f"{p}_nut", f"bed_spring_{i}", f"bed_spring_{i}_seat", f"bed_thumb_{i}_washer", f"bed_thumb_{i}"
        add_washer(d, wt, "M4", (x, y, Z_BED), (0, 0, -1), body="zbody")
        # the head is placed where it seats: CSK_SINK below the surface, its cone on the countersink's cone (the catalogue
        # draws the head at its actual diameter, 7.53, which a countersink cut to the theoretical 8.96 takes that far down)
        sc = add_screw(d, p, "M4", STUD_L, at=(x, y, Z_BED + T_BED - CSK_SINK), direction=(0, 0, -1), body="zbody",
                       clamps=("bed_plate", wt, "z_deck"), head="countersunk", locking="adhesive")
        sc.meta["fully_threaded"] = True          # buy DIN 7991 / ISO 10642 fully threaded: the lock nut sits 6 to 10 mm under the head
        d.join(wt, "bed_plate", "clamped by the stud's lock nut")
        add_nut(d, jam, "M4", at=(x, y, Z_BED - W4), direction=(0, 0, -1), body="zbody", screw=p, locking="adhesive")
        d.join(jam, wt, "clamp")
        place(d, spr, die_spring_dj8x20(SPRING_H), Location((x, y, Z_DECK1 + W4)), body="zbody")
        add_washer(d, seat, "M4", (x, y, Z_DECK1), (0, 0, 1), body="zbody")
        d.join(spr, jam, "spring seat: the spring's top bears on the stud's lock nut")
        d.join(spr, seat, "spring seat")
        d.join(seat, "z_deck", "sliding: the spring's seat washer lies on the deck, held by the spring's preload")
        add_washer(d, dw, "M4", (x, y, Z_SQT), (0, 0, -1), body="zbody", series="large")
        d.join(dw, "z_deck", "clamp: held against the deck's underside by the spring's preload (the located stud)" if i == 0 else
               "sliding free: held against the deck's underside by the spring's preload, slips as the plate grows")
        add_thumb_nut(d, th, "M4", (x, y, Z_SQT - W4L), (0, 0, -1), body="zbody", screw=p)
        d.join(th, dw, "clamp")
        hole = ("a fitted 4.3 mm hole (this stud, front left, locates the bed)" if i == 0 else
                "a 4.3 mm slot pointing at stud 0 (front right: holds the bed from turning)" if i == 1 else "a 5.5 mm oversize hole (rear: free)")
        desc = (f"Bed levelling point {i}: an M4 x {STUD_L:g} countersunk screw from the bed's top face (head 0.7 mm below it, under the "
                f"magnetic base) is locked to the plate by a washer and nut underneath, so it is a fixed stud. A die spring "
                f"(DJ-8X20YCS, {SPRING_K} N/mm, compressed {20 - SPRING_H:g} mm: {SPRING_K * (20 - SPRING_H):.0f} N) between that nut and the "
                f"deck pushes the bed up; the stud passes the deck through {hole} and a large washer and knurled thumb nut under "
                f"the deck hold it down. Turn the thumb nut to level: 0.7 mm per turn, +/-{LEVEL_RANGE:g} mm. Three points: they set the bed's "
                f"plane and cannot twist the plate.")
        for nm_ in (p, jam, spr, th):
            d.get(nm_).meta["description"] = desc
    d.join("bed_plate", "z_deck", "three sprung levelling studs")
    # ================= Z drive: three lead-screw motors, each on its own laser-cut plate ======
    mounts = []
    # v11: the rear motor stands outboard of the back wall; its plate's posts are in the bottom back rail's top slot (y 170)
    rear_posts = [(-MP_POST_DX_R, FY / 2 - 10), (MP_POST_DX_R, FY / 2 - 10)]
    # (tag, screw x, y, motor turn, posts, rail part, base: tray (front) or the rail (rear)). Connectors: rear to +X (along the
    # wall, clear of the rail), fronts inboard
    mounts.append(("", 0.0, LS_Y, 0.0, rear_posts, "frame_bot_back", False))
    for sx, tg in ((-1, "_fl"), (1, "_fr")):
        # posts stay on the bottom side rail's centre line (x +/-160), the motor 15.5 mm inboard of it
        mounts.append((tg, sx * FS_X, FS_Y, 0.0 if sx < 0 else 270.0, [(sx * RAIL_X, FS_Y - MP_POST_DY), (sx * RAIL_X, FS_Y + MP_POST_DY - 1.0)],
                       f"frame_bot_{'left' if sx < 0 else 'right'}", True))
    mount_parts = {}
    for tg, x0, y0, turn, posts, rail, on_tray in mounts:
        mount_parts[tg] = build_z_mount(d, tg, x0, y0, turn, posts, rail, on_tray)
    def on_rail_of(nm):
        nv, base = guide_parts[nm]
        k, want = (0, base[0] + 8.0 * nv[0]) if abs(nv[0]) > 0.5 else (1, base[1] + 8.0 * nv[1])
        return lambda f: abs((f.center().X, f.center().Y)[k] - want) < 1e-6      # the block's face on the rail's top
    names = [g[0] for g in GUIDES]
    zs = {"tags": ("", "_fl", "_fr"), "zcars": [f"z_carriage_{n}" for n in names],
          "rails": {f"z_carriage_{n}": f"z_rail_{n}" for n in names},
          "carrier": ["sq_left", "sq_right", "sq_front", "sq_rear", "z_deck"] + [f"carriage_plate_{n}" for n in names]
                     + [f"sq_bracket_{e}{s}" for e in ("f", "r") for s in ("l", "r")],
          "nut_plates": ["nut_plate", "nut_plate_fl", "nut_plate_fr"],
          "on_rail": {f"z_carriage_{n}": on_rail_of(n) for n in names}}
    return d, zs, bed_own, mounts, mount_parts


def cover_hood(x0, x1, y0, y1, z0, z1, t=1.6, bosses=()):
    """Printed hood over live terminals: a top plate and two walls along Y (at x0 and x1), open at the two ends for the
    wires. Full-height square columns outside the walls take M3 through-bolts from below the tray, with a washer and nyloc
    nut on the column's top (outside the hood, where there is access); clearance hole 3.6 the full height (printed,
    vertical). Printed upside down (top plate on the bed): no bridges, no supports."""
    s = bx(x0, x1, y0, y1, z1 - t, z1) + bx(x0, x0 + t, y0, y1, z0, z1) + bx(x1 - t, x1, y0, y1, z0, z1)
    yb = [b[1] for b in bosses]
    if yb and min(yb) > y1:      # bosses beyond the hood's open end: carry the walls out to them
        s += bx(x0, x0 + t, y1, max(yb) + 4.0, z0, z1) + bx(x1 - t, x1, y1, max(yb) + 4.0, z0, z1)
    for bxx, byy in bosses:
        s += bx(bxx - 4.0, bxx + 4.0, byy - 4.0, byy + 4.0, z0, z1)
        s -= zc(bxx, byy, z0, z1, PH3 / 2)
    return s


def build() -> Design:
    d, zs, bed_own, mounts, mount_parts = build_frame_z()
    # ================= Y axis ====================================================
    zp0, zp1 = Z_PLATE, Z_PLATE + T_YP
    X_ES_X0 = X_CAR_MAX - ES_OT_X + STRIKER[0] + ES_TRIG      # X switch (v10: at the right end): its lever is worked by the tool plates' striker tab
    X_ES_Y0 = YB0 + X_ES_Y
    PC = YB0 - 1.55
    YA0, YA1 = PC + BELT_SLOTS[0] - SLOT_W / 2, PC + BELT_SLOTS[-1] + SLOT_W / 2
    beam_bolts = []
    for sx, n in ((-1, "left"), (1, "right")):
        yr = place(d, f"y_rail_{n}", hiwin_mgn12_rail(295), Location((sx * RAIL_X, Y_RAIL_C, Z_RAIL), (0, 0, 90)))
        for i, (hx, hy, hz) in enumerate(yr.meta["interfaces"]["mount_holes_m3"][::2]):
            add_screw(d, f"y_rail_{n}_screw_{i}", "M3", 8, at=(hx, hy, hz + 3.5), threads_into=f"frame_top_{n}", tnut=True)
        place(d, f"y_carriage_{n}", hiwin_mgn12h_block(), Location((sx * RAIL_X, YB0, Z_RAIL), (0, 0, 90)), body="ybody", guides="y")
        x_out = YB_X + BWY / 2 + 0.5 + 4.8
        # v10: over the beam the plate ends YP_REAR behind the beam's centre line, in front of the X block's path, so the block
        # and the tool plates run on to the end of the 288 mm rail. From X_STOP outward the plate reaches back as before and
        # a tab reaches further, to STOP_Y1: its inner edge is the hard stop for the tool plates' edge. The right plate's tab
        # carries on as a land (inner edge beyond the Roto's reach) for the X switch; the land's rear edge works the Y switch.
        plate = (bx(sx * YP_IN, sx * x_out, YB0 + YP_NOTCH[1], YB0 + YP_REAR, zp0, zp1)
                 + bx(sx * X_STOP, sx * x_out, YB0 + YP_REAR, YB0 + PL_Y1, zp0, zp1)
                 + bx(sx * YP_NOTCH[0], sx * x_out, YB0 + PL_Y0, YB0 + YP_NOTCH[1], zp0, zp1)
                 + bx(sx * X_STOP, sx * TAB_X1, YB0 + PL_Y1, YB0 + STOP_Y1, zp0, zp1))
        plate += fillet_z(sx * YP_NOTCH[0], YB0 + YP_NOTCH[1], -sx, -1, 2.0, zp0, zp1)
        plate += fillet_z(sx * TAB_X1, YB0 + PL_Y1, sx, 1, 2.0, zp0, zp1)
        plate += fillet_z(sx * X_STOP, YB0 + YP_REAR, -sx, 1, 1.5, zp0, zp1)
        for dy in BELT_SLOTS:
            plate -= slot_z(sx * YB_X, PC + dy, 0.0, (BWY + 1.0 - SLOT_W) / 2, SLOT_W, zp0, zp1)
        for x in (-10, 10):
            for y in (-10, 10):
                plate -= Pos(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP / 2) * Cylinder(YH3 / 2, T_YP)
        plate += bx(sx * (YP_IN - 9.0), sx * YP_IN, YB0 + YP_NOTCH[1], YB0 + 9.5, zp0, zp1)
        for xb in BEAM_BOLT_X:
            plate -= slot_z(sx * xb, YB0, 0.0, 1.5, clearance_hole("M5"), zp0, zp1)
        if sx > 0:
            plate += bx(LAND_X0, TAB_X1, YB0 + STOP_Y1, YB0 + LAND_Y1, zp0, zp1)
            plate += fillet_z(LAND_X0, YB0 + STOP_Y1, -1, 1, 1.5, zp0, zp1)
            for dy in (-7.5, 7.5):
                plate -= slot_z(X_ES_X0 + 4.2, X_ES_Y0 + dy, 0.0, ES_SLOT, SH3, zp0, zp1)
        sheet(d, f"y_plate_{n}", plate, AL, body="ybody")
        for i, (x, y) in enumerate([(-10, -10), (-10, 10), (10, -10), (10, 10)]):
            add_screw(d, f"y_plate_{n}_screw_{i}", "M3", 8, at=(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP), body="ybody", threads_into=f"y_carriage_{n}")
        for i, xb in enumerate(BEAM_BOLT_X):
            beam_bolts.append((f"beam_bolt_{n}" + ("" if i == 0 else f"_{i}"), (sx * xb, YB0, zp1), f"y_plate_{n}"))
    # ================= X axis ====================================================
    place(d, "x_beam", extrusion_2020(BEAM_L), Location((0, YB0, Z_BEAM)), body="ybody")
    for nm_, at_, pl_ in beam_bolts:      # v10.1: after the beam (the T-nut is placed in its slot); the screw is v10's
        # v11 (owner): M5 x 12 with a second washer (v10.1: M5 x 10, 0.59 d of thread): through the T-nut's whole thread
        add_screw(d, nm_, "M5", 12, at=at_, body="ybody", threads_into="x_beam", tnut=True, clamps=(pl_,), washer=True, washers=2)
    rear = lambda x: Location(Plane(origin=(x, YB0 + 10.0, Z_BEAM), x_dir=(1, 0, 0), z_dir=(0, 1, 0)))
    # v10: the rail is as long as the beam (HIWIN MGNR12R cut to 288 mm). v9's two rail-stop plates are gone: the hard stops
    # are the Y plates' tabs against the tool plates' edges
    xr = place(d, "x_rail", hiwin_mgn12_rail(X_RAIL_L), rear(0.0), body="ybody")
    xr.meta["description"] = (f"X rail: HIWIN MGNR12R {X_RAIL_L:g} mm, a stock length as sold (not cut), centred on the {BEAM_L:g} mm beam. "
                              f"The block's centre runs +/-{X_CAR_MAX:g} mm with 5 mm of rail beyond it.")
    for i, (hx, hy, hz) in enumerate([h for h in xr.meta["interfaces"]["mount_holes_m3"] if abs(abs(h[0]) - 62.5) > 1 and abs(h[0]) > 30.0][::1]):
        add_screw(d, f"x_rail_screw_{i}", "M3", 8, at=(hx, hy + 3.5, hz), direction=(0, -1, 0), body="ybody", threads_into="x_beam", tnut=True)
    place(d, "x_carriage", hiwin_mgn12h_block(), rear(0.0), body="xbody", guides="x")
    # ---- toolhead: guide block -> front plate + rear plate -> Roto
    yf, yrr = YB0 + R_TPF, YB0 + R_TPR
    ymid = yf + T_TPF                 # interface between the two tool plates
    sheet(d, "tool_plate", tool_plate_front_shape(), AL, body="xbody", r=0.8)
    sheet(d, "tool_plate_rear", tool_plate_rear_shape(), AL, body="xbody", r=0.8)
    for i, (x, z) in enumerate([(-10, -10), (10, -10), (-10, 10), (10, 10)]):
        add_screw(d, f"tool_screw_{i}", "M3", 6, at=(x, ymid, Z_BEAM + z), direction=(0, -1, 0), body="xbody",
                  threads_into="x_carriage", clamps=("tool_plate",))
    place(d, "extruder", extruder_roto(), Location(ROTO_O), body="xbody", process="purchased")
    yb_pm = yrr + ROTO_W                       # the Roto's rear face
    # v12: the BTT Eddy Duo replaces the OMRON E2B, turned 90 degrees so it sits no further back than the E2B did: the 5052 L under the
    # Roto's two screws (as v11) has a narrow strip bent back on the left; the printed holder stands on it beside the Eddy (two vertical
    # M3 from below into captured nylocs); the Eddy hangs on the holder by its own two holes (two horizontal M3 x 30, heads on the
    # holder's left, nuts on the Eddy's right face). Coil face 2.5 mm above the tip.
    g = eddy_geometry(yb_pm)
    x_e, y_e, z_face, z_eh = g["x_e"], g["y_e"], g["z_face"], g["z_eh"]
    d.add("probe_mount", round_profile(eddy_bracket_shape(yb_pm, g), 0.8, B23), material=AL_BEND, body="xbody", process="sheet",
          meta={"finish": "bare", "description": (
              "Probe bracket (v12): 2.286 mm 5052 (SendCutSend .090). A flat leg on the Roto's rear face under its two M3 screws, with one "
              "9 mm strip bent back on the left under the printed holder of the BTT Eddy Duo (two M3 through-bolts).")})
    for i, (hx, hy, hz) in enumerate(d.get("extruder").meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"extruder_screw_{i}", "M3", 50, at=(hx, yb_pm + B23, hz), direction=(0, -1, 0), body="xbody",
                  clamps=("probe_mount", "extruder", "tool_plate_rear", "tool_plate"), washer="large", washers=2)
        add_nut(d, f"extruder_nut_{i}", "M3", at=(hx, ymid, hz), direction=(0, 1, 0), body="xbody", screw=f"extruder_screw_{i}", standard="pem0")
        d.join(f"extruder_nut_{i}", "tool_plate", "PEM self-clinching nut (SendCutSend hardware service)")
    d.add("eddy_holder", eddy_holder_shape(g), material=COOL, body="xbody", process="printed",
          meta={"print_up": "+Z", "print": {**PRINT_ABS, "orientation": "+Z", "infill": 0.6}, "service_temp_c": 50.0,
                "description": "Printed PETG holder for the BTT Eddy Duo: beside the probe's mounting face, on the bracket's bent strip."})
    place(d, "bed_probe", probe_eddy_duo(), Location((x_e, y_e, z_face), (0, 0, 90)), body="xbody")
    xc = g["xh0"] + 3.75
    zp_e = g["z_leg"] + B23 + 3.0
    for i, dy in enumerate(EDDY_HB_DY):
        nm = f"eddy_holder_bolt_{i}"
        add_screw(d, nm, "M3", 12, at=(xc, y_e + dy, g["z_leg"]), direction=(0, 0, 1), body="xbody", clamps=("probe_mount", "eddy_holder"),
                  washer=True).meta["torque_nm"] = PRINTED_JOINT_TORQUE
        captive_nut(d, nm, (xc, y_e + dy, zp_e), (0, 0, 1), "eddy_holder", "xbody")
        d.get(nm).meta["locking"] = "nyloc"
    for i, dy in enumerate((-5.25, 5.25)):
        nm = f"eddy_bolt_{i}"
        bolt_nut(d, nm, "M3", 30, (g["xh0"], y_e + dy, z_eh), (1, 0, 0), "xbody", ("eddy_holder", "bed_probe"),
                 nut_at=(x_e + 15.3 / 2, y_e + dy, z_eh), nyloc=True)
        d.get(nm).meta["torque_nm"] = PRINTED_JOINT_TORQUE
        d.get(nm).meta["locking"] = "nyloc"
    d.join("bed_probe", "eddy_holder", "two M3 through-bolts in its own holes")
    seat = d.get("extruder").meta["interfaces"]["hotend_seat"][0]
    # v10: the HeaterCore's lead sleeve points FORWARD, under the tool plates (2.2 mm) and the X block (4.7 mm). v9: to the
    # left, 14 mm beyond the Roto's side, where it would now meet the top side rail before the Roto does. Not backward:
    # anything behind the nozzle within the Roto's width is inside the unshielded probe's 40 mm metal-free zone
    place(d, "hotend", hotend_revo(40, 24.0, 0.4), Location(tuple(seat), (0, 0, -90)), body="xbody")
    d.allow_overlap("hotend", "extruder")
    d.join("hotend", "extruder", "clamp")
    d.get("hotend").meta["description"] = ("E3D Revo hotend, held in the Roto's hotend seat by the Roto's own clamp (no separate fasteners). "
                                           "v11: fitted with E3D's silicone sock for the Revo HeaterCore (BOM), so the part-cooling jet "
                                           "that passes under the heater does not cool it.")
    d.bom_extra("E3D-REVO-SILICONE-SOCK (E3D Revo HeaterCore silicone sock; v11 part cooling)", 1, 3.0)
    # part cooling (v11): the BFB0524HH blower behind the Roto, 0.1 mm behind the probe bracket's leg, outlet down into the duct
    y_noz = YB0 + HOT_OFF
    bl_y0 = yb_pm + B23 + 2 * WASHER["large"]["M3"][2] + 3.0 + 1.5     # 1.5 mm behind the Roto screws' heads and washers
    d.add("part_duct", part_duct_shape(y_noz, bl_y0), material=HOT, body="xbody", process="printed",
          meta={"print_up": "-Y", "print": {**PRINT_ABS, "orientation": "-Y"}, "service_temp_c": 45.0})
    for i, (x, z) in enumerate(FC_SCREWS):
        # through both tool plates and the duct's flange into a nyloc nut and washer captured in the flange
        add_screw(d, f"part_duct_screw_{i}", "M3", 16, at=(x, yf, Z_BEAM + z), direction=(0, 1, 0), body="xbody",
                  clamps=("tool_plate", "tool_plate_rear", "part_duct"), washer=True).meta["torque_nm"] = PRINTED_JOINT_TORQUE
        captive_nut(d, f"part_duct_screw_{i}", (x, YB0 + R_TPR + POCKET_WALL, Z_BEAM + z), (0, 1, 0), "part_duct", "xbody")
    bc = (BL_X0 + BL_X1) / 2
    # turned so its outlet (local +Z) points down and lies at the blower's left end (local X -> world -X, thickness along Y)
    place(d, "part_fan", blower_bfb0524hh(), Location(Plane(origin=(bc, bl_y0 + BL_T / 2, BL_Z0 + BL_W / 2), x_dir=(-1, 0, 0), z_dir=(0, 0, -1))),
          body="xbody")
    W3n = WASHER["normal"]["M3"][2]
    for i, (x, z) in enumerate(BL_HOLES()):
        # v11: the Delta's two holes (upper left, lower right; measured on its STEP): M3 x 25 through the blower (washer on the plastic) and the duct's
        # cradle, washer and nut on the cradle's back; the outlet seats in the riser's opening below
        # M3 (with washers) in the blower's 4.3 mm holes: lighter than M4; the toolhead stays under its 0.40 kg target
        fs = add_screw(d, f"part_fan_screw_{i}", "M3", 25, at=(x, bl_y0, z), direction=(0, 1, 0), body="xbody",
                       clamps=("part_fan", "part_duct"), washer=True, locking="adhesive")
        fs.meta["torque_nm"] = 0.3
        yb_ = bl_y0 + BL_T + CRADLE_T
        add_washer(d, f"part_fan_screw_{i}_nwasher", "M3", (x, yb_, z), (0, 1, 0), body="xbody", screw=f"part_fan_screw_{i}")
        add_nut(d, f"part_fan_screw_{i}_nut", "M3", at=(x, yb_ + W3n, z), direction=(0, 1, 0), body="xbody", screw=f"part_fan_screw_{i}")
        d.join(f"part_fan_screw_{i}_nut", "part_duct", "clamped through its washer on the cradle's back")
    d.join("part_fan", "part_duct", "the blower's outlet seats in the riser's opening; two M3 through-bolts")
    # ================= X drive ===================================================
    # belt bracket: 5052 2.286 mm bent L on the front tool plate (two M3 into captive nuts in the rear plate); the two belt
    # ends are squeezed between its horizontal leg and a 2.54 mm clamp plate by four M3 with nuts
    t_b = B23
    z_leg = Z_XL + 0.7                                  # underside of the bracket's horizontal leg = top of the belt
    l_b = R_TPF + 8.0
    brk = bent_L(t_b, R_B23, 13.0, l_b, 30.0,
                 holes_a=[(-x, (z_leg + t_b) - (Z_BEAM + BRK_Z), clearance_hole("M3")) for x, _ in BLK_SCREWS],
                 holes_b=[(R_TPF - yy, -xx, clearance_hole("M3")) for xx in (-10.0, 10.0) for yy in CLAMP_Y])
    brk_loc = Location(Plane(origin=(0, yf, z_leg + t_b), x_dir=(0, -1, 0), z_dir=(0, 0, -1)))
    d.add("x_belt_bracket", round_profile(brk_loc * brk, 0.8, B23), material=AL_BEND, body="xbody", process="sheet", meta={"finish": "bare"})
    cp = bx(-15.0, 15.0, YB0 - 6.5, YB0 + 16.0, Z_XL - 0.7 - G20, Z_XL - 0.7)
    for xx in (-10.0, 10.0):
        for yy in CLAMP_Y:
            cp -= zc(xx, YB0 + yy, Z_XL - 0.7 - G20, Z_XL - 0.7, clearance_hole("M3") / 2)
    sheet(d, "x_belt_clamp", cp, AL, body="xbody")
    for i, (x, z) in enumerate(BLK_SCREWS):
        add_screw(d, f"x_belt_bracket_screw_{i}", "M3", 10, at=(x, yf - t_b, Z_BEAM + BRK_Z), direction=(0, 1, 0), body="xbody",
                  clamps=("x_belt_bracket", "tool_plate"), washer=True)
        add_nut(d, f"x_belt_bracket_nut_{i}", "M3", at=(x, ymid, Z_BEAM + BRK_Z), direction=(0, 1, 0), body="xbody", screw=f"x_belt_bracket_screw_{i}")
        d.join(f"x_belt_bracket_nut_{i}", "tool_plate_rear", "captive in a hex pocket")
    k = 0
    for xx in (-10.0, 10.0):
        for yy in CLAMP_Y:
            bolt_nut(d, f"x_belt_clamp_screw_{k}", "M3", 10, (xx, YB0 + yy, z_leg + t_b), (0, 0, -1), "xbody", ("x_belt_bracket", "x_belt_clamp"),
                     nut_at=(xx, YB0 + yy, Z_XL - 0.7 - G20)); k += 1
    d.join("x_belt_clamp", "x_belt_bracket", "the belt ends between them")
    # v11: with the stock 250 mm rail the motor and idler (pulley centres -122.8 / +123.8) stand inside the 276 mm beam's ends.
    # Each mount is a FLAT plate on the beam's front face (two M5 in T-nuts). The motor's plate reaches up and outward to the
    # motor (its upper part above the Y plate and the Y block's screw heads, as v10's wing); its two M5 holes are slots along
    # the beam: the X belt is tensioned by pulling the motor plate outward by hand and tightening (owner: no tensioner, no
    # anchor; v10's bent anchor, PEM nut and jack screw are gone). The idler's plate is flat (v10: bent 5052 with a lug).
    MTM = MT
    yb_f, yb_r = YB0 - 10.0 - MT, YB0 - 10.0
    yb_fm = yb_r - MTM
    fwd = lambda x, y, z: Location(Plane(origin=(x, y, z), x_dir=(1, 0, 0), z_dir=(0, 1, 0)))
    BEAM_END = BEAM_L / 2 - 1.0                       # 137: the mounts' lower part ends 1 mm inside the beam's end
    WING_Z0 = zp1 + 3.0 + 1.5                         # 426.25: 1.5 mm above the Y blocks' M3 screw heads on the Y plates
    XM_IN, XM_OUT = -96.0, XM_X - 23.5
    mm = bx(-BEAM_END, XM_IN, yb_fm, yb_r, Z_BEAM - 8.0, XD_Z + 23.0) + bx(XM_OUT, -BEAM_END, yb_fm, yb_r, WING_Z0, XD_Z + 23.0)
    mm += fillet_y(-BEAM_END, WING_Z0, -1, -1, 3.0, yb_fm, yb_r)
    mm -= Pos(XM_X, (yb_fm + yb_r) / 2, XD_Z) * ycyl(11.5, MTM)
    for x in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            mm -= Pos(XM_X + x, (yb_fm + yb_r) / 2, XD_Z + z) * ycyl(SH3 / 2, MTM)
    X_MOUNT_BOLTS = (-128.0, -104.0)
    for x in X_MOUNT_BOLTS:     # slots along the beam: the motor slides +/-BELT_ADJ to tension the belt
        mm -= Pos(x, (yb_fm + yb_r) / 2, Z_BEAM) * Rot(90, 0, 0) * (Box(2 * BELT_ADJ, clearance_hole("M5"), MTM)
                                                                   + Pos(-BELT_ADJ, 0, 0) * Cylinder(clearance_hole("M5") / 2, MTM)
                                                                   + Pos(BELT_ADJ, 0, 0) * Cylinder(clearance_hole("M5") / 2, MTM))
    sheet(d, "x_motor_mount", mm, AL, body="ybody")
    place(d, "x_motor", nema17(34), fwd(XM_X, yb_fm, XD_Z), body="ybody")
    place(d, "x_pulley", gt2_pulley(20, belt_width=BWX), fwd(XM_X, yb_r + X_PG, XD_Z), body="ybody")
    k = 0
    for x in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            add_screw(d, f"x_motor_screw_{k}", "M3", 8, at=(XM_X + x, yb_r, XD_Z + z), direction=(0, -1, 0), body="ybody",
                      threads_into="x_motor", clamps=("x_motor_mount",), washer=True); k += 1
    for i, x in enumerate(X_MOUNT_BOLTS):
        # v11 (owner): M5 x 8 with one washer (on the slot) into the beam's front slot
        add_screw(d, f"x_motor_mount_bolt_{i}", "M5", 8, at=(x, yb_fm, Z_BEAM), direction=(0, 1, 0), body="ybody",
                  threads_into="x_beam", tnut=True, clamps=("x_motor_mount",), washer=True)
    d.join("x_pulley", "x_motor", "set_screw")
    XIM_BOLTS = (104.0, 128.0)
    im = bx(XIM_BOLTS[0] - 10.0, BEAM_END, yb_f, yb_r, Z_BEAM - 8.0, XD_Z + 12.0)
    im -= Pos(XI_X, (yb_f + yb_r) / 2, XD_Z) * ycyl(clearance_hole("M5") / 2, MT)
    for xb in XIM_BOLTS:
        im -= Pos(xb, (yb_f + yb_r) / 2, Z_BEAM) * ycyl(clearance_hole("M5") / 2, MT)
    sheet(d, "x_idler_mount", im, AL, body="ybody")
    for i, x in enumerate(XIM_BOLTS):
        add_screw(d, f"x_idler_mount_bolt_{i}", "M5", 8, at=(x, yb_f, Z_BEAM), direction=(0, 1, 0), body="ybody",
                  threads_into="x_beam", tnut=True, clamps=("x_idler_mount",), washer=True)
    place(d, "x_idler_spacer", spacer_round("M5", X_SP, "aluminium"), fwd(XI_X, yb_r, XD_Z), body="ybody")
    place(d, "x_idler", gt2_idler(20, belt_width=BWX), fwd(XI_X, yb_r + X_SP, XD_Z), body="ybody")
    add_screw(d, "x_idler_bolt", "M5", 35, at=(XI_X, yb_f, XD_Z), direction=(0, 1, 0), body="ybody",
              clamps=("x_idler_mount", "x_idler_spacer"), washer=True)
    add_nut(d, "x_idler_nut", "M5", at=(XI_X, yb_r + X_SP + I_H(BWX), XD_Z), direction=(0, 1, 0), body="ybody", screw="x_idler_bolt", standard="din934")      # v10.1: the M5 nut that is bought (McMaster 90591A260, DIN 934, 4.0 mm)
    d.join("x_idler", "x_idler_bolt", "axle")
    d.join("x_idler_spacer", "x_idler_mount", "clamp")
    # v10.1: the five PEM nuts are catalogue parts now (hex_nut(standard="pem"), SKU NUT-PEM-S-M3-1), not a BOM-only line
    # X endstop (v10): on TOP of the right Y plate's land, behind the tool plates' plane and outboard of the Roto's reach; the
    # striker tab on the front tool plate's right edge works its lever at the right end of the travel (X homes at maximum).
    # Screws from above through board, spacer and the land's slot; large washer and nut under the land, 1.3 mm above the Y rail
    W3 = WASHER["normal"]["M3"][2]                      # a normal washer (7 mm) under the 3.6 mm slot: a large one would foul the Y block
    xsw = place(d, "x_endstop", endstop_switch(),
                Location(Plane(origin=(X_ES_X0, X_ES_Y0, zp1 + ES_SP_XS), x_dir=(0, 1, 0), z_dir=(0, 0, 1))), body="ybody")
    for i, (hx, hy, hz) in enumerate(xsw.meta["interfaces"]["mount_holes_m3"]):
        place(d, f"x_endstop_spacer_{i}", spacer_harwin(int(ES_SP_XS), "nylon"), Location((hx, hy, zp1)), body="ybody")
        add_screw(d, f"x_endstop_screw_{i}", "M3", 16, at=(hx, hy, zp1 + ES_SP_XS + 1.6), direction=(0, 0, -1), body="ybody",
                  clamps=("x_endstop", f"x_endstop_spacer_{i}", "y_plate_right"), washer=True)
        add_washer(d, f"x_endstop_nwasher_{i}", "M3", (hx, hy, zp0), (0, 0, -1), body="ybody", screw=f"x_endstop_screw_{i}")
        add_nut(d, f"x_endstop_nut_{i}", "M3", at=(hx, hy, zp0 - W3), direction=(0, 0, -1), body="ybody", screw=f"x_endstop_screw_{i}")
        d.join(f"x_endstop_nut_{i}", "y_plate_right", "clamped through its washer")
    # ================= Y drives (v11: flat plates, stock cast corner brackets as the tension anchors) =================
    xf = FX / 2
    YMB = (142.0, 168.0)
    side = lambda x, y, z, sg: Location(Plane(origin=(x, y, z), x_dir=(0, 1, 0), z_dir=(sg, 0, 0)))
    YA_C, YP_C, T_SCREW_V = 116.5, YMB[0] - BRACKET_SLOT_LEG["offsets"][0], 12.0   # anchor and push brackets' corners (y); screw 12 mm out
    for sg, tag, n in ((1, "", "right"), (-1, "_l", "left")):
        rail = f"frame_top_{n}"
        # motor plate: 1.88 mm 304, FLAT (v10: a bent fin at its front edge for the jack screw), same outline otherwise, so the
        # motor's face and the belt plane stay where they were
        xa_, xb_ = sorted((sg * xf, sg * (xf + MT_Y)))
        m = bx(xa_, xb_, 125.0, 180.0, FZ - 10.0, FZ + 10.0)
        arm = bx(xa_, xb_, 170.0, YM_Y + 21.0, FZ - 10.0, Z_YC + 23.0)
        arm += fillet_x(170.0, FZ + 10, -1, 1, 3.0, xa_, xb_)
        m = m + arm
        xm = (xa_ + xb_) / 2
        m -= Pos(xm, YM_Y, Z_YC) * xcyl(11.5, MT_Y)
        for y in (-15.5, 15.5):
            for z in (-15.5, 15.5):
                m -= Pos(xm, YM_Y + y, Z_YC + z) * xcyl(SH3 / 2, MT_Y)
        for y in YMB:
            m -= Pos(xm, y, FZ) * xcyl(clearance_hole("M5") / 2, MT_Y)
        # a 6.4 mm slot under the push bracket's leg for the casting's locating nub (it drops through into the rail's slot
        # opening and keeps the bracket from turning on its one screw)
        m -= Pos(xm, YP_C + 10.0, FZ) * Box(MT_Y, 20.0, 6.4)
        sheet(d, f"y_motor_mount{tag}", m, SS)
        place(d, f"y_motor{tag}", nema17(48), Location(Plane(origin=(sg * xf, YM_Y, Z_YC), x_dir=(0, 0, -1), z_dir=(sg, 0, 0))))
        place(d, f"y_pulley{tag}", gt2_pulley(20, belt_width=BWY),
              Location(Plane(origin=(sg * (YB_X + P_BC(BWY)), YM_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(-sg, 0, 0))))
        k = 0
        for y in (-15.5, 15.5):
            for z in (-15.5, 15.5):
                add_screw(d, f"y_motor{tag}_screw_{k}", "M3", 6, at=(sg * (xf + MT_Y), YM_Y + y, Z_YC + z), direction=(-sg, 0, 0),
                          threads_into=f"y_motor{tag}", clamps=(f"y_motor_mount{tag}",), washer=True); k += 1
        d.join(f"y_pulley{tag}", f"y_motor{tag}", "set_screw")
        # push bracket: a stock cast corner bracket whose leg lies on the motor plate's outer face under the plate's FRONT M5
        # (a flanged button head through the bracket's slot and the plate into the rail's T-nut); its other leg stands out
        # square to the rail and takes the tension screw's push
        pb = f"y_tension_bracket{tag}"
        place_casting(d, pb, (sg * (xf + MT_Y), YP_C, FZ), (0, 1, 0), (sg, 0, 0))
        add_screw(d, f"y_motor_mount{tag}_bolt_0", "M5", 10, at=(sg * (xf + MT_Y + 3.0), YMB[0], FZ), direction=(-sg, 0, 0),
                  threads_into=rail, tnut=True, clamps=(pb, f"y_motor_mount{tag}"), head="flanged_button")
        d.join(pb, f"y_motor_mount{tag}", "clamped under the plate's front M5")
        add_screw(d, f"y_motor_mount{tag}_bolt_1", "M5", 8, at=(sg * (xf + MT_Y), YMB[1], FZ), direction=(-sg, 0, 0),
                  threads_into=rail, tnut=True, clamps=(f"y_motor_mount{tag}",), washer=True)
        # anchor: a stock cast corner bracket on the rail's outer face (one flanged button head into a T-nut), its standing leg
        # in front of the push bracket's. The tension screw (M5 x 30) passes the anchor's slot between two jam nuts with washers;
        # its head bears on the push bracket's standing leg. Turning the nuts moves the screw: no PEM nut, no tapped aluminium
        ab = f"y_tension_anchor{tag}"
        place_casting(d, ab, (sg * xf, YA_C, FZ), (0, -1, 0), (sg, 0, 0))
        foot = np.array([sg * xf, YA_C - BRACKET_SLOT_LEG["offsets"][1], FZ])     # 13.1 out: its driver passes the front jam nut
        add_screw(d, f"{ab}_screw_a", "M5", 8, at=tuple(foot + np.array([sg * 3.0, 0, 0])), direction=(-sg, 0, 0), threads_into=rail,
                  tnut=True, clamps=(ab,), head="flanged_button")
        d.get(f"{ab}_screw_a").meta["bracket_leg_of"] = ab
        d.join(ab, rail, "m5_tnut")
        ts = f"y_tension_screw{tag}"
        x_ts = sg * (xf + T_SCREW_V)
        hh = 5.0                                                 # ISO 4762 M5 head height
        add_screw(d, ts, "M5", 30, at=(x_ts, YP_C - hh, FZ), direction=(0, -1, 0), clamps=(ab,), locking="jam")
        d.get(ts).meta["torque_nm"] = 0.0
        d.get(ts).meta["note"] = "tension screw: positioned by its two jam nuts on the anchor; its head pushes the motor plate's bracket"
        # it is set by turning its nuts, not driven by its head (which bears on the bracket): no driver-access record for it
        d.fasteners[:] = [f_ for f_ in d.fasteners if f_.name != ts]
        for side_, y0_, dv in (("rear", YA_C, (0, 1, 0)), ("front", YA_C - 3.0, (0, -1, 0))):
            add_washer(d, f"{ts}_{side_}_washer", "M5", (x_ts, y0_, FZ), dv, screw=ts)
            add_nut(d, f"{ts}_{side_}_nut", "M5", at=(x_ts, y0_ + dv[1] * W5, FZ), direction=dv, screw=ts, locking="jam", standard="din934")
            d.join(f"{ts}_{side_}_nut", ab, "jam nut on the anchor's leg, through its washer")
        d.join(ts, pb, "the tension screw's head bears on the push bracket's standing leg")
        # idler mount (304 1.52, v11), the idler on an M5 with two washers between it and the mount
        xa_, xb_ = sorted((sg * xf, sg * (xf + MT_YI)))
        xm = (xa_ + xb_) / 2
        y_l1 = YI_Y + 7.5
        imy = bx(xa_, xb_, YI_Y - 9.0, y_l1, FZ - 10.0, Z_YC + 9.0) + bx(xa_, xb_, y_l1, YIM_BOLTS[1] + 10.0, FZ - 10.0, FZ + 8.0)
        imy += fillet_x(y_l1, FZ + 8.0, 1, 1, 2.0, xa_, xb_)
        imy -= Pos(xm, YI_Y, Z_YC) * xcyl(clearance_hole("M5") / 2, MT_YI)
        for y in YIM_BOLTS:
            imy -= Pos(xm, y, FZ) * xcyl(clearance_hole("M5") / 2, MT_YI)
        sheet(d, f"y_idler_mount{tag}", imy, SS)
        for i, y in enumerate(YIM_BOLTS):
            add_screw(d, f"y_idler_mount{tag}_bolt_{i}", "M5", 8, at=(sg * (xf + MT_YI), y, FZ), direction=(-sg, 0, 0),
                      threads_into=rail, tnut=True, clamps=(f"y_idler_mount{tag}",), washer=True)
        place(d, f"y_idler{tag}", gt2_idler(20, belt_width=BWY), side(sg * (YB_X - I_H(BWY) / 2), YI_Y, Z_YC, sg))
        add_screw(d, f"y_idler{tag}_bolt", "M5", 30, at=(sg * (YB_X + I_H(BWY) / 2), YI_Y, Z_YC), direction=(-sg, 0, 0),
                  clamps=(f"y_idler_mount{tag}",))
        add_washer(d, f"y_idler{tag}_spacer", "M5", (sg * (xf + MT_YI), YI_Y, Z_YC), (sg, 0, 0), screw=f"y_idler{tag}_bolt")
        add_washer(d, f"y_idler{tag}_spacer_b", "M5", (sg * (xf + MT_YI + W5), YI_Y, Z_YC), (sg, 0, 0), screw=f"y_idler{tag}_bolt")
        add_washer(d, f"y_idler{tag}_nwasher", "M5", (sg * xf, YI_Y, Z_YC), (-sg, 0, 0), screw=f"y_idler{tag}_bolt")
        add_nut(d, f"y_idler{tag}_nut", "M5", at=(sg * (xf - W5), YI_Y, Z_YC), direction=(-sg, 0, 0), screw=f"y_idler{tag}_bolt", standard="din934")
        d.join(f"y_idler{tag}_nut", f"y_idler_mount{tag}", "clamped through its washer")
        d.join(f"y_idler{tag}", f"y_idler{tag}_bolt", "axle")
    # Y endstop (v11): a FLAT 3.175 mm 6061 plate on the right top rail's top (two M5 into the top slot behind the Y rail's end),
    # reaching inboard over the frame's inside; the switch board lies horizontal on two 8 mm nylon standoffs, its lever pointing
    # forward at the height of the right Y plate's land, whose rear edge works it (v10: a bent 5052 upright)
    y_strike = YB0 + LAND_Y1 + TY
    YE_X0, YE_Y0 = 152.5, y_strike + ES_TRIG          # board origin: its holes at x 145 and 160
    T_YE, SO_H = G32, 8.0
    ze0, ze1 = Z_RAIL, Z_RAIL + T_YE
    ysw = place(d, "y_endstop", endstop_switch(), Location(Plane(origin=(YE_X0, YE_Y0, ze1 + SO_H), x_dir=(-1, 0, 0), z_dir=(0, 0, 1))))
    ys_holes = ysw.meta["interfaces"]["mount_holes_m3"]
    YEM = (140.0, 152.0)                                # the plate's two M5, in the top slot behind the Y rail's end (y 121.5)
    ym = bx(139.5, RAIL_X + 9.0, Y_RAIL_C + 150.0 + 1.0, 160.0, ze0, ze1)
    for y in YEM:
        ym -= zc(RAIL_X, y, ze0, ze1, clearance_hole("M5") / 2)
    for hx, hy, hz in ys_holes:
        ym -= zc(hx, hy, ze0, ze1, clearance_hole("M3") / 2)
    sheet(d, "y_endstop_mount", ym, AL)
    for i, y in enumerate(YEM):
        add_screw(d, f"y_endstop_mount_bolt_{i}", "M5", 8, at=(RAIL_X, y, ze1), direction=(0, 0, -1), threads_into="frame_top_right", tnut=True,
                  clamps=("y_endstop_mount",), washer=True)
    for i, (hx, hy, hz) in enumerate(ys_holes):
        place(d, f"y_endstop_spacer_{i}", spacer_harwin(int(SO_H), "nylon"), Location((hx, hy, ze1)))
        on_slot = abs(hx - RAIL_X) < 0.5
        add_screw(d, f"y_endstop_screw_{i}", "M3", 18, at=(hx, hy, ze1 + SO_H + 1.6), direction=(0, 0, -1), washer=True,
                  clamps=("y_endstop", f"y_endstop_spacer_{i}", "y_endstop_mount"),
                  **({"threads_into": "frame_top_right", "tnut": True} if on_slot else {}))
        if not on_slot:       # the inboard hole: washer and nut under the plate, in the open space inside the frame
            add_washer(d, f"y_endstop_nwasher_{i}", "M3", (hx, hy, ze0), (0, 0, -1), screw=f"y_endstop_screw_{i}")
            add_nut(d, f"y_endstop_nut_{i}", "M3", at=(hx, hy, ze0 - WASHER["normal"]["M3"][2]), direction=(0, 0, -1), screw=f"y_endstop_screw_{i}")
            d.join(f"y_endstop_nut_{i}", "y_endstop_mount", "clamped through its washer")
    return finish_build(d, zs, bed_own, mounts, mount_parts)


def finish_build(d, zs, bed_own, mounts, mount_parts) -> Design:
    # ================= electronics bay: tray across the bottom rails =============
    tray = Pos(0, (TRAY_Y0 + TRAY_Y1) / 2, 20 + T_TRAY / 2) * Box(FX, TRAY_Y1 - TRAY_Y0, T_TRAY)
    grp = ["electronics_tray"]
    psu = place(d, "psu", psu_lrs(PSU_MODEL), Location((-28.0, -30.0, Z_TRAY), (0, 0, -90)))
    # v8.2: BTT Octopus V1.1 (eight drivers: X, Y, Y1, three Z, E, one spare) beside the supply, its motor connectors along
    # the right-hand edge; the Pi Zero 2 W in front of it, where the SKR Mini sat
    board = place(d, "control_board", octopus_v11(), Location((BOARD_XY[0], BOARD_XY[1], Z_TRAY + 6.0), (0, 0, -90)))
    host = place(d, "host", pi5_host(), Location((HOST_XY[0], HOST_XY[1], Z_TRAY + 4.0), (0, 0, 0)))
    pcbs = [(board, "mount_holes_m3", "M3", 16, 6.0, (0, 1, 2, 3)), (host, "mount_holes_m2.5", "M2.5", 12, 4.0, (0, 3))]
    tray_hole = {"M3": clearance_hole("M3"), "M2.5": 3.2}
    # v12: DIN rail along X at y DIN_Y: WAGO end stop, Finder 22.32 contactor, Phoenix PLC-RSC interface relay, end stop. The rail is
    # held by two M3 x 10 through its slots and the tray, washer and nut under the tray
    DIN_Y, DIN_X0, DIN_X1 = -31.0, -134.0, -87.0     # v12: clear of the left carriage plate's descent and the supply
    zr = Z_TRAY
    place(d, "din_rail", din_rail_wago(DIN_X1 - DIN_X0), Location(((DIN_X0 + DIN_X1) / 2, DIN_Y, zr)))
    relay = place(d, "psu_relay", contactor_finder_2232(), Location((-114.25, DIN_Y, zr + 7.5)))
    place(d, "iface_relay", relay_phoenix_1119897(), Location((-102.35, DIN_Y, zr + 7.5)))
    for k_, xs in enumerate((-128.0, -93.3)):
        place(d, f"din_end_{k_}", din_endstop_wago(), Location((xs, DIN_Y, zr + 7.5)))
        d.join(f"din_end_{k_}", "din_rail", "snapped on the rail")
    d.join("psu_relay", "din_rail", "snapped on the rail")
    # the Finder's STEP clip sits inside the rail's channel and its housing against its neighbours by design (DIN modules butt)
    for o_ in ("din_rail", "iface_relay", "din_end_0", "din_end_1"):
        d.allow_overlap("psu_relay", o_, max_volume=500.0)
    d.join("iface_relay", "din_rail", "snapped on the rail")
    din_bolts = [(DIN_X0 + 10.0, DIN_Y), (DIN_X1 - 10.0, DIN_Y)]
    grp += ["din_rail", "psu_relay", "iface_relay", "din_end_0", "din_end_1"]
    # v9: the side uprights and their corner brackets stand on the bottom side rails where the tray lay: two notches; the
    # tray is held by the four front motor posts' bolts and by these two at the back
    tray_bolts = [(sx * RAIL_X, 72.0) for sx in (-1, 1)]
    for sx in (-1, 1):
        tray -= bx(sx * (WALL_X - 2.0), sx * (FX / 2 + 1.0), UP_S_Y - 32.0, UP_S_Y + 32.0, 19.0, Z_TRAY + 1.0)
    for tg, x0, y0, turn, posts, rail, on_tray in mounts:
        if on_tray:
            for x, y in posts:
                tray -= zc(x, y, 20.0, Z_TRAY, clearance_hole("M5") / 2)     # the front motor posts' bolts pass to the rail
    for x, y in tray_bolts:
        tray -= zc(x, y, 20.0, Z_TRAY, clearance_hole("M5") / 2)
    for hx, hy, hz in psu.meta["interfaces"]["mount_holes_m4"]:
        tray -= zc(hx, hy, 20.0, Z_TRAY, clearance_hole("M4") / 2)
    for comp, key, size, _, _, use in pcbs:
        for i, (hx, hy, hz) in enumerate(comp.meta["interfaces"][key]):
            if use is not None and i not in use:
                continue
            tray -= zc(hx, hy, 20.0, Z_TRAY, tray_hole[size] / 2)
    # mains covers (printed PETG hoods over the live terminals): M3 through-bolts from below the tray, nyloc nut and washer on
    # each column's top
    # v12: the Finder and Phoenix are finger-safe (IP20) DIN devices: no hood; the supply's terminals keep theirs
    covers = [("mains_cover_psu", (-89.5, 33.5, 60.0, 77.0, Z_TRAY, PSU_COVER_TOP), [(-93.5, 64.0), (37.5, 64.0)])]
    for x, y in din_bolts:
        tray -= zc(x, y, 20.0, Z_TRAY, clearance_hole("M3") / 2)
    for nm, (x0, x1, y0, y1, z0, z1), bosses in covers:
        d.add(nm, cover_hood(x0, x1, y0, y1, z0, z1, bosses=bosses), material=COOL, process="printed",
              meta={"print_up": "-Z", "print": {**PRINT_ABS, "orientation": "-Z", "infill": 0.3}})
        grp.append(nm)
        for i, (bxx, byy) in enumerate(bosses):
            tray -= zc(bxx, byy, 20.0, Z_TRAY, 3.6 / 2)
            grp += through_bolt_nyloc(d, f"{nm}_screw_{i}", bolt_length(z1 - 20.0, nut_h=2.4), (bxx, byy, 20.0), (0, 0, 1),
                                      ("electronics_tray", nm), (bxx, byy, z1), nyloc=False)
    sheet(d, "electronics_tray", tray, AL, r=3.0)
    for i, (x, y) in enumerate(tray_bolts):
        add_screw(d, f"tray_bolt_{i}", "M5", 8, at=(x, y, Z_TRAY), threads_into=f"frame_bot_{'left' if x < 0 else 'right'}",
                  tnut=True, washer=True)      # v11 (owner): M5 x 8, one washer
    for i, (hx, hy, hz) in enumerate(psu.meta["interfaces"]["mount_holes_m4"]):
        add_screw(d, f"psu_screw_{i}", "M4", 6, at=(hx, hy, 20.0), direction=(0, 0, 1), threads_into="psu")
        grp.append(f"psu_screw_{i}")
    grp.append("psu")
    for comp, key, size, slen, sp, use in pcbs:
        mount_pcb(d, comp.name, comp, key, size, slen, sp, grp, use)
    for i, (x, y) in enumerate(din_bolts):
        bolt_nut(d, f"din_rail_bolt_{i}", "M3", 10, (x, y, Z_TRAY + 1.0), (0, 0, -1), "world", ("din_rail", "electronics_tray"),
                 nut_at=(x, y, 20.0), large=True)
        grp += [f"din_rail_bolt_{i}", f"din_rail_bolt_{i}_washer", f"din_rail_bolt_{i}_nwasher", f"din_rail_bolt_{i}_nut"]
        # the head lies in the rail's 7.5 mm channel (top 4 mm above the tray), under the contactor / relay, whose clip hooks the rail's
        # edges: their simulation solids clear it; the Finder STEP's clip detail is not booleaned against it (an OCCT boolean of
        # that file with a threaded McMaster screw does not finish)
        for o_ in ("psu_relay", "iface_relay"):
            d.allow_overlap(o_, f"din_rail_bolt_{i}", max_volume=1.0)
    d.subassemblies["electronics"] = grp
    # mains inlet on a 2.54 mm panel (the DD11's own 2.75 mm web between cut-out and screw holes meets a one-thickness
    # web only at 2.5 mm or thinner), its rear covered by a printed hood screwed through the panel
    T_IP = G25
    IN_Y, IN_Z, XP = 22.0, 60.0, -FX / 2
    panel = Pos(XP - T_IP / 2, IN_Y, 49.0) * Box(T_IP, 80.0, 94.0)
    inlet = place(d, "inlet", iec_inlet_c14(FUSE_A), Location(Plane(origin=(XP - T_IP, IN_Y, IN_Z), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))),
                  real_part=INLET_REAL)
    cut_x, cut_y = inlet.meta["interfaces"]["cutout"]
    panel -= Pos(XP - T_IP / 2, IN_Y, IN_Z) * Rot(0, 90, 0) * extrude(
        RectangleRounded(cut_y, cut_x, inlet.meta["interfaces"]["cutout_corner_radius"]), T_IP / 2, both=True)
    for hx, hy, hz in inlet.meta["interfaces"]["mount_holes_m3"]:
        panel -= Pos(XP - T_IP / 2, hy, hz) * Rot(0, 90, 0) * Cylinder(clearance_hole("M3") / 2, T_IP)
    PANEL_BOLTS = (IN_Y - 30.0, IN_Y + 30.0)
    for y in PANEL_BOLTS:
        panel -= Pos(XP - T_IP / 2, y, 10.0) * Rot(0, 90, 0) * Cylinder(clearance_hole("M5") / 2, T_IP)
    HOOD_SCREWS = [(IN_Y - 23.0, IN_Z + 20.0), (IN_Y + 23.0, IN_Z + 20.0)]
    for y, z in HOOD_SCREWS:
        panel -= Pos(XP - T_IP / 2, y, z) * Rot(0, 90, 0) * Cylinder(clearance_hole("M3") / 2, T_IP)
    sheet(d, "inlet_panel", panel, AL, r=2.0)
    for i, y in enumerate(PANEL_BOLTS):
        add_screw(d, f"inlet_panel_bolt_{i}", "M5", 8, at=(XP - T_IP, y, 10.0), direction=(1, 0, 0), threads_into="frame_bot_left", tnut=True,
                  clamps=("inlet_panel",), washer=True)      # v11 (owner): M5 x 8, one washer
    for i, (hx, hy, hz) in enumerate(inlet.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"inlet_screw_{i}", "M3", 10, at=(XP - T_IP - 2.5, hy, hz), direction=(1, 0, 0), clamps=("inlet", "inlet_panel"))
        add_washer(d, f"inlet_washer_{i}", "M3", (XP, hy, hz), (1, 0, 0), screw=f"inlet_screw_{i}")
        add_nut(d, f"inlet_nut_{i}", "M3", at=(XP + WASHER["normal"]["M3"][2], hy, hz), direction=(1, 0, 0), screw=f"inlet_screw_{i}")
        d.join(f"inlet_nut_{i}", "inlet_panel", "clamped through its washer")
    # the inlet is 30.5 wide (y) and 65 tall (z) behind the panel; the hood: top, two sides, an inner end wall open below
    # v11: 2 mm deeper (end wall at XP + 32 .. 34): SCHURTER's own STEP is 33.5 mm deep with its terminals (data sheet 30)
    hood = bx(XP, XP + 34.0, IN_Y - 19.0, IN_Y + 19.0, IN_Z + 34.0, IN_Z + 36.0)
    for sy_ in (-1, 1):
        hood += bx(XP, XP + 34.0, IN_Y + sy_ * 18.0 - 1.0, IN_Y + sy_ * 18.0 + 1.0, IN_Z - 34.0, IN_Z + 36.0)
    hood += bx(XP + 32.0, XP + 34.0, IN_Y - 19.0, IN_Y + 19.0, IN_Z + 16.0, IN_Z + 36.0)     # inner end: above the terminals' plugs
    for y, z in HOOD_SCREWS:
        yw = IN_Y + (18.0 if y > IN_Y else -18.0)
        hood += bx(XP, XP + 9.0, min(yw, y - 4.0), max(yw, y + 4.0), z - 4.0, z + 4.0)
        hood -= Pos(XP + 4.5, y, z) * xcyl(PH3 / 2, 9.0)              # printed clearance, vertical in the print (-X up)
    d.add("mains_cover_inlet", hood, material=COOL, process="printed",
          meta={"print_up": "-X", "print": {**PRINT_ABS, "orientation": "-X", "infill": 0.3}})
    for i, (y, z) in enumerate(HOOD_SCREWS):
        # owner review: a through-bolt, head and washer outside the panel, washer and nyloc nut on the boss's inner face
        through_bolt_nyloc(d, f"mains_cover_inlet_screw_{i}", bolt_length(T_IP + 9.0, nut_h=2.4), (XP - T_IP, y, z), (1, 0, 0),
                           ("inlet_panel", "mains_cover_inlet"), (XP + 9.0, y, z), nyloc=False)
    # v10.1: the earth stud's stack is drawn: a DIN 6797 toothed washer on the rail's face, the earth wire's ring terminal on
    # it (a line of the electrical BOM, not drawn: its tongue is taken as 0.8 mm), the head of an M5 x 6 on that. The tip ends
    # 4.6 mm below the rail's face (v10's M5 x 10 went 8 mm into a 6 mm slot).
    EARTH_TONGUE = 0.8
    ew = place(d, "earth_stud_washer", washer_toothed("M5"), Location(Plane(origin=(XP, 80.0, 10.0), z_dir=(-1, 0, 0))))
    add_screw(d, "earth_stud", "M5", 6, at=(XP - ew.meta["interfaces"]["thickness"] - EARTH_TONGUE, 80.0, 10.0), direction=(1, 0, 0),
              threads_into="frame_bot_left", tnut=True, clamps=("earth_stud_washer",))
    d.join("earth_stud", "earth_stud_washer", "washer")
    d.join("earth_stud_washer", "frame_bot_left", "clamped under the earth stud (teeth bite through the anodising)")
    # ================= bench sub-assemblies =======================================
    have = {c.name for c in d.components}
    for tg, x0, y0, turn, posts, rail, on_tray in mounts:
        # motor, its screw and plate go in as one unit onto the two spacers; the post bolts follow
        # v11: the POM nut comes on the screw (threaded on at the bench from the screw's free end) and goes in with the drive; the
        # nut plate and keeper, open-slotted, slide onto it sideways afterwards
        unit = [n for n in mount_parts[tg] if "_bolt_" not in n and "_spacer_" not in n and n in have] + [f"z_nut{tg}"]
        if tg:      # the front ones: the whole nut stack goes in with the drive (from above, before the top side rail), then the
                    # nut plate's two M5 are driven up into the square's member
            unit += [n for n in have if n.startswith((f"nut_plate{tg}", f"nut_keeper{tg}", f"nut_pin{tg}")) and not n.startswith(f"nut_plate{tg}_bolt")]
        d.subassemblies[f"z_drive{tg or '_rear'}"] = unit
    # v9 / v10: the bed is a bench unit: plate with its three countersunk studs, their washers and lock nuts, heater and cut-off;
    # the springs go over the studs, the unit goes down through the deck's holes, the thumb nuts go on from below, and the
    # magnetic base and sheet go on last
    bed_unit = ["bed_plate", "bed_heater", "bed_tco"]
    for i in range(len(BED_MOUNTS)):
        bed_unit += [f"bed_stud_{i}{x}" for x in ("", "_washer", "_nut")] + [f"bed_spring_{i}", f"bed_spring_{i}_seat"]
    d.subassemblies["bed_unit"] = [n for n in bed_unit if n in have]
    d.subassemblies["x_drive"] = ["x_motor_mount", "x_motor", "x_pulley"] + [f"x_motor_screw_{i}{s}" for i in range(4) for s in ("", "_washer")]
    d.subassemblies["x_idler_unit"] = ["x_idler_mount", "x_idler_spacer", "x_idler", "x_idler_bolt", "x_idler_bolt_washer", "x_idler_nut"]
    # v11: no part-cooling bench unit: the blower stands behind the Roto's right-hand screw (its driver passes through where the
    # blower sits), so the order is duct, Roto and its screws, then the blower and its two M3 bolts
    for tag in ("", "_l"):
        d.subassemblies[f"y_drive{tag}"] = ([f"y_motor_mount{tag}", f"y_motor{tag}", f"y_pulley{tag}"]
                                            + [f"y_motor{tag}_screw_{i}{s}" for i in range(4) for s in ("", "_washer")])
    # ================= belts =====================================================
    PC = YB0 - 1.55
    YA0, YA1 = PC + BELT_SLOTS[0] - SLOT_W / 2, PC + BELT_SLOTS[-1] + SLOT_W / 2
    d.belts.append(Belt("x_belt", [("anchor", "xbody", (-14.0, XB_Y, Z_XL)), ("pulley", "x_pulley", "ccw"),
                                   ("pulley", "x_idler", "ccw"), ("anchor", "xbody", (14.0, XB_Y, Z_XL))],
                        axis=(0, 1, 0), width=BWX, adjust=BELT_ADJ))
    d.belts.append(Belt("y_belt", [("anchor", "ybody", (YB_X, YA0, Z_YA)), ("pulley", "y_idler", "ccw"),
                                   ("pulley", "y_pulley", "ccw"), ("anchor", "ybody", (YB_X, YA1, Z_YA))],
                        axis=(1, 0, 0), width=BWY, adjust=BELT_ADJ))
    d.belts.append(Belt("y_belt_l", [("anchor", "ybody", (-YB_X, YA0, Z_YA)), ("pulley", "y_idler_l", "ccw"),
                                     ("pulley", "y_pulley_l", "ccw"), ("anchor", "ybody", (-YB_X, YA1, Z_YA))],
                        axis=(1, 0, 0), width=BWY, adjust=BELT_ADJ))
    d.bom_extra("GT2-BELT-9MM-OPEN-1M", 1, 4.0)
    d.bom_extra("GT2-BELT-12MM-OPEN-1M", 2, 5.0)
    d.bom_extra("THREADLOCKER-MEDIUM (Loctite 243 class: Z motor screws and posts, pulley set screws, jack screws, post jam nuts)", 1, 6.0)
    d.bom_extra("DRIVER-BTT-TMC2209 (Octopus: X, Y, Y1, Z, Z1, Z2, E)", 7, 6.0)
    # ================= joints ====================================================
    d.joints.append(Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-TY_F, TY), overtravel=(ES_OT, ES_OT),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": ["y_motor", "y_motor_l"], "kind": "belt", "pulley": "y_pulley"}))
    d.joints.append(Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(-TX, TX), overtravel=(ES_OT_X, ES_OT_X),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": "x_motor", "kind": "belt", "pulley": "x_pulley"}))
    # v8.2: three motors, each turning its own screw directly (the screw is its shaft); the firmware levels them with
    # Z_TILT_ADJUST ([z_tilt] in build_electrical)
    d.joints.append(Joint("z", "slide", "world", "zbody", (0, 0, 1), range=(-Z_DN, PRINT_Z), overtravel=(0.0, Z_UP),
                          max_speed=V_Z, max_accel=A_Z, min_drive_margin=MARGIN,
                          drive={"motor": [f"z_motor{t}" for t in zs["tags"]], "kind": "leadscrew",
                                 "screw": [f"leadscrew{t}" for t in zs["tags"]],
                                 "nut": [f"z_nut{t}" for t in zs["tags"]], "sync": "independent", "nut_seating": "captive",
                                 # v11: the POM anti-backlash nut has no backlash of its own (spring-preloaded: ASSUMED); what
                                 # it can move before bearing the other way is the keeper's 0.1 mm play
                                 "nut_reverse_gap_mm": KEEP_GAP,
                                 "nut_reverse_gap_basis": f"POM anti-backlash nut (no backlash: assumed) held with the keeper's {KEEP_GAP:g} mm play (v12: stock 6 mm spacer over the 5 mm flange)",
                                 # how far a nut's flange can rock between its plate and its keeper before the tilted carrier
                                 # forces the nut out of square with its screw (v11: the square flange, 23 mm, a stand-in figure)
                                 "nut_tilt_allowance_rad": KEEP_GAP / 26.0,
                                 "nut_tilt_basis": f"keeper play {KEEP_GAP:g} mm over the POM nut's 26 mm flange (drawing A4003)"}))
    d.program = [{"to": {"z": PRINT_Z}},
                 {"to": {"x": -75, "y": -75}}, {"to": {"x": 75, "y": -75}}, {"to": {"x": 75, "y": 75}},
                 {"to": {"x": -75, "y": 75}}, {"to": {"x": -75, "y": -75}}, {"to": {"x": 0, "y": 0}},
                 {"to": {"z": 0.0}}]
    nozzle = (NOZ_X, YB0 + HOT_OFF, Z_NOZZLE)
    d.tool_point = ("xbody", nozzle)
    d.endstops += [{"joint": "x", "switch": "x_endstop", "at": "max"},
                   {"joint": "y", "switch": "y_endstop", "at": "max"},
                   {"joint": "z", "probe": "bed_probe", "at": "max"}]
    build_electrical(d)
    d.adjustments += [
        Adjustment("probe z_offset in the firmware", "z_offset", range_mm=Z_UP),
        Adjustment("the knurled thumb nut under the deck at each of the three bed studs (0.7 mm per turn)", "bed_level", range_mm=LEVEL_RANGE,
                   mover="DIN 466 M4 thumb nut", lock="the die spring's preload on the nut's thread (49 to 72 N over the range)"),
        Adjustment("x switch: its screws run in slots in the right Y plate's land", "endstop", range_mm=ES_SLOT, joint="x"),
        Adjustment("y switch: its flat plate slides along the right top rail's top slot on its T-nuts", "endstop", range_mm=5.0, joint="y"),
        Adjustment("y rails on sliding T-nuts", "rail_align", range_mm=1.6, joint="y",
                   note="an M3 in the 6.2 mm slot slides +/-1.6 mm: left rail to a straight edge, right rail tightened while the gantry runs"),
        Adjustment("z rails on sliding T-nuts", "rail_align", range_mm=1.6, joint="z",
                   note="rear rail to a square; left and right rails tightened while the carrier is run up and down; what is left "
                        "goes into the carriage plates' webs"),
        Adjustment("floating lead screw nut", "float", range_mm=NUT_FLOAT - 0.2, joint="z"),
        Adjustment("x belt: the X motor plate slides in its two slots on the beam's T-nuts, pulled outward by hand, then the two M5 are tightened",
                   "belt_tension", range_mm=BELT_ADJ, joint="x"),
        Adjustment("y belts: each motor plate slides on its T-nuts, pushed by an M5 tension screw positioned by two jam nuts on a cast corner bracket",
                   "belt_tension", range_mm=BELT_ADJ, joint="y", mover="M5 x 30 between two jam nuts", lock="the two jam nuts"),
    ]
    d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z",
                 "stiffness": {"x": "nozzle_stiffness_x", "y": "nozzle_stiffness_y"},
                 "print_area": (PRINT_X, PRINT_Y)}
    # ================= structure =================================================
    moving = ["y_plate_left", "y_plate_right", "x_beam", "x_rail", "x_carriage", "tool_plate", "tool_plate_rear", "extruder", "hotend"]
    y_plate_fix = [("y_plate_left", lambda f: abs(f.center().Z - Z_PLATE) < 1e-6),
                   ("y_plate_right", lambda f: abs(f.center().Z - Z_PLATE) < 1e-6)]
    z_blk = d.get("hotend").meta["interfaces"]["heater_block_box"][0][2]
    block_face = ("hotend", lambda f: abs(f.center().Z - z_blk) < 1e-3)
    for nm, force in (("nozzle_stiffness_y", (0.0, 3.0, -2.0)), ("nozzle_stiffness_x", (3.0, 0.0, -2.0))):
        d.assemblycases.append(AssemblyCase(nm, moving, fixed=y_plate_fix, loaded=block_face, force=force,
                                            probe=nozzle, max_deflection=0.03, min_fos=5.0))
    w_bed = 3.0 * (PAYLOAD_KG + bed_own) * 9.81
    # the bed's three mounts as the FEA meshes them: stud, washer and lock nut under the plate, large washer and thumb nut
    # under the deck. The springs are left out: while they are preloaded the bed is held by the studs against the thumb
    # nuts (docs/PRINTER_V9.md works the preload margin)
    posts = [f"bed_stud_{i}{sfx}" for i in range(len(BED_MOUNTS)) for sfx in ("", "_washer", "_nut")] \
        + [f"bed_thumb_{i}{sfx}" for i in range(len(BED_MOUNTS)) for sfx in ("", "_washer")]
    zcars, on_rail, carrier, nplates = zs["zcars"], zs["on_rail"], zs["carrier"], zs["nut_plates"]
    bed_stack = ["bed_plate", "bed_magnet", "bed"]
    d.printer["bed_support"] = {"parts": [*bed_stack, *posts, *carrier, *zcars, *nplates]}
    on_nut = lambda f: abs(f.center().Z - Z_TAB) < 1e-6 and f.area > 100
    d.assemblycases.append(AssemblyCase(
        "payload_x3_on_bed", [*bed_stack, *posts, *carrier, *zcars, *nplates],
        fixed=[(c, on_rail[c]) for c in zcars] + [(nb, on_nut) for nb in nplates],
        loaded=("bed", lambda f: abs(f.center().Z - (Z_SURF)) < 0.05 and f.area > 1000),
        force=(0.0, 0.0, -w_bed), probe=(BED_CX + PRINT_X / 2, BED_CY - PRINT_Y / 2, Z_SURF), max_deflection=0.3, min_fos=3.0))
    # metal parts in the Z load path (no printed part carries load any more)
    def hole_at(x, y, r):
        # a cylindrical face (a whole hole wall or a piece of one) whose sampled points all lie r from the axis (x, y)
        def sel(f):
            if f.geom_type.name != "CYLINDER":
                return False
            pts = [f.position_at(u, v) for u in (0.1, 0.5, 0.9) for v in (0.2, 0.8)]
            return all(abs(math.hypot(p.X - x, p.Y - y) - r) < 0.05 for p in pts)
        return sel
    # one nut plate (the three are one shape) under three times the whole bed's weight, held at its two M5 holes
    tg, ncx, ncy, nang, _ = NUTS[0]        # v11: the rear one, which reaches 57 mm out through the back wall
    fb = [rxy(u, -NUT_OUT_R - 10.0, ncx, ncy, nang) for u in (-NP_BOLT_U, NP_BOLT_U)]
    d.loadcases.append(LoadCase("nut_thrust", f"nut_plate{tg}",
                                fixed=lambda f: any(hole_at(x, y, clearance_hole("M5") / 2)(f) for x, y in fb),
                                loaded=hole_at(ncx, ncy, NP_HOLE / 2), force=(0.0, 0.0, w_bed), min_fos=3.0, max_deflection=0.05))
    # one carriage plate between its block and the square (the three are one shape), as a beam test of its web: 5 N on the
    # block square to the wall, the square's member held, the block FREE to turn (the harness cannot hold a face against
    # turning only): a cantilever, whose deflection at the block's centre beam theory gives as
    # F (L^3 / 3 + L^2 a + L a^2) / (E I), a = 23.7 mm from the web's end to the block's centre: 0.418 mm. On its rail the
    # block cannot turn and the same web is 12 E I / L^3 = K_FLEX. A requirement compares the two.
    d.assemblycases.append(AssemblyCase(
        "carriage_plate_web", ["carriage_plate_right", "sq_right", "z_carriage_right"],
        fixed=[("sq_right", lambda f: abs(f.center().X - (SQ_X - 20.0)) < 1e-6)],
        loaded=("z_carriage_right", on_rail["z_carriage_right"]), force=(WEB_TEST_N, 0.0, 0.0),
        probe=(WALL_X - 8.0, UP_S_Y, ZC), max_deflection=1.0, min_fos=3.0))
    d.loadcases.append(LoadCase("x_belt_pull", "x_belt_bracket", fixed=lambda f: abs(f.center().Y - (YB0 + R_TPF)) < 1e-6,
                                loaded=lambda f: abs(f.center().Z - (Z_XL + 0.7)) < 1e-6 and f.area > 100,
                                force=(60.0, 0.0, 0.0), min_fos=3.0, max_deflection=0.1))
    # ================= heat: bed 60 K above the frame =============================
    # how the three studs hold the growing plate. As designed: stud 0 is located in its fitted hole, the other two slip
    # under their thumb-nut washers (declared "sliding free": normal load only). "stuck": the bound where friction never
    # lets go at any of the three (it does: 0.2 to 0.6 x 47 to 55 N against several hundred newtons; the doc has the sums);
    # reported, not limited. Carrier and deck 15 K warm under the heater (assumed).
    warm = {c: 15.0 for c in carrier}
    stuck = [(f"bed_thumb_{i}_washer", "z_deck") for i in range(1, len(BED_MOUNTS))]
    for nm, stick, lim in (("bed_heated_60K", (), 0.1), ("bed_heated_60K_studs_stuck", stuck, None)):
        d.thermalcases.append(ThermalCase(
            nm, ["bed_plate", "bed_magnet", "bed", *posts, *carrier, *zcars, *nplates],
            fixed=[(c, on_rail[c]) for c in zcars] + [(nb, on_nut) for nb in nplates],
            temps={**warm, "bed_magnet": 60.0, "bed_plate": 60.0, "bed": 60.0, **{c: 30.0 for c in posts}, "*": 0.0},
            probes={"nozzle": (UP_R_X, Y_FACE - 8.0, ZC), "bed": (BED_CX, YB0 + HOT_OFF, Z_SURF - T_SHEET)},
            gaps={"nozzle gap": ("nozzle", "bed", "z", lim)}, flatness=("bed_plate", "z", lim), stick=stick))
    # the bed plate alone, held at its three countersinks, its mass the plate's plus the 1 kg payload spread over it (close to
    # plate + magnetic base + sheet + heater + a 0.3 kg print): its first bending mode. Fixed faces are ideally rigid, so
    # the real figure is lower; the brief sets no limit, 100 Hz keeps it above the gantry's resonances (60 to 80 Hz)
    # v11 limit (a): the plate alone on its three countersinks under the bed's own weight (plate, magnetic base, sheet, heater,
    # cut-off), spread over its top face: its sag from the plane of the three studs
    w_own = (bed_own + d.get("bed_magnet").mass() + d.get("bed").mass() + d.get("bed_heater").mass() + d.get("bed_tco").mass()) * 9.81
    d.loadcases.append(LoadCase("bed_self_weight_sag", "bed_plate", fixed=lambda f: f.geom_type.name == "CONE",
                                loaded=lambda f: abs(f.center().Z - (Z_BED + T_BED)) < 1e-3 and f.area > 1000,
                                force=(0.0, 0.0, -w_own), min_fos=3.0, max_deflection=FLAT_AS_INSTALLED - MIC6_FLAT_BOUGHT))
    d.modalcases.append(ModalCase("bed_plate_on_three_studs", "bed_plate", fixed=lambda f: f.geom_type.name == "CONE", min_frequency_hz=100.0))
    add_feedback_hardware(d)
    add_soak_case(d, zs, posts, carrier, zcars, nplates, on_rail, on_nut)
    add_requirements(d, zs)
    assign(d, sheet="sendcutsend", machined="xometry")
    # v12: printed parts go to a print service in PETG (ROADMAP, Build 1): its published FDM rules (Hubs: 0.8 mm wall, 2 mm feature)
    d.manufacturing["process_shop"] = "hubs"
    for c in d.components:
        if not c.cots and c.material in ("petg", "abs", "pla"):
            c.meta.setdefault("dfm", {})["process_shop"] = "hubs"
    tag_stages(d)
    return d


def add_requirements(d, zs):
    def jr(dd, name):
        return next(j for j in dd.joints if j.name == name)

    def motors_of(dd, name):
        mm_ = jr(dd, name).drive["motor"]
        return [mm_] if isinstance(mm_, str) else list(mm_)

    def nozzle_tip(dd):
        return dd.tool_point[1]

    def travel(dd):
        t = {n: jr(dd, n).range[1] - jr(dd, n).range[0] for n in "xyz"}
        return t["x"] >= PRINT_X and t["y"] >= PRINT_Y and t["z"] >= PRINT_Z, str(t)
    d.requirements.append(Requirement(f"print volume: travel >= {PRINT_X:g} x {PRINT_Y:g} x {PRINT_Z:g} mm (v10.1: 229.6 x 214.5 x 180 on a cut rail)", travel))

    def nozzle_over_bed(dd):
        nx, ny, _ = nozzle_tip(dd)
        bb = dd.get("bed_plate").shape.bounding_box()
        xr_, yr_ = jr(dd, "x").range, jr(dd, "y").range
        m = min(nx + xr_[0] - bb.min.X, bb.max.X - (nx + xr_[1]), ny + yr_[0] - bb.min.Y, bb.max.Y - (ny + yr_[1]))
        return m >= 0, f"smallest nozzle-to-bed-edge margin over the XY travel: {m:.1f} mm"
    d.requirements.append(Requirement("nozzle stays over the bed plate for all XY positions", nozzle_over_bed))

    def bed_gap(dd):
        top = dd.get("bed").shape.bounding_box().max.Z
        gap = nozzle_tip(dd)[2] - (top + PRINT_Z)
        beyond = jr(dd, "z").range[1] - PRINT_Z
        return (-1e-9 <= gap <= 0.2 + 1e-9 and beyond >= 0, f"nozzle tip is {gap:.2f} mm above the bed surface with the bed {PRINT_Z:g} mm up")
    d.requirements.append(Requirement("bed can reach the nozzle: 0-0.2 mm gap at the top of the print height", bed_gap))
    d.requirements.append(Requirement("bed carries the 1.0 kg payload as mass", lambda dd: (
        (m := dd.get("bed_plate").mass()) >= dd.get("bed_plate").shape.volume * MATERIALS[CAST].density * 1e-9 + PAYLOAD_KG - 1e-9,
        f"bed plate + payload {m:.3f} kg")))

    def speeds(dd):
        s = {n: (jr(dd, n).max_speed, jr(dd, n).max_accel) for n in "xyz"}
        ok = all(s[n][0] >= V_XY and s[n][1] >= A_XY for n in "xy") and s["z"][0] >= V_Z and s["z"][1] >= A_Z
        return ok, str(s)
    d.requirements.append(Requirement("X/Y 250 mm/s at 4000 mm/s^2, Z 12 mm/s at 200 mm/s^2", speeds))
    d.requirements.append(Requirement("drive margin >= 3x on every axis", lambda dd, m: (
        set(m["motion"]["drives"]) == {"x", "y", "z"} and all(v["margin"] >= MARGIN for v in m["motion"]["drives"].values()),
        str({k: v["margin"] for k, v in m["motion"]["drives"].items()}))))
    d.requirements.append(Requirement("all three belts (X, Y, Y left) routed: constant length, clear of parts", lambda dd, m: (
        all(b in m["motion"].get("belts", {}) and m["motion"]["belts"][b]["clear_of_parts"]
            and m["motion"]["belts"][b]["length_change_over_travel_mm"] <= 0.3 for b in ("x_belt", "y_belt", "y_belt_l")),
        str({b: (v.get("clear_of_parts"), v.get("length_change_over_travel_mm")) for b, v in m["motion"].get("belts", {}).items()}))))

    def rail_margins(dd):
        out = {}
        rails = {"y_carriage_left": "y_rail_left", "y_carriage_right": "y_rail_right", "x_carriage": "x_rail", **zs["rails"]}
        for n, rail in rails.items():
            ax = n[0].upper()
            cb, rb = dd.get(n).shape.bounding_box(), dd.get(rail).shape.bounding_box()
            lo, hi = jr(dd, ax.lower()).mechanical_range
            out[n] = round(min(getattr(cb.min, ax) + lo - getattr(rb.min, ax), getattr(rb.max, ax) - getattr(cb.max, ax) - hi), 2)
        return min(out.values()) >= 5.0, str(out)
    d.requirements.append(Requirement("every carriage stays >= 5 mm inside its rail ends over the mechanical travel", lambda dd: rail_margins(dd)))

    def z_beyond(dd):
        ok_rail, detail = rail_margins(dd)
        left = {t: dd.get(f"leadscrew{t}").shape.bounding_box().max.Z - (dd.get(f"z_nut{t}").shape.bounding_box().max.Z + PRINT_Z + Z_UP)
                for t in zs["tags"]}
        return ok_rail and min(left.values()) >= 5.0, f"with Z {Z_UP:g} mm past the nozzle plane: {detail}; lead screws {min(left.values()):.1f} mm above their nuts"
    d.requirements.append(Requirement(f"Z rails, blocks, screws and nuts allow {Z_UP:g} mm of travel beyond the nominal nozzle plane", z_beyond))
    def screws_clear(dd):
        # v11: the 330 mm screws stand taller than the top rails' undersides; none may stand under a frame extrusion
        frame = [c for c in dd.components if c.name.startswith(("frame_top_", "post_", "upright_"))]
        out, ok = [], True
        for t_ in zs["tags"]:
            sb = dd.get(f"leadscrew{t_}").shape.bounding_box()
            over = [c.name for c in frame if c.shape.bounding_box().min.Z < sb.max.Z and c.shape.bounding_box().max.Z > sb.min.Z
                    and c.shape.bounding_box().min.X < sb.max.X and c.shape.bounding_box().max.X > sb.min.X
                    and c.shape.bounding_box().min.Y < sb.max.Y and c.shape.bounding_box().max.Y > sb.min.Y]
            ok = ok and not over and not dd.get(f"leadscrew{t_}").ratings.get("cut_to_length")
            gap = min(abs(sb.max.X - (FX / 2 - 20.0)), abs(sb.min.X + (FX / 2 - 20.0))) if t_ else sb.min.Y - (FY / 2)
            out.append(f"leadscrew{t_ or '_rear'}: top {sb.max.Z:.1f}, {'not cut' if not dd.get(f'leadscrew{t_}').ratings.get('cut_to_length') else 'CUT'}, "
                       f"{'under ' + ', '.join(over) if over else 'under no frame extrusion'}, {gap:.1f} mm from the wall it stands beside")
        rails = max(dd.get(n).shape.bounding_box().max.Z for n in ["z_rail_left", "z_rail_right", "z_rail_rear"])
        return ok and rails < FZ - 10, f"Z rail tops {rails:.1f} (extrusion underside {FZ - 10:g}); " + "; ".join(out)
    d.requirements.append(Requirement("v11: the Z lead screws are used at 330 mm as sold and stand under no frame extrusion; the Z rails end below the top rails",
                                      screws_clear))
    d.requirements.append(Requirement("all three joints driven by catalog NEMA 17 motors", lambda dd: (
        all(dd.get(mn).sku.startswith("NEMA17") and dd.get(mn).meta["catalog"] for n in "xyz" for mn in motors_of(dd, n)),
        str({n: [dd.get(mn).sku for mn in motors_of(dd, n)] for n in "xyz"}))))
    def z_direct(dd):
        drv = jr(dd, "z").drive
        ms = motors_of(dd, "z")
        belts_on_z = [b.name for b in dd.belts if any(n[0] == "pulley" and n[1].startswith("z_") for n in b.path)]
        ok = (drv.get("sync") == "independent" and len(ms) == 3 and ms == [f"z_motor{t}" for t in zs["tags"]] and not belts_on_z
              and all(dd.get(m).ratings.get("integral_leadscrew") for m in ms) and "coupler" not in drv)
        return ok, f"Z motors {ms}, sync {drv.get('sync')}, belts on Z: {belts_on_z or 'none'}, couplers: {drv.get('coupler', 'none')}"
    d.requirements.append(Requirement("Z: three motors, each screw is its own motor's shaft (no belt, no coupler)", z_direct))
    d.requirements.append(Requirement("Z: the firmware levels the three screws (Klipper [z_tilt] with three screw positions and three points)", lambda dd: (
        len((zt := dd.electrical.firmware.get("z_tilt") or {}).get("z_positions", [])) == 3 and len(zt.get("points", [])) == 3,
        f"z_positions {zt.get('z_positions')}, points {zt.get('points')}")))
    d.requirements.append(Requirement("Z lead screws self-locking (efficiency < 0.5)", lambda dd: (
        all(dd.get(f"leadscrew{t}").ratings["efficiency"] < 0.5 for t in zs["tags"]), f"efficiency {dd.get('leadscrew').ratings['efficiency']}")))
    d.requirements.append(Requirement("reported, not a limit: part count", lambda dd: (True, f"{len(dd.components)} parts")))
    # ---- v9: the owner's sketch, as checks -------------------------------------------------------------------------------
    def three_rails(dd, m):
        pr = m["tolerance"]["paired_rails"]["z"]
        ic, aa = pr["in_plane_constraints"], pr.get("after_alignment", {})
        ok = len(pr["rails"]) == 3 and len(pr["floats"]) == 3 and ic["redundant"] == 0 and aa.get("within_allowed_side_load")
        return ok, (f"{len(pr['rails'])} rails, {len(pr['floats'])} floating mounts at {K_FLEX:.0f} N/mm, stiff directions {ic['stiff_directions_held']} "
                    f"of 3 needed; as built the rails are up to {pr['parallelism_error_over_travel_mm_99']} mm out of parallel over the travel "
                    f"(aligned at assembly); with {aa.get('residual_between_rails_mm')} mm left a block carries {aa.get('side_load_on_blocks_n_99')} N "
                    f"sideways (allowed {pr['side_load_allowed_n']} N), webs bend {max(aa.get('float_used_mm_99', {0: 0}).values())} mm of {FLEX_RANGE}")
    d.requirements.append(Requirement("v9: Z guided on three rails without over-constraint: three stiff directions, the rest on flexures", three_rails))

    def web_stiffness(dd, m):
        ac = m["fea"]["carriage_plate_web"]
        hi, lo = ac["deflection_mm"], ac["deflection_screwed_joints_mm"]
        ok = abs(hi / WEB_TEST_MM - 1.0) <= 0.15 and lo <= 1.6 * WEB_TEST_MM
        return ok, (f"{WEB_TEST_N:g} N on a block free to turn: FEA {hi:.3f} mm bonded, {lo:.3f} mm with joints held round their screws; beam "
                    f"theory {WEB_TEST_MM:.3f} mm. The same web with the block held square by its rail: {K_FLEX:.0f} N/mm (declared), "
                    f"{K_FLEX * WEB_TEST_MM / lo:.0f} N/mm on the screwed bound")
    d.requirements.append(Requirement("v9: the carriage plates' web is the flexure the tolerance model assumes (FEA within 15 % of beam theory)",
                                      web_stiffness))

    def carrier_square(dd):
        vol = lambda n: dd.get(n).shape.volume
        mem = [dd.get(f"sq_{n}") for n in ("left", "right", "front", "rear")]
        cp = [vol(f"carriage_plate_{g[0]}") for g in GUIDES]
        npv = [vol(f"nut_plate{t[0]}") for t in NUTS]
        mpv = [vol(f"z_motor_plate{t[0]}") for t in NUTS]
        kv = [vol(f"nut_keeper{t[0]}") for t in NUTS]
        same = lambda v: max(v) - min(v) < 1e-3 * max(v)
        dk = dd.get("z_deck").shape.bounding_box()
        ok = (all(c.sku.startswith("EXTRUSION-2020") or "2020" in c.sku for c in mem) and all(c.body == "zbody" for c in mem)
              and same(cp) and same(npv[1:]) and same(mpv[1:]) and same(kv) and abs(dk.size.Z - 3.175) < 1e-6
              and abs(dk.size.X - 270.8) < 1e-6 and abs(dk.size.Y - 281.8) < 1e-6)       # v10: the carrier is v9's, not resized
        return ok, (f"four 2020 members {2 * SQ_X:.1f} x {SQ_Y1 - SQ_Y0:.1f} mm outside; deck {dk.size.X:.1f} x {dk.size.Y:.1f} x {dk.size.Z:.3f} mm; "
                    f"three carriage plates one shape: {same(cp)}; nut plates: the two front ones one shape ({same(npv[1:])}), the rear one "
                    f"reaches out through the back wall; three keepers: {same(kv)}; motor plates: the two front ones one shape ({same(mpv[1:])})")
    d.requirements.append(Requirement("v9: carrier is a closed 2020 rectangle with a 1/8 in deck (v11: rear nut plate and motor plate differ from the fronts)", carrier_square))

    def stud_loads(px, py, w=1.0):
        """Statics of the plate on its three studs: the load on each stud for w at (px, py)."""
        A = np.array([[1.0, 1.0, 1.0], [x for x, _ in BED_MOUNTS], [y for _, y in BED_MOUNTS]])
        return np.linalg.solve(A, np.array([w, w * px, w * py]))

    def bed_mass(dd):
        on_bed = ["bed_plate", "bed_magnet", "bed", "bed_heater", "bed_tco"] + [f"bed_stud_{i}{s}" for i in range(len(BED_MOUNTS)) for s in ("", "_washer", "_nut")]
        return sum(dd.get(n).mass() for n in on_bed) - PAYLOAD_KG

    PRINT_CORNERS = [(BED_CX + sx * PRINT_X / 2, BED_CY + sy * PRINT_Y / 2) for sx in (-1, 1) for sy in (-1, 1)]

    def spring_preload(dd):
        m_bed = bed_mass(dd)
        az = A_Z / 1000.0
        own = stud_loads(BED_CX, BED_CY, m_bed * (9.81 + az))            # the bed's own weight on each stud
        # the 1 kg payload wherever in the print area it loads a stud most: a corner (the loads are linear in its position)
        pay = np.max([stud_loads(px, py, PAYLOAD_KG * (9.81 + az)) for px, py in PRINT_CORNERS], axis=0)
        share = float(np.max(own + pay))
        lo, nom, hi = (SPRING_K * (20.0 - SPRING_H + s * LEVEL_RANGE) for s in (-1, 0, 1))
        n = len(BED_MOUNTS)
        f_hz = math.sqrt(n * SPRING_K * 1000.0 / (m_bed + PAYLOAD_KG)) / (2 * math.pi)
        a_lift = (n * lo - (m_bed + PAYLOAD_KG) * 9.81) / (m_bed + PAYLOAD_KG)
        # a hand pressing on a print corner: what is left between the weakest thumb nut and the deck (empty bed, weak end)
        hand = 20.0
        left = min(float(np.min(lo - own - stud_loads(px, py, hand))) for px, py in PRINT_CORNERS)
        ok = lo >= 2.0 * share and 20.0 - SPRING_H + LEVEL_RANGE <= 10.0 + 1e-9
        return ok, (f"three studs; bed without payload {m_bed:.2f} kg, {own[0]:.1f} / {own[1]:.1f} / {own[2]:.1f} N on the studs; worst stud carries "
                    f"{share:.1f} N (its share of the bed and the {PAYLOAD_KG:g} kg payload on the print corner that loads it most, Z at {A_Z:g} mm/s^2); "
                    f"spring preload {lo:.1f} / {nom:.1f} / {hi:.1f} N over the +/-{LEVEL_RANGE:g} mm levelling range (spring deflection "
                    f"{20.0 - SPRING_H - LEVEL_RANGE:g} to {20.0 - SPRING_H + LEVEL_RANGE:g} mm of the 10 mm the maker lists): factor {lo / share:.2f} at the "
                    f"weak end. A {hand:g} N hand on any print corner leaves at least {left:.1f} N between every thumb nut and the deck (weak end, "
                    f"empty bed): the bed does not leave its nuts. It leaves them only above {a_lift:.1f} m/s^2 of upward carrier acceleration "
                    f"(Z runs {az:g}); on the springs alone it would bounce at {f_hz:.1f} Hz")
    d.requirements.append(Requirement("v10: every bed spring's preload is at least twice the load on its stud over the levelling range (the bed stays "
                                      "on its three thumb nuts)", spring_preload))

    def plate_growth(dd):
        a, dt = 23.6e-6, 60.0
        (x0, y0) = BED_MOUNTS[0]
        need = {i: math.hypot(x - x0, y - y0) * a * dt for i, (x, y) in enumerate(BED_MOUNTS) if i}
        free = (DECK_FREE - 4.0) / 2
        ok = need[1] <= 1.0 - 0.2 and need[2] <= free - 0.2 and abs(BED_MOUNTS[1][1] - y0) < 1e-9
        return ok, (f"plate {dt:g} K warmer than the deck: studs move {need[1]:.2f} (front right, along its slot, +/-1.0) and {need[2]:.2f} mm (rear, "
                    f"oversize hole, {free:.2f} mm radial) from the fitted front-left stud; 0.2 mm kept for hole position")
    d.requirements.append(Requirement("v10: the heated plate's growth fits the deck's slot and oversize hole (no stud is bent)", plate_growth))

    def three_points(dd):
        studs = [c.name for c in dd.components if re.fullmatch(r"bed_stud_\d+", c.name)]
        thumbs = [c.name for c in dd.components if re.fullmatch(r"bed_thumb_\d+", c.name)]
        springs = [c.name for c in dd.components if re.fullmatch(r"bed_spring_\d+", c.name)]
        (x0, y0), (x1, y1), (x2, y2) = BED_MOUNTS
        area = abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2
        nuts = [(dd.get(f"z_nut{t[0]}").shape.bounding_box().center().X, dd.get(f"z_nut{t[0]}").shape.bounding_box().center().Y) for t in NUTS]
        near = [min(math.hypot(x - nx, y - ny) for nx, ny in nuts) for x, y in BED_MOUNTS]
        com_in = min(stud_loads(BED_CX, BED_CY)) > 0.15
        tapped = [c.name for c in dd.components if c.name.startswith("bed_stud") and "bed_plate" in (c.meta.get("threads_into") or [])]
        ok = len(studs) == len(thumbs) == len(springs) == 3 and area > 15000.0 and com_in and not tapped
        return ok, (f"{len(studs)} studs, {len(springs)} springs, {len(thumbs)} thumb nuts; the triangle they span is {area / 100:.0f} cm2 "
                    f"({2 * LEV_X:g} mm wide at the front, {2 * LEV_Y:g} mm deep); each stud is {near[0]:.0f} / {near[1]:.0f} / {near[2]:.0f} mm from the "
                    f"nearest lead-screw nut; the bed's centre puts {' / '.join(f'{v:.2f}' for v in stud_loads(BED_CX, BED_CY))} of its weight on them; "
                    f"no thread in the plate")
    d.requirements.append(Requirement("v10: the bed stands on three sprung, thumb-nut levelling points (a plane, no twist), none tapped into the plate", three_points))

    def heater_cover(dd):
        hb = dd.get("bed_heater").shape.bounding_box()
        x0, x1, y0, y1 = BED_CX - PRINT_X / 2, BED_CX + PRINT_X / 2, BED_CY - PRINT_Y / 2, BED_CY + PRINT_Y / 2
        cov = max(0.0, min(hb.max.X, x1) - max(hb.min.X, x0)) * max(0.0, min(hb.max.Y, y1) - max(hb.min.Y, y0)) / (PRINT_X * PRINT_Y)
        return cov >= 0.90, (f"pad {hb.size.X:g} x {hb.size.Y:g} mm under a {PRINT_X:g} x {PRINT_Y:g} mm print area: {cov:.1%} covered; not covered: "
                             f"{max(0.0, hb.min.Y - y0):.2f} mm at the front and {max(0.0, y1 - hb.max.Y):.2f} mm at the rear (the studs' washers), "
                             f"{max(0.0, hb.min.X - x0):.2f} / {max(0.0, x1 - hb.max.X):.2f} mm at the sides")
    d.requirements.append(Requirement("v12: the stock heater pad covers at least 90 % of the print area (v10: 95 % with a pad made to size)", heater_cover))

    def sheet_use(dd):
        sb = dd.get("bed").shape.bounding_box()
        xr_, yr_ = jr(dd, "x").range, jr(dd, "y").range
        nx, ny, _ = nozzle_tip(dd)
        m = min(nx + xr_[0] - sb.min.X, sb.max.X - (nx + xr_[1]), ny + yr_[0] - sb.min.Y, sb.max.Y - (ny + yr_[1]))
        used = PRINT_X * PRINT_Y / (sb.size.X * sb.size.Y)
        return m >= 0 and used >= 0.82, (f"print area {PRINT_X:g} x {PRINT_Y:g} mm on a {sb.size.X:g} x {sb.size.Y:g} mm sheet ({dd.get('bed').sku}): {used:.1%} of it "
                                         f"(v10.1: 89.2 % of 235 x 235); the nozzle stays {m:.2f} mm or more inside the sheet's edge")
    d.requirements.append(Requirement("v11: the print sheet is a stock size the nozzle's reach nearly fills (at least 82 % of it printed on; v12: X is 5 mm shorter on the 245 mm rail; v11: 84)", sheet_use))

    def x_travel(dd):
        cb, rb = dd.get("x_carriage").shape.bounding_box(), dd.get("x_rail").shape.bounding_box()
        lo, hi = jr(dd, "x").mechanical_range
        on_rail = min(cb.min.X + lo - rb.min.X, rb.max.X - cb.max.X - hi)
        # the toolhead (everything on the X body below the top of the top side rails) against the rails' inner faces. v11: only the
        # part of each solid below the rails' top counts (the blower and the duct's cradle reach out over the rails above z 424.5,
        # where nothing on the frame reaches in; the motion check covers them)
        def below(c):
            bb = c.shape.bounding_box()
            if bb.max.Z <= FZ + 10.0:
                return bb
            cut = c.shape & Pos((bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + FZ + 10.0) / 2) * Box(
                bb.size.X + 2.0, bb.size.Y + 2.0, FZ + 10.0 - bb.min.Z)
            return cut.bounding_box()
        xs = [(b.min.X, b.max.X, c.name) for c in dd.components
              if c.body == "xbody" and c.shape.bounding_box().min.Z < FZ + 10.0 for b in [below(c)]]
        left = min(xs)
        right = max(xs, key=lambda v: v[1])
        cl, cr = left[0] + lo + (FX / 2 - 20.0), (FX / 2 - 20.0) - (right[1] + hi)
        ok = on_rail >= 5.0 - 1e-6 and min(cl, cr) >= 1.9 and abs(dd.get("frame_top_left").shape.bounding_box().size.Y - FD) < 1e-6
        ok = ok and abs(rb.size.X - X_RAIL_L) < 1e-6 and X_RAIL_L in (245.0, 295.0)
        return ok, (f"X working travel {jr(dd, 'x').range[1] - jr(dd, 'x').range[0]:g} mm ({hi - lo:g} mm mechanical) on a {rb.size.X:g} mm stock rail on the "
                    f"{BEAM_L:g} mm beam: the block stays {on_rail:.1f} mm inside the rail's ends; at the ends of the mechanical travel "
                    f"{left[2]} is {cl:.2f} mm from the left top rail and {right[2]} {cr:.2f} mm from the right one; frame unchanged "
                    f"({FX:g} x {FD:g} x {FZ + 10:g} mm outside)")
    d.requirements.append(Requirement("v12: X travel is what a stock HIWIN 245 mm MGNR12R allows (5 mm of rail beyond the block), with the toolhead 1.9 mm "
                                      "or more clear of the top side rails; the frame is v9's", x_travel))

    def motor_tilt(dd, m):
        ta = m["fea"]["bed_support"].get("tilt_allowance") or {}
        if "overload_free_mm" not in ta:
            return False, f"not evaluated: {ta.get('why', 'no tilt allowance in the bed-support metrics')}"
        routine = ta["routine_height_error_mm"]
        ok = ta["overload_free_mm"] >= 3.0 * routine and ta.get("seated_up_to_mm", 0.0) >= routine and ta["overload_free_mm"] <= 2 * LEVEL_RANGE
        ps = ta["per_screw"]
        return ok, (f"one Z motor may stand {ta['overload_free_mm']:.2f} mm out of the plane of the other two ({ta['across_print_area_mm']:.2f} mm "
                    f"across the print area) before the first limit: {ta['first_limit']} ({ta['governing_screw']}); per screw "
                    + ", ".join(f"{k} {v['overload_free_up_to_mm']:.2f}" for k, v in ps.items()) + " mm; limits for the governing screw: "
                    + "; ".join(f"{k} {v:.2f} mm" for k, v in sorted(ps[ta['governing_screw']]['limits_mm'].items(), key=lambda kv: kv[1])[:4])
                    + f". Every nut stays on its weight-bearing flank up to {ta['seated_up_to_mm']:.2f} mm. Routine height error (LSC-015 budget) "
                    f"{routine:.3f} mm: {ta['overload_free_over_routine']:.1f} times inside the limit. Division of labour: thumb nuts (+/-{LEVEL_RANGE:g} mm "
                    f"each) for the one-time coarse tram, until Z_TILT_ADJUST's first pass asks for less than {ta['seated_up_to_mm']:.2f} mm at any "
                    f"screw; motors for everything after that, never more than {ta['overload_free_mm']:.2f} mm")
    d.requirements.append(Requirement("v10: the Z motors may tilt the carrier by at least 3 x the routine height error before a guide block, a flexure "
                                      "web or a nut seat reaches its limit, and every nut stays seated over the routine error; the thumb nuts' "
                                      "range covers what the motors may not", motor_tilt))
    def probed(dd, m):
        us = m["subsystems"]["homing"]["z"].get("unprobed_strip_mm", {})
        nan = float("nan")
        px, py = PRINT_X - us.get("x_low", nan) - us.get("x_high", nan), PRINT_Y - us.get("y_low", nan) - us.get("y_high", nan)
        return True, (f"sheet {SHEET:g} x {SHEET:g}, plate {BED:g} x {BED:g} x {T_BED:g}; nozzle over the sheet {PRINT_X:g} x {PRINT_Y:g} mm, probed "
                      f"{px:g} x {py:g} mm ({px * py / (PRINT_X * PRINT_Y):.0%} of it; unprobed strips: front {us.get('y_low', nan):g}, rear "
                      f"{us.get('y_high', nan):g}, left {us.get('x_low', nan):g}, right {us.get('x_high', nan):g} mm)")
    d.requirements.append(Requirement("reported: bed and print area", probed))
    d.requirements.append(Requirement(f"target: direct drive, at most {MAX_TOOLHEAD_KG:g} kg moving in X", lambda dd: (
        dd.get("extruder").body == "xbody" and (m := sum(c.mass() for c in dd.components if c.body == "xbody")) <= MAX_TOOLHEAD_KG,
        f"{m:.3f} kg on the X guide block, block included")))
    d.requirements.append(Requirement(f"target: both Y belts within 1 mm of plane in >= {MIN_BELT_IN_PLANE:.0%} of builds", lambda dd, m: (
        all(m["tolerance"]["belts"][b]["p_within_1mm"] >= MIN_BELT_IN_PLANE for b in ("y_belt", "y_belt_l")),
        str({b: m["tolerance"]["belts"][b]["p_within_1mm"] for b in ("y_belt", "y_belt_l")}))))
    d.requirements.append(Requirement("the bed probe switches before the nozzle touches for every unit, and over-travel ends short of its face", lambda dd, m: (
        (pz := m["subsystems"]["homing"]["z"])["z_offset_range_mm"][0] > 0.3 and Z_UP < EDDY_H,
        f"nozzle {pz['z_offset_range_mm'][0]:.2f} .. {pz['z_offset_range_mm'][1]:.2f} mm above the bed when the probe switches")))
    # ---- v11 requirements --------------------------------------------------------------------------------------------
    def cooling(dd):
        noz = np.array(dd.tool_point[1])
        hb = dd.get("hotend").meta["interfaces"]["heater_block_box"]
        blk = bx(hb[0][0], hb[1][0], hb[0][1], hb[1][1], hb[0][2], hb[1][2])
        duct = dd.get("part_duct").shape
        gap_block = float(duct.distance_to(blk))
        above_tip = duct.bounding_box().min.Z - noz[2]
        o, ax = _outlet_frame(noz[1])
        t_ = (noz[2] - 0.5 - o[2]) / ax[2]
        hit = o + ax * t_
        miss = float(np.hypot(hit[0] - noz[0], hit[1] - noz[1]))
        # the jet's axis where it passes the heater's round core (r 8.35): below the block's underside?
        r_c = (hb[1][0] - hb[0][0]) / 2
        t_c = (OUT_D - r_c) / math.hypot(ax[0], ax[1]) / 1.0
        z_at_core = o[2] + ax[2] * t_c
        est = blower_flow_estimate_pa(OUT_W * OUT_H, round(sum(DUCT_K.values()), 2), dd.get("part_fan").ratings["pq_curve_cfm_pa"])
        ok = gap_block >= 4.5 and above_tip >= 2.5 and miss < 0.5 and z_at_core < hb[0][2]
        return ok, (f"duct {gap_block:.2f} mm from the heater block (owner: 4 to 5), its lowest face {above_tip:.2f} mm above the nozzle tip (owner: >= 2.5); "
                    f"jet axis from {OUT_D:g} mm out, {math.degrees(math.asin(-ax[2])):.1f} degrees down, reaches the nozzle's axis 0.5 mm under the tip "
                    f"(off by {miss:.2f} mm) and passes the heater core's edge {hb[0][2] - z_at_core:.2f} mm under the block (silicone sock fitted). "
                    f"ESTIMATE of delivered flow: {est['flow_cfm']:.2f} CFM ({est['flow_l_per_min']:.1f} l/min) at {est['outlet_velocity_m_s']:.1f} m/s "
                    f"through the {OUT_W:g} x {OUT_H:g} mm outlet, {est['pressure_pa']:.0f} Pa, from the blower's P-Q curve (Delta BFB0524HH: free air "
                    f"{est['free_air_cfm']:g} CFM and shut-off {est['shutoff_pa']:.0f} Pa from the listing, the curve's shape between them assumed) and a duct loss of K = {est['k_total']:g} (handbook figures)")
    d.requirements.append(Requirement("v11: part cooling: the radial blower's jet lands just under the nozzle tip; the duct is >= 2.5 mm above the tip and "
                                      ">= 4.5 mm from the heater block (flow reported as an estimate)", cooling))

    def bent(dd):
        b = sorted(c.name for c in dd.components if not c.cots and c.material == "al5052")
        return b == ["probe_mount", "x_belt_bracket"] or b == ["x_belt_bracket", "probe_mount"], (
            f"bent sheet parts: {b} (v10 / v10.1: eight: X belt bracket, X idler mount, X tension anchor, two Y motor mounts, two Y "
            f"tension anchors, Y switch bracket; the owner keeps the X belt bracket bent; the probe holder is the one-bend L the owner asked for)")
    d.requirements.append(Requirement("v11: bent parts only where the owner asked: the X belt bracket (kept) and the probe L", bent))

    def stock_sizes(dd):
        cut = [c.name for c in dd.components if c.ratings.get("cut_to_length")]
        xr = dd.get("x_rail").shape.bounding_box().size.X
        ext = sorted({c.sku for c in dd.components if (c.sku or "").startswith("EXT2020")})
        return not cut and abs(xr - X_RAIL_L) < 1e-6, (
            f"purchased parts cut to length: {cut or 'none'}; X rail {xr:g} mm (a stock MGNR12R length); the three lead screws as sold; "
            f"the one purchased part bought cut is the 2020 extrusion, cut by Misumi (HFS5-2020-<L>): {len(ext)} lengths")
    d.requirements.append(Requirement("v11: purchased parts at stock sizes (no rail or screw cut); only the extrusion is bought cut, by its supplier", stock_sizes))

    def probe_zone(dd, m):
        # v12: BTT Eddy Duo. TI LDC1612 layout guidance (HEIGHT_SENSING 1.4): no metal plane close behind the coil and no closed
        # conductive ring round it. Checked: aluminium within 5 mm of the coil face's level band (the lowest 5 mm of the probe)
        pr = dd.get("bed_probe")
        bb = pr.shape.bounding_box()
        band = Pos((bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, bb.min.Z + 2.5) * Box(bb.size.X + 10.0, bb.size.Y + 10.0, 5.0)
        metals = ("al6061", "al5052", "al_mic6", "steel", "stainless304", "brass")
        hits = [c.name for c in dd.components if c.body == pr.body and c.name != "bed_probe" and not c.name.startswith("eddy_bolt")
                and c.material in metals and (c.shape & band).volume > 0.1]
        return not hits, (f"BTT Eddy Duo: metal on the toolhead within 5 mm of the coil (the probe's lowest 5 mm, 5 mm round it): {hits or 'none'}; "
                          f"the aluminium bracket's strip is {7.0 - EDDY_H:.1f} mm above the coil face, under the printed holder beside the probe")
    d.requirements.append(Requirement("v12: no metal close round the Eddy's coil (TI LDC1612 layout guidance)", probe_zone))

    def probe_temperature(dd, m):
        # v12: the Eddy's 60 degC rating (BTT manual), the same lumped estimate as v11 (bed 80 degC, coil face 2.5 mm above the sheet,
        # sock seen at about 38 mm); the probe's plastic body taken like the E2B's barrel (conduction to its holder lower: PETG)
        sig = 5.67e-8
        rating = dd.get("bed_probe").ratings["electrical"]["ratings"]["max_ambient_c"]

        def solve(t_air, h, t_br, t_sock, t_bed=BED_MAX_C):
            af, as_ = 0.0181 * 0.0153, 2 * (0.0181 + 0.0153) * 0.015
            g = 0.2 * 0.0181 * 0.0153 / 0.007
            f_sock = (0.017 * 0.017) / (math.pi * 0.039 ** 2) / 2
            lo, hi = 273.0, 420.0
            for _ in range(60):
                t = (lo + hi) / 2
                q = (0.85 * sig * ((t_bed + 273) ** 4 - t ** 4) * af + h * as_ * ((t_air + 273) - t)
                     + 0.9 * sig * ((t_sock + 273) ** 4 - t ** 4) * as_ * f_sock + g * ((t_br + 273) - t))
                lo, hi = (t, hi) if q > 0 else (lo, t)
            return t - 273.0
        nom = solve(55.0, 15.0, 45.0, 150.0)
        hot = solve(70.0, 10.0, 55.0, 180.0)
        # judged on the nominal case with 5 K in hand; the hot case is reported (an estimate with assumed air and holder temperatures)
        return nom <= rating - 5.0, (f"Eddy at its holder, bed at {BED_MAX_C:g} degC, coil face {EDDY_H:g} mm above the sheet: about {nom:.0f} degC (air over "
                               f"the bed 55 degC, holder 45 degC, sock 150 degC) and {hot:.0f} degC in a hot case (air 70, holder 55, sock 180, "
                               f"weaker convection) against the probe's {rating:g} degC rating (BTT). An ESTIMATE (assumed air and holder temperatures)")
    d.requirements.append(Requirement("v12: the Eddy stays 5 K under its 60 degC rating at its mounting point in the nominal case (thermal estimate; hot case reported)", probe_temperature))
    STANDINS = []
    d.requirements.append(Requirement("target: no purchased part is a stand-in where the catalogue has a real one", lambda dd: (
        sorted(px := [c.name for c in dd.components if c.cots and not c.meta.get("catalog")]) == STANDINS,
        f"hand-made purchased parts: {px or 'none'} (v12: the Wham Bam magnetic base is a catalogue part)")))
    PRINTED = ["part_duct", "mains_cover_psu", "mains_cover_inlet", "eddy_holder", "cam_overview_mount", "cam_topdown_mount", "sfs_mount",
               "led_clip_0", "led_clip_1"]
    d.requirements.append(Requirement("no printed part in a load path (owner's guideline): printed parts are the duct, covers and sensor holders", lambda dd: (
        sorted(pp := [c.name for c in dd.components if c.material in ("abs", "petg", "pla") and not c.cots]) == sorted(PRINTED), f"printed: {pp}")))
    # ---- v11: the bed's three achievable limits (owner), replacing v10's 0.02 mm sag limit
    def flat_installed(dd, m):
        lc = m["fea"].get("bed_self_weight_sag") or {}
        sag = lc.get("max_deflection_mm")
        if sag is None:
            return False, f"the bed_self_weight_sag load case did not report: {lc}"
        tot, tot_maker = MIC6_FLAT_BOUGHT + sag, MIC6_FLAT_MAKER + sag
        return tot <= FLAT_AS_INSTALLED + 1e-9, (
            f"(a) out of flat as installed: plate as bought {MIC6_FLAT_BOUGHT:g} mm (owner's figure; inspect the cut plate to it) + sag under the "
            f"bed's own weight on its three studs {sag:.4f} mm (FEA, plate alone) = {tot:.3f} mm, limit {FLAT_AS_INSTALLED:g} (what mesh "
            f"levelling corrects). On the maker's brochure figure for 6.35 to 15.9 mm cast plate ({MIC6_FLAT_MAKER:g} mm, whole plate) it "
            f"would be {tot_maker:.3f} mm")
    d.requirements.append(Requirement(f"v11 (a): bed out of flat as installed (plate flatness as bought + sag under its own weight) <= {FLAT_AS_INSTALLED:g} mm", flat_installed))

    def after_probing(dd, m):
        th = m["fea"].get("bed_heated_60K") or {}
        rise = (th.get("gap_change_mm") or {}).get("nozzle gap")
        flat = (th.get("bow_mm") or {}).get("bed_plate")
        if rise is None or flat is None:
            return False, f"thermal case figures not found: {sorted(th)}"
        worst = max(abs(rise), abs(flat))
        return worst <= FLAT_AFTER_PROBING + 1e-9, (
            f"(b) change after probing during the first layers: bounded by the whole heat growth from cold to 80 degC (bed 60 K above the "
            f"frame, carrier 15 K), as if the bed were probed before it had grown at all: nozzle-gap change {rise:.4f} mm, plate out of flat "
            f"{flat:.4f} mm; limit {FLAT_AFTER_PROBING:g}. A light first-layer print (well under the 1 kg of (c)) adds less than (c)'s figure")
    d.requirements.append(Requirement(f"v11 (b): change after probing during the first layers (heat growth at 80 degC) <= {FLAT_AFTER_PROBING:g} mm", after_probing))
    d.requirements.append(Requirement(f"v11 (c): sag under a full 1 kg print at the worst corner <= {SAG_1KG_CORNER:g} mm (screw-only bound; sanity)", lambda dd, m: (
        (pw := m["fea"]["bed_support"]["print_weight"])["judged_mm"] <= SAG_1KG_CORNER + 1e-9
        and m["fea"]["bed_support"].get("flexure", {}).get("evaluated", False),
        f"{pw['judged_mm']:.4f} mm at {pw.get('worst_point')} (v10.1, 12.7 mm plate: 0.0119)"
        + ("" if m["fea"]["bed_support"].get("flexure", {}).get("evaluated", False) else
           "; NOT EVALUATED: the bed-support flexure FEA did not run, so this is the guides' and nuts' compliance only"))))
    def nuts_held(dd, m):
        bs = m["fea"]["bed_support"]
        lv = bs["nut_seating_and_lead_error"]["levels"][2]
        kind = bs["nut_seating_and_lead_error"]["nut_seating"]["kind"]
        wc = lv["worst_case"]
        ok = (not lv["a_nut_unseats"]) or (kind == "captive" and wc["print_weight_sag_on_supports_mm"] <= SAG_1KG_CORNER + 1e-9)
        return ok, (f"nuts {kind}; height error {lv['height_error_mm']} mm; least nut load margin {min(lv['nut_load_margin_n'].values()):.1f} N; "
                    f"worst case: {wc['nuts_not_seated'] or 'all seated'} off their weight-bearing flank, bed level change "
                    f"{wc['bed_level_change_across_print_area_mm']} mm, 1 kg sag on the supports {wc['print_weight_sag_on_supports_mm']} mm")
    d.requirements.append(Requirement("every lead-screw nut stays held with two screws at opposite lead limits (LSC-015): seated, or "
                                      "captive with the bed's 1 kg sag on its supports <= 0.2 mm (v11's limit (c))", nuts_held))


# ======================================================================= v12 additions
INLET_REAL = {"maker": "SCHURTER", "mpn": "DD11.0114.1111",
              "sellers": [{"name": "Digi-Key", "part_number": "486-DD11.0114.1111 (DD11.0114.1111)", "checked": "2026-11-20",
                           "note": "$17.62, 2,557 in stock (V12_PLAN, distributor API)"}],
              "stock_size": "1-pole fuseholder, screw version A", "datasheet": "vendor_docs/INLET-C14-SW-FUSE-T8A_datasheet.pdf",
              "ratings_source": {"amps": "DD11 data sheet p.1: 10 A", "volts": "DD11 data sheet p.1: 250 VAC",
                                 "fuse_a": "design: T8A at 120 V (Schurter SPT 0001.2513)",
                                 "fuse_power_acceptance_w": "DD11 data sheet: fuse power acceptance at 23 degC, 1-pole", "max_ambient_c": "DD11 data sheet: 85 degC"},
              "note": "display model: SCHURTER's DD11 STEP (vendor_cad/inbox/INLET-C14-SW-FUSE-T8A.step, the 0111 variant: the same housing as "
                      "0114 per the family drawing; the 0114 differs inside, in the switch)"}

BOM_V12 = [
    # (sku, qty, unit $, stage, real_part)
    ("FUSE-DRAWER-SCHURTER-4301.1405", 1, 3.57, 1, {"maker": "SCHURTER", "mpn": "4301.1405", "sellers": [{"name": "Digi-Key", "part_number": "4301.1405",
        "checked": "2026-11-20", "note": "11,250 in stock"}], "datasheet": "vendor_docs/Schurter_Fusedrawer-2_4301.1401_datasheet.pdf (family sheet)"}),
    ("FUSE-BLADE-LITTELFUSE-0297010.WXNV", 1, 0.39, 1, {"maker": "Littelfuse", "mpn": "0297010.WXNV", "sellers": [{"name": "Digi-Key",
        "part_number": "F2996-ND (0297010.WXNV)", "checked": "2026-11-20", "note": "76,730 in stock"}], "datasheet": "vendor_docs/Littelfuse_297_MINI32V_datasheet.pdf"}),
    ("TRANSISTOR-ST-PN2222A", 1, 0.04, 1, {"maker": "STMicroelectronics", "mpn": "PN2222A", "sellers": [{"name": "Digi-Key", "part_number": "PN2222A",
        "checked": "2026-11-20"}], "datasheet": "vendor_docs/ST_PN2222A_datasheet.pdf"}),
    ("PSU-RPI-27W-USBC-SC1153", 1, 12.0, 1, {"maker": "Raspberry Pi Ltd", "mpn": "SC1153", "sellers": [{"name": "Digi-Key", "part_number": "SC1153",
        "checked": "2026-11-20", "note": "$12.00, 6,881 in stock"}], "datasheet": "vendor_docs/RaspberryPi_27W-USB-C-PSU_product_brief.pdf"}),
    ("COOLER-RPI5-ACTIVE-SC1148", 1, 5.0, 1, {"maker": "Raspberry Pi Ltd", "mpn": "SC1148", "sellers": [{"name": "Digi-Key", "part_number": "SC1148",
        "checked": "2026-11-20", "note": "$5.00, 31,905 in stock"}], "datasheet": "vendor_docs/RaspberryPi_Active-Cooler_product_brief.pdf"}),
    ("THERMISTOR-SEMITEC-104NT-4-R025H42G", 1, 0.91, 1, {"maker": "SEMITEC", "mpn": "104NT-4-R025H42G", "sellers": [{"name": "Digi-Key",
        "part_number": "104NT-4-R025H42G", "checked": "2026-11-20", "note": "$0.91, 250 in stock"}], "datasheet": "vendor_docs/Semitec_NT-4_thermistor_datasheet.pdf"}),
    ("CONN-MOLEX-MINIFIT-39-01-2020", 2, 0.27, 1, {"maker": "Molex", "mpn": "39-01-2020", "sellers": [{"name": "Digi-Key", "part_number": "39-01-2020",
        "checked": "2026-11-20", "note": "270,631 in stock"}], "datasheet": "vendor_docs/Molex_39-01-2020_drawing.pdf"}),
    ("CONN-MOLEX-MINIFIT-HCS-0457503111", 4, 0.17, 1, {"maker": "Molex", "mpn": "0457503111", "sellers": [{"name": "Digi-Key", "part_number": "0457503111",
        "checked": "2026-11-20", "note": "95,831 in stock"}], "datasheet": "vendor_docs/Molex_45750-3111_drawing.pdf"}),
    ("CABLE-IGUS-CF880-15-02-M", 1, 2.66, 1, {"maker": "igus", "mpn": "CF880-15-02", "sellers": [{"name": "Digi-Key Marketplace", "part_number": "CF880-15-02",
        "checked": "2026-11-20", "note": "$0.81/ft, 3,981 ft"}], "datasheet": "vendor_docs/igus_CF880_datasheet.pdf", "stock_size": "per foot (1 m: the bed run)"}),
    ("CABLE-IGUS-CF130-03-02-M", 6, 5.05, 2, {"maker": "igus", "mpn": "CF130-03-02", "sellers": [{"name": "Digi-Key", "part_number": "CF130-03-02",
        "checked": "2026-11-20", "note": "$1.54/ft"}], "datasheet": "vendor_docs/igus_CF130_datasheet.pdf", "stock_size": "per foot (flexing signal runs)"}),
    ("WIRE-LAPP-4160400-GNYE-16AWG-M", 2, 1.0, 1, {"maker": "LAPP", "mpn": "4160400", "sellers": [{"name": "Digi-Key", "part_number": "4160400",
        "checked": "2026-11-20", "note": "per foot, in stock"}], "stock_size": "per foot (earth: inlet -> stud -> supply, bed)"}),
    ("BELT-GATES-LL2MR09-M", 3, 19.6, 2, {"maker": "Gates", "mpn": "LL2MR09 (9396-0052)", "sellers": [{"name": "VBeltSupply.com", "checked": "2026-11-20",
        "note": "$5.98/ft, 50 ft minimum ($300 Gates minimum): the order is a 50 ft roll"}], "datasheet": "vendor_docs/Gates_GT2_design_manual.pdf",
        "stock_size": "open length by the foot"}),
    ("LASER-QUARTON-VLM-520-56-LPO-D30-F10", 1, 98.40, 3, {"maker": "Quarton", "mpn": "VLM-520-56 LPO-D30-F10", "sellers": [{"name": "Digi-Key",
        "part_number": "100-VLM-520-56LPO-D30-F10-ND", "checked": "2026-11-20", "note": "3 in stock, 4-week maker lead"}]}),
    ("CAM-ARDUCAM-B0454", 1, 38.99, 3, {"maker": "Arducam", "mpn": "B0454", "sellers": [{"name": "UCTRONICS (Arducam store)", "checked": "2026-11-20"}],
        "datasheet": "vendor_docs/Arducam_B0454_datasheet.pdf"}),
    ("LENS-COMMONLANDS-CIL062-F4.0-M12A650", 1, 23.0, 3, {"maker": "Commonlands", "mpn": "CIL062-F4.0-M12A650", "sellers": [{"name": "Digi-Key Marketplace",
        "part_number": "4946-CIL062-F4.0-M12A650-ND", "checked": "2026-11-20"}]}),
    ("LED-COB-INSPIRED-24V-4000K (2 x 50 mm at the nozzle)", 2, 1.23, 3, {"maker": "Inspired LED", "mpn": "24V-COB-4000K-12M",
        "sellers": [{"name": "Digi-Key", "part_number": "1647-24V-COB-4000K-12MCT-ND", "checked": "2026-11-20"}]}),
    ("CABLE-RPI5-CSI-22-15-300MM", 2, 3.0, 3, {"maker": "Raspberry Pi Ltd", "mpn": "Camera cable 22-15 pin 300 mm (Pi 5)", "sellers": [{"name": "Digi-Key",
        "checked": "2026-11-20"}], "datasheet": "vendor_docs/RaspberryPi_camera_cable_Pi5_page_2026-11-20.pdf"}),
    ("ADXL345-BTT-V2", 1, 9.25, 3, {"maker": "BIGTREETECH", "mpn": "ADXL345 V2.0.1", "sellers": [{"name": "biqu.equipment (BTT store)",
        "checked": "2026-11-20", "note": "$9.25, in stock"}], "datasheet": "vendor_docs/BTT_ADXL345-V2.0_manual.pdf"}),
    ("LABEL-LASER-CLASS-1M", 1, 0.0, 3, {"maker": "Quarton", "mpn": "warning label supplied with the VLM-520-56", "sellers": [{"name": "Digi-Key (with the laser)"}]}),
]


def add_v12_bom_lines(d):
    for sku, q, c, st, rp in BOM_V12:
        d.bom_extra(sku, q, c, real_part=rp, stage=st)
    d.bom_extras.pop("GT2-BELT-9MM-OPEN-1M", None)
    d.bom_extras.pop("GT2-BELT-12MM-OPEN-1M", None)
    # one THREADLOCKER line (Loctite 243, Henkel 1329837): the v11 duplicate is merged (V12_PLAN wiring decisions)
    for k in [k for k in d.bom_extras if k.startswith("THREADLOCKER-MEDIUM (")]:
        d.bom_extras.pop(k)


EDDY_CFG = ["# BIGTREETECH Eddy Duo on USB (HEIGHT_SENSING 5.1): mainline Klipper [probe_eddy_current]; tap for Z zero to be proven on the machine",
            "[probe_eddy_current btt_eddy]", "sensor_type: ldc1612", "i2c_mcu: eddy", "i2c_bus: i2c0f",
            "x_offset: {x_offset:g}", "y_offset: {y_offset:g}", "z_offset: 2.5", "speed: 5", "lift_speed: 10",
            "", "[temperature_probe btt_eddy]", "sensor_type: Generic 3950", "sensor_pin: eddy:gpio26", "horizontal_move_z: 2"]


def feedback_firmware(el, d):
    """v12: Klipper sections for the feedback hardware and the Eddy (written into printer.cfg and loaded by klippy with the RP2040 and
    host-MCU dictionaries), and Moonraker's power device (as a comment block: moonraker.conf)."""
    fw = el.firmware
    fw["extra_mcus"] = [{"name": "eddy", "serial": "/dev/serial/by-id/usb-Klipper_rp2040_EDDY-if00", "klipper_mcu": "rp2040",
                         "note": "BTT Eddy Duo (RP2040), USB to the Pi 5"},
                        {"name": "adxl", "serial": "/dev/serial/by-id/usb-Klipper_rp2040_ADXL-if00", "klipper_mcu": "rp2040",
                         "note": "BTT ADXL345 V2.0 (RP2040), USB to the Pi 5"},
                        {"name": "host", "serial": "/tmp/klipper_host_mcu", "klipper_mcu": "linux",
                         "note": "the Pi 5's own GPIO (klipper-mcu service): the laser's PN2222A"}]
    fw["probe_klipper"] = EDDY_CFG
    fw["extra_sections"] = [
        "[adxl345]", "cs_pin: adxl:gpio9", "spi_software_sclk_pin: adxl:gpio10", "spi_software_mosi_pin: adxl:gpio11",
        "spi_software_miso_pin: adxl:gpio12", "axes_map: x,z,y", "",
        "[resonance_tester]", "accel_chip: adxl345", f"probe_points: {TX:g}, {TY:g}, 20", "",
        "# BTT SFS V2.0 on the Octopus DIAG3 header (its DIAG jumper removed)",
        "[filament_motion_sensor sfs]", "switch_pin: ^PG11", "detection_length: 10", "extruder: extruder", "pause_on_runout: True", "",
        "# 24 V COB lights (overview strip + two nozzle segments) on FAN2",
        "[output_pin lights]", "pin: PD12", "pwm: True", "value: 0.5", "shutdown_value: 0", "",
        "# Quarton VLM-520-56 line laser (Class 1M): off by default, on only inside the measurement macro; PN2222A from Pi GPIO17",
        "[output_pin nozzle_laser]", "pin: host:gpio17", "value: 0", "shutdown_value: 0", "",
        "# commissioning (owner, v11.1 plan): probe only after the bed has soaked at temperature",
        "[gcode_macro START_PRINT]", "gcode:",
        "    {% set BED = params.BED|default(60)|float %}", "    {% set SOAK = params.SOAK|default(" + f"{SOAK_S:.0f}" + ")|int %}",
        "    M190 S{BED}", "    G4 P{SOAK * 1000}", "    G28", "    Z_TILT_ADJUST", "    BED_MESH_CALIBRATE", "",
        "[gcode_macro LASER_CAPTURE]", "gcode:", "    SET_PIN PIN=lights VALUE=0.1", "    SET_PIN PIN=nozzle_laser VALUE=1", "    G4 P2000",
        "    SET_PIN PIN=nozzle_laser VALUE=0", "    SET_PIN PIN=lights VALUE=0.5",
    ]


# ---- limit (b) after a heat soak (owner, v11.1 plan) ----------------------------------------------------------------------------
# Lumped first-order warming of the parts under the plate, driven by the plate at temperature (textbook figures, ESTIMATES):
#  carrier (2020 square + deck, ~1.15 kg of 6061, c 896 J/kg K) exchanging with the plate across the 16.8 mm gap by radiation and
#  convection (h ~ 6 W/m2K over the deck's 0.073 m2) and losing to the room by convection (h ~ 5 W/m2K over ~0.25 m2):
#  tau = m c / (G_in + G_out); the studs (M4 stacks, conducted from the plate) follow the plate with a tau of minutes.
CARRIER_TAU_S = 1.15 * 896.0 / (6.0 * 0.073 + 5.0 * 0.25)        # about 610 s
STUD_TAU_S = 240.0
SOAK_S = 3.0 * CARRIER_TAU_S                                      # the soak: 3 time constants of the carrier (95 % of its rise)


def add_soak_case(d, zs, posts, carrier, zcars, nplates, on_rail, on_nut):
    """The warming that is LEFT after the soak, as a ThermalCase (FEA is linear in temperature): bed and sheet at their final
    temperature already (0 K more), studs and carrier the remainder of their rise, exp(-t / tau)."""
    rem_c, rem_s = 15.0 * math.exp(-SOAK_S / CARRIER_TAU_S), 30.0 * math.exp(-SOAK_S / STUD_TAU_S)
    d.thermalcases.append(ThermalCase(
        "bed_after_soak", ["bed_plate", "bed_magnet", "bed", *posts, *carrier, *zcars, *nplates],
        fixed=[(c, on_rail[c]) for c in zcars] + [(nb, on_nut) for nb in nplates],
        temps={**{c: rem_c for c in carrier}, "bed_magnet": 0.0, "bed_plate": 0.0, "bed": 0.0, **{c: rem_s for c in posts}, "*": 0.0},
        probes={"nozzle": (UP_R_X, Y_FACE - 8.0, ZC), "bed": (BED_CX, YB0 + HOT_OFF, Z_SURF - T_SHEET)},
        gaps={"nozzle gap": ("nozzle", "bed", "z", FLAT_AFTER_PROBING)}, flatness=("bed_plate", "z", FLAT_AFTER_PROBING)))


# ---- feedback hardware on the frame (stage 3) ------------------------------------------------------------------------------------
def add_feedback_hardware(d):
    """Overview and top-down Pi Camera Module 3s on printed brackets on the top front / back rails, the BTT SFS V2 on the left top rail,
    the overview COB strip in two printed clips on the top front rail. The nozzle camera, its lens, the line laser, the two nozzle LED
    segments and the toolhead ADXL345 are BOM lines in v12: their toolhead bracket is not drawn
    (open item: the Eddy fills the rear view; docs/PRINTER_V12.md)."""
    W2 = WASHER["normal"]["M2"][2] if "M2" in WASHER["normal"] else 0.3
    def t_screw(nm, x, y, z, ext, L=10, d_=(0, 0, -1), clamps=()):
        add_screw(d, nm, "M3", L, at=(x, y, z), direction=d_, threads_into=ext, tnut=True, washer=True, clamps=clamps)
    # cameras: a printed block on the rail's top (two M3 x 25 into T-nuts, 16 mm either side of the camera), the camera on its two lower
    # holes by M2 x 20 through the block (14 mm), washers and nuts behind
    # overview camera: a printed stand on the top front rail's top (two M3 x 10 into T-nuts), the camera on its two lower holes by M2 x 20
    x0, y0, zt = 0.0, FRONT_Y, FZ + 10.0
    zh = zt + 23.0
    blk = bx(x0 - 22.0, x0 + 22.0, y0 - 7.0, y0 + 7.0, zt, zt + 6.0) + bx(x0 - 12.5, x0 + 12.5, y0 - 7.0, y0 + 7.0, zt + 6.0, zt + 30.0)
    blk -= zc(x0 - 16.0, y0, zt, zt + 6.0, PH3 / 2) + zc(x0 + 16.0, y0, zt, zt + 6.0, PH3 / 2)
    for xh in (-10.5, 10.5):
        blk -= Pos(x0 + xh, y0, zh) * ycyl(2.4 / 2, 14.0)
    d.add("cam_overview_mount", blk, material=COOL, process="printed", meta={"print_up": "+Z", "print": {**PRINT_ABS, "orientation": "+Z", "infill": 0.4},
                                                                         "description": "printed stand for the overview camera on the top front rail"})
    for i, xh in enumerate((-16.0, 16.0)):
        t_screw(f"cam_overview_mount_screw_{i}", x0 + xh, y0, zt + 6.0, "frame_top_front", L=10, clamps=("cam_overview_mount",))
    yc = y0 + 7.0
    place(d, "cam_overview", picam3(), Location(Plane(origin=(x0, yc, zh - 9.931), x_dir=(1, 0, 0), z_dir=(0, 1, 0))))
    for i, xh in enumerate((-10.5, 10.5)):
        bolt_nut(d, f"cam_overview_screw_{i}", "M2", 20, (x0 + xh, y0 - 7.0, zh), (0, 1, 0), "world", ("cam_overview_mount", "cam_overview"),
                 nut_at=(x0 + xh, yc + 1.0, zh))
    # top-down camera and filament sensor: printed brackets on the top back rail's REAR face (y 180), behind the toolhead's reach at the
    # rear end of Y (the blower passes over the rail's top there); each by two M3 x 10 into T-nuts in the rail's rear slot
    yb = FY / 2                                          # the rail's rear face
    for nm, xb in (("cam_topdown", -60.0), ("sfs", 30.0)):
        br = bx(xb - 22.0, xb + 22.0, yb, yb + 6.0, FZ - 9.0, FZ + 9.0)
        br -= Pos(xb - 16.0, yb + 3.0, FZ) * ycyl(PH3 / 2, 6.0) + Pos(xb + 16.0, yb + 3.0, FZ) * ycyl(PH3 / 2, 6.0)
        if nm == "sfs":              # a pad between the screws that the sensor sits on
            br += bx(xb - 10.0, xb + 10.0, yb + 6.0, yb + 10.0, FZ - 9.0, FZ + 9.0)
        if nm == "cam_topdown":      # a ledge back from the plate and a column carrying the camera above the rail, lens towards the bed
            br += bx(xb - 12.5, xb + 12.5, yb + 6.0, yb + 20.0, FZ + 5.0, FZ + 9.0) + bx(xb - 12.5, xb + 12.5, yb + 14.0, yb + 20.0, FZ + 9.0, FZ + 44.0)
            for xh in (-10.5, 10.5):
                br -= Pos(xb + xh, yb + 17.0, FZ + 30.0) * ycyl(2.4 / 2, 6.0)
        d.add(f"{nm}_mount", br, material=COOL, process="printed", meta={"print_up": "+Z", "print": {**PRINT_ABS, "orientation": "+Z", "infill": 0.4}})
        for i, xh in enumerate((-16.0, 16.0)):
            add_screw(d, f"{nm}_mount_screw_{i}", "M3", 10, at=(xb + xh, yb + 6.0, FZ), direction=(0, -1, 0), threads_into="frame_top_back", tnut=True,
                      washer=True, clamps=(f"{nm}_mount",))
    yc = yb + 14.0
    place(d, "cam_topdown", picam3(), Location(Plane(origin=(-60.0, yc, FZ + 30.0 + 9.931), x_dir=(1, 0, 0), z_dir=(0, -1, 0))))
    for i, xh in enumerate((-10.5, 10.5)):
        bolt_nut(d, f"cam_topdown_screw_{i}", "M2", 20, (-60.0 + xh, yb + 20.0, FZ + 30.0), (0, -1, 0), "world", ("cam_topdown_mount", "cam_topdown"),
                 nut_at=(-60.0 + xh, yc - 1.0, FZ + 30.0))
    place(d, "filament_sensor", sfs_v2(), Location((30.0, yb + 10.0 + 14.0, FZ)))
    d.join("filament_sensor", "sfs_mount", "two cable ties round the sensor and the bracket's plate (its own holes face the spool)")
    # overview COB strip in two printed clips on the top front rail's inner face: the clip's plate on the face (screw at the slot), the
    # strip in a channel in front of it below the screw head
    yi = FRONT_Y + 10.0
    zl = FZ - 10.0
    place(d, "led_overview", cob_led(150.0), Location(Plane(origin=(0.0, yi + 3.0, zl), x_dir=(1, 0, 0), z_dir=(0, 1, 0))))
    for i, xc in enumerate((-60.0, 60.0)):
        clip = (bx(xc - 6.0, xc + 6.0, yi, yi + 3.0, FZ - 16.0, FZ + 6.0) + bx(xc - 6.0, xc + 6.0, yi + 3.0, yi + 6.0, FZ - 16.0, FZ - 14.0)
                + bx(xc - 6.0, xc + 6.0, yi + 3.0, yi + 6.0, FZ - 6.0, FZ - 4.0))
        clip -= Pos(xc, yi + 1.5, FZ) * ycyl(PH3 / 2, 3.0)
        d.add(f"led_clip_{i}", clip, material=COOL, process="printed", meta={"print_up": "-Y", "print": {**PRINT_ABS, "orientation": "-Y"}})
        add_screw(d, f"led_clip_{i}_screw", "M3", 8, at=(xc, yi + 3.0, FZ), direction=(0, -1, 0), threads_into="frame_top_front", tnut=True,
                  washer=True, clamps=(f"led_clip_{i}",))
        d.join("led_overview", f"led_clip_{i}", "held in the clip's channel")


STAGE_RULES = [  # (stage, name prefixes): first match wins; screws, nuts, washers and T-nuts are named after what they fix
    (3, ("cam_", "led_", "sfs_", "filament_sensor", "adxl", "sensor_plate")),
    (2, ("y_", "x_", "tool_", "extruder", "hotend", "part_", "beam_bolt", "bed_probe", "eddy", "probe_mount")),
    (1, ("frame_", "post_", "bracket_", "brkt_up_", "upright_", "z_", "sq_", "carriage_plate", "nut_", "bed", "leadscrew", "electronics",
         "psu", "control_board", "host", "inlet", "mains_", "earth", "tray", "din_", "iface_", "z_mount")),
]


def tag_stages(d):
    """meta["build_stage"] on every part (staged Build 1). Unmatched parts are stage 2 and listed in d.meta_stage_unmatched."""
    miss = []
    for c in d.components:
        n = c.name
        st = next((k for k, pre in STAGE_RULES if n.startswith(pre)), None)
        if st is None:
            st = 2
            miss.append(n)
        c.meta["build_stage"] = st
    d.stage_unmatched = miss
    for sku, e in d.bom_extras.items():
        if e.get("stage") is None:
            e["stage"] = 2 if any(w in sku for w in ("BELT", "SOCK", "TMC2209", "USB")) else 1
