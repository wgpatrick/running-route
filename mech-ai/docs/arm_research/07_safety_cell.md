# 07 - Safety, standards and cell integration for the mechloop arm

Scope: a home/hobby workshop cell holding the mechloop printer (hotend about 250 C, bed about 80 C,
Class 1M line laser, mains PSU inside, front door planned later), a flatbed scanner, parts trays and
a small arm we design ourselves (payload 0.2-1 kg, reach 300-600 mm) that sometimes runs unattended.

This note is not a compliance argument. Nothing hobby-built here will be certified, and the standards
are written for industrial machines with trained users. What the standards give us is a vocabulary
and a set of numbers to borrow so that our own rules are not invented from nothing. Each section ends
with what we adopt. Section 9 is a checklist written so that items can become verifier checks.

## 0. What the repo already has (and the gap it leaves)

From `docs/ELECTRICAL.md` and the generated `printer.cfg` (printer_v12):

- `[verify_heater extruder]` and `[verify_heater heater_bed]` are configured, so Klipper shuts down
  on a heater that does not track its target (thermal runaway detection in software).
- A 133 C axial thermal cut-off is crimped in series with the bed heater (hardware, independent of
  firmware). The hotend has no equivalent independent cut-off; its only independent path is the relay
  ahead of the supply.
- A mains contactor sits ahead of the 24 V supply. It is switched from a Raspberry Pi GPIO by
  Moonraker (`[power printer] type: gpio, off_when_shutdown: True, locked_while_printing: True`),
  not by Klipper and not by any hardware chain.

The gap: every path that removes printer power today runs through software (Klipper detects a
fault, goes to shutdown, Moonraker sees the shutdown, Moonraker drops a GPIO). If the Pi hangs,
Moonraker crashes, or the SD card corrupts, nothing removes power. An e-stop button that only calls
`printer.emergency_stop` inherits the same weakness. The recommended architecture (section 6) keeps
this path as a convenient secondary layer and adds a hardwired chain that opens the contactor coil
directly.

## 1. The standards in plain terms

| Standard | What it is | What a hobby cell borrows |
|---|---|---|
| ISO 10218-1:2025 | Safety of industrial robots, written for the robot manufacturer. The 2025 edition absorbed the content of ISO/TS 15066 (collaborative operation), added robot classes (Class I / Class II, with a maximum-force test for Class I), clarified functional-safety requirements and added cybersecurity. | Required safety functions: protective stop, emergency stop, reduced speed for teaching (classically 250 mm/s at the tool), speed and separation monitoring, power and force limiting, axis/space limiting. |
| ISO 10218-2:2025 | Robot applications and robot cells, written for the integrator. Covers the layout, guards, end-effectors, manual load/unload, and the risk assessment of the whole cell. | The idea that the cell, not the arm, is the unit of safety. The gripper, the printer, the hot parts and the laser all belong in one risk assessment. |
| ISO/TS 15066:2016 (now folded into 10218) | Collaborative robots. Four modes: safety-rated monitored stop, hand guiding, speed and separation monitoring, power and force limiting (PFL). PFL gives biomechanical limits for 29 body regions, split into quasi-static (clamping) and transient (impact) contact, force limits for blunt contact and pressure limits for semi-sharp contact. Many values are explicitly provisional. | Force numbers to design against (section 3). The rule that clamping is worse than a free impact, so pinch points matter more than peak speed. |
| ISO 13849-1:2023 | Functional safety of control systems. A safety function gets a required Performance Level (PLr, a to e) from a risk graph: severity, frequency of exposure, possibility of avoidance. The achieved PL comes from architecture (Category B, 1, 2, 3, 4), component reliability (MTTFd), diagnostic coverage and common-cause measures. Category 3 means a single fault does not lose the safety function, and reaches at most PLd. | The architecture categories as a design language: our e-stop should be at least "Category 1 in spirit" (well-tried components, positive-opening contacts, de-energize to trip) and ideally two channels. We do not compute MTTFd. |
| IEC 60204-1 | Electrical equipment of machines. Defines stop categories: 0 = remove power immediately; 1 = controlled stop, then remove power; 2 = controlled stop, power kept. An emergency stop must be category 0 or 1, never 2. Also: de-energize to trip, protective earth, colour codes, a supply disconnect, no automatic restart after power returns. | Stop categories; e-stop must remove energy, not just send a stop command; no automatic restart; protective earth on every metal part a hand can touch. |
| ISO 13850 / IEC 60947-5-5 | Emergency stop function and devices. Red mushroom actuator on yellow, latching until deliberately reset, direct (positive) opening contacts that are forced apart by the actuator and do not depend on a spring. Resetting the button must not by itself restart the machine. | Buy a real e-stop button (they are cheap). Do not use an ordinary red pushbutton. |
| IEC 60825-1 | Laser product classes. Class 1M is safe to the naked eye but not when viewed through, or refocused by, optics (magnifiers, binoculars, lenses). | Keep lenses, cameras with focusing optics and polished parts carried by the arm out of the beam, or interlock the laser to arm position. |

