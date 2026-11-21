# 02 - Actuators, transmissions and motor control

Scope: options for driving the joints of the arm we will design ourselves to tend the printer, assemble parts and swap tools in mechloop. Targets: payload 0.2-1 kg, reach 300-600 mm, repeatability ±0.1-0.2 mm at the tool. This note covers motors, drivers, reductions, encoders and brakes. It names real products and ends with joint recipes and the data the digital twin needs.

Prices are single-unit USD figures seen in November 2026 search results. They come from cached shop pages and change often, so check the live page before ordering. Anything marked **(est.)** is my own engineering estimate, not a figure from a maker.

---

## 1. What the targets demand (est.)

### 1.1 Torque budget

Assumptions: 0.6 m reach, 1 kg payload, about 1.5 kg of moving arm with its center of mass near mid-reach, and a 1.5x margin for acceleration and safety.

| Joint | Static gravity torque (est.) | Design peak (est.) |
|---|---|---|
| Shoulder pitch | 1·9.81·0.5 + 1.5·9.81·0.25 ≈ 8.6 N·m | 12-15 N·m |
| Elbow | ≈ 3-4 N·m | 5-7 N·m |
| Base yaw | inertia-dominated, low gravity load | 3-5 N·m |
| Wrist pitch and roll | ≈ 0.3-0.8 N·m | 1-1.5 N·m |

At 0.4 m reach and 0.5 kg payload, all of these drop by roughly half. A spring counterbalance on the shoulder (a gas spring or an extension spring with a cam) can cancel most of the static load. That lets the shoulder use the same smaller actuator as the elbow.

### 1.2 Angular error budget

This is the requirement that actually drives the design. Tip error is roughly the sum of each joint's link length times its angular error. For ±0.1 mm at 500 mm, the shoulder alone may contribute only 0.2 mrad, which is **about 0.7 arcmin**.

Consequences:

- **Backlash must essentially disappear.** Economy NEMA17 planetaries are rated ≤1-3°, and "high precision" ones about 0.8° or ≤50 arcmin (StepperOnline listings below). A backlash of 0.8° alone moves the tool about 7 mm at 500 mm. Gravity preload makes a joint repeat on one side of its backlash, but contact forces during assembly cross over it. The usable options are zero-backlash reductions (capstan, strain-wave, preloaded cycloidal, belts) or a joint encoder on the output plus a controlled approach direction.
- **The joint (output) encoder sets the floor.**

  | Encoder | Bits | Step | Tip step at 500 mm |
  |---|---|---|---|
  | AS5600 | 12 | 0.088° | 0.77 mm (not usable on the output of a proximal joint) |
  | AS5047P | 14 | 0.022° | 0.19 mm, before INL errors |

  A 21-bit class encoder such as the MagnTek MT6835 or the RLS AksIM-2 is needed for the shoulder and elbow outputs, or the AS5047P must be calibrated and averaged. A motor-side encoder ahead of an N:1 reduction gains N times the resolution but cannot see backlash or the windup of a compliant reduction.
- **Wrist servos matter too.** With 100 mm from the wrist to the tool point, 0.25° of wrist backlash gives about 0.44 mm. Hobby smart servos alone will not meet ±0.1 mm.

**Realistic verdict (est.):** about ±0.2 mm is reachable with zero-backlash proximal joints, output encoders and kinematic calibration. ±0.1 mm across the full 600 mm reach is hard at hobby cost. We should design for ±0.2 mm and recover the last bit with vision or fiducial-based local correction at the inspection and assembly stations.

---

## 2. Motors and drivers

### 2.1 Steppers, open and closed loop

