"""What each verifier reads: its declared inputs, granularity and tier.

Reuse is decided by what a result actually read (recorder.py: Design fields, the parts list, each part attribute, at
run time) and the code that ran (coderec.py), not by this table. The table still matters:
- every verifier the runner knows (runner.ORDER and "requirements") must have an entry; a verifier without one is
  always re-run (tests/test_incremental.py asserts there is none),
- `upstream`: earlier verifiers whose metrics it reads in the same run (their metrics are part of its key: printing
  reads FEA's stiffness),
- `granularity`: how finely results are reused --
    "verifier": the whole result,
    "per_case": FEA: each load / modal / assembly / thermal case and the bed-support study on its own,
    "pairwise": interference: per-pair kernel results (overlap volume, gap) of unchanged pairs; the whole-design logic
                re-runs on them,
    "always":   cheap and reads the results of the others: re-runs every time,
  (manufacture also reuses each custom part's DFM checks on its own; geometry, motion and assemblability memoise
  their geometric kernels per pair of part fingerprints),
- `quick`: part of `--tier quick`,
- `fields`, `module`, `note`: documentation of what it is expected to read and where its code lives.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ALL_FIELDS = "*"


@dataclass(frozen=True)
class Deps:
    module: str
    parts: str = "all"
    fields: tuple = ALL_FIELDS
    upstream: tuple = ()
    granularity: str = "verifier"
    quick: bool = False
    note: str = ""
    extra_modules: tuple = field(default=())


# Design fields that only say how to show / name things or that no verifier reads are still listed where read.
_MECH = ("joints", "fasteners", "joins", "allowed_overlaps", "min_clearances", "base", "subassemblies", "free_standing",
         "tnut_style", "manufacturing", "gravity", "printer", "electrical", "bom_extras")

DEPS: dict[str, Deps] = {
    "part_quality": Deps("mechloop.verifiers.part_quality",
                         fields=("joints", "fasteners", "joins", "allowed_overlaps", "name"),
                         note="opt-in (runner.OPTIONAL): clean-solid and feature-purpose checks per custom part (memoised on the "
                              "part's intrinsic fingerprint), allowed-overlap / join-note / purchased-part hole audits"),
    "geometry": Deps("mechloop.verifiers.geometry",
                     fields=("envelope", "max_mass_kg", "manufacturing", "allowed_overlaps", "name"), quick=True,
                     note="per-part validity, overall size and mass (printed parts' mass reads the print settings), "
                          "simulation solid vs vendor CAD"),
    "interference": Deps("mechloop.verifiers.interference",
                         fields=("allowed_overlaps", "min_clearances", "joins", "fasteners", "free_standing", "tnut_style",
                                 "joints", "subassemblies", "bom_extras", "manufacturing", "name"),
                         granularity="pairwise", quick=True,
                         note="pairwise overlap / clearance / contact on changed pairs only; floating parts and "
                              "fastening on the whole contact graph"),
    "tolerance": Deps("mechloop.tolerance", fields=ALL_FIELDS,
                      note="Monte Carlo stack-ups across the machine: reads the whole design"),
    "manufacture": Deps("mechloop.verifiers.manufacture",
                        fields=("manufacturing", "fasteners", "printer", "joins", "allowed_overlaps", "loadcases",
                                "modalcases", "assemblycases", "thermalcases", "name"),
                        quick=True, note="DFM per custom part plus design-wide print settings and lead-ins"),
    "practice": Deps("mechloop.verifiers.practice", fields=ALL_FIELDS, quick=True,
                     note="design-practice rules across screws, bearings, belts, BOM, waivers"),
    "ratings": Deps("mechloop.verifiers.ratings",
                    fields=("joints", "belts", "bom_extras", "gravity", "electrical", "manufacturing", "fasteners",
                            "printer", "adjustments", "name"),
                    quick=True, note="drives, guide and bearing loads, BOM"),
    "motion": Deps("mechloop.verifiers.motion",
                   fields=("joints", "allowed_overlaps", "gravity", "printer", "program", "tool_point",
                           "tracking_tolerance", "belts", "electrical", "manufacturing", "joins", "practice", "fasteners",
                           "base", "adjustments", "name"),
                   note="collision sweep over poses of every moving body against everything: any part can collide"),
    "subsystems": Deps("mechloop.verifiers.subsystems", fields=ALL_FIELDS,
                       note="homing, cables, printer essentials"),
    "electrical": Deps("mechloop.verifiers.electrical", fields=ALL_FIELDS,
                       note="wiring, power, firmware config; also writes printer.cfg and wiring tables "
                            "(a reused result leaves the files of the run it came from)"),
    "assemblability": Deps("mechloop.verifiers.assemblability",
                           fields=("allowed_overlaps", "base", "fasteners", "joins", "subassemblies", "free_standing",
                                   "tnut_style", "joints", "manufacturing", "name"),
                           note="global disassembly search: any part can block another's path; exact overlap tests "
                                "along the paths are memoised per pair of part fingerprints"),
    "fea": Deps("mechloop.verifiers.fea", fields=ALL_FIELDS, granularity="per_case",
                note="each case keyed on its own parts; bed-support study on the whole machine"),
    "printing": Deps("mechloop.verifiers.printing", fields=ALL_FIELDS, upstream=("fea",),
                     note="digital-twin test print: reads the machine and this run's FEA stiffness"),
    "requirements": Deps("mechloop.verifiers.geometry", fields=ALL_FIELDS, granularity="always",
                         note="the brief's acceptance tests read every verifier's metrics; < 1 s, always re-run"),
}

QUICK = tuple(n for n, d in DEPS.items() if d.quick)


def deps_of(name: str) -> Deps | None:
    return DEPS.get(name)