Our adopted subset, stated once: the cell has a hardwired, latching, de-energize-to-trip emergency
stop that removes power from the arm motors, the printer heaters and the laser (stop category 0 for
heaters and laser, category 0 or 1 for the arm); the arm is designed to be inherently force-limited
so that clamping a hand is painful rather than injurious; software limits (speed, force, zones,
collision detection) sit on top of that and are not trusted alone; and the printer and arm never
share space without an explicit, timed-out handshake.

## 2. Hazards

| Hazard | Source in this cell | Severity (hobby scale) | Likelihood without measures |
|---|---|---|---|
| Pinch / crush | Arm links closing on each other or against the printer frame, the trays, the bench or a wall; gripper fingers; printer bed and gantry; scanner lid | Moderate (finger bruise, laceration) with a small arm; higher at the gripper if it is a geared, non-backdrivable drive | High when a person reaches in while the arm moves |
| Impact | Arm swinging into a head or hand; carried part hitting a person | Low-moderate at 1 kg and <1 m/s; eye injury from a sharp part or tool is the worst case | Medium |
| Hot surfaces | Nozzle 250 C, heater block, bed 80 C, freshly printed parts | Burns to a person; for the arm, melted printed links, burnt cable jackets, a gripper picking a part still soft | High for the arm if keep-out zones are not enforced |
| Laser | Class 1M line laser on the printer | Eye injury only if the beam is refocused (lens, camera optics) or viewed with magnification; specular reflection off a shiny part is a secondary concern | Low, but rises if the arm carries optics or a camera into the beam |
| Fire | Hotend thermal runaway (MOSFET shorted on, thermistor detached), connector or crimp overheating, PSU fault, filament or dust ignition, a part dropped onto a hot nozzle or bed; unattended running | Severe (property and life); this is the dominant hazard of the whole cell | Low per hour but significant over many unattended hours |
| Electric shock | Mains inside the printer, the PSU terminals, a mains-powered arm supply, damaged cables chafed by arm motion | Severe | Low if enclosed and earthed; raised by arm motion abrading cables |
| Dropped parts | Gripper loses grip, power loss opens a gripper, collision knocks a part | Low for people; a dropped part can land on the bed or nozzle (fire/jam) or jam a gantry | Medium |
| Cable snag | Arm dress pack catching the printer, trays, scanner lid, or wrapping around a joint; a person's sleeve or hair catching | Low-moderate; snag can tear connectors, short a supply, pull the printer | Medium |
| Unexpected start | Arm resumes after power returns, after an e-stop reset, or because a scheduled job starts while someone is in the cell | Moderate | Medium with unattended scheduling |
| Gravity fall | Arm sags or drops when motor power is removed, if joints are backdrivable and unbraked | Low-moderate (crush under the falling link, dropped payload) | Certain on every e-stop unless designed out |
| Fumes | ABS/ASA styrene, ultrafine particles | Chronic, not acute | Continuous; out of scope here except as a reason for an enclosure and extraction |

## 3. Numbers to design against

ISO/TS 15066 Annex A values are provisional and the ones below come from secondary transcriptions; we
use them only as orders of magnitude, then design well under them.

- Quasi-static (clamping) force limits from a secondary table: skull/forehead 130 N, face 65 N,
  neck 150 N (with effective spring constants 150, 75 and 50 N/mm). Hands and arms are higher than the
  face. Transient (impact) limits are derived from the quasi-static ones by a scaling factor (commonly
  quoted as 2x) and apply only where the body part can move away freely.
- The classical reduced speed for manual/teach mode in ISO 10218 is 250 mm/s at the tool.

Adopted cell targets (our own numbers, conservative against the above):