| Product | Maker P/N | Key spec | Price | Seller | CAD / datasheet |
|---|---|---|---|---|---|
| NEMA17 with 1000 PPR magnetic encoder | StepperOnline 17HS24-2104-ME1K | 65 N·cm holding | $21.81 | omc-stepperonline.com (US warehouse) | Drawing and datasheet on product page; STEP usually provided (verify per part) |
| NEMA17 P-series with optical encoder | StepperOnline 17E1K-07 | 72 N·cm, 1000 PPR | $32.52 | omc-stepperonline.com | Same as above |
| NEMA17 with 0.25 N·m power-off brake | StepperOnline 17HS19-2004D-B025 | 0.59 N·m, 24 V 5 W brake | $47.44 | omc-stepperonline.com | Same as above |
| NEMA17 with brake | StepperOnline 17HS24-2104D-B025 | 0.65 N·m, 25 N·cm brake | price not captured | omc-stepperonline.com | Same as above |
| Integrated closed-loop stepper | StepperOnline ESS17-04 | 0.48 N·m, 24-36 V, 1000 CPR | (check) | omc-stepperonline.com | Same as above |
| FOC closed-loop stepper driver | Makerbase MKS SERVO42D (CAN version MOT-SERVO42D-CAN) | NEMA17, FOC, CAN, Modbus-RTU, on-board magnetic encoder | $27.07 (board, no motor) | Abra Electronics (US/CA) | GitHub manual and drawings from Makerbase; no formal maker CAD (weak on the project rule) |

**Strengths.** Very cheap. Good holding torque at low speed. Easy to drive. Huge US stock.

**Weaknesses.**

- Torque falls off steeply with speed.
- Poor torque density: about 0.65 N·m from 350 g, or roughly 2 N·m/kg.
- Open loop loses steps silently.
- Not usefully backdrivable once geared.
- No real torque sensing. Current is not proportional to load in a normal stepper drive, which hurts contact tasks such as pressing inserts or screwing.

Closed-loop FOC stepper drivers (MKS SERVO42D, ESS series) fix the lost-steps problem and give some current-based effort estimate.

**Twin fidelity:** medium. The model needs pull-out torque-speed curves at the actual supply voltage and driver, and stepper torque ripple and detent torque are harder to model.

### 2.2 BLDC with FOC drivers

| Product | Maker P/N | Key spec | Price | Seller | CAD / datasheet |
|---|---|---|---|---|---|
| moteus-c1 controller | mjbots moteus-c1 | small FOC controller, CAN-FD, on-board encoder, aux encoder port | $69 | mjbots.com (US, Washington state); also reach.dog | Docs, pinout and STEP at mjbots.github.io/moteus |
| moteus r4.11 controller | mjbots moteus r4.11 | higher current than the c1 | $59-79 | mjbots.com / reach.dog | Same as above |
| mj5208 motor | mjbots mj5208 | 5208 gimbal-class outrunner | $74 | mjbots.com / reach.dog | STEP and specs on mjbots site |
| moteus-c1 developer kit | mjbots | c1 + mj5208 + accessories | $149 | mjbots.com | n/a |
| qdd100 beta 3 integrated servo | mjbots qdd100 beta 3 | 16 N·m peak, 507 g, 10-44 V, planetary, integrated | $559 | reach.dog / mjbots | Beta product with sparse docs; mjbots itself flags reliability caveats |
| ODrive S1 | ODrive Robotics S1 | FOC, CAN, on-board encoder | about $149 (undated price sheet) | shop.odriverobotics.com (US) | Docs, STEP and datasheet at docs.odriverobotics.com |
| ODrive Micro | ODrive Robotics ODMICRO | compact FOC | $89 (often sold out) | shop.odriverobotics.com; Mouser | Same as above |
| M8325s motor | ODrive Robotics M8325s 100KV | 8325 outrunner with encoder magnet | $119-149 | shop.odriverobotics.com | Same as above |
| S1 + M8325s kit | ODrive Robotics | kit | $314 (sold out at time of search) | shop.odriverobotics.com | Same as above |
| AK60-6 V1.1 KV80 | CubeMars | integrated 6:1 planetary, 0.55° backlash, 368 g | $299-347 | RobotShop US, RoboticsCenter | Drawings and STEP from CubeMars |
| AK80-9 V3.0 KV100 | CubeMars | 22 N·m peak, 490 g | $480-580 | cubemars.com, RobotShop US | Same as above |

**Strengths.**

- Torque density about 2-5x a stepper.
- Phase current maps almost linearly to torque (Kt), which gives cheap force sensing for insertion and screwing.
- Transparent and backdrivable at low ratios, so collisions are survivable.
- Smooth, high bandwidth.
- moteus and ODrive both have open firmware, Python APIs and CAN, which suits a digital-twin loop well.

