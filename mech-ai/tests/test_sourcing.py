"""Sourcing module (mechloop/sourcing): clients on recorded distributor responses (tests/fixtures/sourcing, no secrets), price
arithmetic, cache and offline mode, part resolution, flags, fabricated-part lead times, the Build 1 schedule and the report.
Runs offline. One live test runs only with MECHLOOP_LIVE_SOURCING=1 and the distributor keys in the environment."""
import datetime as dt
import json
import os
from pathlib import Path

import pytest

from mechloop.sourcing import clients as C
from mechloop.sourcing import http as H
from mechloop.sourcing.cache import Cache
from mechloop.sourcing.evaluate import evaluate_line
from mechloop.sourcing.fab import fabricated_lines, lead_for
from mechloop.sourcing.offers import Offer, best_order, norm_pn, same_maker, status_of
from mechloop.sourcing.report import bom_columns, markdown, run, write
from mechloop.sourcing.resolve import dg07_records, is_placeholder, resolve_sku
from mechloop.sourcing.schedule import add_business_days, schedule
from mechloop.sourcing.search import Finder

FX = Path(__file__).parent / "fixtures" / "sourcing"
DUMMY = {"DIGIKEY_CLIENT_ID": "dummy-id", "DIGIKEY_CLIENT_SECRET": "dummy-secret", "MOUSER_API_KEY": "dummy-mouser",
         "ELEMENT14_API_KEY": "dummy-e14"}


def fx(name):
    return json.loads((FX / name).read_text())


class FakeTransport:
    """Answers the clients' calls from the recorded fixtures; counts calls."""

    def __init__(self, routes):
        self.routes = routes            # [(who, url substring, Response or callable)]
        self.calls = []

    def request(self, who, method, url, **kw):
        self.calls.append((who, method, url, kw))
        for w, frag, resp in self.routes:
            if w == who and frag in url:
                return resp(kw) if callable(resp) else resp
        return H.Response(404, {})


@pytest.fixture
def env(monkeypatch):
    for k, v in DUMMY.items():
        monkeypatch.setenv(k, v)


def d2f_routes():
    return [("Digi-Key", "oauth2/token", H.Response(200, {"access_token": "tok", "expires_in": 600, "token_type": "Bearer"})),
            ("Digi-Key", "/productdetails", H.Response(200, fx("digikey_productdetails_D2F-01L.json"))),
            ("Digi-Key", "/media", H.Response(200, fx("digikey_media_SW154-ND.json"))),
            ("Mouser", "/search/partnumber", H.Response(200, fx("mouser_partnumber_D2F-01L.json"))),
            ("Newark", "catalog/products", H.Response(200, fx("element14_newark_D2F-01L.json"))),
            ("Farnell", "catalog/products", H.Response(200, fx("element14_farnell_D2F-01L.json")))]


def fake_clients(routes=None):
    t = FakeTransport(routes or d2f_routes())
    return t, [C.DigiKey(t), C.Mouser(t), C.Element14(t, "Newark"), C.Element14(t, "Farnell")]


# ------------------------------------------------------------------------------------------------ parsing
def test_digikey_product_parses_to_one_offer_per_packaging():
    p = fx("digikey_productdetails_D2F-01L.json")["Product"]
    offers = C.parse_digikey_product(p, "2026-11-20T00:00:00+00:00", media=[{"type": "CAD Models", "title": "x", "url": "u"}])
    o = offers[0]
    assert o.distributor == "Digi-Key" and o.distributor_pn == "SW154-ND" and o.mpn == "D2F-01L"
    assert o.stock == 79863 and o.moq == 1 and o.price_breaks[0] == [1, 1.44] and o.currency == "USD"
    assert o.factory_lead_weeks == 26 and o.status == "active" and o.datasheet_url.startswith("https://mm.digikey.com/")
    assert o.media and o.packaging == "Bulk"


def test_digikey_media_keeps_cad_and_datasheet_links():
    m = C.parse_digikey_media(fx("digikey_media_SW154-ND.json"))
    types = {x["type"] for x in m}
    assert "CAD Models" in types and "Datasheets" in types and "Product Photos" not in types


def test_mouser_part_parses_stock_lead_and_breaks():
    p = fx("mouser_partnumber_D2F-01L.json")["SearchResults"]["Parts"][0]
    o = C.parse_mouser_part(p, "t")
    assert o.distributor_pn == "653-D2F-01L" and o.stock == 9830 and o.moq == 1 and o.multiple == 1
    assert o.price_breaks == [[1, 1.44], [10, 1.21], [6000, 1.18]]
    assert o.factory_lead_weeks == pytest.approx(4.0) and "28 Days" in o.lead_time_text
    assert o.status == "unknown"                    # Mouser gives no lifecycle for this part: not flagged