| Quantity | Target | Why |
|---|---|---|
| Static force the arm can exert at the tool or at any pinch point, at worst-case pose | <= 50 N, enforced by joint current/torque limits | Below the lowest quoted clamping limit (face, 65 N) |
| Gripper finger force | <= 20 N, mechanically limited (spring or slip clutch) where possible | A finger caught in the gripper is the most likely injury |
| TCP speed, person possibly present (presence sensor triggered, door open, or attended mode) | <= 250 mm/s | ISO 10218 reduced speed |
| TCP speed, cell confirmed empty (unattended, door closed) | <= 1000 mm/s | Keeps impact energy small: 2 kg effective moving mass at 1 m/s is 1 J |
| Collision detection reaction | contact detected and motion stopped within 50 ms; overall extra travel after contact <= 10 mm at 250 mm/s | Limits clamping build-up |
| Minimum gap between moving arm and fixed structure at end of any planned motion | >= 25 mm, or >= 120 mm where an arm/hand could enter | Common finger/arm clearance figures for avoiding pinch points (EN ISO 13854 style); a finger gap of 25 mm is the usual minimum |

## 4. Mitigations

### 4.1 Inherent design (the most valuable layer)

- Small motors and gearing that physically cannot produce more than the force targets. For steppers
  this means sizing current and gear ratio so the stall force at the tool is under 50 N; for BLDC/QDD
  joints it means a hard current limit in the driver, not just in the planner.
- Backdrivable or clutched joints (low gear ratio, quasi-direct drive, or a slip clutch on high-ratio
  joints). A backdrivable arm can be pushed away by hand after an e-stop, which matters more than
  most software features.
- Gravity: decide per joint. Either the joint holds its pose unpowered (non-backdrivable worm, a
  spring-applied brake, or counterbalance spring), or the arm parks in a pose where losing power
  drops nothing. Shoulder and elbow should hold or be counterbalanced; wrist and gripper may fall.
- Gripper holds its part on power loss (spring-closed or self-locking) so an e-stop does not drop a
  part onto the bed or nozzle; the holding force stays within the 20 N finger target.
- Rounded link edges, no exposed gear meshes or belts, covers over pinch points at joints.
- Heat-resistant materials where the arm may meet hot parts: a metal or PEEK/PEI gripper tip if it
  handles parts just off the bed; keep printed PLA links away from the nozzle zone entirely.

### 4.2 Software limits on the arm controller

- Joint position limits (soft limits inside the hard stops) and Cartesian keep-out zones: the printer
  envelope (with a larger, hot zone around the nozzle and heater block), the PSU and mains corner,
  the scanner lid hinge, the laser plane, and the space above the bench where a person stands.
- Speed limits by mode (table above); acceleration limits to keep jerk low.
- Collision detection: compare commanded and measured current (BLDC) or following error from output
  encoders (steppers with encoders); TMC StallGuard as a coarse extra on steppers. On detection: stop
  (category 2 software stop), retract a few mm along the reverse path to release clamping, then hold
  and raise a fault. Collision detection is a software function and is not part of the e-stop chain.
- Payload check: measured joint torques after a pick must match the expected part mass, otherwise
  fault (catches failed picks and parts still stuck to the bed).
- Watchdog: the joint drivers disable themselves if the motion controller stops sending a heartbeat
  (for example within 100 ms).

### 4.3 Presence sensing

A hobby cell cannot afford safety-rated laser scanners, and cheap sensors are not safety-rated. Treat
them as triggers for speed reduction and pause, not as the reason the cell is safe.

| Option | Cost | Use |
|---|---|---|
| Interlocked door / hinged cover on the cell (or the printer door that is planned) | Low | Best single measure. Use a coded magnetic safety switch or a tongue-actuated interlock switch with positive opening contacts, wired into the hardwired chain. |
| mmWave presence radar (e.g. 24 GHz modules) | Very low | Detects a person standing near the cell even when still; drives "attended" speed limit. |
| ToF multizone sensors or a 2D lidar watching the approach | Low-medium | Reduce speed when something enters a zone, pause when it enters the inner zone. |
| Hobby light curtain or beam-break pair across the cell front | Low-medium | Pause on break. Safety-rated Type 2/4 curtains exist second hand; only those may go in the hardwired chain. |
| Camera with person detection | Low (camera already planned) | Logging and advisory only. |

### 4.4 Emergency stop chain

- At least one real e-stop (ISO 13850 style) on the cell, reachable without leaning over the arm, and
  ideally a second near the door or the room entrance. A wireless e-stop is acceptable only as an
  extra, never as the only one, and only if it is fail-safe (loss of link trips).