**Weaknesses.**

- More expensive per joint.
- Needs encoder calibration and tuning.
- No holding torque when unpowered, so it needs a brake or a counterbalance.
- Quasi-direct-drive planetaries such as the AK60-6 still carry about 0.2-0.6° of backlash, which fails the angular budget unless an output encoder is added.

### 2.3 Smart servos

| Product | Maker P/N | Key spec | Price | Seller | CAD / datasheet |
|---|---|---|---|---|---|
| Dynamixel XL430-W250-T | ROBOTIS | about 1.5 N·m stall, 12-bit absolute encoder | $45-55 | robotis.us, RobotShop US | Excellent: e-Manual with drawings, STEP and published torque-speed and current curves |
| Dynamixel XM430-W350-T | ROBOTIS | about 4.1 N·m stall at 12 V, current-based torque control | $310 | robotis.us, RobotShop US | Same as above |
| Dynamixel XH540-W270-T | ROBOTIS | about 10 N·m class | $621 | robotis.us | Same as above |
| Feetech STS3215 (12 V 30 kg·cm) | Feetech STS3215 / ST3215-C047 | about 2.9 N·m stall, 12-bit magnetic encoder | $31-39 | RobotShop US, eBay US; Seeed | Translated datasheet only; CAD comes from Seeed and the community, so it is weak on the project rule |

**Strengths.** All-in-one, daisy-chained, cheap at the low end. Dynamixel has the best documentation of anything here, with published performance graphs that suit the digital twin.

**Weaknesses.**

- Metal spur gear trains have backlash. Dynamixel figures are about 0.25-0.3° (est., verify in each e-Manual). Feetech is likely larger (est.).
- Not truly backdrivable.
- 12-bit output encoders (0.088°).
- Duty-cycle and thermal limits are low.

**Fit:** good for the wrist roll, the tool-changer lock and the gripper. Too sloppy for proximal joints at our accuracy target. The STS3215 is the actuator in the LeRobot SO-100/SO-101 arms, so community kinematics and calibration code exist.

---

## 3. Transmissions

Columns: torque density, backlash, torsional stiffness, efficiency and backdrivability, cost per joint, how printable it is.

| Type | Backlash | Stiffness | Efficiency / backdrive | Cost / joint | Printability | Notes |
|---|---|---|---|---|---|---|
| **Economy planetary** (StepperOnline PG series, e.g. 17HS19-1684S-PG27, true ratio 26.85:1, about 81% eff.) | ≤1-3° | medium | 80-90%; backdrivable only at ≤10:1 | $34-50 incl. motor | n/a (buy) | Fails the backlash budget at any proximal joint |
| **"High precision" planetary** (StepperOnline 17HS19-1684S-HG10, 10:1, 85%, ≤0.8°, 3.5 N·m max; HG20 ≤50 arcmin, $62) | 0.8° | medium | 85% | $50-62 incl. motor | n/a | Still about 7 mm at 500 mm. Only usable with an output encoder plus gravity preload |
| **Printed planetary** (QDD style, 6-10:1) | 0.3-1° (est.) | 200-250 N·m/rad reported for printed planetary variants (arXiv 2510.07197) | high, backdrivable | $10-20 + bearings | excellent | Good for QDD BLDC joints that close the loop on an output encoder |
| **Commercial strain-wave** (StepperOnline HSS-14-50-I-D8, 50:1, ≤20 arcsec, Φ73 mm) | ≤20 arcsec | high | 60-80% (typical, est.); not backdrivable | $222 | n/a | Best value commercial zero-backlash option found. STEP and drawing on product page |
| Commercial strain-wave (AutomationDirect SureGear HPGCN17-805M, NEMA17, 12 N·m) | "zero" | high | as above | about $1,051 | n/a | US seller with excellent drawings, but costly |
| Commercial strain-wave (Harmonic Drive LLC CSF-11 component set) | <1 arcmin | high | as above | about $500-900 (est., quote only) | n/a | Gold standard, overkill for budget |
| **Printed strain-wave** | small at first, grows with wear | low (flexspline is printed TPU/PETG/nylon) | low | $10-30 | possible but finicky | HowToMechatronics printed test showed wear. Not recommended for load-bearing joints |
| **Printed cycloidal** (1-2 discs, 10-30:1) | 7 arcmin reported for a preloaded QDD cycloidal (arXiv 2410.16591); anti-backlash variants 2-3x better at under 2x friction (Volbeda, U. Twente 2024) | medium-high | 70-85% (est.); backdrivable at about 10:1 | $15-40 (pins and bearings) | good: compact, robust, tolerant of print error with preload | Strong DIY candidate for elbow and base |
| **Capstan / cable drive** (steel or Dyneema cable on a drum, 6-15:1 per stage) | **zero** | set by cable (good with 1.0-1.5 mm wire rope, lower with Dyneema) | 95%+, fully backdrivable, no torque ripple | $10-25 (cable, tensioner, bearings) | excellent: drum and sector are printed; only cable and bearings are bought | Bulky sector, limited travel (fine for shoulder and elbow, under 270°). Best accuracy per dollar for proximal joints |
| **Belt reduction** (GT2/GT3/HTD 3M, 2 stages to 10-20:1) | near zero (tooth clearance, tension dependent) | low-medium (belt stretch, est. 100-500 N·m/rad at joint) | 95%+, backdrivable | $10-30 (Gates belts and pulleys from McMaster or SDP/SI) | excellent | Proven in low-cost arms. Belt compliance must be in the twin. Use wide or steel-core belts |
| Worm | 0.5-2° | high | 30-60%; self-locking | $20-60 | possible | Gives a free brake but is slow, inefficient and backlashy. Avoid |

