"""Electrical catalog parts: geometry proxies from vendor drawings plus the electrical template the
electrical verifier reads (ports, ratings, and WHERE EACH NUMBER COMES FROM).

Source tags used below
  [MW]    Mean Well LRS-350 / LRS-200 specification sheets (www.meanwell.com, file dates 2025-09-12)
  [BTT]   BIGTREETECH-SKR-mini-E3 repository, hardware/BTT SKR MINI E3 V3.0: _SIZE_20220301.pdf (outline, holes),
          _PIN.pdf (pins), _SCH.pdf (fuses F1 20 A/32 V and F2 T110 1.1 A/16 V, sense resistors 0R11, bed MOSFET
          WSK220N04), user manual; the 3D STEP gave the 14.2 mm component height
  [BTT-R] BIGTREETECH-Relay-V1.2 repository, "Relay V1.2-Operating Instruction.pdf" (80.32 x 36.19 mm, holes 74.17 x 29.21)
  [KLIP]  Klipper config/generic-bigtreetech-skr-mini-e3-v3.0.cfg, klippy/extras/temperature_sensors.cfg (thermistor
          R-T points with their own data-sheet links), tmc2208.py (current scaling, MAX_CURRENT 2.0 A)
  [SO]    omc-stepperonline.com product pages 17HS13-0404S1, 17HS16-2004S1, 17HS19-2004S1, 17HS24-2104S
  [MARLIN] Marlin 2.1.x Configuration.h MPC example values (40 W, 16.7 J/K, 0.068 W/K, sensor 0.22 1/s)
  [IEC]   IEC 60320-1 sheet C14: 10 A, 250 V (standard rating of the connector type)
  typical, unverified: a usual value for the part class that I could not fetch a data sheet for. Replace before purchase.
"""
from __future__ import annotations

import math

from build123d import Box, Cylinder, Pos, Rot

from ..electrical import Device, Electrical, Port
from . import Stock, part

TU = "typical, unverified"


def _ports_to_interfaces(ports: dict) -> dict:
    """Connector positions travel through `place` as interface points: [position, position + direction]."""
    out = {}
    for name, p in ports.items():
        if p.get("at") is not None:
            a, d = p["at"], p.get("dir", (0, 0, 1))
            out[f"port:{name}"] = [tuple(a), (a[0] + d[0], a[1] + d[1], a[2] + d[2])]
    return out