- The chain is a series loop of normally-closed contacts: e-stop buttons, door interlock, smoke/heat
  detector relay contact, over-temperature bimetal on the enclosure. It feeds a safety relay (or, at
  minimum, a monitored relay with force-guided contacts) whose outputs hold in the contactors.
- What the chain opens: K1, the printer mains contactor already planned ahead of the 24 V PSU (this
  kills heaters, steppers, laser and the printer's own fans); K2, the arm motor supply. Logic (Pi,
  arm controller, sensors) stays powered so faults are logged and the state is known.
- The existing Moonraker GPIO path drives a separate relay whose contact is in series with the safety
  relay's output to the K1 coil. Software can always remove power, never restore it past an open
  hardware chain. Keep `off_when_shutdown: True`.
- Reset is manual, local and deliberate: releasing the e-stop does nothing until a reset button is
  pressed, and reset does not start motion or heaters. After reset, Klipper must be restarted
  (`FIRMWARE_RESTART`) and the arm re-homed or re-validated before anything moves.
- Software e-stop entry points (web UI button, the arm supervisor, the mechloop agent) call
  Moonraker's `printer.emergency_stop` and drop the arm drivers' enable line. Moonraker's docs warn
  that M112 sent as G-code queues behind earlier commands; use the endpoint, not G-code.

### 4.5 Fire: detection, cut-off, suppression

Fire is the hazard that makes unattended running questionable at all. Treat it in layers:

1. Prevent: `verify_heater` already on; add an independent hotend cut-off (thermal fuse or bimetal on
   the heater block circuit, or a second thermistor read by an independent microcontroller that drops
   a relay); crimp, never solder, heater connections; rated connectors with margin; fused PSU output;
   PSU and electronics in a metal sub-enclosure; no filament spool or paper (scanner) directly above
   the printer.
2. Detect: a photoelectric smoke detector with a relay output above or inside the cell (devices such
   as "Smoke Signal" exist specifically to cut printer power); a heat sensor at the top of the
   enclosure (fixed 70-80 C bimetal); optional VOC/CO sensor for logging. Both relay outputs are
   normally-closed contacts in the hardwired chain, so detection cuts power without software.
3. Suppress: an automatic, self-contained, heat-triggered extinguisher above the printer (clean-agent
   tube systems, e.g. the type Prusa sells for its enclosure, FE-36 units that trigger around 79 C, or
   aerosol "pucks"). Clean agents avoid powder damage to electronics. The RepRap safety wiki's view is
   that an enclosure with an automatic extinguisher inside may be the only defensible way to run a
   printer unattended. Pair with a household smoke alarm in the room that people will hear.
4. Contain: printer and arm on a non-combustible surface (metal or tile), metal or flame-retardant
   enclosure, nothing combustible within 30-50 cm.
5. Notify: on any trip, push a notification to the owner (Moonraker notifier, Home Assistant).

Unattended rule: the cell may run unattended only when all of layers 1-3 are installed and their last
test is recorded within the test interval (section 9).

### 4.6 Laser, hot parts, dropped parts, cables

- Laser: the line laser is powered from the K1 side so the e-stop kills it; enable it only while the
  arm is parked or outside a defined laser zone; the arm never carries a lens, magnifier or camera
  with focusing optics into the beam path; no reflective tools in the laser plane.
- Hot parts: the arm may enter the printer only with the hotend below 60 C or parked behind a hot-zone
  keep-out, and picks parts only after the bed is below a release temperature (around 35-40 C for PLA
  on PEI, which also improves release). Parts are placed on a heat-tolerant tray.
- Dropped parts: carry paths avoid passing over the printer bed, the nozzle and the PSU; travel low
  over trays; verify grip with the payload check; a part missing after a pick is a fault, not a retry
  loop.
- Cables: flex-rated cable through a dress pack or internal routing with strain relief at each joint;
  joint ranges limited so cables cannot wind up (e.g. no continuous rotation without a slip ring);
  breakaway or latched connectors that fail open rather than tear; no mains cabling on the arm.

## 5. Printer-arm coordination

### 5.1 Interfaces

Moonraker exposes Klipper over HTTP and JSON-RPC on a websocket. The arm supervisor should subscribe
(`printer.objects.subscribe`) rather than poll, and read:

| Object.field | Used for |
|---|---|
| `webhooks.state` (`ready`, `startup`, `shutdown`, `error`) and `state_message` | Klipper alive and not shut down |
| `print_stats.state` (`standby`, `printing`, `paused`, `complete`, `cancelled`, `error`) | Job phase; requires `[virtual_sdcard]` |
| `extruder.temperature`, `extruder.target`, `heater_bed.temperature`, `heater_bed.target` | Hot-zone and part-release gating |
| `toolhead.position`, `toolhead.homed_axes` | Toolhead parked at a known safe pose |
| `gcode_macro CELL.*` variables (see below) | Explicit lock/handshake owned by Klipper |
| `server.info`, Moonraker `power` device status | Contactor state |

Commands to the printer go through `printer.gcode.script` (macros below) and
`printer.emergency_stop`. Printer-side lock state lives in Klipper (a `[gcode_macro CELL]` with
variables, persisted with `[save_variables]`), so it survives a supervisor restart and the printer
itself refuses to move while the arm holds the lock.

### 5.2 Handshake macros (printer side)

- `CELL_REQUEST_ACCESS`: allowed only when `print_stats.state` is `standby`, `complete` or
  `cancelled`; parks the toolhead at the rear/top, lowers or presents the bed, sets heater targets to
  0 (or holds the bed at a release temperature), waits until temperatures are under the gates, then
  sets `CELL.arm_has_access = 1` with a lease timestamp.
- Every print-start macro (`PRINT_START`) and every move macro checks `CELL.arm_has_access == 0` and
  aborts otherwise.
- `CELL_RELEASE_ACCESS`: arm confirms it is outside the printer envelope (by its own joint positions
  and, ideally, a physical "arm parked" switch read by Klipper as a `[gcode_button]`), then clears the
  lock.
- Lease: the supervisor renews the lease every few seconds; if it expires while the arm is inside,
  the printer stays locked and the cell raises a fault (it does not assume the arm left).

A physical "arm parked" switch read by Klipper is worth the extra wire: it lets the printer refuse to
home or print while the arm is anywhere near it, without trusting the network.

### 5.3 Cell state machine (supervisor)

| State | Entry condition | Allowed | Exit |
|---|---|---|---|
| `SAFE_OFF` | Power-up, after e-stop, after reset | Nothing moves, heaters off | Owner reset + self-test pass -> `IDLE` |
| `IDLE` | Self-test pass | Arm parked, printer idle | Job scheduled -> `PRINTING` or `ARM_TASK` |
| `PRINTING` | `print_stats.state = printing`, arm parked switch closed | Printer moves and heats; arm may work only in zones far from the printer (trays, scanner) at reduced speed | Print complete -> `COOLDOWN`; fault -> `FAULT` |
| `COOLDOWN` | Print complete | Heaters off, waiting for gates | Gates met -> `ARM_ACCESS_REQUESTED` |
| `ARM_ACCESS_REQUESTED` | `CELL_REQUEST_ACCESS` sent | Printer parks, confirms | `CELL.arm_has_access = 1` -> `ARM_IN_PRINTER`; timeout -> `FAULT` |
| `ARM_IN_PRINTER` | Lock held, lease fresh | Arm removes part, clears bed; printer locked | Arm parked + release -> `ARM_TASK` or `IDLE` |
| `ARM_TASK` | Part in gripper | Scanner placement, trays, inspection | Done -> `IDLE` |
| `PAUSED_PRESENCE` | Presence sensor triggered (non-safety) | Arm holds or slows to 250 mm/s; printer may keep printing | Clear for N seconds -> previous state |
| `FAULT` | Any fault in 5.4 | Arm stops and holds, printer heaters off (by command, and by contactor if the fault is severe) | Owner acknowledges -> `SAFE_OFF` |

Rules: only one owner of the shared space at a time; every transition has a timeout; any unexpected
value (for example `webhooks.state` not `ready`, a temperature reading out of range, a lost
subscription) moves to `FAULT`, never to "retry and continue".

### 5.4 Fault handling