def test_element14_exact_match_and_store_currency(env):
    t, cl = fake_clients()
    st, offers = cl[2].lookup("D2F-01L", maker="Omron")
    assert st == "ok" and offers and all(norm_pn(o.mpn) == "D2F01L" for o in offers)      # D2F01LD is not D2F-01L
    assert all(o.currency == "USD" and o.distributor == "Newark" for o in offers)
    st, far = cl[3].lookup("D2F-01L")
    assert all(o.currency == "GBP" for o in far)


def test_status_words_and_maker_match():
    assert status_of("Active") == "active" and status_of("Not For New Designs") == "nrnd" and status_of("Obsolete") == "obsolete"
    assert status_of("Last Time Buy") == "obsolete" and status_of("") == "unknown"
    assert same_maker("Omron", "Aratas (Formerly Omron Components)") and not same_maker("Vishay", "Nexperia")
    assert same_maker("Omron", "Aratas") and same_maker("Henkel / Loctite", "LOCTITE")       # Mouser names the maker "Aratas"
    assert norm_pn("BAT85,133") == "BAT85133"


# ------------------------------------------------------------------------------------------------ price arithmetic
def test_best_order_respects_moq_multiple_and_buys_up_to_a_cheaper_break():
    o = Offer("Mouser", "x", "M", "Mk", stock=1000, moq=1, multiple=1, price_breaks=[[1, 1.98], [10, 1.50]])
    b = best_order(o, 9)
    assert b["order_qty"] == 10 and b["total"] == pytest.approx(15.0)          # 9 x 1.98 = 17.82 > 10 x 1.50
    o2 = Offer("Mouser", "x", "M", "Mk", stock=1000, moq=50, multiple=25, price_breaks=[[50, 0.10]])
    assert best_order(o2, 3)["order_qty"] == 50
    assert best_order(o2, 60)["order_qty"] == 75
    o3 = Offer("Digi-Key", "x", "M", "Mk", stock=1000, moq=1, price_breaks=[[1, 1.0]], fees=7.0)
    assert best_order(o3, 2)["total"] == pytest.approx(9.0)


# ------------------------------------------------------------------------------------------------ clients and transport
def test_digikey_lookup_caches_token_in_memory_and_gets_media(env):
    t, cl = fake_clients()
    dk = cl[0]
    st, offers = dk.lookup("D2F-01L", maker="Omron")
    st2, _ = dk.lookup("D2F-01L")
    assert st == st2 == "ok" and offers[0].media
    assert sum(1 for c in t.calls if "oauth2/token" in c[2]) == 1


def test_mouser_rate_limit_is_retried_with_backoff_and_errors_never_carry_the_key(monkeypatch, env):
    import requests

    seq = [{"Errors": [{"Code": "TooManyRequests", "Message": "rate"}], "SearchResults": None},
           fx("mouser_partnumber_D2F-01L.json")]
    waits = []

    class R:
        def __init__(self, body):
            self.status_code, self._b, self.headers, self.text = 200, body, {}, ""

        def json(self):
            return self._b

    monkeypatch.setattr(requests, "request", lambda *a, **k: R(seq.pop(0)))
    t = H.Transport(sleep=waits.append, backoff_s=1.0)
    st, offers = C.Mouser(t).lookup("D2F-01L")
    assert st == "ok" and offers and waits == [1.0]

    def boom(method, url, params=None, **k):
        raise requests.ConnectionError(f"failed {url}?apiKey={params['apiKey']}")
    monkeypatch.setattr(requests, "request", boom)
    with pytest.raises(H.SourcingError) as e:
        C.Mouser(H.Transport(sleep=lambda s: None, retries=1)).lookup("D2F-01L")
    assert "dummy-mouser" not in str(e.value) and e.value.__cause__ is None and "Mouser" in str(e.value)


def test_missing_credential_is_a_clean_error(monkeypatch):
    monkeypatch.delenv("MOUSER_API_KEY", raising=False)
    with pytest.raises(H.SourcingError, match="MOUSER_API_KEY is not set"):
        C.Mouser(FakeTransport([])).lookup("X")