# ----------------------------------------------------------------- control board
@part
def skr_mini_e3_v3() -> Stock:
    """BIGTREETECH SKR Mini E3 V3.0 (103.75 x 70.25 mm, 4 on-board TMC2209). Local frame: PCB centred, underside on Z=0
    (stand it on >= 5 mm spacers), X along the long edge, power terminals at -X/-Y, motor connectors along +Y."""
    W, H, T = 103.75, 70.25, 1.6
    ox, oy = -W / 2, -H / 2
    holes = [(23.39, H - 3.22), (W - 18.20, H - 3.02), (5.53, 32.05), (37.34, 29.41), (W - 2.53, 2.56)]   # [BTT] SIZE drawing
    holes = [(x + ox, y + oy, 0.0) for x, y in holes]
    pcb = Pos(0, 0, T / 2) * Box(W, H, T)
    env = Pos(0, 0, T + 6.5) * Box(W - 1.0, H - 1.0, 13.0)       # component envelope (tallest part 14.2 above the PCB top)
    for x, y, _ in holes:
        pcb -= Pos(x, y, T / 2) * Cylinder(1.55, T)
        env -= Pos(x, y, T + 6.5) * Cylinder(4.0, 13.0)          # room for a cap head and its driver
    z = T + 8.0

    def v(x, y):   # vendor drawing coordinates (origin lower-left, scaled from the SIZE/PIN drawings, +/- 1 mm)
        return (x + ox, y + oy, z)

    up, edge = (0, 0, 1), (0, -1, 0)
    xh = dict(connector="JST-XH", max_a=3.0)
    drv = lambda step, dir_, en, addr: {"step": step, "dir": dir_, "enable": en, "uart": "PC11", "tx": "PC10", "uart_address": addr}
    ports = {
        "POWER": dict(kind="power_in", connector="screw-5.08", max_a=20.0, at=v(8.3, 3.5), dir=edge),
        "HB": dict(kind="heater_out", connector="screw-5.08", max_a=10.0, pin="PC9", at=v(21.6, 3.5), dir=edge),
        "E0": dict(kind="heater_out", connector="screw-5.08", max_a=5.0, pin="PC8", at=v(32.5, 3.5), dir=edge),
        "FAN2": dict(kind="fan_out", pin="PB15", at=v(45.1, 3.4), dir=up, **xh),
        "FAN0": dict(kind="fan_out", pin="PC6", at=v(53.1, 3.4), dir=up, **xh),
        "FAN1": dict(kind="fan_out", pin="PC7", at=v(53.1, 16.5), dir=up, **xh),
        "X-STOP": dict(kind="endstop_in", pin="PC0", at=v(61.3, 3.4), dir=up, **xh),
        "Y-STOP": dict(kind="endstop_in", pin="PC1", at=v(69.6, 3.4), dir=up, **xh),
        "Z-STOP": dict(kind="endstop_in", pin="PC2", at=v(77.9, 3.4), dir=up, **xh),
        "E0-STOP": dict(kind="endstop_in", pin="PC15", at=v(74.5, 16.5), dir=up, **xh),
        "THB": dict(kind="thermistor_in", pin="PC4", at=v(86.2, 3.4), dir=up, pullup_ohm=4700.0, adc_bits=12, **xh),
        "TH0": dict(kind="thermistor_in", pin="PA0", at=v(94.4, 3.4), dir=up, pullup_ohm=4700.0, adc_bits=12, **xh),
        "XM": dict(kind="stepper_out", pin=drv("PB13", "!PB12", "PB14", 0), group="X", conductors=4, at=v(13.2, 66.9), dir=up, **xh),
        "YM": dict(kind="stepper_out", pin=drv("PB10", "!PB2", "PB11", 2), group="Y", conductors=4, at=v(33.6, 66.9), dir=up, **xh),
        "ZAM": dict(kind="stepper_out", pin=drv("PB0", "PC5", "PB1", 1), group="Z", conductors=4, at=v(47.1, 66.9), dir=up, **xh),
        "ZBM": dict(kind="stepper_out", pin=drv("PB0", "PC5", "PB1", 1), group="Z", conductors=4, at=v(60.2, 66.9), dir=up, **xh),
        "EM": dict(kind="stepper_out", pin=drv("PB3", "!PB4", "PD1", 3), group="E", conductors=4, at=v(73.9, 66.9), dir=up, **xh),
        "PS-ON": dict(kind="signal_out", pin="PC13", at=v(61.5, 16.5), dir=up, **xh),
        "TFT": dict(kind="host", connector="dupont", max_a=2.0, pin="USART2 PA2/PA3", conductors=4, at=v(74.0, 25.0), dir=up),
    }
    ratings = {
        "supply_v": (12.0, 24.0), "input_fuse_a": 20.0, "stepper_drivers": 4,
        "driver": "TMC2209", "sense_resistor_ohm": 0.11, "driver_max_rms_a": 1.74, "driver_abs_max_rms_a": 2.0,
        "driver_rds_on_ohm": 0.17, "driver_max_v": 29.0, "output_resistance_ohm": 0.012, "logic_w": 1.5,
        "rail_5v_max_a": 3.0, "adc_bits": 12, "thermistor_pullup_ohm": 4700.0, "max_ambient_c": 60.0}
    sources = {
        "outline_holes": "[BTT] SIZE drawing: 103.75 x 70.25 mm, five 3.1 mm holes",
        "connector_positions": "[BTT] scaled from the SIZE/PIN drawings, +/- 1 mm",
        "pins": "[BTT] PIN drawing, cross-checked with [KLIP] generic-bigtreetech-skr-mini-e3-v3.0.cfg",
        "input_fuse_a": "[BTT] schematic F1: 20 A / 32 V",
        "sense_resistor_ohm": "[BTT] schematic 0R11; [KLIP] default 0.110",
        "driver_max_rms_a": "[KLIP] tmc2208.py: CS=31 -> 32*0.32/(32*(0.11+0.02)*sqrt(2)) = 1.74 A rms",
        "driver_abs_max_rms_a": "[KLIP] tmc2208.py MAX_CURRENT = 2.0",
        "driver_rds_on_ohm": f"TMC2209 data sheet rev 1.09 RDS(on) 170 mOhm per switch: recalled, analog.com not reachable ({TU})",
        "driver_max_v": f"TMC2209 data sheet VS max 29 V: recalled ({TU})",
        "HB.max_a / E0.max_a / fan max_a": f"10 A / 5 A / JST-XH contact 3 A: BTT's figures for sibling boards, not in the V3.0 manual ({TU})",
        "output_resistance_ohm": f"MOSFET + trace + terminal, assumed 12 mOhm ({TU}); WSK220N04 itself is a few mOhm",
        "logic_w": TU, "rail_5v_max_a": f"MP1584EN buck, 3 A device limit ([BTT] schematic part number; rating {TU})",
        "thermistor_pullup_ohm": "[BTT] schematic 4.7K on TH0/THB; [KLIP] default pullup 4700",
        "adc_bits": f"STM32G0B1 12-bit ADC ({TU}; Klipper sums 8 samples, not modelled)",
        "max_ambient_c": TU, "mass": TU, "cost": TU}
    return Stock(pcb + env, "CTRL-SKR-MINI-E3-V3", "BIGTREETECH SKR Mini E3 V3.0 control board", 0.07, material="abs",
                 ratings={"electrical": {"kind": "board", "ports": ports, "ratings": ratings, "sources": sources,
                                         "product": {'product': 'BIGTREETECH SKR Mini E3 V3.0', 'vendor': 'BIGTREETECH (Shenzhen Big Tree Technology)', 'part_number': 'SKR MINI E3 V3.0', 'form': 'assembled board', 'off_the_shelf': True, 'custom_pcb': False, 'builder_work': 'mount on spacers; land ferruled wires in the screw terminals; plug JST-XH housings; flash Klipper from SD card'}, "params": {"power_port": "POWER"}}, "stepper_drivers": 4, "approximate": True},
                 interfaces={"mount_holes_m3": holes, "standoff_min": 5.0, **_ports_to_interfaces(ports)}, cost_usd=35.0)


