"""Offers for one MPN from every configured distributor, through the cache.

`find(mpn, maker)` -> {distributor: {"status": "ok" | "not_found" | "error" | "not_cached", "offers": [Offer], "retrieved_at",
"stale", "cached", "error"}}. Offline mode never calls a distributor (a missing record is "not_cached").
"""
from __future__ import annotations

from .cache import Cache
from .clients import default_clients, now_iso
from .config import config
from .http import SourcingError


class Finder:
    def __init__(self, clients=None, cache: Cache | None = None, offline: bool = False, refresh: bool = False, cfg: dict | None = None,
                 log=None):
        self.cfg = cfg or config()
        self.offline = offline
        self.refresh = refresh
        self.cache = cache or Cache(ttl_hours=self.cfg["cache_ttl_hours"])
        self._clients = clients
        self.log = log or (lambda s: None)
        self.stats = {"api": 0, "cache": 0, "errors": 0, "not_cached": 0}

    @property
    def clients(self):
        if self._clients is None:
            self._clients = default_clients()
        return self._clients

    def names(self) -> list[str]:
        return [c.name for c in self._clients] if self._clients is not None else list(self.cfg["distributors"])

    def find(self, mpn: str, maker: str | None = None, match: str = "exact") -> dict:
        out = {}
        for name in self.names():
            rec = None if self.refresh and not self.offline else self.cache.get(name, mpn, match, offline=self.offline)
            if rec is not None:
                self.stats["cache"] += 1
                out[name] = rec
                continue
            if self.offline:
                self.stats["not_cached"] += 1
                out[name] = {"status": "not_cached", "offers": [], "retrieved_at": None, "stale": None, "cached": False}
                continue
            client = next(c for c in self.clients if c.name == name)
            try:
                self.stats["api"] += 1
                status, offers = client.lookup(mpn, maker=maker, match=match)
                when = offers[0].retrieved_at if offers else now_iso()
                self.cache.put(name, mpn, status, offers, when, match)
                out[name] = {"status": status, "offers": offers, "retrieved_at": when, "stale": False, "cached": False}
                self.log(f"{name} {mpn}: {status} ({len(offers)} offers)")
            except SourcingError as e:         # the message is credential-free by construction
                self.stats["errors"] += 1
                out[name] = {"status": "error", "offers": [], "retrieved_at": None, "stale": None, "cached": False, "error": str(e)}
                self.log(f"{name} {mpn}: error {e}")
        return out