# ------------------------------------------------------------------------------------------------ cache, offline
def test_cache_ttl_and_offline(tmp_path):
    c = Cache(tmp_path, ttl_hours=24)
    o = Offer("Mouser", "653-X", "X", "Mk", stock=5, price_breaks=[[1, 2.0]], retrieved_at="2026-11-18T00:00:00+00:00")
    c.put("Mouser", "X", "ok", [o], "2026-11-18T00:00:00+00:00")
    now = dt.datetime(2026, 11, 20, tzinfo=dt.timezone.utc)
    assert c.get("Mouser", "X", now=now) is None                              # 48 h old: expired
    rec = c.get("Mouser", "X", offline=True, now=now)
    assert rec["stale"] and rec["offers"][0].distributor_pn == "653-X"
    assert c.get("Mouser", "X", now=dt.datetime(2026, 11, 18, 12, tzinfo=dt.timezone.utc))["stale"] is False


def test_finder_uses_the_cache_and_offline_never_calls(tmp_path, env):
    t, cl = fake_clients()
    f = Finder(clients=cl, cache=Cache(tmp_path))
    r1 = f.find("D2F-01L", "Omron")
    n = len(t.calls)
    r2 = Finder(clients=cl, cache=Cache(tmp_path)).find("D2F-01L", "Omron")
    assert len(t.calls) == n and all(v["cached"] for v in r2.values()) and r1.keys() == r2.keys()
    off = Finder(clients=cl, cache=Cache(tmp_path / "empty"), offline=True).find("D2F-01L")
    assert len(t.calls) == n and all(v["status"] == "not_cached" for v in off.values())
    # the cache holds no credential or token
    blob = "".join(p.read_text() for p in tmp_path.rglob("*.json"))
    assert not any(v in blob for v in DUMMY.values()) and "tok" not in blob.replace("stock", "")


# ------------------------------------------------------------------------------------------------ resolution
def test_resolution_order_and_placeholders():
    r = resolve_sku("ENDSTOP-MICRO")
    assert r["kind"] == "distributor" and r["items"][0]["mpn"] == "D2F-01L" and "PROVENANCE_AUDIT" in r["source"]
    inlet = resolve_sku("INLET-C14-SW-FUSE-T8A")
    assert [i["mpn"] for i in inlet["items"]] == ["DD11.0114.1111", "4301.1401"]
    mc = resolve_sku("SHCS-M3x8", line={"maker": "any (to the standard)", "maker_part_number": "ISO 4762 M3", "mcmaster_number": "91290A400",
                                        "mcmaster_status": "confirmed on McMaster's page"})
    assert mc["kind"] == "catalogue_house" and mc["seller"] == "McMaster-Carr"
    mi = resolve_sku("TNUT-2020-M5", line={"maker": "MISUMI", "maker_part_number": "MISUMI HNTAJ5-5"})
    assert mi["kind"] == "catalogue_house" and mi["items"][0]["mpn"] == "HNTAJ5-5"
    assert resolve_sku("CTRL-OCTOPUS-V1.1")["kind"] == "maker_direct"
    assert is_placeholder("BRKT-2020", line={"maker": "not specified", "maker_part_number": "not specified"})
    gt = resolve_sku("GT2-20T-B5 [12 mm belt]")
    assert gt["placeholder"] and "9 mm GT2" in gt["replace_with"]
    assert resolve_sku("DRIVER-BTT-TMC2209 (Octopus: X, Y)")["kind"] == "maker_direct"


def test_dg07_records_use_the_real_parts_schema(tmp_path):
    recs = dg07_records(Cache(tmp_path))
    e = recs["ENDSTOP-MICRO"]
    assert e["maker"] == "Omron" and e["mpn"] == "D2F-01L" and e["sellers"] == [] and not e["sold_by_maker"]
    assert recs["CTRL-OCTOPUS-V1.1"]["sold_by_maker"] and "INLET-C14-SW-FUSE-T8A" not in recs


# ------------------------------------------------------------------------------------------------ evaluation and flags
def _finder_with(offers_by_dist, tmp_path):
    class FakeClient:
        def __init__(self, name):
            self.name = name

        def lookup(self, mpn, maker=None, match="exact"):
            o = offers_by_dist.get(self.name, [])
            return ("ok" if o else "not_found"), o
    return Finder(clients=[FakeClient(n) for n in ("Digi-Key", "Mouser", "Newark", "Farnell")], cache=Cache(tmp_path))