# ----------------------------------------------------------------- power supply
_LRS = {   # model: (watts, amps, efficiency, {115: A, 230: A}, inrush A, mass kg, cost)   [MW]
    "LRS-200-24": (211.2, 8.8, 0.895, {115: 4.0, 230: 2.2}, 60.0, 0.66, 28.0),
    "LRS-350-24": (350.4, 14.6, 0.88, {115: 6.8, 230: 3.4}, 60.0, 0.76, 35.0),
}


def psu_for_load(watts: float, margin: float = 0.85) -> str:
    """Smallest catalog supply whose rating covers `watts` with the margin."""
    for model, row in sorted(_LRS.items(), key=lambda kv: kv[1][0]):
        if watts <= row[0] * margin:
            return model
    raise ValueError(f"no catalog supply for {watts:.0f} W")


@part
def psu_lrs(model: str = "LRS-350-24") -> Stock:
    """Mean Well LRS enclosed 24 V supply, 215 x 115 x 30 mm (LRS-200-24 or LRS-350-24). Local frame: underside on Z=0,
    centred, terminal strip at the -X end; four M4 holes in the base on 150 x 50 mm, usable depth 3 mm."""
    if model not in _LRS:
        raise ValueError(f"psu_lrs model must be one of {sorted(_LRS)}")
    watts, amps, eff, ac, inrush, mass, cost = _LRS[model]
    body = Pos(0, 0, 15) * Box(215, 115, 30)
    holes = [(x, y, 0.0) for x in (-75.0, 75.0) for y in (-25.0, 25.0)]
    xt, zt = -107.5 + 8.0, 22.0
    pitch = 9.5
    ys = [(-4 + i) * pitch for i in range(9)]            # nine-way barrier strip
    out = (-1, 0, 0.6)
    scr = dict(connector="screw-psu", max_a=20.0)
    ports = {"L": dict(kind="mains_in", at=(xt, ys[0], zt), dir=out, **scr), "N": dict(kind="mains_in", at=(xt, ys[1], zt), dir=out, **scr),
             "FG": dict(kind="pe", at=(xt, ys[2], zt), dir=out, **scr)}
    for i in range(3):
        ports[f"V-{i + 1}"] = dict(kind="power_out", at=(xt, ys[3 + i], zt), dir=out, **scr)
        ports[f"V+{i + 1}"] = dict(kind="power_out", at=(xt, ys[6 + i], zt), dir=out, **scr)
    ratings = {"watts": watts, "volts": 24.0, "amps": amps, "efficiency": eff, "ac_current_a": ac, "inrush_a": inrush,
               "full_load_ambient_c": 50.0, "derate_to_frac_at_70c": 0.6, "has_fan": model == "LRS-350-24"}
    sources = {k: "[MW] specification table" for k in ("watts", "amps", "efficiency", "ac_current_a", "inrush_a")}
    sources.update({"full_load_ambient_c": "[MW] derating curve: 100 % to 50 degC, 60 % at 70 degC",
                    "dimensions": "[MW] 215*115*30 mm (L*W*H)", "mass": "[MW] packing weight",
                    "mount_holes": "[MW] mechanical drawing, case 207A: 4-M4 L=3mm in the base, 150 x 50 mm"
                                   + ("" if model == "LRS-350-24" else f" (drawing read for the LRS-350 only; LRS-200 pattern {TU})"),
                    "terminal_positions": f"nine-way strip at one end, 9.5 mm pitch read off the drawing, +/- 2 mm ({TU})",
                    "has_fan": "[MW] LRS-350: built-in fan, on at 50 degC internal", "cost": TU})
    return Stock(body, f"PSU-{model}", f"Mean Well {model}: 24 V {amps} A {watts:.0f} W enclosed supply", mass, material="steel",
                 ratings={"electrical": {"kind": "psu", "ports": ports, "ratings": ratings, "sources": sources, "product": dict(product=f"MEAN WELL {model}", vendor="MEAN WELL", part_number=model, form="module", off_the_shelf=True, custom_pcb=False, builder_work="set the 115/230 V selector; ring or fork terminals on mains, earth and DC wires"), "params": {}},
                          "watts": watts},
                 interfaces={"mount_holes_m4": holes, "thread_depth": 3.0, **_ports_to_interfaces(ports)}, cost_usd=cost)


