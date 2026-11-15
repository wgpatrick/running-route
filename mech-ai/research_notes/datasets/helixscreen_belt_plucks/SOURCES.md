# Belt pluck ring-down recordings (HelixScreen test fixtures)

- URL: https://github.com/prestonbrown/helixscreen/tree/HEAD/tests/fixtures/belt_plucks (raw files fetched from `raw.githubusercontent.com/prestonbrown/helixscreen/HEAD/tests/fixtures/belt_plucks/<name>.csv`)
- Licence: GPL-3.0 (LICENSE copied here). Fetched 2026-11-15.

Eight raw accelerometer time series (`#time,accel_x,accel_y,accel_z`, ADXL345 on the toolhead, about 3.09 kHz, 0.5 s each) of a plucked belt ringing down on one Voron 2.4 300 mm, 151 mm free span, steppers energised. The fixture README states the two belt paths were at 86 Hz (A) and 82 Hz (B), against the Voron target of 110 Hz, and that all files come from one machine on one evening. Use: a worked example of belt tension from pluck frequency (T = 4 rho L^2 f^2) and of the octave error a naive peak-picker makes; a naive FFT peak on `a_belt_86hz_1` lands on 172.8 Hz, the second harmonic.