**Torque density, rough ranking (est., actuator plus reduction, N·m per kg):**

| Actuator and reduction | N·m/kg (est.) |
|---|---|
| BLDC + cycloid or strain-wave | 20-40 |
| BLDC + planetary (AK80-9: 22 N·m / 0.49 kg ≈ 45 peak) | ~45 peak |
| BLDC + capstan | 10-20 (bulky) |
| Stepper + capstan or belt | 8-15 |
| Smart servo (XM430: 4.1 N·m / 82 g ≈ 50 stall, but low continuous) | ~50 stall |

---

## 4. Encoders

| Part | Maker P/N | Resolution | Interface | Price | US seller | Notes |
|---|---|---|---|---|---|---|
| AS5600 | ams OSRAM AS5600-ASOM | 12-bit | I²C / analog | about $2-4 chip (est.) | DigiKey, Mouser | Fine at the motor side only |
| AS5047P | ams OSRAM AS5047P-ATSM; adapter board AS5047P-TS_EK_AB (DigiKey 4991-AS5047PADAPTERBOARD-ND, magnet included) | 14-bit, ABI/UVW/SPI | SPI | board about $15-17 | DigiKey (159 in stock) | Supported by moteus, ODrive and SimpleFOC. Datasheet from ams |
| AS5048A | ams OSRAM | 14-bit | SPI / PWM | about $10-20 board | DigiKey | Similar to AS5047P |
| MT6835 | MagnTek MT6835 | 21-bit (absolute accuracy about 0.02-0.07° after calibration, est.) | SPI | about $5-10 chip (est.) | mostly LCSC / AliExpress; US distribution unclear (check DigiKey) | Best low-cost output encoder; moteus supports it as an aux encoder (verify) |
| AksIM-2 off-axis | RLS (Renishaw) MBxxxx | 18-20 bit, off-axis ring (hollow shaft) | SPI/BiSS | about $150-300 (est.) | RLS US office / quote | Real "industrial" option. Hollow bore suits cable routing. Directly supported by moteus |
| Motor encoder bundled with closed-loop steppers | StepperOnline ME1K | 4000 CPR incremental | ABZ | included | omc-stepperonline | Incremental, so the joint needs homing |

**Recommendation:**

- Every joint gets a motor-side encoder for commutation and velocity (built into moteus, ODrive and MKS boards).
- Proximal joints (base, shoulder, elbow) also get an absolute output encoder (dual loop): MT6835 or AksIM-2 on the shoulder, AS5047P (calibrated) acceptable on the elbow and base, AS5600 nowhere on an output.
- Absolute output encoders also remove homing, which matters for unattended recovery in the loop.