# ----------------------------------------------------------------- mains inlet, relay, host
@part
def iec_inlet_c14(fuse_a: float = 6.3) -> Stock:
    """IEC 60320 C14 appliance inlet with rocker switch and 5 x 20 mm fuse drawer (screw flange). Local frame: flange
    rear face on Z=0 (it sits against the outside of a panel), body through the panel along -Z, flange 60 x 50 x 3 on +Z;
    two M3 holes 40 mm apart on X. Panel cut-out 48 x 28. Geometry is typical, unverified."""
    flange = Pos(0, 0, 1.5) * Box(50, 60, 3)
    body = Pos(0, 0, -15) * Box(27, 47, 30)
    holes = [(0.0, -25.0, 0.0), (0.0, 25.0, 0.0)]
    for x, y, _ in holes:
        flange -= Pos(x, y, 1.5) * Cylinder(1.7, 3)
    back = (0, 0, -1)
    fs = dict(connector="faston-6.3", max_a=10.0)
    ports = {"L": dict(kind="mains_out", at=(-6.0, -12.0, -30.0), dir=back, **fs),
             "N": dict(kind="mains_out", at=(6.0, -12.0, -30.0), dir=back, **fs),
             "PE": dict(kind="pe", at=(0.0, 12.0, -30.0), dir=back, multi=True, **fs)}
    ratings = {"amps": 10.0, "volts": 250.0, "fuse_a": fuse_a, "fuse_type": "T (time-lag) 5x20 mm", "switch": "2-pole rocker"}
    sources = {"amps": "[IEC] C14: 10 A 250 V", "fuse_a": "chosen by the design from the standard 5x20 values",
               "geometry": TU, "mass": TU, "cost": TU}
    return Stock(flange + body, f"INLET-C14-SW-FUSE-T{fuse_a:g}A", f"IEC C14 inlet with switch and T{fuse_a:g}A fuse", 0.035, material="abs",
                 ratings={"electrical": {"kind": "inlet", "ports": ports, "ratings": ratings, "sources": sources, "product": {'product': 'IEC 60320 C14 inlet module with rocker switch and 5x20 mm fuse drawer, 10 A 250 V', 'vendor': 'commodity (several makers)', 'part_number': None, 'form': 'module', 'off_the_shelf': True, 'custom_pcb': False, 'builder_work': 'cut the panel opening; crimp 6.3 mm faston receptacles; fit the T fuse'}, "params": {}},
                          "approximate": True},
                 interfaces={"mount_holes_m3": holes, "cutout": (28.0, 48.0), **_ports_to_interfaces(ports)}, cost_usd=4.0)


@part
def relay_btt_v12() -> Stock:
    """BIGTREETECH Relay V1.2 mains relay module (80.32 x 36.19 mm PCB). Local frame: PCB centred, underside on Z=0,
    mains terminals at +X, logic header at -X; four M3 holes on 74.17 x 29.21 mm."""
    W, H, T = 80.32, 36.19, 1.6
    pcb = Pos(0, 0, T / 2) * Box(W, H, T)
    env = Pos(4.0, 0, T + 9.0) * Box(58.0, H - 9.0, 18.0)
    holes = [(x, y, 0.0) for x in (-74.17 / 2, 74.17 / 2) for y in (-29.21 / 2, 29.21 / 2)]
    for x, y, _ in holes:
        pcb -= Pos(x, y, T / 2) * Cylinder(1.6, T)
    sc = dict(connector="screw-5.08", max_a=10.0)
    ports = {"LIN": dict(kind="series", at=(33.0, -9.0, 12.0), dir=(1, 0, 0), **sc),
             "LOT": dict(kind="series", at=(33.0, 9.0, 12.0), dir=(1, 0, 0), **sc),
             "ctrl": dict(kind="signal_in", connector="JST-XH", max_a=3.0, at=(-33.0, 0.0, 8.0), dir=(0, 0, 1), conductors=3)}
    ratings = {"contact_a": 10.0, "volts": 265.0, "resistance_ohm": 0.0, "supply_w": 0.5}
    sources = {"outline_holes": "[BTT-R] dimensional drawing", "volts": "[BTT-R] AC input 85-265 V",
               "contact_a": f"relay contact rating not in the manual ({TU})", "height": TU, "supply_w": TU, "mass": TU, "cost": TU}
    return Stock(pcb + env, "RELAY-BTT-V1.2", "BIGTREETECH Relay V1.2 mains relay module", 0.03, material="abs",
                 ratings={"electrical": {"kind": "relay", "ports": ports, "ratings": ratings, "sources": sources,
                                         "product": {'product': 'BIGTREETECH Relay V1.2', 'vendor': 'BIGTREETECH', 'part_number': 'Relay V1.2', 'form': 'assembled board', 'off_the_shelf': True, 'custom_pcb': False, 'builder_work': 'mount on spacers; ferrules on the mains wires; 3-wire JST-XH lead to PS-ON'}, "params": {"through": {"LIN": "LOT", "LOT": "LIN"}, "cuts": "psu"}}, "approximate": True},
                 interfaces={"mount_holes_m3": holes, "standoff_min": 4.0, **_ports_to_interfaces(ports)}, cost_usd=9.0)


@part
def raspberry_pi_zero2w() -> Stock:
    """Raspberry Pi Zero 2 W (65 x 30 mm): the Klipper host. Local frame: PCB centred, underside on Z=0; four M2.5 holes
    on 58 x 23 mm; 40-pin header along +Y."""
    T = 1.5
    pcb = Pos(0, 0, T / 2) * Box(65, 30, T)
    env = Pos(0, -2.0, T + 1.5) * Box(52, 18, 3.0)
    holes = [(x, y, 0.0) for x in (-29.0, 29.0) for y in (-11.5, 11.5)]
    for x, y, _ in holes:
        pcb -= Pos(x, y, T / 2) * Cylinder(1.4, T)
    ports = {"GPIO": dict(kind="host", connector="dupont", max_a=2.0, conductors=4, at=(-20.0, 11.5, T + 3.0), dir=(0, 0, 1),
                          pin="5V, GND, GPIO14 TXD, GPIO15 RXD")}
    ratings = {"supply_w": 3.0, "volts": 5.0}
    sources = {"geometry": f"Raspberry Pi Zero mechanical drawing 65 x 30, holes 58 x 23 (recalled; {TU})",
               "supply_w": f"about 0.6 A at 5 V under load ({TU})", "cost": TU}
    return Stock(pcb + env, "HOST-RPI-ZERO-2W", "Raspberry Pi Zero 2 W (Klipper host, UART to the board's TFT header)", 0.011,
                 material="abs",
                 ratings={"electrical": {"kind": "host", "ports": ports, "ratings": ratings, "sources": sources, "product": {'product': 'Raspberry Pi Zero 2 W', 'vendor': 'Raspberry Pi Ltd', 'part_number': 'Raspberry Pi Zero 2 W', 'form': 'assembled board', 'off_the_shelf': True, 'custom_pcb': False, 'builder_work': 'solder or buy with the 40-pin header; 4-wire dupont lead to the TFT header; install Klipper on the SD card'}, "params": {}},
                          "approximate": True},
                 interfaces={"mount_holes_m2.5": holes, "standoff_min": 3.0, **_ports_to_interfaces(ports)}, cost_usd=15.0)


