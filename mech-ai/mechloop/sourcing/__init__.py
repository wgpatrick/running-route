"""Live sourcing of purchased parts (docs/ROADMAP.md priority 1; Build 1 buildability gate).

- clients.py: Digi-Key v4, Mouser, element14 (Newark, Farnell) -> normalised `Offer`s (offers.py); http.py paces, retries and
  keeps credentials out of every message.
- cache.py: out/sourcing_cache/<distributor>/<MPN>.json with a TTL (24 h); offline mode reads only the cache.
- resolve.py: BOM line (SKU) -> maker + MPN (real_parts.json, data/sourcing/mpn_map.json, the catalogue); placeholders for DG-07.
- evaluate.py: best in-stock offer at the build quantity, alternatives, coverage, lead time, flags.
- fab.py: fabricated parts' lead time and price per shop (shop profiles' lead_time, data/sourcing/fab_services.json).
- schedule.py: Build 1 schedule (arrivals, sub-assembly starts, critical path).
- report.py: JSON + markdown per design; `bom_columns()` for tools/build_package.py.

CLI: `python -m mechloop.sourcing --design designs/printer_v10_1.py` (see `--help`).

Credentials (environment only, read at call time, never logged or stored): DIGIKEY_CLIENT_ID, DIGIKEY_CLIENT_SECRET,
MOUSER_API_KEY, ELEMENT14_API_KEY.
"""
from .offers import Offer, best_order
from .resolve import dg07_records, is_placeholder, resolve_sku

__all__ = ["Offer", "best_order", "resolve_sku", "is_placeholder", "dg07_records"]