def test_line_flags_single_source_low_stock_long_lead(tmp_path):
    o = Offer("Digi-Key", "SW154-ND", "D2F-01L", "Omron", stock=8, price_breaks=[[1, 1.44]], status="active")
    far = Offer("Farnell", "1", "D2F-01L", "Omron", stock=0, price_breaks=[[1, 1.0]], currency="GBP", factory_lead_weeks=20)
    f = _finder_with({"Digi-Key": [o], "Farnell": [far]}, tmp_path)
    r = evaluate_line({"sku": "ENDSTOP-MICRO", "qty": 2, "unit_cost_usd": 1.5}, f)
    assert r["api_verified"] and r["cost_usd"] == pytest.approx(2.88) and r["old_estimate_usd"] == 3.0
    assert {"single_source", "low_stock"} <= set(r["flags"]) and "out_of_stock" not in r["flags"]
    assert r["lead_business_days"] == 3 and r["items"][0]["stock_coverage"] == 4.0
    oos = Offer("Digi-Key", "x", "D2F-01L", "Omron", stock=0, price_breaks=[[1, 1.44]], factory_lead_weeks=26, status="Not For New Designs")
    oos.status = "nrnd"
    r2 = evaluate_line({"sku": "ENDSTOP-MICRO", "qty": 2}, _finder_with({"Digi-Key": [oos]}, tmp_path / "b"))
    assert {"out_of_stock", "long_lead", "not_active"} <= set(r2["flags"]) and r2["lead_business_days"] == 26 * 5 + 3


def test_houses_and_placeholders_are_not_api_verified(tmp_path):
    f = _finder_with({}, tmp_path)
    mc = evaluate_line({"sku": "SHCS-M3x8", "qty": 45, "unit_cost_usd": 0.08, "mcmaster_number": "91290A400", "mcmaster_status": "confirmed"}, f)
    assert mc["flags"] == ["no_distributor"] and mc["cost_usd"] == 3.6 and mc["lead_business_days"] == 2 and not mc["api_verified"]
    ph = evaluate_line({"sku": "BRKT-2020", "qty": 32, "unit_cost_usd": 0.6, "maker": "not specified"}, f)
    assert "placeholder" in ph["flags"]
    nf = evaluate_line({"sku": "ENDSTOP-MICRO", "qty": 2, "unit_cost_usd": 1.5}, f)
    assert {"not_found", "no_distributor"} <= set(nf["flags"])


# ------------------------------------------------------------------------------------------------ fabricated, schedule
def test_fabricated_lead_times_from_profiles_and_benchmark():
    assert lead_for("sendcutsend", "sheet", "bent")["business_days"] == 3
    assert lead_for("sendcutsend", "sheet", "flat")["business_days"] == 2
    cc = lead_for(None, "printed")
    assert cc["shop"] == "craftcloud" and cc["business_days"] == 11 and "8-11 business days" in cc["verbatim"]
    assert lead_for("craftcloud", "printed", option="fast")["business_days"] == 4
    assert lead_for("hubs", "printed")["business_days"] == 8
    x = lead_for("xometry", "machined")
    assert x["estimated"] and x["business_days"] == 9 and "pcbway" in x["basis"]
    assert lead_for("jlccnc", "sheet", "flat")["business_days"] == 9      # 2 build + 7 international shipping (planning)
    fl = fabricated_lines([{"name": "duct", "process": "printed", "estimate_usd": 0.24}, {"name": "plate", "process": "sheet", "form": "flat",
                                                                                         "shop": "sendcutsend", "estimate_usd": 1.0}])
    assert fl["by_shop"]["craftcloud"]["order_usd"] == 24.02 and fl["by_shop"]["sendcutsend"]["order_usd"] == 1.0


def test_business_days_and_schedule_critical_path():
    fri = dt.date(2026, 11, 20)
    assert add_business_days(fri, 1) == dt.date(2026, 11, 23) and add_business_days(fri, 5) == dt.date(2026, 11, 27)
    s = schedule(fri, [{"sku": "MOTOR", "lead_business_days": 3, "members": ["m1"]}, {"sku": "RAIL", "lead_business_days": 10, "members": ["r1"]},
                       {"sku": "TNUT", "lead_business_days": 5, "members": []}],
                 [{"name": "plate", "shop": "sendcutsend", "lead_business_days": 2}, {"name": "duct", "shop": "craftcloud", "lead_business_days": 11}],
                 {"drive": ["m1", "plate"], "cooling": ["duct"]})
    subs = {x["name"]: x for x in s["subassemblies"]}
    assert subs["drive"]["gated_by"] == "MOTOR" and subs["drive"]["earliest_start"] == "2026-11-25"
    assert s["final_assembly"]["earliest_start"] == add_business_days(fri, 11).isoformat()
    assert s["critical_path"][0]["path"] == ["duct", "cooling", "final assembly"]