# ----------------------------------------------------------------- heaters, sensors, protection
THERMISTORS = {   # Klipper sensor_type -> R-T points [KLIP] temperature_sensors.cfg (each cites the maker's table)
    "ATC Semitec 104NT-4-R025H42G": [(25.0, 100000.0), (160.0, 1074.0), (300.0, 82.78)],
    "ATC Semitec 104GT-2": [(20.0, 126800.0), (150.0, 1360.0), (300.0, 80.65)],
    "Generic 3950": [(25.0, 100000.0), (150.0, 1770.0), (250.0, 230.0)],
    "EPCOS 100K B57560G104F": [(25.0, 100000.0), (150.0, 1641.9), (250.0, 226.15)],
}


@part
def heater_cartridge(watts: float = 40.0, volts: float = 24.0) -> Stock:
    """Hotend heater cartridge, 6 mm x 20 mm. Local frame: axis along X, centred."""
    ports = {"in": dict(kind="heater", connector="ferrule", max_a=5.0, at=(10.0, 0.0, 0.0), dir=(1, 0, 0))}
    ratings = {"watts": watts, "volts": volts, "max_temp_c": 500.0}
    sources = {"watts": f"E3D-style 6 x 20 mm cartridge, {watts:g} W at {volts:g} V nominal ({TU}; +/-10 % is usual)",
               "thermal": "[MARLIN] MPC example hotend (16.7 J/K, 0.068 W/K) used as the cross-check; block capacity from the "
                          f"V6 block's size ({TU})", "cost": TU}
    params = {"model": "block",
              # V6 block 23 x 16 x 11.5 aluminium (about 9.7 g -> 8.7 J/K) + brass nozzle + heat-break end + sensor: 12 J/K
              "block_capacity_j_k": 12.0, "cartridge_capacity_j_k": 1.5, "block_area_m2": 1.63e-3, "block_height_m": 0.0115,
              "emissivity": 0.3, "heatbreak_w_k": 0.025, "cartridge_contact_w_k": 2.0}
    return Stock(Rot(0, 90, 0) * Cylinder(3.0, 20.0), f"HEATER-CART-{volts:g}V-{watts:g}W", f"Heater cartridge 6x20 mm, {volts:g} V {watts:g} W",
                 0.005, material="stainless304",
                 ratings={"electrical": {"kind": "heater", "ports": ports, "ratings": ratings, "sources": sources, "product": dict(product=f"E3D V6 heater cartridge {volts:g} V {watts:g} W (6 x 20 mm)", vendor="E3D-Online", part_number=None, form="component", off_the_shelf=True, custom_pcb=False, builder_work="clamp in the heater block; ferrules on the leads or butt-splice to the loom"), "params": params},
                          "approximate": True},
                 interfaces=_ports_to_interfaces(ports), cost_usd=6.0)


@part
def thermistor_cartridge(sensor_type: str = "ATC Semitec 104NT-4-R025H42G") -> Stock:
    """Hotend thermistor cartridge, 3 mm x 15 mm (glass NTC in a metal sleeve). Local frame: axis along X, centred."""
    ports = {"out": dict(kind="thermistor", connector="molex-microfit", max_a=1.0, at=(7.5, 0.0, 0.0), dir=(1, 0, 0))}
    sources = {"points": "[KLIP] temperature_sensors.cfg", "tau_s": "[MARLIN] MPC_SENSOR_RESPONSIVENESS 0.22 1/s -> 4.5 s",
               "max_temp_c": f"glass bead 300 degC ({TU})", "cost": TU}
    return Stock(Rot(0, 90, 0) * Cylinder(1.5, 15.0), "THERMISTOR-CART-104NT", f"Thermistor cartridge 3x15 mm ({sensor_type})", 0.002,
                 material="stainless304",
                 ratings={"electrical": {"kind": "thermistor", "ports": ports, "ratings": {"max_temp_c": 300.0}, "sources": sources,
                                         "product": {'product': 'E3D V6 thermistor cartridge (Semitec 104NT-4-R025H42G)', 'vendor': 'E3D-Online', 'part_number': None, 'form': 'component', 'off_the_shelf': True, 'custom_pcb': False, 'builder_work': 'plugs into its extension lead; crimp JST-XH at the board end'}, "params": {"sensor_type": sensor_type, "points": THERMISTORS[sensor_type], "tau_s": 4.5,
                                                    "node": "block"}}, "approximate": True},
                 interfaces=_ports_to_interfaces(ports), cost_usd=5.0)