---

## 5. Joint brakes and safe holding

| Approach | Product | Price | Notes |
|---|---|---|---|
| Stepper with built-in power-off brake | StepperOnline 17HS19-2004D-B025, 17HS24-2104D-B025, 17BK05-05 | $47-60 | 0.25 N·m at the motor, multiplied by the ratio at the joint. Drawing and datasheet provided |
| Add-on NEMA17 24 V brake | Oyostepper "DC electromagnetic brake 24V 0.25 N·m for NEMA17" | (check) | Needs a rear shaft |
| Printed solenoid pawl / pin lock on the output gear or drum | e.g. Adafruit 412 or TE / Ledex solenoid (est. $8-15) | about $10-20 | Cheap discrete lock for BLDC joints; engages only at set positions |
| Spring counterbalance | gas spring (McMaster) or extension spring + printed cam | $10-30 | Reduces how much braking is needed and the size of the shoulder actuator. Recommended regardless |
| Non-backdrivable reduction | worm or high-ratio strain-wave | n/a | Strain-wave at 50:1 is weakly backdrivable but not reliable as a brake |

A brake is needed on the shoulder and elbow, or a counterbalance that keeps the arm passive-safe when power drops. The base yaw and the wrist do not need one.

---

## 6. Recommended joint recipes

All costs are single-quantity, rounded, and **(est.)** for the assembled joint: actuator, driver, reduction parts, encoder and fasteners, excluding printed plastic and the power supply.

### Recipe A - "Budget stepper + zero-backlash printed reduction" (lowest cost, good accuracy)

**Shoulder and elbow:**

- Motor and driver: StepperOnline 17HS24-2104-ME1K ($22) with an MKS SERVO42D CAN driver ($27). For the shoulder, use a brake motor such as the 17HS24-2104D-B025 (about $50).
- Reduction: printed **capstan** with 1/16 in or 1.2 mm 7x19 stainless wire rope (McMaster), 2 stages, about 10:1 × 2.5:1 ≈ 25:1. That gives about 0.65 × 25 × 0.9 ≈ 14 N·m.
- Output encoder: AS5047P adapter board ($16), calibrated, or MT6835.
- Shoulder counterbalance spring.
- Cost: about **$80-130 per joint**.

**Base:** the same, with a belt or cycloidal reduction instead of a capstan for continuous rotation, about $70-100.

**Wrist (2 DOF):** 2x Dynamixel XL430-W250-T ($45-55 each), or 2x Feetech STS3215 ($31-39) if cost dominates. About **$60-110 for the wrist**.

**Arm total (5 DOF + gripper servo):** about **$400-600** in actuation, plus a CAN adapter and a 24 V supply.

**Caveats:** stepper torque falls with speed; contact sensing is weak, so add a cheap load cell at the tool for insertion and screwing; backdrivability is poor.

### Recipe B - "BLDC FOC + capstan/cycloid" (best for contact tasks and twin fidelity; recommended)

**Shoulder:**

- Motor and driver: ODrive M8325s + S1 (about $270-314), or mj5208 + moteus-c1 ($143) with a higher ratio.
- Reduction: printed capstan or preloaded printed cycloidal at about 15-20:1 (M8325s) or 25-30:1 (mj5208).
- Output encoder: MT6835 or AksIM-2.
- Pin-lock brake and counterbalance.
- Cost: about **$200-400**.

**Elbow and base:** mj5208 + moteus-c1 ($143) with a printed cycloidal or capstan at 15-25:1, plus an AS5047P output encoder. About **$170-200 per joint**.

**Wrist:**

- Lower cost: Dynamixel XL430 ×2 (about $100).
- Higher fidelity: XM430-W350-T ×2 (about $620), which adds current-based torque control.
- Middle ground: a small gimbal BLDC with a moteus-c1 and printed planetary per axis (about $120-150 per axis, est.).

**Arm total:** about **$800-1,300**.

**Why recommended:**

- Current gives joint torque, which supports compliant insertion, collision detection and identification of the twin's dynamics.
- Capstan and cycloid both give zero or small backlash and are printable, so reductions can be iterated by mechloop itself.
- moteus and ODrive have open Python/CAN APIs and publish motor constants.

