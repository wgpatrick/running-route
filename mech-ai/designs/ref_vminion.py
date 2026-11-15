"""ref_vminion: the Rat Rig V-Minion, modelled from published data to measure the harness's false-alarm rate.

NOT a mechloop design. It is a model of a machine that exists and works, built to be judged by the 12 verifiers and
the twin. Nothing here was tuned to make a check pass. See docs/REFERENCE_MACHINE.md for sources, licences, every
simplification and substitution, and the classification of every finding.

Machine: Rat Rig V-Minion (180 x 180 x 180 mm cartesian bed-slinger, cantilevered X arm on one Z column, linear rails
on all axes, one T8x4 lead screw, EVA toolhead with direct drive). Design CC BY-NC-SA 4.0 (Rat Rig); no Rat Rig CAD
file is in this repository: the geometry below is re-drawn from the BOM, the dimension drawings, the bounding boxes of
the published printed-part STEP files and the RatOS configuration.

Layout (X = width, column on the -X side; Y = depth, +Y is the back; Z = up; z = 0 is the underside of the frame,
the 16.5 mm rubber feet are not drawn):
  y_base   3060 x 270 along Y, 60 tall, the bed's rail on its top face
  link     3060 x 115 along X between column and y_base
  column   3060 x 345 standing beside the link, the Z rail on its REAR face
  X arm    2020 x 362 behind the column on a 4 mm plate on the Z block; X rail on top of it; toolhead hangs in front
Joints: y = bed on the base (world -> ybody), z = arm on the column (world -> zbody), x = toolhead on the arm
(zbody -> xbody). Home pose: toolhead and bed centred, arm at the TOP of its travel (z joint = 0); the Z joint runs
downward and z = 180 is the nozzle 0.1 mm above the print surface (the harness's convention: see the toolhead constants).

SUBSTITUTIONS (catalogue part used for a part the catalogue lacks) and SIMPLIFICATIONS are listed in the doc; the
flags S1.. in the comments below refer to that list.
"""
import math

from build123d import Box, Cylinder, Location, Plane, Pos, RectangleRounded, Rot, extrude

from mechloop import Adjustment, AssemblyCase, Design, Joint, LoadCase, Requirement
from mechloop.electrical import Bay, Electrical, Waypoint
from mechloop.model import Belt, ThermalCase
from mechloop.parts import (Stock, add_corner_bracket, add_nut, add_screw, bearing, clearance_hole, endstop_switch,
                            extruder_direct, extrusion_2020, fan, gt2_idler, gt2_pulley, leadscrew_nut_t8,
                            leadscrew_t8, mgn12_rail, mgn12h_carriage, nema17, place, shaft_coupler)
from mechloop.parts.electrical import (THERMISTORS, add_electrical_bom, bed_heater_pad, device_from, embedded_device,
                                       heater_cartridge, iec_inlet_c14, psu_lrs, raspberry_pi_zero2w, skr_mini_e3_v3,
                                       thermal_fuse, thermistor_cartridge)
from mechloop.parts.hardware import spacer_round
from mechloop.parts.probes import add_probe_nuts, probe_omron_e2e
from mechloop.parts.toolhead import hotend_v6

# ---- published figures -------------------------------------------------------------
PRINT = 180.0                 # 180 x 180 x 180 mm (Rat Rig; RatOS position_max 180 on all three axes)
V_XY, A_XY = 200.0, 3000.0    # RatOS v-minion speed-limits-basic.cfg: max_velocity 200, max_accel 3000
V_Z, A_Z = 15.0, 200.0        # same file: max_z_velocity 15, max_z_accel 200
RUN_CURRENT = {"x": 0.8, "y": 0.8, "z": 0.8, "extruder": 0.5}   # RatOS printer-definition.json rails (0.8 A), tmc2209.cfg (0.5 A)
PROBE_OFF = (-27.8, -12.0)    # RatOS z-probe/probe.cfg x_offset, y_offset
BED_SCREWS = [(-37.8, 6.0), (37.2, -30.0), (37.2, 45.0)]   # RatOS screws_tilt_adjust minus the probe offset, from the bed centre
Z_BELOW = 5.0                 # RatOS stepper_z position_min -5 ("needed for z-offset calibration and tilt_adjust")
BED = 184.0                   # flex plate 184 x 184 (BOM); the cast plate is drawn the same size (not published)
T_BED, T_FLEX = 5.0, 0.8      # 5 mm cast tooling plate (BOM); spring-steel sheet thickness assumed
T_SUB, T_XP = 4.0, 4.0        # sub_plate and x_plate: 4 mm (BOM)
H_STANDOFF = 12.0             # stainless spacers 12 mm (BOM)
PETG = "petg"                 # machine.json: every printed part PETG

# ---- frame -------------------------------------------------------------------------
BASE_L, LINK_L, COL_L, BEAM_L = 270.0, 115.0, 345.0, 362.0     # BOM cut lengths
COL_X = -15.0 - LINK_L - 30.0          # column centre line, x = -160
YC = -10.0                             # column / link centre plane in Y
Y_COLR = YC + 15.0                     # column rear face: the Z rail's seat
Z_TOP = 60.0                           # top of the base
BY = Y_COLR + 13.0 + T_XP + 10.0       # X beam centre line in Y: 32
BEAM_X0, BEAM_X1 = -226.0, 136.0       # beam ends (from the front-view drawing)
RAIL_L = 250.0                         # all three rails (BOM)
# ---- bed stack ---------------------------------------------------------------------
Z_YCAR = Z_TOP + 13.0                  # Y block top (MGN12H: 13; the real MGN15H is 16)
Z_SUB = Z_YCAR + T_SUB
Z_BED0 = Z_SUB + H_STANDOFF            # underside of the cast plate
Z_BEDTOP = Z_BED0 + T_BED + T_FLEX     # print surface
SUB_X, SUB_Y = 50.0, (-40.0, 55.0)     # sub_plate outline (not published; it carries the three bed screws)
# ---- toolhead ----------------------------------------------------------------------
GAP = 0.1
# HOME POSE: arm at the TOP of its working travel. The harness's convention for a printer's Z joint is that the high end
# of `range` is where nozzle and print surface meet (firmware Z = range[1] - q), so the joint runs DOWN: axis (0, 0, -1)
Z_NOZ = Z_BEDTOP + GAP + PRINT
HOT_TOP = Z_NOZ + 62.55                # top of the V6's groove mount
ZB = HOT_TOP - 31.0                    # X beam centre height at home: the carriage slab's top is the hotend's top
Z_SLAB0, Z_SLAB1 = ZB + 23.0, ZB + 31.0   # printed carriage slab on the X block (block top = beam top + 13)
PRB_FACE = 2.0                         # probe sensing face above the nozzle tip (not published)
Z_PRB = Z_NOZ + PRB_FACE
PRB_CLAMP = (16.0, 22.0)
# ---- drives ------------------------------------------------------------------------
PR = 20 * 2.0 / math.pi / 2            # pitch radius, 20T
XB_Y = BY + 10.0 + 7.0                 # X belt plane: behind the beam
XM_X, XI_X = -205.0, 126.0             # X motor and idler axes
YB_X = 28.0                            # Y belt plane: beside the base, on the side away from the link
YM_Y, YI_Y, YM_Z = 172.0, -147.0, 51.0   # the motor's top is just under the sub plate, as in the side-view drawing
ES_OT = 1.5                            # homing over-travel past the nominal switch point (see the endstop notes)
# ---- Z drive -----------------------------------------------------------------------
LS = (COL_X, 58.0)                     # lead screw axis (behind the arm; from the side-view drawing)
Z_MF = 52.0                            # Z motor face
Z_CPL = Z_MF + 11.5                    # coupler bottom
LS_IN = 8.0
Z_LS0 = Z_CPL + 25.0 - LS_IN
NB_Z0, NB_Z1 = ZB - 24.0, ZB - 10.0    # nut block under the beam
ZC = ZB - 24.0                         # Z block centre: below the beam, so the plate's screw heads clear it
Z_ZRAIL0 = 70.0                        # Z rail 70 .. 320 on the column
# ---- electronics case (free-standing box, 260 x 162 x 90 mm; upright beside the column) ------
CX0, CX1 = -345.0, -255.0
CY0, CY1 = -130.0, 130.0
CZ1 = 162.0
T_PAN = 4.0