@part
def bed_heater_pad(size_x: float = 200.0, size_y: float = 200.0, watts: float = 200.0, volts: float = 24.0) -> Stock:
    """Silicone heater pad with adhesive face and an embedded 100 k NTC (beta 3950), 1.5 mm thick. Local frame: centred,
    adhesive (top) face on Z=0; leads leave from the middle of the -Y edge."""
    ports = {"in": dict(kind="heater", connector="ferrule", max_a=15.0, at=(-8.0, -size_y / 2, -0.75), dir=(0, -1, 0)),
             "ntc": dict(kind="thermistor", connector="JST-XH", max_a=1.0, at=(8.0, -size_y / 2, -0.75), dir=(0, -1, 0))}
    ratings = {"watts": watts, "volts": volts, "max_temp_c": 180.0}
    sources = {"watts": f"silicone pad class, {watts:g} W at {volts:g} V ({TU}; makers quote +/-10 %)",
               "max_temp_c": f"silicone pad continuous limit about 180 degC; acrylic adhesive about 150 degC ({TU})",
               "ntc": "[KLIP] 'Generic 3950' points (Keenovo R-T table)", "cost": TU}
    params = {"model": "plate", "bond_w_m2k": 1000.0, "emissivity_bottom": 0.9, "emissivity_top": 0.9, "emissivity_plate": 0.1}
    return Stock(Pos(0, 0, -0.75) * Box(size_x, size_y, 1.5), f"HEATER-SIL-{size_x:g}x{size_y:g}-{volts:g}V-{watts:g}W",
                 f"Silicone bed heater pad {size_x:g} x {size_y:g} mm, {volts:g} V {watts:g} W, with 100k NTC", 0.04 + size_x * size_y * 2.0e-6,
                 material="rubber_gt2",
                 ratings={"electrical": {"kind": "heater", "ports": ports, "ratings": ratings, "sources": sources, "product": dict(product=f"Silicone heater pad {size_x:g} x {size_y:g} mm, {volts:g} V {watts:g} W, adhesive backed, 100k NTC 3950 embedded", vendor="commodity (e.g. Keenovo)", part_number=None, form="component", off_the_shelf=True, custom_pcb=False, builder_work="stick to the degreased plate; ferrules on the power leads; JST-XH on the NTC leads"), "params": params},
                          "watts": watts, "approximate": True},
                 interfaces=_ports_to_interfaces(ports), cost_usd=18.0)


@part
def thermal_fuse(trip_c: float = 133.0, hold_c: float = 109.0, amps: float = 10.0) -> Stock:
    """Axial one-shot thermal cut-off, 4 mm x 11 mm, taped against the part it protects and wired in series with the
    heater. Local frame: axis along X, centred."""
    ports = {"a": dict(kind="series", connector="ferrule", max_a=amps, at=(-5.5, 0, 0), dir=(-1, 0, 0)),
             "b": dict(kind="series", connector="ferrule", max_a=amps, at=(5.5, 0, 0), dir=(1, 0, 0))}
    ratings = {"trip_c": trip_c, "hold_c": hold_c, "amps": amps, "resistance_ohm": 0.002}
    sources = {"trip_c": f"SEFUSE SF-E class: Tf {trip_c:g} degC, holding {hold_c:g} degC, {amps:g} A 250 V AC: recalled ({TU}). "
                         "DC interrupting capacity at 24 V is not stated by the makers.", "cost": TU}
    return Stock(Rot(0, 90, 0) * Cylinder(2.0, 11.0), f"TCO-{trip_c:g}C-{amps:g}A", f"Thermal cut-off {trip_c:g} degC {amps:g} A", 0.001,
                 material="brass",
                 ratings={"electrical": {"kind": "thermal_fuse", "ports": ports, "ratings": ratings, "sources": sources,
                                         "product": dict(product=f"Axial thermal cut-off, Tf {trip_c:g} degC, {amps:g} A (SEFUSE SF-E class)", vendor="commodity (Schott/NEC SEFUSE or equivalent)", part_number=None, form="component", off_the_shelf=True, custom_pcb=False, builder_work="crimp (never solder) in series with the heater lead; tape against the plate with polyimide tape"), "params": {"through": {"a": "b", "b": "a"}, "node": "plate"}}, "approximate": True},
                 interfaces=_ports_to_interfaces(ports), cost_usd=1.0)


