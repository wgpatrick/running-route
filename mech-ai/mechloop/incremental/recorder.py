"""Record what a computation reads from the design, at run time: the dependency set a cached result is checked against.

While a Tracking is active, every read of
  - a Design field (joints, fasteners, manufacturing, ...),
  - the list of parts itself (design.components: iterating it, or design.get / bodies(), which read it),
  - an attribute of a part (shape, detail, meta, material, body, ratings, mass_kg, ...)
is recorded. A part attribute read through the part's __dict__, pickling or copying counts as a read of the whole
part. A cached result stores the fingerprints (taken at the start of the run, before any verifier ran) of exactly what
it read; it is reused only when all of them are unchanged. The computation is deterministic, so with the same inputs
it would take the same path and read the same things: a part it never looked at (or only looked at the body of) can
change without re-running it.

The design's and the parts' classes are swapped for recording subclasses while tracking (isinstance still holds)
and restored afterwards.
"""
from __future__ import annotations

import contextlib

from .fingerprint import design_field_names

_ACTIVE: list["Reads"] = []
_DESIGN_SUB: dict[type, type] = {}
_PART_SUB: dict[type, type] = {}
WHOLE = ("__dict__", "__getstate__", "__reduce_ex__", "__reduce__", "__copy__", "__deepcopy__")


class Reads:
    def __init__(self, field_names):
        self.names = frozenset(field_names)
        self.fields: set[str] = set()
        self.parts_list = False
        self.attrs: set[tuple[str, str]] = set()

    def absorb(self, deps: dict | None) -> None:
        """A reused sub-result's dependencies count for the enclosing computation too."""
        if not deps:
            return
        self.fields |= set(deps.get("fields", {}))
        self.parts_list = self.parts_list or "parts_list" in deps
        for k in deps.get("attrs", {}):
            n, a = k.split("\x1f", 1)
            self.attrs.add((n, a))


def _design_sub(cls):
    sub = _DESIGN_SUB.get(cls)
    if sub is None:
        def __getattribute__(self, n, _base=cls):
            if _ACTIVE:
                if n == "components":
                    for r in _ACTIVE:
                        r.parts_list = True
                else:
                    for r in _ACTIVE:
                        if n in r.names:
                            r.fields.add(n)
            return _base.__getattribute__(self, n)

        sub = type(cls.__name__, (cls,), {"__getattribute__": __getattribute__, "__module__": cls.__module__,
                                          "__qualname__": cls.__qualname__})
        _DESIGN_SUB[cls] = sub
    return sub


def _part_sub(cls):
    sub = _PART_SUB.get(cls)
    if sub is None:
        def __getattribute__(self, n, _base=cls):
            if _ACTIVE and (n in WHOLE or (n[:1] != "_" and n in object.__getattribute__(self, "__dict__"))):
                key = (object.__getattribute__(self, "name"), "*" if n in WHOLE else n)
                for r in _ACTIVE:
                    r.attrs.add(key)
            return _base.__getattribute__(self, n)

        sub = type(cls.__name__, (cls,), {"__getattribute__": __getattribute__, "__module__": cls.__module__,
                                          "__qualname__": cls.__qualname__})
        _PART_SUB[cls] = sub
    return sub


@contextlib.contextmanager
def tracking(design):
    """Yields a Reads that collects what the block reads from `design` and its parts. Nests: an inner tracking's
    reads also go to the outer ones."""
    reads = Reads(design_field_names(design))
    outer = bool(_ACTIVE)
    swapped = []
    if not outer:
        dcls = type(design)
        design.__class__ = _design_sub(dcls)
        swapped.append((design, dcls))
        for c in object.__getattribute__(design, "components"):
            pc = type(c)
            c.__class__ = _part_sub(pc)
            swapped.append((c, pc))
    _ACTIVE.append(reads)
    try:
        yield reads
    finally:
        _ACTIVE.remove(reads)
        if not outer:
            for obj, cls in swapped:
                obj.__class__ = cls


def push(deps: dict | None) -> None:
    for r in _ACTIVE:
        r.absorb(deps)


# kept for the declared-fields check
@contextlib.contextmanager
def recording(design):
    with tracking(design) as r:
        yield r.fields
