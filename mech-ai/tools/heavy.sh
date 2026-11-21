#!/usr/bin/env bash
# Run a heavy mechloop job (design build, verify, FEA) in one of N shared slots, so parallel agents
# use the machine without running out of memory. Usage: tools/heavy.sh <command...>   (slots: HEAVY_SLOTS, default 3)
N=${HEAVY_SLOTS:-3}
while true; do
  for i in $(seq 1 "$N"); do
    exec 9>"/tmp/mechloop_heavy.slot$i"
    if flock -n 9; then "$@"; rc=$?; flock -u 9; exit $rc; fi
  done
  sleep 3
done