@part
def mosfet_module(amps: float = 25.0) -> Stock:
    """External heated-bed MOSFET module (60 x 50 mm PCB with heat sink). Local frame: PCB centred, underside on Z=0;
    four M3 holes on 52 x 42 mm. Supply terminals at -X, bed terminals at +X, control input at -Y. Typical, unverified."""
    T = 1.6
    pcb = Pos(0, 0, T / 2) * Box(60, 50, T)
    env = Pos(0, 0, T + 10) * Box(46, 34, 20)
    holes = [(x, y, 0.0) for x in (-26.0, 26.0) for y in (-21.0, 21.0)]
    for x, y, _ in holes:
        pcb -= Pos(x, y, T / 2) * Cylinder(1.6, T)
    sc = dict(connector="screw-5.08", max_a=amps)
    ports = {"pwr": dict(kind="power_in", at=(-27.0, 0.0, 10.0), dir=(-1, 0, 0), **sc),
             "out": dict(kind="switched_out", at=(27.0, 0.0, 10.0), dir=(1, 0, 0), **sc),
             "ctrl": dict(kind="switch_in", connector="JST-XH", max_a=3.0, at=(0.0, -22.0, 8.0), dir=(0, -1, 0))}
    ratings = {"amps": amps, "resistance_ohm": 0.008}
    sources = {"amps": f"generic 'heat bed power module', sold as {amps:g} A ({TU})", "resistance_ohm": TU, "geometry": TU, "cost": TU}
    return Stock(pcb + env, f"MOSFET-BED-{amps:g}A", f"Heated-bed MOSFET module, {amps:g} A", 0.04, material="abs",
                 ratings={"electrical": {"kind": "mosfet", "ports": ports, "ratings": ratings, "sources": sources,
                                         "product": dict(product=f"Heated-bed MOSFET module {amps:g} A", vendor="commodity", part_number=None, form="assembled board", off_the_shelf=True, custom_pcb=False, builder_work="mount on spacers; ferruled wires in the screw terminals"), "params": {"through": {"out": "ctrl"}, "feed": "pwr"}}, "approximate": True},
                 interfaces={"mount_holes_m3": holes, "standoff_min": 4.0, **_ports_to_interfaces(ports)}, cost_usd=6.0)


# ----------------------------------------------------------------- electrical data for the existing catalog parts
MOTOR_ELECTRICAL = {   # catalog SKU -> winding data [SO]
    "NEMA17-34": {"model": "17HS13-0404S1", "rated_current_a": 0.4, "phase_resistance_ohm": 30.0, "phase_inductance_mh": 37.0,
                  "holding_torque_nmm": 260.0},
    "NEMA17-40": {"model": "17HS16-2004S1", "rated_current_a": 2.0, "phase_resistance_ohm": 1.3, "phase_inductance_mh": 2.6,
                  "holding_torque_nmm": 450.0},
    "NEMA17-48": {"model": "17HS19-2004S1", "rated_current_a": 2.0, "phase_resistance_ohm": 1.6, "phase_inductance_mh": 3.0,
                  "holding_torque_nmm": 590.0},
    "NEMA17-60": {"model": "17HS24-2104S", "rated_current_a": 2.1, "phase_resistance_ohm": 1.6, "phase_inductance_mh": 3.0,
                  "holding_torque_nmm": 760.0},
}
_ALIASES = {"rated_current_a": ("rated_current_a", "rated_current", "current_a"),
            "phase_resistance_ohm": ("phase_resistance_ohm", "resistance_ohm", "phase_resistance"),
            "phase_inductance_mh": ("phase_inductance_mh", "inductance_mh", "phase_inductance")}


def _ots(product, vendor, part_number, form, work) -> dict:
    return dict(product=product, vendor=vendor, part_number=part_number, form=form, off_the_shelf=True, custom_pcb=False, builder_work=work)


def _template_for(c) -> dict | None:
    sku = c.sku or ""
    one = lambda kind, conn, n=2, max_a=3.0: {"x": dict(kind=kind, connector=conn, max_a=max_a, conductors=n)}
    if sku.startswith("NEMA17"):
        base = dict(MOTOR_ELECTRICAL.get(sku, {}))
        src = {k: f"[SO] {base.get('model', '?')} product page" for k in _ALIASES}
        for k, names in _ALIASES.items():      # the catalog's own vendor data wins when it is there
            for nm in names:
                if nm in c.ratings:
                    base[k] = float(c.ratings[nm])
                    src[k] = "catalog part ratings (mechloop.parts)"
                    break
        base.setdefault("insulation_class_c", 130.0)
        src["insulation_class_c"] = "[SO] class B 130 degC"
        pn = c.ratings.get("vendor_part") or base.get("model")
        return {"kind": "stepper", "ports": {"coils": dict(kind="stepper", connector="JST-XH", max_a=3.0, conductors=4)},
                "ratings": base, "sources": src, "params": {},
                "product": _ots(f"NEMA 17 stepper motor {pn}", "STEPPERONLINE", pn, "component", "crimp a 4-way JST-XH on the motor lead (or buy the lead)")}
    if sku.startswith("EXTRUDER"):
        return {"kind": "stepper", "ports": {"coils": dict(kind="stepper", connector="JST-XH", max_a=3.0, conductors=4)},
                "ratings": {"rated_current_a": 1.0, "phase_resistance_ohm": 3.5, "phase_inductance_mh": 4.5, "holding_torque_nmm": 160.0,
                            "insulation_class_c": 130.0},
                "sources": {k: f"pancake NEMA 17 (about 20 mm body) winding, {TU}" for k in
                            ("rated_current_a", "phase_resistance_ohm", "phase_inductance_mh", "holding_torque_nmm")}, "params": {},
                "product": _ots("Direct-drive extruder with pancake NEMA 17 (complete unit)", "commodity", None, "component",
                                "crimp a 4-way JST-XH on the motor lead")}
    if sku.startswith("FAN"):
        amps = {"FAN-3010": 0.05, "FAN-4010": 0.07}.get(sku, 0.1)
        return {"kind": "fan", "ports": {"in": dict(kind="fan", connector="JST-XH", max_a=3.0)},
                "ratings": {"current_a": amps, "volts": 24.0}, "sources": {"current_a": f"24 V axial fan of this size ({TU})"}, "params": {},
                "product": _ots(f"24 V axial fan {sku[4:6]} x {sku[4:6]} x 10 mm, 2-wire", "commodity", None, "component", "crimp a 2-way JST-XH")}
    if sku.startswith("ENDSTOP"):
        return {"kind": "endstop", "ports": {"out": dict(kind="endstop", connector="JST-XH", max_a=1.0, conductors=3)},
                "ratings": {}, "sources": {}, "params": {},
                "product": _ots("Mechanical endstop module (microswitch on a small PCB, 3-pin)", "commodity", None, "assembled board",
                                "crimp a 3-way JST-XH on its lead")}
    return None