# ------------------------------------------------------------------------------------------------ report
def test_report_end_to_end_offline_from_recorded_responses(tmp_path, env):
    t, cl = fake_clients()
    cache = Cache(tmp_path / "cache")
    Finder(clients=cl, cache=cache).find("D2F-01L", "Omron")          # fill the cache from the fixtures
    data = {"design": "toy", "lines": [{"sku": "ENDSTOP-MICRO", "qty": 2, "unit_cost_usd": 1.5, "members": ["sw1", "sw2"]},
                                       {"sku": "SHCS-M3x8", "qty": 10, "unit_cost_usd": 0.08, "mcmaster_number": "91290A400", "mcmaster_status": "confirmed"},
                                       {"sku": "BRKT-2020", "qty": 4, "unit_cost_usd": 0.6}],
            "fabricated": [{"name": "duct", "process": "printed", "estimate_usd": 0.24}],
            "subassemblies": {"endstops": ["sw1", "sw2"]}}
    f = Finder(clients=cl, cache=cache, offline=True)
    rep = run(data, f, order_date=dt.date(2026, 11, 23))
    s = rep["summary"]
    assert s["lines"] == 3 and s["api_verified"]["lines"] == 1 and s["flags"]["placeholder"] == 1 and s["offline"]
    end = next(r for r in rep["lines"] if r["sku"] == "ENDSTOP-MICRO")
    assert end["items"][0]["best"]["distributor"] in ("Digi-Key", "Mouser") and end["items"][0]["cad_links"]
    assert s["critical_path"][0]["path"][0] == "duct"                 # print service, 11 business days, beats the placeholder's 10
    md, smd = markdown(rep)
    assert "## Purchased lines" in md and "Critical path" in smd
    out = write(rep, tmp_path / "out" / "toy")
    cols = bom_columns("toy", root=tmp_path / "out")
    assert cols["ENDSTOP-MICRO"]["price"] == end["cost_usd"] and (out / "SCHEDULE.md").exists()


# ------------------------------------------------------------------------------------------------ live (optional)
@pytest.mark.skipif(os.environ.get("MECHLOOP_LIVE_SOURCING") != "1", reason="live distributor test: set MECHLOOP_LIVE_SOURCING=1")
def test_live_d2f01l_at_all_distributors(tmp_path):
    f = Finder(cache=Cache(tmp_path))
    r = f.find("D2F-01L", "Omron")
    assert r["Digi-Key"]["status"] == "ok" and r["Mouser"]["status"] == "ok"
    assert any(o.stock > 0 for v in r.values() for o in v["offers"])


def test_reel_only_obsolete_part_is_not_counted_and_alternates_are_priced(tmp_path):
    reel = Offer("Digi-Key", "497-2406-ND", "PN2222A", "ST", stock=0, moq=20000, price_breaks=[[20000, 0.04133]], status="obsolete",
                 status_text="Obsolete")
    alt = Offer("Mouser", "512-PN2222ATA", "PN2222ATA", "onsemi", stock=23202, price_breaks=[[1, 0.32]], status="active")

    class FC:
        def __init__(self, name):
            self.name = name

        def lookup(self, mpn, maker=None, match="exact"):
            o = {"PN2222A": {"Digi-Key": [reel]}, "PN2222ATA": {"Mouser": [alt]}}.get(mpn, {}).get(self.name, [])
            return ("ok" if o else "not_found"), o
    f = Finder(clients=[FC(n) for n in ("Digi-Key", "Mouser")], cache=Cache(tmp_path))
    r = evaluate_line({"sku": "TRANSISTOR-PN2222A", "qty": 1, "items": [{"maker": "ST", "mpn": "PN2222A"}],
                       "alternates": [{"maker": "onsemi", "mpn": "PN2222ATA"}]}, f)
    assert {"moq_excess", "not_active", "out_of_stock"} <= set(r["flags"]) and r["cost_usd"] is None and not r["api_verified"]
    assert r["alternate_parts"][0]["distributor_pn"] == "512-PN2222ATA" and r["alternate_parts"][0]["flags"] == ["single_source"]


def test_build_package_sourcing_cells():
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_package", Path(__file__).resolve().parents[1] / "tools" / "build_package.py")
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    cell = bp._sourcing_cell({"price": 2.88, "distributor": "Digi-Key", "stock": "79,863", "lead": 3, "flags": ["single_source"]})
    assert cell == "$2.88 Digi-Key, stock 79,863; lead 3 bd; single_source"
    assert bp._sourcing_cell(None) == "not in the sourcing report"
    assert bp._sourcing_csv({"price": 1.234, "distributor": "Mouser", "distributor_pn": "653-X x2", "stock": "5", "lead": 3, "flags": []}) == \
        [1.23, "Mouser", "653-X x2", "5", 3, ""]
    assert bp._sourcing_columns("no-such-design-xyz") == {}
