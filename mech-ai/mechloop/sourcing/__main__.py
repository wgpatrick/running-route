"""python -m mechloop.sourcing: sourcing report + Build 1 schedule for a design, a build-package BOM or an orderable list."""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys

from .config import config
from .report import lines_from_bom_csv, lines_from_list, run, snapshot_design, write
from .search import Finder

ELECTRICAL_WORDS = ("Electronics", "Wire, connectors", "Toolhead", "Bed: heater")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--design", help="design file (purchased parts, fabricated parts and sub-assemblies)")
    src.add_argument("--bom-csv", help="a build package's bom.csv (purchased lines only)")
    src.add_argument("--list", help="an orderable list JSON (e.g. mechloop/data/sourcing/v12_electronics.json)")
    ap.add_argument("--offline", action="store_true", help="use only the cache; never call a distributor")
    ap.add_argument("--refresh", action="store_true", help="ignore fresh cache records and ask the distributors again")
    ap.add_argument("--builds", type=int, help="build quantity (machines)")
    ap.add_argument("--order-date", help="YYYY-MM-DD (default: next business day)")
    ap.add_argument("--with-mpn-only", action="store_true", help="only lines that resolve to a distributor MPN")
    ap.add_argument("--electrical-only", action="store_true", help="only electrical / purchased-electronics categories (bom.csv input)")
    ap.add_argument("--print-service", help="print service for printed parts (default from fab_services.json: craftcloud)")
    ap.add_argument("--print-option", help="print service lead option (craftcloud: fast)")
    ap.add_argument("--distributors", help="comma-separated subset of Digi-Key,Mouser,Newark,Farnell")
    ap.add_argument("--out", help="output folder (default out/sourcing/<name>)")
    ap.add_argument("--name", help="report name (default: the design / list name)")
    ap.add_argument("--report-root", help="root of the verify reports (default out/)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    cfg = config()
    if a.distributors:
        cfg["distributors"] = [x.strip() for x in a.distributors.split(",")]
    if a.design:
        data = snapshot_design(a.design, a.report_root)
    elif a.bom_csv:
        data = lines_from_bom_csv(a.bom_csv)
    else:
        data = lines_from_list(a.list)
    if a.name:
        data["design"] = a.name
    log = (lambda s: print(s, file=sys.stderr, flush=True)) if a.verbose else None
    finder = Finder(offline=a.offline, refresh=a.refresh, cfg=cfg, log=log)
    only = None
    if a.with_mpn_only or a.electrical_only:
        from .resolve import resolve_sku

        def only(L):
            if a.electrical_only and L.get("category") and not any(L["category"].startswith(w) for w in ELECTRICAL_WORDS):
                return False
            if a.with_mpn_only:
                return bool(L.get("items")) or resolve_sku(L["sku"], line=L)["kind"] == "distributor" and not resolve_sku(L["sku"], line=L)["placeholder"]
            return True
    od = _dt.date.fromisoformat(a.order_date) if a.order_date else None
    rep = run(data, finder, cfg, a.builds, od, only=only, print_service=a.print_service, print_option=a.print_option, log=log)
    out = write(rep, a.out)
    print(json.dumps({**{k: rep["summary"][k] for k in ("design", "lines", "purchased_cost_usd", "purchased_old_estimate_usd", "api_verified",
                                                        "fabricated_cost_usd", "total_cost_usd", "flags", "final_assembly", "critical_path", "lookups")},
                      "out": str(out)}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