def bx(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def cyl_x(x0, x1, y, z, r):
    return Pos((x0 + x1) / 2, y, z) * Rot(0, 90, 0) * Cylinder(r, x1 - x0)


def cyl_y(x, y0, y1, z, r):
    return Pos(x, (y0 + y1) / 2, z) * Rot(90, 0, 0) * Cylinder(r, y1 - y0)


def cyl_z(x, y, z0, z1, r):
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(r, z1 - z0)


def ext3060(length: float) -> Stock:
    """S1. Hand-made proxy for Rat Rig's 3060 T-slot (the catalogue has 2020 only). Local frame: along X, 60 along Y,
    30 along Z, centred. Drawn as a 30 x 60 box tube with 3 mm walls, a centre web and two solid cores for the end
    taps: that section has I = 2.3e5 / 7.5e4 mm^4, close to what twice a 3030's published 2.9e4..3.3e4 (weak axis)
    suggests. Mass 1.95 kg/m is an estimate. Only the slot mouths are drawn (1.2 mm deep): T-nut screws are declared with tnut=True."""
    sec = Box(length, 60, 30) - Box(length, 54, 24)
    sec += Box(length, 3, 24)
    for y in (-15.0, 15.0):
        sec += Pos(0, y, 0) * Rot(0, 90, 0) * Cylinder(6.0, length)
        sec -= Pos(0, y, 0) * Rot(0, 90, 0) * Cylinder(3.4, length)        # M8 tap drill 6.8
        for z in (-15.0, 15.0):                                             # slot mouths (1.2 deep: what the cast brackets' tabs sit in)
            sec -= Pos(0, y, z) * Box(length, 8.2, 2.4)
    for y in (-30.0, 30.0):
        sec -= Pos(0, y, 0) * Box(length, 2.4, 8.2)
    return Stock(sec, f"EXT3060-{int(length)}", f"3060 T-slot extrusion, {length:.0f} mm (hand-made proxy)", 1.95 * length / 1000,
                 material="al6061", interfaces={"slot_width": 8.2, "end_tap": "M8"}, cost_usd=5 + 0.03 * length)


def flex_plate() -> Stock:
    """S2. Powder-coated PEI spring-steel sheet 184 x 184 (BOM HW2770GC). Hand-made proxy; thickness assumed 0.8 mm;
    the magnetic sticker under it is not drawn."""
    return Stock(Pos(0, 0, T_FLEX / 2) * Box(BED, BED, T_FLEX), "FLEXPLATE-PEI-184", "PEI spring-steel flex plate 184 x 184 (hand-made proxy)",
                 BED * BED * T_FLEX * 7.85e-6, material="steel", cost_usd=20.0)


# =====================================================================================
def build_electrical(d: Design) -> Electrical:
    """Stock wiring of the full kit (Rat Rig wiring diagrams): mains inlet -> supply -> board; no mains relay, no
    hotend cut-off, no earth wire to the frame (the BOM has one 200 mm earth wire: inlet to supply). The bed heater has
    a thermal fuse built in (Keenovo, BOM)."""
    el = Electrical(supply_v=24.0, mains_v=(115.0, 230.0))
    d.electrical = el
    for nm in ("control_board", "psu", "inlet", "host", "hotend_heater", "hotend_thermistor", "hotend_fan", "part_fan",
               "case_fan", "x_endstop", "y_endstop", "bed_probe", "x_motor", "y_motor", "z_motor", "extruder", "bed_tco"):
        device_from(el, d, nm)
    device_from(el, d, "bed_heater", plate="bed_plate")
    embedded_device(el, d, "bed_heater", "bed_ntc", "thermistor", "ntc", "thermistor", ratings={"max_temp_c": 180.0},
                    sources={"points": "Klipper 'Generic 3950' (Keenovo R-T table)", "tau_s": "assumed 10 s (typical, unverified)"},
                    sensor_type="Generic 3950", points=THERMISTORS["Generic 3950"], tau_s=10.0, node="pad")
    # ---- looms. The case stands beside the column; sleeved bundles leave it through the vent slots of its front end
    # and run to the foot of the column (BOM: 900 mm of 9.5 mm sleeve). The bed's leads have their own sleeve.
    zc = ZB + 22.0
    F = (COL_X - 33.0, YC, 28.0)                   # foot of the column, left face
    C = (COL_X - 31.5, YC, 220.0)                  # clamp on the column's left face, mid height
    BW = (-17.5, 40.0, 30.0)                       # clamp on the base's -X face
    el.loom("trunk", [("world", (-270.0, 60.0, 60.0)), ("world", (-280.0, -100.0, 60.0)), ("world", (-280.0, -150.0, 60.0)),
                      ("world", (-240.0, -160.0, 25.0)), ("world", (-200.0, -90.0, 25.0)), ("world", F)])
    el.loom("column", [("world", F), ("world", (COL_X - 31.5, YC, 70.0)), ("world", C)])
    # arm loom: tied to the X motor cage, hangs from the column (Z travel 180)
    el.loom("arm", [Waypoint("zbody", (BEAM_X0 - 10.0, 59.5, zc), clamp="x_motor_cage"),
                    Waypoint("world", C, clamp="column")], flex_length={0: 230.0})
    # toolhead loom: from the top of the extruder to the X motor cage (X travel 180)
    el.loom("toolhead", [Waypoint("xbody", (0.0, 10.0, Z_SLAB1 + 37.5), clamp="extruder"),
                         Waypoint("zbody", (BEAM_X0 - 10.0, 59.5, zc), clamp="x_motor_cage")], flex_length={0: 420.0})
    el.loom("zmot", [("world", F), ("world", (COL_X - 33.0, 40.0, 20.0)), ("world", (COL_X - 30.0, 80.0, 30.0))])
    # round the back of the column under the Z motor bracket, along the link's rear face, along the base's -X face
    el.loom("base", [("world", F), ("world", (COL_X - 33.0, 30.0, 4.0)), ("world", (-125.0, 30.0, 4.0)), ("world", (-100.0, 10.0, 30.0)),
                     ("world", (-45.0, 10.0, 30.0)), ("world", (-26.0, 22.0, 30.0)), ("world", BW)])
    el.loom("base_rear", [("world", BW), ("world", (-19.0, 125.0, 30.0)), ("world", (-22.0, 150.0, 14.0)), ("world", (0.0, 200.0, 10.0)),
                          ("world", (30.0, 190.0, 30.0))])
    el.loom("bed_trunk", [("world", (-270.0, 40.0, 80.0)), ("world", (-290.0, -100.0, 80.0)), ("world", (-290.0, -150.0, 80.0)),
                          ("world", (-240.0, -175.0, 30.0)), ("world", (-150.0, -120.0, 30.0)), ("world", (-60.0, -60.0, 30.0)),
                          ("world", (-26.0, -30.0, 30.0)), ("world", (-21.0, 10.0, 30.0)), ("world", BW)])
    # bed loom: from the sub plate to the side of the base (Y travel 180)
    el.loom("bed", [Waypoint("ybody", (-30.0, 40.0, Z_YCAR - 1.5), clamp="sub_plate"),
                    Waypoint("world", BW, clamp="y_base")], flex_length={0: 190.0})
    tool, arm = ["trunk", "column", "arm", "toolhead"], ["trunk", "column", "arm"]
    # ---- mains (BOM: 18 AWG brown / blue / green-yellow)
    mk = dict(conductors=1, insulation="pvc105")
    el.wire("mains L", "inlet.L", "psu.L", 18, **mk)
    el.wire("mains N", "inlet.N", "psu.N", 18, **mk)
    el.wire("earth to supply", "inlet.PE", "psu.FG", 18, **mk)
    # ---- 24 V (BOM: 15 AWG red / black, 250 mm; 16 is the nearest gauge the wire table has)
    el.wire("24 V to board", "psu.V+1", "control_board.POWER", 16, insulation="silicone")
    el.wire("bed heater", "control_board.HB", "bed_tco.a", 16, insulation="silicone", via=["bed_trunk", "bed"])
    el.wire("bed heater tail", "bed_tco.b", "bed_heater.in", 16, insulation="silicone", length=60.0)
    el.wire("bed thermistor", "control_board.THB", "bed_ntc.out", 26, insulation="silicone", via=["bed_trunk", "bed"])
    el.wire("hotend heater", "control_board.E0", "hotend_heater.in", 20, insulation="silicone", via=tool, pigtail=(150.0, "fiberglass"))
    el.wire("hotend thermistor", "control_board.TH0", "hotend_thermistor.out", 26, insulation="silicone", via=tool, pigtail=(150.0, "fiberglass"))
    el.wire("heat-sink fan", "control_board.FAN1", "hotend_fan.in", 26, via=tool)
    el.wire("part fan", "control_board.FAN0", "part_fan.in", 26, via=tool)
    el.wire("case fan", "control_board.FAN2", "case_fan.in", 26)
    el.wire("bed probe", "control_board.Z-STOP", "bed_probe.out", 26, conductors=3, via=tool)
    # S3: the catalogue sensor is a 10-30 V part, the real one is a 5 V part on the board's probe header
    el.devices["bed_probe"].params.update(supply_v=24.0, supply_from="24 V rail at the control board's power terminals")
    el.wire("extruder motor", "control_board.EM", "extruder.coils", 24, conductors=4, via=tool)
    el.wire("X endstop", "control_board.X-STOP", "x_endstop.out", 26, conductors=3, via=tool)
    el.wire("X motor", "control_board.XM", "x_motor.coils", 24, conductors=4, via=arm)
    el.wire("Y motor", "control_board.YM", "y_motor.coils", 24, conductors=4, via=["trunk", "base", "base_rear"])
    el.wire("Y endstop", "control_board.Y-STOP", "y_endstop.out", 26, conductors=3, via=["trunk", "base", "base_rear"])
    el.wire("Z motor", "control_board.ZAM", "z_motor.coils", 24, conductors=4, via=["trunk", "zmot"])
    el.wire("host serial + 5 V", "control_board.TFT", "host.GPIO", 26, conductors=4)
    el.firmware = {
        "kind": "klipper",
        "steppers": {"x": {"run_current": RUN_CURRENT["x"]}, "y": {"run_current": RUN_CURRENT["y"]},
                     "z": {"run_current": RUN_CURRENT["z"]},
                     "extruder": {"motors": ["extruder"], "run_current": RUN_CURRENT["extruder"], "rotation_distance": 5.7}},
        "heaters": {"extruder": {"heater": "hotend_heater", "sensor": "hotend_thermistor", "control": "pid", "min_temp": 0,
                                 "max_temp": 285, "targets": [250.0], "verify_heater": {}},
                    "heater_bed": {"heater": "bed_heater", "sensor": "bed_ntc", "control": "pid", "min_temp": 0,
                                   "max_temp": 130, "targets": [60.0, 100.0], "verify_heater": {}}},   # RatOS: max_temp 130
        "fans": {"part_fan": {"device": "part_fan", "role": "part"}, "hotend_fan": {"device": "hotend_fan", "role": "heatsink"}},
    }
    hb = d.get("hotend").meta["interfaces"]["heater_block_box"]
    el.hot_parts = {"hotend": {"temp": 250.0, "box": (*hb[0], *hb[1])}, "bed": 100.0}
    # the case: closed box 260 x 162 x 90 with one 40 mm fan (about 10 m^3/h at free air, typical) and slotted ends
    el.bay = Bay(devices=["psu", "control_board", "host"], enclosed=True, surface_m2=2 * (0.26 * 0.162 + 0.26 * 0.09 + 0.162 * 0.09),
                 vent_area_m2=0.0012, height_m=0.16, fan_m3h=10.0)
    el.sync_cables(d)
    add_electrical_bom(el, d)
    d.bom_extra("FUSE-5x20-T5A", 1, 0.3)
    return el


# =====================================================================================
def build() -> Design:
    d = Design("ref_vminion", envelope=(530.0, 400.0, 420.0), base="y_base")
    d.manufacturing = {"shop": "generic", "sheet": {"method": "laser"}, "printer": {"build_volume": (220.0, 220.0, 220.0), "nozzle": 0.4}}
    ext_meta = dict(process="extrusion")

    # ================= frame =====================================================
    place(d, "y_base", ext3060(BASE_L), Location(Plane(origin=(0, 0, 30), x_dir=(0, 1, 0), z_dir=(1, 0, 0))), **ext_meta)      # along Y, 60 tall
    place(d, "link", ext3060(LINK_L), Location(Plane(origin=(-15.0 - LINK_L / 2, YC, 30), x_dir=(1, 0, 0), z_dir=(0, -1, 0))), **ext_meta)  # along X, 60 tall
    place(d, "column", ext3060(COL_L), Location(Plane(origin=(COL_X, YC, COL_L / 2), x_dir=(0, 0, 1), z_dir=(0, 1, 0))), **ext_meta)
    # joining plate on the front faces of column and link ("Joining Plate for 3030 - 90 Degree"): 4 mm, M6 x 12 in T-nuts
    yf = YC - 15.0
    jp = bx(COL_X - 30, COL_X + 30, yf - 4, yf, 0, 120) + bx(COL_X + 30, -40.0, yf - 4, yf, 0, 60)
    JP_HOLES = [(COL_X - 15, 30.0), (COL_X + 15, 30.0), (COL_X - 15, 90.0), (COL_X + 15, 90.0), (-100.0, 15.0), (-100.0, 45.0), (-60.0, 15.0), (-60.0, 45.0)]
    for x, z in JP_HOLES:
        jp -= cyl_y(x, yf - 4, yf, z, clearance_hole("M6") / 2)
    d.add("join_plate_front", jp, material="al6061", process="sheet")
    for i, (x, z) in enumerate(JP_HOLES):
        add_screw(d, f"join_plate_screw_{i}", "M6", 12, at=(x, yf - 4, z), direction=(0, 1, 0),
                  threads_into="column" if x < COL_X + 30 else "link", clamps=("join_plate_front",), tnut=True)
    # T plate under the link / base joint ("Joining Plate for 3030 - T")
    tp = bx(-75.0, 15.0, YC - 15, YC + 15, -4, 0) + bx(-15.0, 15.0, YC - 50, YC + 50, -4, 0)
    TP_HOLES = [(-60.0, YC, "link"), (-35.0, YC, "link"), (0.0, YC - 35, "y_base"), (0.0, YC + 35, "y_base")]
    for x, y, _ in TP_HOLES:
        tp -= cyl_z(x, y, -4, 0, clearance_hole("M6") / 2)
    d.add("join_plate_t", tp, material="al6061", process="sheet")
    for i, (x, y, into) in enumerate(TP_HOLES):
        add_screw(d, f"t_plate_screw_{i}", "M6", 12, at=(x, y, -4.0), direction=(0, 0, 1), threads_into=into,
                  clamps=("join_plate_t",), tnut=True)
    # cast corner brackets (BOM: 5). S4: the catalogue's bracket is the 2020 size (17 wide); the real ones are 3030 castings
    add_corner_bracket(d, "bracket_col", "link", "column", (COL_X + 30, YC, Z_TOP), (1, 0, 0), (0, 0, 1))
    for i, (sy, z) in enumerate([(-1, 15.0), (-1, 45.0), (1, 15.0), (1, 45.0)]):
        add_corner_bracket(d, f"bracket_base_{i}", "link", "y_base", (-15.0, YC + sy * 15.0, z), (-1, 0, 0), (0, sy, 0))

    # ================= Y axis: the bed ===========================================
    # S5: MGN12 rail and MGN12H block stand in for the MGN15 rail and MGN15H block (catalogue has MGN12 only)
    yr = place(d, "y_rail", mgn12_rail(RAIL_L), Location((0, 0, Z_TOP), (0, 0, 90)))
    seat = yr.meta["interfaces"]["screw_seat_z"]
    yholes = yr.meta["interfaces"]["mount_holes_m3"]
    for i in (0, 2, 4, 5, 7, 9):       # six of the ten holes: the real MGN15 rail has six holes at 40 mm pitch
        hx, hy, _ = yholes[i]
        add_screw(d, f"y_rail_screw_{i}", "M3", 8, at=(hx, hy, Z_TOP + seat), threads_into="y_base", clamps=("y_rail",), tnut=True)
    ycar = place(d, "y_carriage", mgn12h_carriage(), Location((0, 0, Z_TOP), (0, 0, 90)), body="ybody", guides="y")
    sub = bx(-SUB_X, SUB_X, SUB_Y[0], SUB_Y[1], Z_YCAR, Z_SUB)
    for hx, hy, _ in ycar.meta["interfaces"]["mount_holes_m3"]:
        sub -= cyl_z(hx, hy, Z_YCAR, Z_SUB, clearance_hole("M3") / 2)
    for x, y in BED_SCREWS:
        sub -= cyl_z(x, y, Z_YCAR, Z_SUB, clearance_hole("M4") / 2)
    BM_SCREWS = [(37.0, -12.0), (37.0, 25.0)]
    for x, y in BM_SCREWS:
        sub -= cyl_z(x, y, Z_YCAR, Z_SUB, clearance_hole("M3") / 2)
    d.add("sub_plate", sub, material="al6061", body="ybody", process="sheet")
    for i, (hx, hy, _) in enumerate(ycar.meta["interfaces"]["mount_holes_m3"]):
        # M3 x 8 through the 4 mm plate (BOM: 36 x M3 x 8). The real MGN15H block's threads are 4 mm deep, the stand-in's 3.5
        add_screw(d, f"sub_plate_screw_{i}", "M3", 8, at=(hx, hy, Z_SUB), body="ybody", threads_into="y_carriage", clamps=("sub_plate",))
    # bed: 5 mm cast plate on three 12 mm stainless spacers, M4 x 30 countersunk from the top, locknut under the sub plate
    # (drawn M4 x 25: with the head sunk 4.2 mm and the stack 3 mm lower than the real one, a 30 would reach the link).
    # S6: the catalogue has cap screws only, so each head sits in a counterbore instead of a countersink
    CB = 4.2
    bed = bx(-BED / 2, BED / 2, -BED / 2, BED / 2, Z_BED0, Z_BED0 + T_BED)
    for x, y in BED_SCREWS:
        bed -= cyl_z(x, y, Z_BED0, Z_BED0 + T_BED, clearance_hole("M4") / 2)
        bed -= cyl_z(x, y, Z_BED0 + T_BED - CB, Z_BED0 + T_BED, 3.8)
    d.add("bed_plate", bed, material="al_mic6", body="ybody", process="machined")
    place(d, "bed", flex_plate(), Location((0, 0, Z_BED0 + T_BED)), body="ybody")
    d.join("bed", "bed_plate", "magnet")
    for i, (x, y) in enumerate(BED_SCREWS):
        place(d, f"bed_standoff_{i}", spacer_round("M4", H_STANDOFF, "aluminium"), Location((x, y, Z_SUB)), body="ybody")   # S7: stainless in the BOM
        add_screw(d, f"bed_screw_{i}", "M4", 25, at=(x, y, Z_BED0 + T_BED - CB), body="ybody",
                  clamps=("bed_plate", f"bed_standoff_{i}", "sub_plate"))
        add_nut(d, f"bed_nut_{i}", "M4", at=(x, y, Z_YCAR), direction=(0, 0, -1), body="ybody", screw=f"bed_screw_{i}")
    # heater: Keenovo 160 x 160 mm 24 V 180 W pad with NTC and thermal fuse (BOM). S8: the real pad is cut out round the
    # three bed screws; the catalogue pad is a plain rectangle, so it overlaps the three spacers by declaration
    place(d, "bed_heater", bed_heater_pad(160.0, 160.0, 180.0), Location((0, 0, Z_BED0), (0, 0, 180)), body="ybody")
    d.join("bed_heater", "bed_plate", "adhesive")
    for i in range(3):
        d.allow_overlap("bed_heater", f"bed_standoff_{i}")
        d.allow_overlap("bed_heater", f"bed_screw_{i}")
    place(d, "bed_tco", thermal_fuse(133.0, 109.0, 10.0), Location((-20.0, 60.0, Z_BED0 - 3.5)), body="ybody")
    d.join("bed_tco", "bed_heater", "bonded in the pad (built in)")
    # Y belt mount under the sub plate (real: y_belt_mount 27 x 54 x 22); also the Y endstop's striker
    BMX0, BMX1, BMY0, BMY1, BMZ0 = 22.5, 41.0, -20.0, 35.0, 18.0
    bm = bx(BMX0, BMX1, BMY0, BMY1, BMZ0, Z_YCAR)
    bm -= bx(BMX0, 33.5, BMY0, BMY1, YM_Z - PR - 3.0, YM_Z - PR + 3.0)        # the lower belt run passes through
    bm -= bx(BMX0, 33.5, BMY0, BMY1, YM_Z + PR - 1.0, YM_Z + PR + 1.0)        # the clamped upper run
    d.add("y_belt_mount", bm, material=PETG, body="ybody", process="printed")
    for i, (x, y) in enumerate(BM_SCREWS):
        add_screw(d, f"y_belt_mount_screw_{i}", "M3", 12, at=(x, y, Z_SUB), body="ybody", threads_into="y_belt_mount", clamps=("sub_plate",))
    # Y motor on a printed plate on the base's +X side face at the rear (real: y_motor_cage, a box 50 x 86 x 80)
    MPX0, MPX1 = 15.0, 21.0
    YE = BASE_L / 2
    mp = bx(MPX0, MPX1, YE, 196.0, 5.0, 72.5) + bx(-15.0, MPX1, YE, YE + 6.0, 0.0, 60.0)      # side plate + flange on the base's end
    ym = place(d, "y_motor", nema17(40), Location(Plane(origin=(MPX0, YM_Y, YM_Z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    mp -= cyl_x(MPX0, MPX1, YM_Y, YM_Z, 11.5)
    for hx, hy, hz in ym.meta["interfaces"]["mount_holes_m3"]:
        mp -= cyl_x(MPX0, MPX1, hy, hz, clearance_hole("M3") / 2)
    MP_BOLTS = (15.0, 45.0)       # M8 x 30 into the base's tapped end (BOM: the 270 mm 3060 is the tapped one)
    for z in MP_BOLTS:
        mp -= cyl_y(0.0, YE, YE + 6.0, z, clearance_hole("M8") / 2)
    d.add("y_motor_plate", mp, material=PETG, process="printed")
    for i, (hx, hy, hz) in enumerate(ym.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"y_motor_screw_{i}", "M3", 10, at=(MPX1, hy, hz), direction=(-1, 0, 0), threads_into="y_motor", clamps=("y_motor_plate",))
    for i, z in enumerate(MP_BOLTS):
        add_screw(d, f"y_motor_plate_bolt_{i}", "M8", 30, at=(0.0, YE + 6.0, z), direction=(0, -1, 0), threads_into="y_base", clamps=("y_motor_plate",))
    # 9 mm belt (BOM). Pulley hub outboard: its toothed end 1 mm off the plate
    place(d, "y_pulley", gt2_pulley(20, belt_width=9.0), Location(Plane(origin=(MPX1 + 1.0 + 18.0, YM_Y, YM_Z), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    d.join("y_pulley", "y_motor", "set_screw")
    ybx = MPX1 + 1.0 + 6.0
    assert abs(ybx - YB_X) < 1e-6
    # front: idler in a printed block bolted to the base's tapped end (real: y_idler + y_belt_tensioner, M8 x 30 into the end taps)
    yi = bx(-15.0, YB_X - 6.0, -160.0, -BASE_L / 2, 0.0, 80.0)
    for z in (15.0, 45.0):
        yi -= cyl_y(0.0, -160.0, -BASE_L / 2, z, clearance_hole("M8") / 2)
        yi -= cyl_y(0.0, -160.0, -153.0, z, 7.0)
    d.add("y_idler_block", yi, material=PETG, process="printed")
    for i, z in enumerate((15.0, 45.0)):
        add_screw(d, f"y_idler_block_bolt_{i}", "M8", 30, at=(0.0, -153.0, z), direction=(0, 1, 0), threads_into="y_base", clamps=("y_idler_block",))
    place(d, "y_idler", gt2_idler(20, belt_width=9.0), Location(Plane(origin=(YB_X - 5.75, YI_Y, YM_Z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    add_screw(d, "y_idler_bolt", "M5", 25, at=(YB_X + 6.0, YI_Y, YM_Z), direction=(-1, 0, 0), threads_into="y_idler_block", clamps=("y_idler",))
    d.join("y_idler", "y_idler_bolt", "runs on its bolt")
    d.belts.append(Belt("y_belt", [("anchor", "ybody", (YB_X, BMY0 + 5.0, YM_Z + PR)), ("pulley", "y_idler", "ccw"),
                                   ("pulley", "y_pulley", "ccw"), ("anchor", "ybody", (YB_X, BMY1 - 5.0, YM_Z + PR))],
                        axis=(1, 0, 0), width=9.0, adjust=5.0))
    d.bom_extra("GT2-BELT-9MM-OPEN-1M", 1, 4.0)
    # Y endstop on the motor plate, struck by the belt mount at the rear end of the bed's travel (firmware Y = 0).
    # Where the real switch sits is not published: it is placed by the catalogue switch's own figures (nominal operating
    # point at the end of the working travel, 1.5 mm of over-travel), so the endstop checks are not an independent test.
    ES_SP = 4.0
    ysw = place(d, "y_endstop", endstop_switch(),
                Location(Plane(origin=(MPX1 + ES_SP, BMY1 + PRINT / 2 + 8.4, 32.0), x_dir=(0, 0, 1), z_dir=(1, 0, 0))))
    for i, (hx, hy, hz) in enumerate(ysw.meta["interfaces"]["mount_holes_m3"]):
        place(d, f"y_endstop_spacer_{i}", spacer_round("M3", ES_SP), Location(Plane(origin=(MPX1, hy, hz), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
        add_screw(d, f"y_endstop_screw_{i}", "M3", 12, at=(hx + 1.6, hy, hz), direction=(-1, 0, 0), threads_into="y_motor_plate",
                  clamps=("y_endstop", f"y_endstop_spacer_{i}"))

    # ================= Z axis: the arm on the column =============================
    zr = place(d, "z_rail", mgn12_rail(RAIL_L), Location(Plane(origin=(COL_X, Y_COLR, Z_ZRAIL0 + RAIL_L / 2), x_dir=(0, 0, 1), z_dir=(0, 1, 0))))
    zholes = zr.meta["interfaces"]["mount_holes_m3"]
    for i in (0, 2, 4, 5, 7, 9):
        hx, hy, hz = zholes[i]
        add_screw(d, f"z_rail_screw_{i}", "M3", 8, at=(hx, Y_COLR + seat, hz), direction=(0, -1, 0), threads_into="column", clamps=("z_rail",), tnut=True)
    zcar = place(d, "z_carriage", mgn12h_carriage(), Location(Plane(origin=(COL_X, Y_COLR, ZC), x_dir=(0, 0, 1), z_dir=(0, 1, 0))),
                 body="zbody", guides="z")
    y0, y1 = Y_COLR + 13.0, Y_COLR + 13.0 + T_XP
    XP_X0, XP_X1 = -210.0, -120.0
    xp = bx(XP_X0, XP_X1, y0, y1, ZC - 25, ZB + 12)
    for hx, hy, hz in zcar.meta["interfaces"]["mount_holes_m3"]:
        xp -= cyl_y(hx, y0, y1, hz, clearance_hole("M3") / 2)
    XP_BOLTS = (-205.0, -125.0)
    for x in XP_BOLTS:
        xp -= cyl_y(x, y0, y1, ZB, clearance_hole("M5") / 2)
    d.add("x_plate", xp, material="al6061", body="zbody", process="sheet")
    for i, (hx, hy, hz) in enumerate(zcar.meta["interfaces"]["mount_holes_m3"]):
        # the plate's M3 screws are driven from behind, before the beam goes on
        add_screw(d, f"x_plate_screw_{i}", "M3", 8, at=(hx, y1, hz), direction=(0, -1, 0), body="zbody", threads_into="z_carriage", clamps=("x_plate",))
    place(d, "x_beam", extrusion_2020(BEAM_L), Location(((BEAM_X0 + BEAM_X1) / 2, BY, ZB)), body="zbody")
    for i, x in enumerate(XP_BOLTS):
        add_screw(d, f"x_beam_bolt_{i}", "M5", 10, at=(x, y0, ZB), direction=(0, 1, 0), body="zbody", threads_into="x_beam", clamps=("x_plate",), tnut=True)
    # lead screw nut. S9: the real part is a TR8x4 anti-backlash nut block; here the catalogue's brass flange nut in an
    # aluminium block bolted under the beam (how the real block meets the arm is not published)
    nb = bx(LS[0] - 17, LS[0] + 17, BY - 6, LS[1] + 14, NB_Z0, NB_Z1)
    nb -= cyl_z(LS[0], LS[1], NB_Z0, NB_Z1, 5.3)
    NB_BOLTS = (LS[0] - 10.0, LS[0] + 10.0)
    for x in NB_BOLTS:
        nb -= cyl_z(x, BY, NB_Z0, NB_Z1, clearance_hole("M5") / 2)
    d.add("z_nut_block", nb, material="al6061", body="zbody", process="machined")
    for i, x in enumerate(NB_BOLTS):
        add_screw(d, f"z_nut_block_bolt_{i}", "M5", 20, at=(x, BY, NB_Z0), direction=(0, 0, 1), body="zbody", threads_into="x_beam",
                  clamps=("z_nut_block",), tnut=True)
    nut = place(d, "z_nut", leadscrew_nut_t8(), Location((LS[0], LS[1], NB_Z0 - 3.5)), body="zbody", guides="z")
    d.allow_overlap("z_nut", "leadscrew")
    for i, (hx, hy, hz) in enumerate(nut.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"z_nut_screw_{i}", "M3", 10, at=(hx, hy, NB_Z0 - 3.5), direction=(0, 0, 1), body="zbody",
                  threads_into="z_nut_block", clamps=("z_nut",))
        d.allow_overlap("z_nut", f"z_nut_screw_{i}")       # the catalogue nut's flange is drawn without its four holes
    # Z motor under a printed bracket on the column's rear face (real: z_motor_cage 53 x 97.5 x 47)
    zm = place(d, "z_motor", nema17(40), Location((LS[0], LS[1], Z_MF), (0, 0, 90)))
    zmm = bx(COL_X - 26, COL_X + 26, Y_COLR, LS[1] + 24, Z_MF, Z_MF + 6) + bx(COL_X - 26, COL_X + 26, Y_COLR, Y_COLR + 8, 10.0, Z_MF)
    zmm -= bx(LS[0] - 11.5, LS[0] + 11.5, LS[1] - 15.5, LS[1] + 15.5, Z_MF, Z_MF + 6)
    ZM_SLOT = 3.65        # the published z_motor_cage.step has four 3.3 mm slots 7.3 mm long: the motor slides to line the screw up
    for hx, hy, hz in zm.meta["interfaces"]["mount_holes_m3"]:
        zmm -= cyl_z(hx, hy - ZM_SLOT, Z_MF, Z_MF + 6, clearance_hole("M3") / 2) + cyl_z(hx, hy + ZM_SLOT, Z_MF, Z_MF + 6, clearance_hole("M3") / 2) \
            + bx(hx - clearance_hole("M3") / 2, hx + clearance_hole("M3") / 2, hy - ZM_SLOT, hy + ZM_SLOT, Z_MF, Z_MF + 6)
    ZMM_BOLTS = (COL_X - 15.0, COL_X + 15.0)
    for x in ZMM_BOLTS:
        zmm -= cyl_y(x, Y_COLR, Y_COLR + 8, 30.0, clearance_hole("M6") / 2)
    d.add("z_motor_cage", zmm, material=PETG, process="printed")
    for i, (hx, hy, hz) in enumerate(zm.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"z_motor_screw_{i}", "M3", 10, at=(hx, hy, Z_MF + 6), threads_into="z_motor", clamps=("z_motor_cage",))
    for i, x in enumerate(ZMM_BOLTS):
        add_screw(d, f"z_motor_cage_bolt_{i}", "M6", 12, at=(x, Y_COLR + 8, 30.0), direction=(0, -1, 0), threads_into="column",
                  clamps=("z_motor_cage",), tnut=True)
    place(d, "z_coupler", shaft_coupler(5.0, 8.0), Location((LS[0], LS[1], Z_CPL)))
    d.join("z_coupler", "z_motor", "clamp")
    d.allow_overlap("z_coupler", "z_motor")
    place(d, "leadscrew", leadscrew_t8(250, lead=4.0), Location((LS[0], LS[1], Z_LS0)))      # TR8x4 (BOM; RatOS rotation_distance 4)
    d.join("leadscrew", "z_coupler", "clamp")
    d.allow_overlap("leadscrew", "z_coupler")
    # top of the column: printed cap with the screw's top bearing (real: z_cap + pillow_block + F8-16M thrust bearing).
    # S10: a 608 radial bearing stands in for the thrust bearing
    z_brg = Z_LS0 + 250.0 - 4.0
    cap = bx(COL_X - 30, COL_X + 30, YC - 15, LS[1] + 17, COL_L, COL_L + 8) + bx(COL_X - 17, COL_X + 17, LS[1] - 17, LS[1] + 17, z_brg - 5.5, COL_L)
    cap -= cyl_z(LS[0], LS[1], z_brg - 3.5, COL_L + 8, 11.0)
    cap -= cyl_z(LS[0], LS[1], z_brg - 5.5, z_brg - 3.5, 6.0)
    for x in (COL_X - 15.0, COL_X + 15.0):
        cap -= cyl_z(x, YC, COL_L, COL_L + 8, clearance_hole("M8") / 2)
    d.add("z_cap", cap, material=PETG, process="printed")
    for i, x in enumerate((COL_X - 15.0, COL_X + 15.0)):
        add_screw(d, f"z_cap_bolt_{i}", "M8", 30, at=(x, YC, COL_L + 8), threads_into="column", clamps=("z_cap",))
    place(d, "z_top_bearing", bearing("608"), Location((LS[0], LS[1], z_brg)))
    d.join("z_top_bearing", "z_cap", "press")
    d.join("z_top_bearing", "leadscrew", "slide")

    # ================= X axis: the toolhead ======================================
    xr = place(d, "x_rail", mgn12_rail(RAIL_L), Location((0, BY, ZB + 10)), body="zbody")
    for i, (hx, hy, hz) in enumerate(xr.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"x_rail_screw_{i}", "M3", 8, at=(hx, hy, ZB + 10 + seat), body="zbody", threads_into="x_beam", clamps=("x_rail",), tnut=True)
    # S11: MGN12H block (45.4 long, 54 g) for the real MGN12C (34.7 long, 34 g)
    xcar = place(d, "x_carriage", mgn12h_carriage(), Location((0, BY, ZB + 10)), body="xbody", guides="x")
    # EVA 2.4 carriage, drawn as ONE printed part (S12): slab on the block reaching forward over the hotend, rear wall
    # with the belt clamp, front web, two cheeks and the probe's tab. Real: top_mgn12, back_cartesian,
    # bottom_mgn12_short_duct, universal_face, bmo_face, bmo_support, shroud, duct (about 97 cm^3 of solid plastic)
    XL, XR = -21.0, 22.0
    eva = bx(XL, XR, -22.0, 58.0, Z_SLAB0, Z_SLAB1)
    eva += bx(XL, XR, BY + 14.0, 58.0, ZB - 16.0, Z_SLAB0)                          # rear wall behind the beam
    eva -= bx(XL, XR, BY + 14.0, XB_Y + 4.0, ZB - 10.0, ZB + 3.0)                   # channel for the free lower run; the upper run is clamped above it
    eva += bx(XL, XR, 12.0, 18.0, ZB - 22.0, Z_SLAB0)                               # front web
    eva += bx(19.0, XR, -22.0, 12.0, ZB - 10.0, Z_SLAB0)                            # right cheek
    eva += bx(XL, XL + 2.5, -22.0, 12.0, ZB - 2.0, Z_SLAB0)                         # left cheek (short: the probe's nuts are below it)
    px, py = PROBE_OFF
    tz0, tz1 = Z_PRB + PRB_CLAMP[0], Z_PRB + PRB_CLAMP[1]
    eva += bx(px - 9.5, XL + 2.5, py - 9.5, 18.0, tz0, tz1)                         # probe tab, carried by the front web
    eva -= cyl_z(px, py, tz0, tz1, 6.25)
    eva += bx(-38.0, XL, -22.0, 6.0, Z_SLAB1 - 6.0, Z_SLAB1)                        # ear for the X endstop, above the probe
    eva -= cyl_z(0.0, 0.0, Z_SLAB0, Z_SLAB1, 8.0)                                   # groove-mount bore
    for hx, hy, hz in xcar.meta["interfaces"]["mount_holes_m3"]:
        eva -= cyl_z(hx, hy, Z_SLAB0, Z_SLAB1, clearance_hole("M3") / 2)
        eva -= cyl_z(hx, hy, Z_SLAB1 - 3.2, Z_SLAB1, 3.0)
    EX_SCREWS = [(-15.5, -15.5), (15.5, -15.5)]
    for x, y in EX_SCREWS:
        eva -= cyl_z(x, y, Z_SLAB0, Z_SLAB1, clearance_hole("M3") / 2)
    d.add("eva_carriage", eva, material=PETG, body="xbody", process="printed")
    for i, (hx, hy, hz) in enumerate(xcar.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"eva_screw_{i}", "M3", 8, at=(hx, hy, Z_SLAB1 - 3.2), body="xbody", threads_into="x_carriage", clamps=("eva_carriage",))
    # hotend. S13: E3D V6 for the Dragonfly BMO; heater block turned to +X, away from the probe
    place(d, "hotend", hotend_v6(), Location((0, 0, HOT_TOP), (0, 0, 180)), body="xbody")
    d.join("hotend", "eva_carriage", "press")       # clamped in its groove (the real mount is split and screwed shut)
    d.allow_overlap("hotend", "eva_carriage")
    hi = d.get("hotend").meta["interfaces"]
    hbx, hby, hbz = hi["heater_bore"][0]
    sbx, sby, sbz = hi["sensor_bore"][0]
    place(d, "hotend_heater", heater_cartridge(60.0, 24.0), Location((hbx, hby, hbz)), body="xbody")       # 60 W (BOM)
    place(d, "hotend_thermistor", thermistor_cartridge(), Location((sbx, sby, sbz)), body="xbody")
    for nm in ("hotend_heater", "hotend_thermistor"):
        d.allow_overlap(nm, "hotend")
        d.join(nm, "hotend", "clamp")
    # extruder. S14: the catalogue's generic direct-drive extruder (0.24 kg) for the Bondtech LGX Lite
    place(d, "extruder", extruder_direct(), Location((0, 0, Z_SLAB1)), body="xbody")
    for i, (x, y) in enumerate(EX_SCREWS):
        add_screw(d, f"extruder_screw_{i}", "M3", 14, at=(x, y, Z_SLAB0), direction=(0, 0, 1), body="xbody", threads_into="extruder", clamps=("eva_carriage",))
    # fans. Heat-sink fan 40 mm axial (BOM). S15: a 30 mm axial fan stands in for the 5015 blower. Both held by
    # self-tapping screws in the real shroud: declared joins here (S16)
    place(d, "hotend_fan", fan(40), Location(Plane(origin=(0.0, -27.0, HOT_TOP - 27.65), x_dir=(1, 0, 0), z_dir=(0, -1, 0))), body="xbody")
    d.join("hotend_fan", "eva_carriage", "screwed to the shroud (not drawn)")
    place(d, "part_fan", fan(30), Location(Plane(origin=(XR + 5.0, -4.0, ZB + 3.0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))), body="xbody")
    d.join("part_fan", "eva_carriage", "screwed to the duct (not drawn)")
    d.bom_extra("SHCS-M3x20", 4, 0.06)
    # bed probe. S3: OMRON E2E-X5ME1 (M12, 10-30 V, unshielded) for the kit's 8 mm 5 V inductive probe, at the real offsets
    place(d, "bed_probe", probe_omron_e2e("E2E-X5ME1", clamp=PRB_CLAMP, nuts="separate"), Location((px, py, Z_PRB)), body="xbody")
    add_probe_nuts(d, "bed_probe")
    d.join("bed_probe", "eva_carriage", "clamped by its two nuts")
    # X belt: 6 mm (BOM), loop in a vertical plane behind the beam; motor at the column end, idler at the free end
    cage = bx(BEAM_X0 - 20, BEAM_X0, BY - 10, XB_Y + 12.5, ZB - 21, ZB + 21) + bx(BEAM_X0 - 20, XM_X + 21, XB_Y + 8.5, XB_Y + 12.5, ZB - 21, ZB + 21)
    cage += bx(BEAM_X0, BEAM_X0 + 20, BY - 10, BY + 10, ZB + 10, ZB + 12.5)
    xm = place(d, "x_motor", nema17(40), Location(Plane(origin=(XM_X, XB_Y + 12.5, ZB), x_dir=(1, 0, 0), z_dir=(0, -1, 0))), body="zbody")
    cage -= cyl_y(XM_X, XB_Y + 8.5, XB_Y + 12.5, ZB, 11.5)
    for hx, hy, hz in xm.meta["interfaces"]["mount_holes_m3"]:
        cage -= cyl_y(hx, XB_Y + 8.5, XB_Y + 12.5, hz, clearance_hole("M3") / 2)
    cage -= cyl_x(BEAM_X0 - 20, BEAM_X0, BY, ZB, clearance_hole("M5") / 2)
    cage -= cyl_z(BEAM_X0 + 10, BY, ZB + 10, ZB + 12.5, clearance_hole("M5") / 2)
    d.add("x_motor_cage", cage, material=PETG, body="zbody", process="printed")
    for i, (hx, hy, hz) in enumerate(xm.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"x_motor_screw_{i}", "M3", 8, at=(hx, XB_Y + 8.5, hz), direction=(0, 1, 0), body="zbody", threads_into="x_motor", clamps=("x_motor_cage",))
    add_screw(d, "x_motor_cage_bolt", "M5", 30, at=(BEAM_X0 - 20, BY, ZB), direction=(1, 0, 0), body="zbody", threads_into="x_beam", clamps=("x_motor_cage",))
    add_screw(d, "x_motor_cage_tnut", "M5", 8, at=(BEAM_X0 + 10, BY, ZB + 12.5), body="zbody", threads_into="x_beam", clamps=("x_motor_cage",), tnut=True)
    place(d, "x_pulley", gt2_pulley(20), Location(Plane(origin=(XM_X, XB_Y + 10.5, ZB), x_dir=(1, 0, 0), z_dir=(0, -1, 0))), body="zbody")
    d.join("x_pulley", "x_motor", "set_screw")
    # idler block on the free end (real: x_idler 25 x 46 x 30 + x_gantry_end_cap); 
    xi = bx(BEAM_X1, BEAM_X1 + 20, BY - 10, XB_Y + 11, ZB - 15, ZB + 15) + bx(XI_X - 9, BEAM_X1, XB_Y + 5, XB_Y + 11, ZB - 15, ZB + 15)
    xi -= cyl_x(BEAM_X1, BEAM_X1 + 20, BY, ZB, clearance_hole("M5") / 2)
    xi -= cyl_y(XI_X, XB_Y + 5, XB_Y + 11, ZB, clearance_hole("M5") / 2)
    d.add("x_idler_block", xi, material=PETG, body="zbody", process="printed")
    add_screw(d, "x_idler_block_bolt", "M5", 30, at=(BEAM_X1 + 20, BY, ZB), direction=(-1, 0, 0), body="zbody", threads_into="x_beam", clamps=("x_idler_block",))
    place(d, "x_idler", gt2_idler(20), Location(Plane(origin=(XI_X, XB_Y + 4.25, ZB), x_dir=(1, 0, 0), z_dir=(0, -1, 0))), body="zbody")
    add_screw(d, "x_idler_bolt", "M5", 25, at=(XI_X, XB_Y + 11, ZB), direction=(0, -1, 0), body="zbody", threads_into="x_beam",
              clamps=("x_idler_block", "x_idler"), tnut=True)
    d.join("x_idler", "x_idler_bolt", "runs on its bolt")
    d.belts.append(Belt("x_belt", [("anchor", "xbody", (XL, XB_Y, ZB + PR)), ("pulley", "x_pulley", "cw"),
                                   ("pulley", "x_idler", "cw"), ("anchor", "xbody", (XR, XB_Y, ZB + PR))],
                        axis=(0, 1, 0), width=6.0, adjust=5.0))
    d.bom_extra("GT2-BELT-6MM-OPEN-1M", 1, 3.0)
    # X endstop on the toolhead (real: top_endstop_angled on the EVA top), homing at X = 0 (left): the lever meets the
    # column's right face. Where the real switch sits is not published (the same caveat as the Y endstop): it is on a
    # printed ear of the carriage (drawn above, with the slab), placed by the catalogue switch's own figures
    ESX = (COL_X + 30.0 + PRINT / 2 + 8.4, -8.0)      # nominal operating point on the column face at X = 0
    xsw = place(d, "x_endstop", endstop_switch(), Location(Plane(origin=(ESX[0], ESX[1], Z_SLAB1 + ES_SP), x_dir=(0, 1, 0), z_dir=(0, 0, 1))), body="xbody")
    for i, (hx, hy, hz) in enumerate(xsw.meta["interfaces"]["mount_holes_m3"]):
        place(d, f"x_endstop_spacer_{i}", spacer_round("M3", ES_SP), Location((hx, hy, Z_SLAB1)), body="xbody")
        add_screw(d, f"x_endstop_screw_{i}", "M3", 12, at=(hx, hy, hz + 1.6), body="xbody", threads_into="eva_carriage",
                  clamps=("x_endstop", f"x_endstop_spacer_{i}"))

    # ================= electronics case ==========================================
    # Free-standing box (260 x 162 x 90, Rat Rig's drawing), upright beside the column. 4 mm polycarbonate panels
    # (S17: drawn in PETG, the nearest material in the table) and printed ends. The panels' own M3 screws, locknuts and
    # 70 mm standoffs are BOM lines and declared joins, not geometry (S18).
    psu = place(d, "psu", psu_lrs("LRS-350-24"), Location(Plane(origin=(CX0 + T_PAN, 0.0, 80.0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))   # S19: Weho 350 W in the BOM
    board = place(d, "control_board", skr_mini_e3_v3(), Location(Plane(origin=(CX1 - T_PAN - 6.0, 40.0, 100.0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))   # S20: SKRat 1.0 in the kit
    host = place(d, "host", raspberry_pi_zero2w(), Location(Plane(origin=(CX1 - T_PAN - 5.0, -70.0, 100.0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))    # S21: Pi 3/4 in the kit
    pp = bx(CX0, CX0 + T_PAN, CY0, CY1, 0, CZ1)
    for hx, hy, hz in psu.meta["interfaces"]["mount_holes_m4"]:
        pp -= cyl_x(CX0, CX0 + T_PAN, hy, hz, clearance_hole("M4") / 2)
    d.add("case_panel_psu", pp, material=PETG, process="sheet")
    for i, (hx, hy, hz) in enumerate(psu.meta["interfaces"]["mount_holes_m4"]):
        # BOM: 4 x M4 x 6 through the 4 mm panel into the supply's 3 mm deep threads
        add_screw(d, f"psu_screw_{i}", "M4", 6, at=(CX0, hy, hz), direction=(1, 0, 0), threads_into="psu", clamps=("case_panel_psu",))
    bp = bx(CX1 - T_PAN, CX1, CY0, CY1, 0, CZ1)
    pcbs = [("control_board", board, "mount_holes_m3", "M3", 6.0, 16, 1.6, (0, 1, 2, 4)), ("host", host, "mount_holes_m2.5", "M2.5", 5.0, 16, 1.5, None)]
    for nm, comp, key, size, sp, slen, t_pcb, use in pcbs:
        for i, (hx, hy, hz) in enumerate(comp.meta["interfaces"][key]):
            if use is None or i in use:
                bp -= cyl_x(CX1 - T_PAN, CX1, hy, hz, clearance_hole(size) / 2)
    d.add("case_panel_board", bp, material=PETG, process="sheet")
    for nm, comp, key, size, sp, slen, t_pcb, use in pcbs:
        for i, (hx, hy, hz) in enumerate(comp.meta["interfaces"][key]):
            if use is not None and i not in use:
                continue
            place(d, f"{nm}_spacer_{i}", spacer_round(size, sp), Location(Plane(origin=(CX1 - T_PAN, hy, hz), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
            add_screw(d, f"{nm}_screw_{i}", size, slen, at=(CX1 - T_PAN - sp - t_pcb, hy, hz), direction=(1, 0, 0),
                      clamps=(nm, f"{nm}_spacer_{i}", "case_panel_board"))
            add_nut(d, f"{nm}_nut_{i}", size, at=(CX1, hy, hz), direction=(1, 0, 0), screw=f"{nm}_screw_{i}")
    d.add("case_panel_bottom", bx(CX0 + T_PAN, CX1 - T_PAN, CY0, CY1, 0, T_PAN), material=PETG, process="sheet")
    topp = bx(CX0 + T_PAN, CX1 - T_PAN, CY0, CY1, CZ1 - T_PAN, CZ1) - cyl_z((CX0 + CX1) / 2, 60.0, CZ1 - T_PAN, CZ1, 18.5)
    d.add("case_panel_top", topp, material=PETG, process="sheet")
    place(d, "case_fan", fan(40), Location(((CX0 + CX1) / 2, 60.0, CZ1 - T_PAN - 5.0)))
    d.join("case_fan", "case_panel_top", "4 x M3 x 16 and locknuts (not drawn)")
    front = bx(CX0 + T_PAN, CX1 - T_PAN, CY0, CY0 + T_PAN, T_PAN, CZ1 - T_PAN)
    for z in (40.0, 60.0, 80.0, 100.0, 120.0):
        front -= bx(CX0 + 20, CX1 - 20, CY0, CY0 + T_PAN, z - 3, z + 3)                 # vent slots
    d.add("case_front", front, material=PETG, process="printed")
    IN = ((CX0 + CX1) / 2 + 14.0, 45.0)
    back = bx(CX0 + T_PAN, CX1 - T_PAN, CY1 - T_PAN, CY1, T_PAN, CZ1 - T_PAN)
    inlet = place(d, "inlet", iec_inlet_c14(5.0), Location(Plane(origin=(IN[0], CY1, IN[1]), x_dir=(1, 0, 0), z_dir=(0, 1, 0))))   # 5 A fuse (BOM)
    cut_x, cut_y = inlet.meta["interfaces"]["cutout"]
    back -= Pos(IN[0], CY1 - T_PAN / 2, IN[1]) * Rot(90, 0, 0) * extrude(RectangleRounded(cut_x, cut_y, inlet.meta["interfaces"]["cutout_corner_radius"]), T_PAN / 2, both=True)
    for hx, hy, hz in inlet.meta["interfaces"]["mount_holes_m3"]:
        back -= cyl_y(hx, CY1 - T_PAN, CY1, hz, clearance_hole("M3") / 2)
    d.add("case_back", back, material=PETG, process="printed")
    for i, (hx, hy, hz) in enumerate(inlet.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"inlet_screw_{i}", "M3", 12, at=(hx, CY1 + 2.5, hz), direction=(0, -1, 0), clamps=("inlet", "case_back"))
        add_nut(d, f"inlet_nut_{i}", "M3", at=(hx, CY1 - T_PAN, hz), direction=(0, -1, 0), screw=f"inlet_screw_{i}")
    for a in ("case_panel_psu", "case_panel_board", "case_panel_bottom", "case_panel_top"):
        for b in ("case_front", "case_back"):
            d.join(a, b, "M3 screws and locknuts in the printed end (BOM lines, not drawn)")
    d.bom_extra("SHCS-M3x10", 21, 0.05)
    d.bom_extra("NUT-M3-LOCK", 25, 0.04)
    d.bom_extra("STANDOFF-BRASS-M3x70", 4, 0.8)
    # bench jobs (what a builder does anyway): boards on their panel and the supply on its panel before the case is
    # closed; the X motor in its cage before the cage goes on the beam
    d.subassemblies["board_panel"] = ["case_panel_board"] + [c.name for c in d.components if c.name.startswith(("control_board", "host"))]
    d.subassemblies["psu_panel"] = ["case_panel_psu", "psu"] + [f"psu_screw_{i}" for i in range(4)]
    d.subassemblies["x_drive"] = ["x_motor_cage", "x_motor", "x_pulley"] + [f"x_motor_screw_{i}" for i in range(4)]

    # ================= joints ====================================================
    TR = PRINT / 2
    d.joints.append(Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-TR, TR), overtravel=(ES_OT, ES_OT),
                          max_speed=V_XY, max_accel=A_XY, drive={"motor": "y_motor", "kind": "belt", "pulley": "y_pulley"}))
    # z = 180: nozzle 0.1 mm above the print surface (firmware Z 0). RatOS lets Z go 5 mm below zero (position_min -5):
    # declared as over-travel past the nozzle plane, as the harness asks for a probe's z_offset
    d.joints.append(Joint("z", "slide", "world", "zbody", (0, 0, -1), range=(0.0, PRINT), overtravel=(2.0, Z_BELOW),
                          max_speed=V_Z, max_accel=A_Z,
                          drive={"motor": "z_motor", "kind": "leadscrew", "screw": "leadscrew", "nut": "z_nut", "coupler": "z_coupler"}))
    d.joints.append(Joint("x", "slide", "zbody", "xbody", (1, 0, 0), range=(-TR, TR), overtravel=(ES_OT, ES_OT),
                          max_speed=V_XY, max_accel=A_XY, drive={"motor": "x_motor", "kind": "belt", "pulley": "x_pulley"}))
    d.program = [{"to": {"z": PRINT - 20.0}}, {"to": {"x": -75, "y": -75}}, {"to": {"x": 75, "y": -75}}, {"to": {"x": 75, "y": 75}},
                 {"to": {"x": -75, "y": 75}}, {"to": {"x": -75, "y": -75}}, {"to": {"x": 0, "y": 0}}, {"to": {"z": 0.0}}]
    nozzle = (0.0, 0.0, Z_NOZ)
    d.tool_point = ("xbody", nozzle)
    d.endstops += [{"joint": "x", "switch": "x_endstop", "at": "min"},
                   {"joint": "y", "switch": "y_endstop", "at": "max"},     # bed at the rear = firmware Y 0
                   {"joint": "z", "probe": "bed_probe", "at": "max"}]
    build_electrical(d)
    d.adjustments += [
        Adjustment("probe z_offset in the firmware (RatOS position_min -5)", "z_offset", range_mm=Z_BELOW),
        # RatOS screws_tilt_adjust names the three M4 bed screws: the plate is trammed at its three mounts. How much
        # travel they have is not published; 1 mm (the three 1 mm nylon washers per screw in the BOM) is assumed
        Adjustment("three M4 bed screws (screws_tilt_adjust)", "bed_level", range_mm=1.0),
        # the Z motor's four screw holes in the published z_motor_cage are 7.3 mm slots: the motor (and with it the foot
        # of the screw) is slid until the screw runs true to the nut, then tightened
        Adjustment("Z motor slides in the slots of its cage", "float", range_mm=3.6, joint="z"),
        Adjustment("x belt: tension slider in the carriage (tension_slider_6mm_belt_M3s)", "belt_tension", range_mm=5.0, joint="x"),
        Adjustment("y belt: y_belt_tensioner at the front idler", "belt_tension", range_mm=5.0, joint="y"),
    ]
    d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z",
                 "stiffness": {"x": "nozzle_stiffness_x", "y": "nozzle_stiffness_y"},
                 "print_area": (PRINT, PRINT)}

    # ================= structure =================================================
    # nozzle stiffness: the whole cantilever, column foot held (the column's joint to the link is NOT in the model)
    arm = ["column", "z_rail", "z_carriage", "x_plate", "x_beam", "x_rail", "x_carriage", "eva_carriage", "hotend"]
    foot = [("column", lambda f: abs(f.center().Z) < 1e-6)]
    z_blk = hi["heater_block_box"][0][2]
    block_face = ("hotend", lambda f: abs(f.center().Z - z_blk) < 1e-3)
    for nm, force in (("nozzle_stiffness_x", (3.0, 0.0, 0.0)), ("nozzle_stiffness_y", (0.0, 3.0, 0.0))):
        d.assemblycases.append(AssemblyCase(nm, arm, fixed=foot, loaded=block_face, force=force, probe=nozzle))
    # the bed stack under a 1 kg print (x3) plus its own weight (x3)
    stack = ["y_carriage", "sub_plate", "bed_standoff_0", "bed_standoff_1", "bed_standoff_2", "bed_plate"]
    w = 3.0 * (1.0 + d.get("bed_plate").mass() + d.get("bed").mass()) * 9.81
    d.assemblycases.append(AssemblyCase(
        "payload_x3_on_bed", stack, fixed=[("y_carriage", lambda f: abs(f.center().Z - (Z_TOP + 8.0)) < 1e-6)],
        loaded=("bed_plate", lambda f: abs(f.center().Z - (Z_BED0 + T_BED)) < 1e-6 and f.area > 1000),
        force=(0.0, 0.0, -w), probe=(BED / 2, BED / 2, Z_BED0 + T_BED), max_deflection=0.3, min_fos=3.0))
    d.loadcases.append(LoadCase(      # weight of the arm (x3) on the nut block
        "z_nut_thrust", "z_nut_block", fixed=lambda f: abs(f.center().Z - NB_Z1) < 1e-6,
        loaded=lambda f: abs(f.center().Z - NB_Z0) < 1e-6, force=(0.0, 0.0, 3.0 * 1.6 * 9.81), min_fos=3.0, max_deflection=0.3))
    d.thermalcases.append(ThermalCase(
        "bed_heated_60K", stack, fixed=[("y_carriage", lambda f: abs(f.center().Z - (Z_TOP + 8.0)) < 1e-6)],
        temps={"bed_plate": 60.0, **{f"bed_standoff_{i}": 30.0 for i in range(3)}, "*": 0.0},
        probes={"carriage": (0.0, 0.0, Z_TOP + 8.0), "bed": (0.0, 0.0, Z_BED0 + T_BED)},
        gaps={"nozzle gap": ("carriage", "bed", "z", None)}, flatness=("bed_plate", "z", None)))

    # ================= requirements: the published claims only ====================
    def jr(dd, name):
        return next(j for j in dd.joints if j.name == name)

    d.requirements.append(Requirement("published build volume 180 x 180 x 180 mm", lambda dd: (
        all(jr(dd, n).range[1] - jr(dd, n).range[0] >= PRINT for n in "xyz"), str({n: jr(dd, n).range for n in "xyz"}))))

    def over_bed(dd):
        bb = dd.get("bed").shape.bounding_box()
        nx, ny, _ = dd.tool_point[1]
        m = min(nx - TR - bb.min.X, bb.max.X - (nx + TR), ny - TR - bb.min.Y, bb.max.Y - (ny + TR))
        return m >= 0, f"smallest nozzle-to-plate-edge margin over the travel: {m:.1f} mm"
    d.requirements.append(Requirement("nozzle stays over the flex plate for all XY positions", over_bed))
    d.requirements.append(Requirement("published overall size 372 x 375.2 x 366.5 mm (machine without the case, feet not drawn)", lambda dd: (
        (s := _machine_size(dd))[0] <= 372.0 + 15 and s[1] <= 375.2 + 15 and s[2] <= 366.5 - 16.5 + 15,
        f"model {s[0]:.0f} x {s[1]:.0f} x {s[2]:.0f} mm at home")))
    return d


def _machine_size(dd):
    lo, hi = [1e9] * 3, [-1e9] * 3
    for c in dd.components:
        if c.name.startswith(("case_", "psu", "control_board", "host", "inlet")):
            continue
        bb = c.shape.bounding_box()
        for k, (a, b) in enumerate(((bb.min.X, bb.max.X), (bb.min.Y, bb.max.Y), (bb.min.Z, bb.max.Z))):
            lo[k], hi[k] = min(lo[k], a), max(hi[k], b)
    return [hi[k] - lo[k] for k in range(3)]