def device_from(el: Electrical, design, component: str, name: str | None = None, **params) -> Device:
    """Make the electrical Device for a placed catalog part and add it to `el`. Connector positions come from the
    part's placed interfaces; a port without one sits at the centre of the part."""
    c = design.get(component)
    tpl = c.ratings.get("electrical")
    if not isinstance(tpl, dict):
        tpl = _template_for(c)
    if tpl is None:
        raise ValueError(f"{component} ({c.sku}) has no electrical template")
    bb = c.shape.bounding_box()
    ctr = ((bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2)
    ports = {}
    for pn, p in tpl["ports"].items():
        pts = c.meta.get("interfaces", {}).get(f"port:{pn}")
        at = tuple(pts[0]) if pts else ctr
        d = tuple(b - a for a, b in zip(pts[0], pts[1])) if pts else None
        ports[pn] = Port(pn, p["kind"], p.get("connector", ""), p.get("max_a"), p.get("pin"), p.get("conductors", 2), at, d,
                         p.get("group"), p.get("multi", False),
                         {"body": c.body, **{k: v for k, v in p.items() if k in ("pullup_ohm", "adc_bits")}})
    dev = Device(name or component, tpl["kind"], component, ports, dict(tpl.get("ratings", {})), dict(tpl.get("sources", {})),
                 {**tpl.get("params", {}), **params}, dict(tpl.get("product", {})))
    return el.add(dev)


def embedded_device(el: Electrical, design, component: str, name: str, kind: str, port: str, port_kind: str, at=None,
                    ratings=None, sources=None, **params) -> Device:
    """A device that is part of another catalog part (the NTC moulded into a heater pad): same CAD component."""
    c = design.get(component)
    src = el.devices.get(component)
    p0 = src.ports.get(port) if src else None
    bb = c.shape.bounding_box()
    pos = at or (p0.at if p0 else ((bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2))
    if p0 is not None:
        del src.ports[port]
    dev = Device(name, kind, component, {"out": Port("out", port_kind, p0.connector if p0 else "JST-XH", 1.0, None, 2, pos,
                                                       p0.direction if p0 else None, extra={"body": c.body})},
                 dict(ratings or {}), dict(sources or {}), params,
                 {**(src.product if src else {}), "product": f"part of: {(src.product.get('product') if src else component)}",
                  "builder_work": "none (moulded into the part)"})
    return el.add(dev)


# ----------------------------------------------------------------- BOM for what is not a CAD part
WIRE_COST_PER_M = {"pvc": 0.25, "pvc105": 0.8, "silicone": 0.6, "ptfe": 1.0, "fiberglass": 1.0}    # per conductor, typical, unverified
CONNECTOR_COST = {"JST-XH": 0.15, "JST-VH": 0.3, "ferrule": 0.03, "ring-M4": 0.1, "faston-6.3": 0.1, "faston-4.8": 0.1,
                  "dupont": 0.1, "molex-microfit": 0.4, "screw-5.08": 0.0, "screw-psu": 0.0, "solder": 0.0, "usb": 0.0}


def add_electrical_bom(el: Electrical, design) -> None:
    """Wire by the metre (per gauge and insulation), crimp housings/terminals, sleeve and ties go into design.bom_extras
    so the ratings verifier's BOM and cost include them. Prices are typical, unverified."""
    lengths, conns = {}, {}
    for w in el.wires:
        key = (w.awg, w.insulation)
        lengths[key] = lengths.get(key, 0.0) + el.wire_length(w) * w.conductors * 1e-3
        for ref, override in ((w.a, w.connector_a), (w.b, w.connector_b)):
            _, p = el.port(ref)
            cn = override or (p.connector if p else "")
            if cn.startswith("screw"):
                cn, n = "ferrule", w.conductors
            else:
                n = 1 if cn.startswith(("JST", "molex", "dupont")) else w.conductors
            if cn:
                conns[cn] = conns.get(cn, 0) + n
    for (awg, ins), m in sorted(lengths.items()):
        design.bom_extra(f"WIRE-AWG{awg}-{ins.upper()}-M", int(math.ceil(m)), WIRE_COST_PER_M.get(ins, 0.5) * (1.0 + (22 - awg) * 0.15))
    for cn, n in sorted(conns.items()):
        design.bom_extra(f"CONN-{cn.upper()}", n, CONNECTOR_COST.get(cn, 0.2))
    flex = sum(1 for lm in el.looms.values() for s in lm.spans() if s[3])
    total = sum(lm.length() for lm in el.looms.values()) * 1e-3
    design.bom_extra("SLEEVE-BRAIDED-8MM-M", int(math.ceil(total)), 0.8)
    design.bom_extra("CABLE-TIE-100MM", 4 * sum(len(lm.route) for lm in el.looms.values()) // 2 + 2 * flex, 0.02)
