"""Settings of the sourcing module: mechloop/data/sourcing/config.json, overridable per call."""
from __future__ import annotations

import functools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent.parent / "data" / "sourcing"
CACHE_DIR = ROOT / "out" / "sourcing_cache"
OUT_DIR = ROOT / "out" / "sourcing"


@functools.lru_cache(maxsize=1)
def _file() -> dict:
    return json.loads((DATA / "config.json").read_text(encoding="utf-8"))


def config(**over) -> dict:
    c = json.loads(json.dumps(_file()))
    c["pacing_s"] = {k: v for k, v in c["pacing_s"].items() if k != "note"}
    c.update({k: v for k, v in over.items() if v is not None})
    return c


def fx(cur: str, cfg: dict | None = None) -> float | None:
    t = (cfg or config())["fx_to_usd"]
    v = t.get(cur)
    return float(v) if isinstance(v, (int, float)) else None
