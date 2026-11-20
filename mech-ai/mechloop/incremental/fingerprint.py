"""Stable fingerprints of what a verify reads: parts, bodies, sub-assemblies, fasteners, the design's other settings.

A fingerprint is a short SHA-256 hex digest that is the same in two processes for the same input and changes when
anything a check could read changes. It does not depend on tessellation (meshes are never hashed), on the process's
hash seed, on dict/set order or on memory addresses.

- shape_fp(shape): the shape's B-rep written as text WITHOUT triangulation (OCCT BRepTools, format version 1: every
  surface, curve, vertex and the shape's placement; the per-shape state flags, which flip when a part is meshed or
  checked, are left out), plus its bounding box. Two builds of the same geometry by the
  same code give the same text; any change of geometry or placement changes it.
- canon(obj): a JSON-able, order-independent form of any design value (dicts, dataclasses, numpy arrays, shapes,
  callables: their byte code, constants, closure values and the module-level values they name). A value that has no
  stable form (an object whose repr is only a memory address) makes canon() raise Unstable: the caller then treats the
  input as unknown and re-runs the check (never reuses on a guess).
"""
from __future__ import annotations

import dataclasses
import enum
import hashlib
import io
import json
import math
import types

FP_VERSION = "fp2"      # bump when the fingerprint recipe changes (old cache entries then simply miss)


class Unstable(Exception):
    """A value with no stable fingerprint: whatever reads it must re-run."""