| Fault | Detection | Response |
|---|---|---|
| Klipper shutdown (thermal runaway, MCU lost) | `webhooks.state = shutdown` | Arm stops in place and holds; Moonraker drops K1 (existing `off_when_shutdown`); notify |
| Moonraker or Pi unresponsive | Arm supervisor heartbeat to Moonraker fails for > 2 s | Arm stops; supervisor opens its own relay in series with K1 coil; notify |
| Arm controller hang | Driver watchdog | Drivers disable; Klipper sees "arm parked" switch state and keeps the printer locked if open |
| Collision | Current/following error | Stop, back off, hold, fault; printer unaffected unless the collision was inside the printer |
| Failed pick / unexpected payload | Payload check, scanner or camera mismatch | Fault; no retry loop inside the printer |
| Smoke / heat | Detector relay in chain | Hardware opens K1 and K2; supervisor logs and notifies; extinguisher acts on its own |
| Door opened during unattended run | Door interlock in chain | Hardware stop; requires manual reset |
| Presence detected (non-safety) | mmWave / ToF | `PAUSED_PRESENCE`, reduced speed |
| Power cut and return | Supervisor boots into `SAFE_OFF` | No automatic restart of arm or heaters; owner must reset |
| Lease expired with arm inside printer | Lease timer | Printer stays locked; fault |

## 6. Recommended safety architecture

Three independent layers, each able to make the cell safe on its own for the hazards it covers:

```
Layer A - hardwired (no software)
  [E-stop 1]--[E-stop 2]--[Door interlock]--[Smoke relay NC]--[Heat bimetal NC]--> Safety relay (dual channel, manual reset)
                                                                                     |
                     +---------------------------------------------------------------+
                     |                                         |
          [Supervisor relay NC]--[Moonraker GPIO relay]--> K1 coil       --> K2 coil
          (software may open, never close past chain)         |                  |
                                                      printer mains:      arm motor supply
                                                      PSU 24 V, heaters,  (logic stays on)
                                                      laser, steppers
  Plus in the printer: bed thermal fuse (exists), hotend independent cut-off (to add),
  arm current limits in the drivers, gripper force limited mechanically.

Layer B - firmware/supervisor (software, fast)
  Klipper verify_heater, min/max temp, CELL lock macros
  Arm controller: speed modes, joint/zone limits, collision detection, watchdog, payload check
  Supervisor: state machine, leases, heartbeats, presence-based speed reduction

Layer C - environment
  Non-combustible bench and enclosure, automatic clean-agent extinguisher above the printer,
  room smoke alarm, notification to owner, physical separation of mains, cable dress pack
```

Design choices behind it:

- De-energize to trip everywhere: a broken wire or unplugged sensor stops the cell.
- Arm stop category: category 0 (motor power removed by K2) is acceptable only if shoulder and elbow
  hold their pose unpowered (brake, worm or counterbalance). If they do not, use category 1: the
  safety relay has a time-delayed output for K2 (around 0.5 s) so the controller can decelerate first,
  while K1 opens instantly.
- K1 should be a contactor or relay with force-guided (mirror) contacts, its auxiliary contact read by
  the safety relay feedback loop so a welded contact prevents reset.
- A certified safety relay module is the one component worth buying new or reputable second hand;
  it is the cheapest way to get dual-channel monitoring, cross-fault detection and manual reset
  without designing them.

## 7. Arm-specific design requirements for the other researchers

- Motor and gear sizing must report worst-case static tool force (target <= 50 N) and gripper force
  (<= 20 N) alongside payload and reach.
- Each joint states its unpowered behaviour (holds, falls, backdrivable) and the chosen stop category.
- Drivers expose an enable input that the hardwired K2 side or the supervisor can drop, and a current
  limit that is set in hardware or driver firmware, not only by the planner.
- The arm reports joint current or output encoder data at >= 200 Hz so collision detection is possible.
- A physical "parked" switch at the home pose, wired to Klipper.
- No mains on the arm; motor supply 24 V or lower.

## 8. What we deliberately do not do

- Claim PL or SIL values; we have no MTTFd data for printed parts and hobby drivers.
- Put non-safety sensors (mmWave, ToF, cameras) into the hardwired chain as primary protection.
- Allow the arm and printer to move inside the printer envelope at the same time.
- Run unattended without the fire layers installed and tested.

## 9. Checklist for verifier checks

Kind: D = design-time check on the mechloop model (static, automatable now), C = commissioning test on
hardware (recorded with date and result), R = runtime monitor in the supervisor.