### Recipe C - "Buy precision" (least design risk, highest cost)

- Shoulder and elbow: StepperOnline HSS-14-50-I-D8 strain-wave ($222) driven by a closed-loop NEMA17 (17E1K-07, $33) and MKS SERVO42D ($27), with an AS5047P output encoder. About **$300 per joint**, 20 arcsec backlash, not backdrivable, which acts as a partial brake.
- Alternative: CubeMars AK80-9 ($480-580) with an output encoder to correct its planetary backlash.
- Wrist: Dynamixel XM430-W350-T ×2.
- Arm total: about **$1,300-1,900**.

**Suggested path:** prototype one Recipe-B elbow joint (mj5208 + moteus-c1 + printed capstan + AS5047P) first, on a test fixture, and characterize it as below. Fall back to Recipe A for any joint where cost matters more than torque sensing.

---

## 7. Data the digital twin needs per joint

| Quantity | Source |
|---|---|
| Motor Kt (N·m/A), phase R and L, pole pairs, rotor inertia | Maker datasheet (ODrive, mjbots, Dynamixel e-Manual, StepperOnline). Verify by measurement |
| Torque-speed envelope (stepper pull-out curve at our voltage and driver; BLDC peak and continuous vs. speed; servo stall and no-load) | Maker curves; re-measure on a dynamometer or with an inertia-wheel spin-up |
| Thermal model (winding Rth, Cth, max temperature, continuous current) | Datasheet plus temperature logging from moteus/ODrive/Dynamixel telemetry |
| Exact gear ratio (e.g. PG27 is really 26.85:1; capstan ratio depends on cable diameter) | Measured with dual encoders |
| Backlash or lost motion (deadband width) | Output locked, sweep motor torque ±, read motor vs. output encoders, or use a dial indicator on a lever arm |
| Torsional stiffness and hysteresis (N·m/rad, loading curve) | Lock the output, apply known torque with a lever and weights or by motor current, measure windup with the output encoder |
| Friction model: Coulomb, viscous, Stribeck, forward vs. back efficiency | Constant-velocity current sweeps in both directions; backdrive test |
| Encoder resolution, noise, INL (calibration table) | Calibrate the output encoder against a reference: a higher-res encoder or a dial-indexed rotary table |
| Controller behavior: loop rates, bandwidth, latency, saturation, CAN timing | Step and chirp responses logged from the controller |
| Brake: holding torque, engage and release time | Datasheet plus a bench test |
| Mass, CoM and inertia of each moving body | From CAD (printed parts with measured density) plus a pendulum or swing test |

Two fixtures would cover most of this: a lockable joint-test rig with lever and weight hanger, dual encoders and a load cell, and a free-swing pendulum rig. Logging both through the same moteus/ODrive Python stack makes system identification of the twin automatic and repeatable, which suits the recursive loop.

---

## 8. Open questions and risks

- MT6835 US distribution and moteus support need confirming. If unavailable, use the RLS AksIM-2 (costly) or a calibrated AS5047P.
- Several shop prices were stale or the items were sold out (ODrive kit, XM430, AK60-6). Re-check stock before freezing the BOM.
- Feetech and Makerbase lack formal maker CAD. Under the project rule they would need a dimensioned maker drawing, or we prefer Dynamixel and StepperOnline.
- Long-term creep of printed capstan drums and cycloid discs under constant gravity load is unquantified. Plan PETG-CF or nylon-CF parts, metal pins, and a creep test.
- Achieving ±0.1 mm needs kinematic calibration (vision or touch probe) on top of good hardware. Hardware alone targets ±0.2 mm (est.).

## Sources

