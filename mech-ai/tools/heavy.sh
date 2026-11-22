#!/usr/bin/env bash
# Run a heavy mechloop job in a shared slot so parallel agents use the machine without running out of memory.
# Two lanes so fast checks never wait behind slow verifies:
#   fast lane (HEAVY_FAST_SLOTS, default 2): `--only` runs without fea/tolerance/motion/printing, or build_change.py without --verify
#   slow lane (HEAVY_SLOTS, default 2): everything else (full / affected-tier verifies, FEA, tolerance Monte Carlo)
# Force a lane with HEAVY_LANE=fast|slow.  Usage: tools/heavy.sh <command...>
args=" $* "
lane=${HEAVY_LANE:-}
if [ -z "$lane" ]; then
  lane=slow
  if [[ "$args" == *" --only "* ]] && [[ "$args" != *" fea"* && "$args" != *" tolerance"* && "$args" != *" motion"* && "$args" != *" printing"* ]]; then lane=fast; fi
  if [[ "$args" == *"build_change.py"* ]] && [[ "$args" != *" --verify"* ]]; then lane=fast; fi
fi
if [ "$lane" = fast ]; then N=${HEAVY_FAST_SLOTS:-2}; pre=fast; else N=${HEAVY_SLOTS:-2}; pre=slot; fi
while true; do
  for i in $(seq 1 "$N"); do
    exec 9>"/tmp/mechloop_heavy.$pre$i"
    if flock -n 9; then "$@"; rc=$?; flock -u 9; exit $rc; fi
  done
  sleep 2
done
