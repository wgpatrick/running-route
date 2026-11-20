"""Record which Design fields a verifier reads while it runs (the run-time check of its dependency declaration)."""
from __future__ import annotations

import contextlib

from .fingerprint import design_field_names

_SUBCLASSES: dict[type, type] = {}


@contextlib.contextmanager
def recording(design):
    """Within the block, every read of a Design field (other than the parts) on `design` is added to the yielded set.
    The design's class is swapped for a recording subclass and restored afterwards; isinstance() still holds."""
    cls = type(design)
    reads: set[str] = set()
    names = frozenset(design_field_names(design))
    sub = _SUBCLASSES.get(cls)
    if sub is None:
        def __getattribute__(self, n, _base=cls):
            rec = object.__getattribute__(self, "__dict__").get("_mechloop_reads")
            if rec is not None and n in rec[0]:
                rec[1].add(n)
            return _base.__getattribute__(self, n)

        sub = type(cls.__name__, (cls,), {"__getattribute__": __getattribute__, "__module__": cls.__module__,
                                          "__qualname__": cls.__qualname__})
        _SUBCLASSES[cls] = sub
    prev = design.__dict__.get("_mechloop_reads")
    design.__dict__["_mechloop_reads"] = (names, reads)
    design.__class__ = sub
    try:
        yield reads
    finally:
        design.__class__ = cls
        if prev is None:
            design.__dict__.pop("_mechloop_reads", None)
        else:
            design.__dict__["_mechloop_reads"] = prev