- mjbots moteus-c1, r4.11, mj5208, qdd100: https://reach.dog/shop/mjbots-robotic-systems/products/moteus-c1 , https://reach.dog/shop/mjbots-robotic-systems/products/moteus-r4-11 , https://reach.dog/shop/mjbots-robotic-systems/products/mj5208 , https://reach.dog/shop/mjbots-robotic-systems/products/qdd100-beta-3 , https://blog-575.pages.dev/2024/04/30/moteus-c1 , https://mjbots.github.io/moteus
- ODrive S1/M8325s/Micro: https://shop.odriverobotics.com/products/s1-and-m8325s-start-kit , https://shop.odriverobotics.com/products/m8325s , https://shop.odriverobotics.com/products/odrive-micro , https://docs.google.com/spreadsheets/d/1bW0icrPqa08WVS28njdinUzttKD15rJSScYrE6aIzno
- CubeMars: https://www.cubemars.com/categorys/ak-series-robotic-actuator , https://www.robotshop.com/products/cubemars-ak60-6-v30-kv80-robotic-actuator , https://www.roboticscenter.ai/ar/store/product/cubemars-ak60-6-v1-1-kv80
- Dynamixel: https://robotis.us/dynamixel-xm430-w350-t/ , https://www.robotis.us/xh/ , https://www.robotis.us/robotis-blog/xl430-price-change-xseries-accessories/ , https://www.robotshop.com/products/robotis-dynamixel-xl430-w250-t-smart-servo-actuator , https://emanual.robotis.com/docs/en/dxl/x/xm430-w350
- Feetech STS3215: https://www.robotshop.com/products/feetech-12v-30kgcm-magnetic-encoding-servo-sts3215 , https://files.seeedstudio.com/Bazaar/product_pdf/101090142.pdf , https://core-electronics.com.au/feetech-sts3215-smart-servo.html
- StepperOnline planetary, encoder, brake, harmonic: https://www.omc-stepperonline.com/nema-17-stepper-motor-l-48mm-gear-ratio-10-1-high-precision-planetary-gearbox-17hs19-1684s-hg10 , https://www.omc-stepperonline.com/nema-17-stepper-motor-l-48mm-gear-ratio-20-1-high-precision-planetary-gearbox-17hs19-1684s-hg20 , https://oyostepper.com/goods-301-Nema-17-Stepper-Motor-Bipolar-L=48mm-w-Gear-Ratio-27-1-Planetary-Gearbox.html , https://www.omc-stepperonline.com/nema-17-closed-loop-stepper-motor-65ncm-92oz-in-with-magnetic-encoder-1000ppr-4000cpr.html , https://www.omc-stepperonline.com/p-series-nema-17-closed-loop-stepper-motor-72ncm-101-98oz-in-with-encoder-1000ppr-4000cpr-17e1k-07 , https://www.omc-stepperonline.com/nema-17-stepper-059nm84ozin-w-brake-friction-torque-025nm354ozin-17hs19-2004d-b025.html , https://www.omc-stepperonline.com/nema-17-stepper-0-65nm-92oz-in-w-brake-friction-torque-0-25nm-35-4oz-in-17hs24-2104d-b025 , https://www.omc-stepperonline.com/hss-series-harmonic-drive-gearbox-73mm-ratio-50-1-backlash-20arcsec-8mm-input-diameter-hss-14-50-i-d8 , https://www.omc-stepperonline.com/ess-series-0-48nm-68oz-in-nema-17-integrated-closed-loop-stepper-servo-motor-24-36vdc-1000cpr-ess17-04
- MKS SERVO42D: https://abra-electronics.com/electromechanical/motors/motor-controllers/mot-servo42d-can-mks-servo42d-can-mb-closed-loop-stepper-motor-board-without-motor.html
- AutomationDirect strain wave: https://cdn.automationdirect.com/static/catalog/images/product-pdf/MC-Motion-PlanetaryStrainWave-Overview.pdf , https://cdn.automationdirect.com/static/specs/cutsheet/HPGCN17-805M_cutsheet.pdf
- AS5047P adapter board: https://www.digikey.at/en/products/detail/ams-osram-usa-inc/AS5047P-ADAPTERBOARD/5452344 , https://nz.element14.com/ams-osram-group/as5047p-ts-ek-ab/adapter-board-kit-position-sensor/dp/4158644
- Printed reductions: https://essay.utwente.nl/essays/103595 (Volbeda 2024), https://arxiv.org/pdf/2410.16591 , https://arxiv.org/pdf/2510.07197 , https://howtomechatronics.com/how-it-works/harmonic-vs-cycloidal-drive-designing-3d-printing-testing