| ID | Check | Kind | Pass criterion |
|---|---|---|---|
| S01 | E-stop chain exists and is a series NC loop feeding a safety relay | D | Wiring graph: every listed device (e-stops, door, smoke, heat) is NC and in series; safety relay present |
| S02 | E-stop opens printer mains (heaters, laser, steppers) | D, C | K1 coil reachable only through chain output; test: press e-stop during heat-up, heater power drops to 0 within 100 ms (measure at heater) |
| S03 | E-stop opens arm motor supply | D, C | K2 coil through chain; test: press during motion, arm stops within stated distance |
| S04 | Software cannot override chain | D | No path to K1/K2 coils that bypasses the safety relay output |
| S05 | Software can still open K1 | D, C | Moonraker relay contact in series with K1 coil; test: `printer.emergency_stop` plus Klipper shutdown drops K1 |
| S06 | Manual reset required, no auto restart | C | Release e-stop -> nothing energizes; reset -> heaters remain off, arm does not move |
| S07 | Power-loss restart behaviour | C | Pull and restore mains: supervisor in `SAFE_OFF`, heaters off, arm still |
| S08 | E-stop device type | D | Part record: latching, positive opening (IEC 60947-5-5 / ISO 13850), red on yellow |
| S09 | Contactor monitoring | D, C | Force-guided aux contact in safety relay feedback; test: with K1 forced closed (simulated), reset is refused |
| S10 | Hotend independent cut-off | D | A thermal fuse or independent relay path that opens with the MOSFET shorted, in the thermal fault simulation (ELECTRICAL.md method) |
| S11 | Bed thermal fuse present | D | Exists today; keep as regression check |
| S12 | verify_heater configured for every heater | D | Generated printer.cfg contains `[verify_heater]` per heater |
| S13 | Smoke and heat detectors in chain | D, C | Present in wiring graph; test with detector test button / heat gun: K1 and K2 open |
| S14 | Automatic extinguisher installed above printer | C | Present, within expiry, positioned per maker; recorded |
| S15 | Non-combustible surface and clearance | C | Bench/enclosure material recorded; >= 30 cm clear of combustibles |
| S16 | Arm static tool force | D | Computed from motor stall torque, current limit, gearing and worst pose: <= 50 N |
| S17 | Gripper force | D, C | <= 20 N computed; measured with a scale |
| S18 | Speed modes | D, R | Configured limits 250 / 1000 mm/s; runtime: commanded TCP speed never exceeds the mode limit |
| S19 | Collision detection works | C | Push a padded force gauge into the arm path at 250 mm/s: stop within 50 ms, peak force <= 50 N, arm backs off |
| S20 | Joint unpowered behaviour | D, C | Each joint declared hold/fall; test: drop K2 at max-load pose, shoulder/elbow sag <= 5 mm |
| S21 | Gripper holds on power loss | C | Drop K2 holding max payload; part retained |
| S22 | Keep-out zones defined | D | Arm config has zones for printer envelope, nozzle hot zone, PSU, laser plane, scanner hinge; every planned path checked against them |
| S23 | Pinch clearance | D | Swept arm volume vs fixed geometry: >= 25 mm gap at every planned end pose, or >= 120 mm where an arm could enter |
| S24 | Cable wind-up | D | Joint ranges within the dress pack's rated twist; no continuous rotation without slip ring |
| S25 | Laser gated | D, R | Laser powered from K1 side; enable only while arm in `parked` or outside laser zone; arm tool list contains no focusing optics in laser zone |
| S26 | Access handshake | D, R | `PRINT_START` and homing macros refuse while `CELL.arm_has_access = 1` or parked switch open; arm enters printer envelope only with lock held and lease fresh |
| S27 | Temperature gates | R | Arm entry only with extruder < 60 C and bed below release temperature, read live from Moonraker |
| S28 | Fault transitions | R, C | Simulated: Moonraker killed, Klipper shutdown, lease expiry, payload mismatch each lead to `FAULT` with arm stopped; none retries automatically |
| S29 | Heartbeats and watchdogs | R, C | Driver watchdog trips within 100 ms of controller stop; supervisor trips within 2 s of Moonraker loss |
| S30 | Presence response | R, C | Person-sized target in zone -> speed <= 250 mm/s within 200 ms; inner zone -> hold |
| S31 | Door interlock | D, C | Interlock in chain; opening during motion stops arm and printer, needs reset |
| S32 | Protective earth | D, C | Every touchable metal part of printer frame, enclosure and arm base bonded to PE; continuity < 0.1 ohm (measured) |
| S33 | No mains on the arm | D | Arm wiring graph contains no mains nets |
| S34 | Notification on trip | C | Each trip source produces a message to the owner within 60 s |
| S35 | Unattended gate | R | Supervisor refuses unattended mode unless S13, S14, S19, S31 have passing records within the last 90 days and the door is closed |
| S36 | Periodic tests | R | E-stop and detector tests at least monthly; overdue -> unattended mode disabled |

## Sources

