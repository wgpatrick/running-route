"""On-disk cache of distributor answers: out/sourcing_cache/<distributor>/<MPN>.json (out/ is gitignored).

Keyed by distributor + MPN (+ match mode). A record holds the normalised offers (never the raw response, never a URL with a
key) and the time it was retrieved. Fresh within the TTL (default 24 h, config `cache_ttl_hours`); offline mode reads any
record regardless of age and marks it stale. "not_found" answers are cached too, so a verify run does not ask again.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path

from .config import CACHE_DIR
from .offers import Offer


def _key(mpn: str, match: str = "exact") -> str:
    k = re.sub(r"[^A-Za-z0-9._-]+", "_", mpn.strip())[:120] or "_"
    return k + ("" if match == "exact" else f"__{match}")


class Cache:
    def __init__(self, root: Path | str = CACHE_DIR, ttl_hours: float = 24.0):
        self.root = Path(root)
        self.ttl = _dt.timedelta(hours=ttl_hours)

    def path(self, distributor: str, mpn: str, match: str = "exact") -> Path:
        return self.root / re.sub(r"[^A-Za-z0-9]+", "_", distributor) / (_key(mpn, match) + ".json")

    def get(self, distributor: str, mpn: str, match: str = "exact", offline: bool = False, now=None) -> dict | None:
        """{"status", "offers": [Offer], "retrieved_at", "stale"} or None when missing (or expired and not offline)."""
        p = self.path(distributor, mpn, match)
        if not p.exists():
            return None
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
        when = _dt.datetime.fromisoformat(rec["retrieved_at"])
        now = now or _dt.datetime.now(_dt.timezone.utc)
        stale = now - when > self.ttl
        if stale and not offline:
            return None
        return {"status": rec["status"], "offers": [Offer.from_dict(o) for o in rec.get("offers", [])],
                "retrieved_at": rec["retrieved_at"], "stale": stale, "cached": True}

    def put(self, distributor: str, mpn: str, status: str, offers: list[Offer], retrieved_at: str, match: str = "exact") -> None:
        p = self.path(distributor, mpn, match)
        p.parent.mkdir(parents=True, exist_ok=True)
        rec = {"distributor": distributor, "mpn": mpn, "match": match, "status": status, "retrieved_at": retrieved_at,
               "offers": [o.to_dict() for o in offers]}
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec, indent=1), encoding="utf-8")
        tmp.replace(p)