def digest(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        if not isinstance(p, (bytes, bytearray)):
            p = p if isinstance(p, str) else json.dumps(p, sort_keys=True, separators=(",", ":"), default=str)
            p = p.encode()
        h.update(p)
        h.update(b"\x1f")
    return h.hexdigest()[:24]


# ---------------------------------------------------------------------------------------------------------- shapes
_FLAGS = __import__("re").compile(rb"(?m)^[01]{7}\r?\n")
_SHAPE_FP: dict[int, tuple] = {}      # id(wrapped) -> (wrapped, fp); holding `wrapped` keeps the id from being reused


def _wrapped(shape):
    return getattr(shape, "wrapped", shape)


def _fps_of(w) -> tuple[str, str]:
    """(fingerprint, intrinsic fingerprint) of a TopoDS shape: the intrinsic one is the B-rep with the shape's own
    placement taken off (two instances of one part, placed apart, share it); the full one adds that placement."""
    hit = _SHAPE_FP.get(id(w))
    if hit is not None and hit[0] is w:
        return hit[1], hit[2]
    from OCP.BRepTools import BRepTools
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopTools import TopTools_FormatVersion

    buf = io.BytesIO()
    BRepTools.Write_s(w.Located(TopLoc_Location()), buf, False, False, TopTools_FormatVersion.TopTools_FormatVersion_VERSION_1)
    # drop the per-shape state flags (free / modified / checked / orientable / closed / infinite / convex): "modified"
    # and "checked" flip when a part is meshed or checked, which is not a change of the part
    intrinsic = hashlib.sha256(_FLAGS.sub(b"", buf.getvalue())).hexdigest()[:24]
    t = w.Location().Transformation()
    loc = [round(t.Value(i, j), 9) for i in range(1, 4) for j in range(1, 5)]
    h = hashlib.sha256((intrinsic + json.dumps(loc)).encode())
    try:
        from OCP.Bnd import Bnd_Box
        from OCP.BRepBndLib import BRepBndLib

        bb = Bnd_Box()
        BRepBndLib.Add_s(w, bb, False)       # no triangulation: the bbox of the exact geometry
        if not bb.IsVoid():
            h.update(json.dumps([round(v, 4) for v in bb.Get()]).encode())
    except Exception:
        pass
    fp = h.hexdigest()[:24]
    _SHAPE_FP[id(w)] = (w, fp, intrinsic)
    return fp, intrinsic


def shape_fp(shape) -> str:
    """Fingerprint of a build123d Shape (or a TopoDS_Shape): its B-rep text without triangulation, its placement and
    its bbox."""
    if shape is None:
        return "none"
    w = _wrapped(shape)
    if w is None:
        return "null-shape"
    return _fps_of(w)[0]


def intrinsic_fp(shape) -> str:
    """The shape's fingerprint without its own placement: equal for identical instances of one part."""
    if shape is None:
        return "none"
    w = _wrapped(shape)
    return "null-shape" if w is None else _fps_of(w)[1]


def shape_summary(shape) -> dict:
    """Volume, area and bbox of a shape (for the manifest a person reads; the fingerprint itself is shape_fp)."""
    try:
        bb = shape.bounding_box()
        return {"volume_mm3": round(float(shape.volume), 3), "area_mm2": round(float(shape.area), 3),
                "bbox": [round(v, 3) for v in (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z)]}
    except Exception as e:
        return {"error": f"{type(e).__name__}"}


# ------------------------------------------------------------------------------------------------- generic values
def _float(x: float):
    if math.isnan(x):
        return "nan"
    if math.isinf(x):
        return "inf" if x > 0 else "-inf"
    return float(f"{x:.12g}")


def _code(co: types.CodeType, depth: int, seen: set):
    return ["code", co.co_name, co.co_code.hex(), co.co_names, co.co_varnames[:co.co_argcount],
            [canon(c, depth + 1, seen) if not isinstance(c, types.CodeType) else _code(c, depth + 1, seen)
             for c in co.co_consts]]


def _callable(fn, depth: int, seen: set):
    if isinstance(fn, (types.BuiltinFunctionType, types.BuiltinMethodType)):
        return ["builtin", getattr(fn, "__module__", None), fn.__qualname__]
    if isinstance(fn, types.MethodType):
        return ["method", _callable(fn.__func__, depth, seen), canon(fn.__self__, depth + 1, seen)]
    if isinstance(fn, functools_partial()):
        return ["partial", _callable(fn.func, depth, seen), canon(fn.args, depth + 1, seen), canon(fn.keywords, depth + 1, seen)]
    co = getattr(fn, "__code__", None)
    if co is None:
        if callable(fn) and hasattr(fn, "__dict__"):
            return ["callable_obj", type(fn).__qualname__, canon(vars(fn), depth + 1, seen)]
        raise Unstable(f"callable without code: {fn!r}")
    mod = getattr(fn, "__module__", "") or ""
    # a design script is loaded as module "design_<file stem>": the file's name is not part of what the function does
    out = ["fn", "design" if mod.startswith("design_") else mod, fn.__qualname__, _code(co, depth, seen),
           canon(fn.__defaults__, depth + 1, seen), canon(fn.__kwdefaults__, depth + 1, seen)]
    if fn.__closure__:
        cells = []
        for name, cell in zip(co.co_freevars, fn.__closure__):
            try:
                v = cell.cell_contents
            except ValueError:
                v = "<empty cell>"
            cells.append([name, canon(v, depth + 1, seen)])
        out.append(cells)
    # module-level values the code names (a constant H used in a face predicate), recursively through nested code
    g = getattr(fn, "__globals__", {}) or {}
    names = set()

    def walk(c):
        names.update(c.co_names)
        for k in c.co_consts:
            if isinstance(k, types.CodeType):
                walk(k)
    walk(co)
    gl = []
    for n in sorted(names):
        if n in g:
            v = g[n]
            if isinstance(v, types.ModuleType):
                gl.append([n, "module", v.__name__])
            elif mod.startswith("mechloop") or (isinstance(v, (types.FunctionType, type)) and (getattr(v, "__module__", "") or "").startswith("mechloop")):
                gl.append([n, "mechloop", getattr(v, "__qualname__", type(v).__qualname__)])   # covered by the code hash
            else:
                gl.append([n, canon(v, depth + 1, seen)])
    out.append(gl)
    return out


def functools_partial():
    import functools

    return functools.partial


def canon(obj, depth: int = 0, seen: set | None = None):
    """JSON-able, order-independent, address-free form of a design value. Raises Unstable when there is none."""
    if depth > 60:
        raise Unstable("value nested too deeply to fingerprint")
    seen = set() if seen is None else seen
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj
    if isinstance(obj, float):
        return _float(obj)
    if isinstance(obj, bytes):
        return ["bytes", hashlib.sha256(obj).hexdigest()]
    if isinstance(obj, enum.Enum):
        return ["enum", type(obj).__qualname__, str(obj.name)]
    try:
        import numpy as np

        if isinstance(obj, np.generic):
            return canon(obj.item(), depth, seen)
        if isinstance(obj, np.ndarray):
            if obj.dtype == object:
                return ["nd", list(obj.shape), canon(obj.tolist(), depth + 1, seen)]
            a = np.round(obj.astype(float), 9) if obj.dtype.kind == "f" else obj
            return ["nd", str(a.dtype), list(a.shape), hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()]
    except ImportError:     # pragma: no cover
        pass
    # shapes and geometry
    tname = type(obj).__module__ or ""
    if tname.startswith("build123d") or tname.startswith("OCP"):
        if hasattr(obj, "wrapped") and _is_topods(obj.wrapped):
            return ["shape", shape_fp(obj)]
        if _is_topods(obj):
            return ["shape", shape_fp(obj)]
        if type(obj).__name__ == "Location":
            t = obj.wrapped.Transformation()
            return ["loc", [_float(t.Value(i, j)) for i in range(1, 4) for j in range(1, 5)]]
        if type(obj).__name__ in ("Vector", "Vertex") or hasattr(obj, "X") and hasattr(obj, "Y") and hasattr(obj, "Z"):
            try:
                return ["vec", [_float(float(obj.X)), _float(float(obj.Y)), _float(float(obj.Z))]]
            except Exception:
                pass
        if type(obj).__name__ == "Plane":
            return ["plane", canon(obj.location, depth + 1, seen)]
        if type(obj).__name__ == "Axis":
            return ["axis", canon(obj.position, depth + 1, seen), canon(obj.direction, depth + 1, seen)]
    if isinstance(obj, (list, tuple)):
        return [canon(v, depth + 1, seen) for v in obj]
    if isinstance(obj, (set, frozenset)):
        items = [canon(v, depth + 1, seen) for v in obj]
        return ["set", sorted(items, key=lambda v: json.dumps(v, sort_keys=True, default=str))]
    if isinstance(obj, dict):
        items = [[canon(k, depth + 1, seen), canon(v, depth + 1, seen)] for k, v in obj.items()]
        return ["dict", sorted(items, key=lambda kv: json.dumps(kv[0], sort_keys=True, default=str))]
    if isinstance(obj, type):
        return ["type", obj.__module__, obj.__qualname__]
    if isinstance(obj, types.ModuleType):
        return ["module", obj.__name__]
    if callable(obj) and (isinstance(obj, (types.FunctionType, types.MethodType, types.BuiltinFunctionType))
                          or isinstance(obj, functools_partial())):
        return _callable(obj, depth, seen)
    if type(obj).__name__ == "weakref" or isinstance(obj, __import__("weakref").ref):
        return ["weakref"]        # back-references (a part's link to its design) carry nothing of their own
    key = id(obj)
    if key in seen:
        return ["cycle", type(obj).__qualname__]
    seen.add(key)
    try:
        if dataclasses.is_dataclass(obj):
            return ["dc", type(obj).__module__, type(obj).__qualname__,
                    [[f.name, canon(getattr(obj, f.name, None), depth + 1, seen)]
                     for f in dataclasses.fields(obj) if not f.name.startswith("_")]]
        if hasattr(obj, "__dict__"):
            d = {k: v for k, v in vars(obj).items() if not k.startswith("_")}
            return ["obj", type(obj).__module__, type(obj).__qualname__, canon(d, depth + 1, seen)]
        if hasattr(obj, "__slots__"):
            return ["slots", type(obj).__qualname__,
                    [[s, canon(getattr(obj, s, None), depth + 1, seen)] for s in obj.__slots__ if hasattr(obj, s)]]
    finally:
        seen.discard(key)
    r = repr(obj)
    if " at 0x" in r or "object at" in r:
        raise Unstable(f"no stable form for {type(obj).__qualname__}")
    return ["repr", type(obj).__qualname__, r]


def _is_topods(w) -> bool:
    return type(w).__module__.startswith("OCP") and type(w).__name__.startswith("TopoDS")


def value_fp(obj) -> str:
    """Fingerprint of any design value; 'unstable:<reason>' when it has none (callers must then re-run)."""
    try:
        return digest(FP_VERSION, canon(obj))
    except Unstable as e:
        return f"unstable:{e}"
    except RecursionError:
        return "unstable:recursion"


def is_unstable(fp: str) -> bool:
    return isinstance(fp, str) and fp.startswith("unstable:")


# -------------------------------------------------------------------------------------------------------- designs
# Component fields that no check reads (render colour); everything else is part of a part's fingerprint.
PART_FIELDS_IGNORED = ("color",)
# Design fields that decide no result: `release` only chooses the tier.
DESIGN_FIELDS_IGNORED = ("release",)


def part_fp(c) -> dict:
    """{"fp": the whole part, "geometry": shape (+ detail), "placement"... } for one Component."""
    geo = shape_fp(c.shape)
    det = shape_fp(c.detail) if getattr(c, "detail", None) is not None else "none"
    rest = {}
    for f in dataclasses.fields(c):
        if f.name in ("shape", "detail") or f.name in PART_FIELDS_IGNORED or f.name.startswith("_"):
            continue
        rest[f.name] = getattr(c, f.name)
    extra = {k: v for k, v in vars(c).items()
             if not k.startswith("_") and k not in rest and k not in ("shape", "detail") and k not in PART_FIELDS_IGNORED}
    meta = value_fp(rest.pop("meta", {}))
    other = value_fp([rest, extra])
    whole = "unstable" if is_unstable(meta) or is_unstable(other) else digest(geo, det, meta, other)
    # identical instances: same shape (placement aside), material, catalogue entry and ratings; the meta is left out
    # (it holds each instance's placement), so a check that reads meta must not be shared on this alone
    inst = digest("instance", intrinsic_fp(c.shape), c.material, c.sku, c.cots, value_fp(c.ratings), c.process or "")
    # one fingerprint per attribute, for results that read only some of them (mechloop.incremental.recorder)
    a = {k: value_fp(v) for k, v in vars(c).items() if not k.startswith("_") and k not in ("shape", "detail", "meta")}
    a.update({"shape": geo, "detail": det, "meta": meta})
    return {"fp": whole if whole != "unstable" else f"unstable:{c.name}", "shape": geo, "detail": det,
            "meta": meta, "attrs": other, "body": c.body, "instance": inst, "a": a}


def design_field_names(design) -> list[str]:
    names = [f.name for f in dataclasses.fields(design)] if dataclasses.is_dataclass(design) else []
    names += [k for k in vars(design) if k not in names]
    return [n for n in names if not n.startswith("_") and n != "components" and n not in DESIGN_FIELDS_IGNORED]


@dataclasses.dataclass
class Fingerprints:
    """Every fingerprint of one built design."""

    parts: dict            # name -> part_fp(...) dict
    fields: dict           # design field -> value_fp
    fasteners: dict        # fastener (screw part) name -> value_fp of its record
    bodies: dict           # body -> digest of its parts' fingerprints
    subassemblies: dict    # sub-assembly -> digest of its parts' fingerprints
    design: str            # every global setting (all fields but the parts)
    seconds: float = 0.0

    def part(self, name: str) -> str:
        p = self.parts.get(name)
        return p["fp"] if p else f"missing:{name}"

    def attr(self, name: str, attr: str) -> str:
        """Fingerprint of one attribute of one part ("*" = the whole part)."""
        p = self.parts.get(name)
        if p is None:
            return f"missing:{name}"
        if attr == "*":
            return p["fp"]
        return p["a"].get(attr, "absent")

    def parts_list(self) -> str:
        return digest("parts-list", list(self.parts))

    def parts_digest(self, names=None) -> str:
        names = sorted(self.parts) if names is None else sorted(set(names))
        fps = [[n, self.part(n)] for n in names]
        if any(is_unstable(f) for _, f in fps):
            return "unstable:parts"
        return digest("parts", fps)

    def fields_digest(self, names) -> str:
        vals = [[n, self.fields.get(n, "absent")] for n in sorted(set(names))]
        if any(is_unstable(v) for _, v in vals):
            bad = [n for n, v in vals if is_unstable(v)]
            return f"unstable:fields {bad}"
        return digest("fields", vals)

    def manifest(self) -> dict:
        return {"parts": {n: p["fp"] for n, p in self.parts.items()}, "fields": dict(self.fields),
                "fasteners": dict(self.fasteners), "bodies": dict(self.bodies),
                "subassemblies": dict(self.subassemblies), "design": self.design}


def fingerprint(design) -> Fingerprints:
    import time

    t0 = time.time()
    parts = {c.name: part_fp(c) for c in design.components}
    fields = {n: value_fp(getattr(design, n, None)) for n in design_field_names(design)}
    fasteners = {}
    for f in getattr(design, "fasteners", []) or []:
        fasteners[f.name] = value_fp(f)
    bodies: dict[str, list] = {}
    for n, p in parts.items():
        bodies.setdefault(p["body"], []).append([n, p["fp"]])
    bodies = {b: digest("body", sorted(v)) for b, v in bodies.items()}
    subs = {}
    for s, names in (getattr(design, "subassemblies", {}) or {}).items():
        subs[s] = digest("sub", sorted([n, parts[n]["fp"] if n in parts else "missing"] for n in names))
    glob = digest("design", sorted(fields.items()))
    return Fingerprints(parts, fields, fasteners, bodies, subs, glob, seconds=round(time.time() - t0, 2))


def diff(old: dict | None, new: Fingerprints) -> dict:
    """What changed between a stored manifest and these fingerprints: parts added/removed/changed, fields changed."""
    if not old:
        return {"first_run": True, "parts_changed": sorted(new.parts), "parts_added": sorted(new.parts),
                "parts_removed": [], "fields_changed": sorted(new.fields)}
    op, of = old.get("parts", {}), old.get("fields", {})
    changed = sorted(n for n in new.parts if op.get(n) != new.part(n) or is_unstable(new.part(n)))
    ob, osub = old.get("bodies", {}), old.get("subassemblies", {})
    return {"first_run": False, "parts_changed": changed, "parts_added": sorted(set(new.parts) - set(op)),
            "bodies_changed": sorted(b for b in set(new.bodies) | set(ob) if ob.get(b) != new.bodies.get(b)),
            "subassemblies_changed": sorted(x for x in set(new.subassemblies) | set(osub)
                                            if osub.get(x) != new.subassemblies.get(x)),
            "fasteners_changed": sorted(x for x in set(new.fasteners) | set(old.get("fasteners", {}))
                                        if old.get("fasteners", {}).get(x) != new.fasteners.get(x)),
            "parts_removed": sorted(set(op) - set(new.parts)),
            "fields_changed": sorted(n for n in set(new.fields) | set(of)
                                     if of.get(n) != new.fields.get(n) or is_unstable(new.fields.get(n, "")))}