- ISO 10218-1:2025 product page: https://www.iso.org/standard/73934.html
- ANSI blog, ISO 10218-1:2025 overview: https://blog.ansi.org/ansi/iso-10218-1-2025-robots-and-robotic-devices-safety/
- Modern Materials Handling, "Industrial robot safety standards get major updates for 2025": https://www.mmh.com/article/iso-updates-industrial-robot-safety-standards-2025/Safety
- arXiv 2602.17822, review comparing ISO 10218 2011 and 2025: https://www.arxiv.org/pdf/2602.17822
- DGUV/IFA, medical-biomechanical requirements for collaborative robots: https://www.dguv.de/ifa/%3B/fachinfos/kollaborierende-roboter/medizinisch-biomechanische-anforderungen/index-2.jsp
- DGUV information sheet 080, collaborative robot systems: https://www.sifa.dguv.de/medien/fb-holzundmetall/publikationen-dokumente/infoblaetter/infobl_englisch/080_collaborativerobotsystems.pdf
- NIST, biomechanical thresholds for robot operators: https://www.nist.gov/document/head-toe-biomechanical-thresholds-protect-robot-operators-against-injuries
- Energy-tank control satisfying ISO/TS 15066 (contains the secondary force table quoted): https://arxiv.org/pdf/2304.14059
- Frontiers in Robotics and AI, statistical model for biomechanical limits: https://doi.org/10.3389/frobt.2021.667818
- ISO 13849 overview: https://wikipedia.com/wiki/ISO_13849
- Schneider Electric, safety chain solutions catalogue (stop categories, Cat 3 PLd e-stop circuits): https://download.schneider-electric.com/doc/DIA3ED2140902EN/Catalog%20Safety%20Chain%20solutions%20and%20Safety%20functions_English_July%202020.pdf
- Rockwell Automation, functional safety documentation: https://www.rockwellautomation.com/de-at/support/documentation/technical-data/functionalsafetydocum20180905-1614.html
- RS DesignSpark, emergency stops to EN 13850 and EN 60947-5-5: https://www.rs-online.com/designspark/emergency-stops-stop-switches-en-13850-and-en-60947-5-5
- Schneider Electric blog, the ABCs of emergency stop buttons: https://blog.se.com/industry/machine-and-process-management/2018/04/06/the-abcs-of-emergency-stop-buttonsa-simple-concept-that-can-get-really-complicated/
- EAO, emergency stops, what designers need to know: https://www.newark.com/pdfs/techarticles/eao/EAO_Emergency_Stops-What_Designers_Need_to_Know.pdf
- Berkeley Lab, laser classification explanation: https://ehs.lbl.gov/resource/laser-classification-explanation/
- Lasermet, table of laser classes: https://www.lasermet.com/resources/table-of-laser-classes/
- Moonraker printer API (emergency_stop, objects query/subscribe): https://moonraker.readthedocs.io/en/latest/external_api/printer/
- Moonraker printer objects (print_stats, webhooks): https://moonraker.readthedocs.io/en/stable/printer_objects/
- Klipper API server: https://www.klipper3d.org/API_Server.html
- RepRap wiki, safety: https://reprap.org/wiki/Safety
- Prusa, fire suppression system for the enclosure: https://help.prusa3d.com/article/fire-suppression-system-enclosure_335524
- Safelincs, 3D printer fire detection and suppression case study: https://safelincs.co.uk/templates_safelincs/templates/snippets/snippet_CS3DPrinter.txt
- 3D Printing Industry, preventing 3D printer fires (Smoke Signal): https://3dprintingindustry.com/news/can-prevent-3d-printer-fires-34183/
- All3DP, unattended printer nearly burns house down: https://all3dp.com/fire-safety-unattended-3d-printer-nearly-burns-house-down/
- Hackaday, open fire suppression and safety standards: https://hackaday.com/2016/04/12/ask-hackaday-open-fire-suppression-and-safety-standards
- Repo context: `mech-ai/docs/ELECTRICAL.md`, `mech-ai/out/printer_v12/.../firmware/printer.cfg` (contactor via Moonraker GPIO, verify_heater, bed thermal fuse)

Caveats: standard clause details and the ISO/TS 15066 numbers come from secondary sources and must
be checked against the published texts before anyone relies on them; the pinch-gap figures
(25 mm / 120 mm) follow the EN ISO 13854 style of minimum gaps from memory and were not verified in
this search; product mentions are examples, not tested recommendations.
