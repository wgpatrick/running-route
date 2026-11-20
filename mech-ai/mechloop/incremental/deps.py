"""What each verifier reads: the declaration that maps a change set to the checks to re-run.

Every verifier the runner knows (runner.ORDER and "requirements") must have an entry here; a verifier without one is
always re-run (tests/test_incremental.py asserts there is none). An entry says:

- module: where its code lives (its code hash, codehash.code_hash, is part of every cache key),
- parts: "all" (any part's fingerprint: shape, placement, material, body, ratings, meta ...) or "none",
- fields: the Design fields it reads besides the parts ("components" is the parts and is never listed),
- upstream: earlier verifiers whose metrics it reads in the same run (their metrics are hashed into its key),
- granularity: how finely results are reused,
    "verifier": the whole result is reused when nothing it reads changed,
    "per_case": FEA: each load / modal / assembly / thermal case is reused on its own, keyed by the parts it names
                (+ the screws that cross them, the joins among them, the case itself); the bed-support study reads
                the whole machine,
    "pairwise": interference: per-pair kernel results (bbox test, overlap volume, gap) are reused for pairs of
                unchanged parts; pairs are found through a spatial index (sorted bbox sweep), and the whole-design
                logic (floating parts, fastening, threads, T-slot screws) re-runs on them,
    "always":   cheap and reads the results of the others: re-runs every time,
- quick: part of `--tier quick`.

The declared fields are checked at run time: while a verifier runs, reads of Design fields are recorded, and a result
that read a field missing from its declaration is not stored in the cache (and the report says so), so a wrong
declaration costs speed, never correctness.
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
