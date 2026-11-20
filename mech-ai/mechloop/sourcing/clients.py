"""Distributor clients: Digi-Key (Products v4), Mouser (Search API v1), element14 (Product Search API; Newark and Farnell).

Each client has `lookup(mpn, maker=None, match="exact") -> (status, [Offer])` where status is "ok" | "not_found", and a pure
`parse_*` function that turns the distributor's JSON into offers (tests call these on recorded responses).

Credentials come from the environment at call time only (DIGIKEY_CLIENT_ID, DIGIKEY_CLIENT_SECRET, MOUSER_API_KEY,
ELEMENT14_API_KEY). The Digi-Key OAuth token is kept in memory on the client and never written anywhere. No credential,
token or keyed URL is ever logged, printed, cached or put in an error (see http.py).
"""
from __future__ import annotations

import datetime as _dt
import os
import time
from urllib.parse import quote

from .http import SourcingError, Transport
from .offers import Offer, int_text, money_text, norm_pn, same_maker, status_of

DIGIKEY = "Digi-Key"
MOUSER = "Mouser"
NEWARK = "Newark"
FARNELL = "Farnell"
E14_STORES = {NEWARK: ("www.newark.com", "USD"), FARNELL: ("uk.farnell.com", "GBP")}


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _https(u) -> str:
    u = str(u or "").strip()
    return "https:" + u if u.startswith("//") else u


def _env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise SourcingError(f"credential {name} is not set in the environment")
    return v


def _matches(found_mpn, want, match: str) -> bool:
    a, b = norm_pn(found_mpn).lstrip("0"), norm_pn(want).lstrip("0")      # Molex: "0430250200" is "43025-0200"
    return bool(b) and (a == b or (match == "prefix" and a.startswith(b)))


# ------------------------------------------------------------------------------------------------ Digi-Key
def parse_digikey_product(p: dict, retrieved_at: str, media: list | None = None) -> list[Offer]:
    """One Digi-Key v4 Product -> one Offer per packaging variation."""
    maker = (p.get("Manufacturer") or {}).get("Name", "")
    mpn = p.get("ManufacturerProductNumber", "")
    st = (p.get("ProductStatus") or {}).get("Status", "")
    if p.get("Discontinued") or p.get("EndOfLife"):
        st = st or "Discontinued"
    lw = p.get("ManufacturerLeadWeeks")
    try:
        lead_w = float(str(lw).split()[0]) if lw not in (None, "") else None
    except ValueError:
        lead_w = None
    out = []
    for v in p.get("ProductVariations") or []:
        breaks = [[int(b["BreakQuantity"]), float(b["UnitPrice"])] for b in v.get("StandardPricing") or [] if b.get("UnitPrice") is not None]
        out.append(Offer(
            distributor=DIGIKEY, distributor_pn=v.get("DigiKeyProductNumber", ""), mpn=mpn, maker=maker,
            stock=int(v.get("QuantityAvailableforPackageType") or 0), moq=int(v.get("MinimumOrderQuantity") or 1), multiple=1,
            price_breaks=breaks, currency="USD", packaging=(v.get("PackageType") or {}).get("Name", ""),
            factory_lead_weeks=lead_w, lead_time_text=f"{lw} weeks (ManufacturerLeadWeeks)" if lw not in (None, "") else "",
            datasheet_url=_https(p.get("DatasheetUrl")), media=list(media or []), product_url=p.get("ProductUrl", ""),
            status=status_of(st), status_text=st, marketplace=bool(v.get("MarketPlace")), fees=float(v.get("DigiReelFee") or 0.0),
            retrieved_at=retrieved_at))
    return out


def parse_digikey_media(body: dict) -> list[dict]:
    keep = ("CAD Models", "Datasheets", "EDA Models", "Drawings", "Dimensional Drawings")
    out = []
    for m in (body or {}).get("MediaLinks") or []:
        t = m.get("MediaType", "")
        if any(k.lower() in t.lower() for k in keep):
            out.append({"type": t, "title": m.get("Title", ""), "url": _https(m.get("Url"))})
    return out


class DigiKey:
    name = DIGIKEY
    base = "https://api.digikey.com"

    def __init__(self, transport: Transport, media: bool = True):
        self.t = transport
        self.media = media
        self._token: str | None = None        # memory only
        self._expires = 0.0

    def _headers(self) -> dict:
        if not self._token or time.time() > self._expires - 60:
            r = self.t.request(DIGIKEY, "POST", self.base + "/v1/oauth2/token",
                               data={"client_id": _env("DIGIKEY_CLIENT_ID"), "client_secret": _env("DIGIKEY_CLIENT_SECRET"),
                                     "grant_type": "client_credentials"})
            if r.status != 200 or not isinstance(r.body, dict) or "access_token" not in r.body:
                raise SourcingError(f"{DIGIKEY}: token request failed (HTTP {r.status})")
            self._token = r.body["access_token"]
            self._expires = time.time() + float(r.body.get("expires_in") or 600)
        return {"Authorization": "Bearer " + self._token, "X-DIGIKEY-Client-Id": _env("DIGIKEY_CLIENT_ID"),
                "X-DIGIKEY-Locale-Site": "US", "X-DIGIKEY-Locale-Language": "en", "X-DIGIKEY-Locale-Currency": "USD"}

    def _get_media(self, dkpn: str) -> list[dict]:
        r = self.t.request(DIGIKEY, "GET", f"{self.base}/products/v4/search/{quote(dkpn, safe='')}/media", headers=self._headers())
        return parse_digikey_media(r.body) if r.status == 200 and isinstance(r.body, dict) else []

    def lookup(self, mpn: str, maker: str | None = None, match: str = "exact"):
        when = now_iso()
        products = []
        r = self.t.request(DIGIKEY, "GET", f"{self.base}/products/v4/search/{quote(mpn, safe='')}/productdetails", headers=self._headers())
        if r.status == 200 and isinstance(r.body, dict) and r.body.get("Product"):
            products = [r.body["Product"]]
        elif r.status not in (200, 404, 400):
            raise SourcingError(f"{DIGIKEY}: productdetails HTTP {r.status}")
        if not products or not _matches(products[0].get("ManufacturerProductNumber"), mpn, match):
            r = self.t.request(DIGIKEY, "POST", f"{self.base}/products/v4/search/keyword", headers=self._headers(),
                               json={"Keywords": mpn, "Limit": 20, "Offset": 0})
            if r.status != 200 or not isinstance(r.body, dict):
                if r.status in (400, 404):
                    return "not_found", []
                raise SourcingError(f"{DIGIKEY}: keyword search HTTP {r.status}")
            cands = (r.body.get("ExactMatches") or []) + (r.body.get("Products") or [])
            seen, products = set(), []
            for p in cands:
                k = p.get("ManufacturerProductNumber")
                if k in seen or not _matches(k, mpn, match):
                    continue
                seen.add(k)
                products.append(p)
        products = [p for p in products if same_maker(maker, (p.get("Manufacturer") or {}).get("Name"))]
        if match == "prefix":
            products = products[:3]
        offers = []
        for p in products:
            media = []
            if self.media and p.get("ProductVariations"):
                try:
                    media = self._get_media(p["ProductVariations"][0].get("DigiKeyProductNumber", ""))
                except SourcingError:
                    media = []
            offers += parse_digikey_product(p, when, media)
        return ("ok" if offers else "not_found"), offers


# ------------------------------------------------------------------------------------------------ Mouser
def parse_mouser_part(p: dict, retrieved_at: str) -> Offer:
    breaks = []
    cur = "USD"
    for b in p.get("PriceBreaks") or []:
        price = b.get("RawPrice")
        price = float(price) if price not in (None, "") else money_text(b.get("Price"))
        if price is None:
            continue
        breaks.append([int(b.get("Quantity") or 1), price])
        cur = b.get("Currency") or cur
    lt = p.get("LeadTime") or ""
    weeks = None
    n = int_text(lt)
    if n:
        weeks = n / 7.0 if "day" in lt.lower() else float(n) if "week" in lt.lower() else None
    stock = int_text(p.get("AvailabilityInStock")) if p.get("AvailabilityInStock") not in (None, "") else (
        int_text(p.get("Availability")) if "stock" in str(p.get("Availability", "")).lower() else 0)
    life = p.get("LifecycleStatus")
    pack = next((a.get("AttributeValue") for a in p.get("ProductAttributes") or [] if a.get("AttributeName") == "Packaging"), "")
    return Offer(distributor=MOUSER, distributor_pn=p.get("MouserPartNumber", ""), mpn=p.get("ManufacturerPartNumber", ""),
                 maker=p.get("Manufacturer", ""), stock=stock, moq=int_text(p.get("Min")) or 1, multiple=int_text(p.get("Mult")) or 1,
                 price_breaks=sorted(breaks), currency=cur, packaging=pack or ("Reel" if p.get("Reeling") else ""),
                 factory_lead_weeks=weeks, lead_time_text=f"{lt} (LeadTime)" if lt else "", datasheet_url=_https(p.get("DataSheetUrl")),
                 product_url=p.get("ProductDetailUrl", ""),
                 status=status_of(life) if life else "unknown", status_text=life or "not stated by Mouser",
                 retrieved_at=retrieved_at)


def _mouser_limited(resp) -> bool:
    b = resp.body if isinstance(resp.body, dict) else {}
    return any("toomany" in str(e.get("Code", "")).lower().replace(" ", "") or "rate" in str(e.get("Message", "")).lower()
               for e in b.get("Errors") or [])


class Mouser:
    name = MOUSER
    base = "https://api.mouser.com/api/v1"

    def __init__(self, transport: Transport):
        self.t = transport

    def _post(self, path: str, body: dict):
        r = self.t.request(MOUSER, "POST", self.base + path, params={"apiKey": _env("MOUSER_API_KEY")}, json=body, retry_on=_mouser_limited)
        if r.status != 200 or not isinstance(r.body, dict):
            raise SourcingError(f"{MOUSER}: HTTP {r.status}")
        errs = [e for e in r.body.get("Errors") or []]
        if errs:
            raise SourcingError(f"{MOUSER}: " + "; ".join(str(e.get("Code") or e.get("Message"))[:60] for e in errs))
        return r.body

    def lookup(self, mpn: str, maker: str | None = None, match: str = "exact"):
        when = now_iso()
        body = self._post("/search/partnumber", {"SearchByPartRequest": {"mouserPartNumber": mpn,
                                                                         "partSearchOptions": "Exact" if match == "exact" else "None"}})
        parts = (body.get("SearchResults") or {}).get("Parts") or []
        if not parts and match == "prefix":
            body = self._post("/search/keyword", {"SearchByKeywordRequest": {"keyword": mpn, "records": 20, "startingRecord": 0}})
            parts = (body.get("SearchResults") or {}).get("Parts") or []
        parts = [p for p in parts if _matches(p.get("ManufacturerPartNumber"), mpn, match) and same_maker(maker, p.get("Manufacturer"))]
        offers = [parse_mouser_part(p, when) for p in parts]
        return ("ok" if offers else "not_found"), offers


# ------------------------------------------------------------------------------------------------ element14
def parse_element14_product(p: dict, distributor: str, currency: str, store: str, retrieved_at: str) -> Offer:
    pack = int(p.get("packSize") or 1) or 1
    breaks = [[int(b.get("from") or 1) * pack, float(b["cost"]) / pack] for b in p.get("prices") or [] if b.get("cost") is not None]
    st = p.get("stock") or {}
    lead_days = st.get("leastLeadTime")
    ds = p.get("datasheets") or []
    status_txt = str(p.get("productStatus") or "")
    stat = status_of(status_txt)
    if status_txt.upper() in ("STOCKED", "DIRECT_SHIP", "ON_DEMAND", "AWAITING_DELIVERY"):
        stat = "active"
    if "NO_LONGER" in status_txt.upper():
        stat = "obsolete"
    return Offer(distributor=distributor, distributor_pn=str(p.get("sku", "")), mpn=p.get("translatedManufacturerPartNumber", ""),
                 maker=p.get("brandName") or p.get("vendorName") or "", stock=int(st.get("level") or 0),
                 moq=int(p.get("translatedMinimumOrderQuality") or 1) * pack, multiple=pack, price_breaks=sorted(breaks),
                 currency=currency, packaging=f"{p.get('unitOfMeasure', '')} of {pack}" if pack > 1 else str(p.get("unitOfMeasure", "")).lower(),
                 factory_lead_weeks=(float(lead_days) / 7.0) if lead_days not in (None, "", 0) else None,
                 lead_time_text=f"{lead_days} days (stock.leastLeadTime)" if lead_days not in (None, "", 0) else "",
                 datasheet_url=_https(ds[0].get("url")) if ds else "", status=stat, status_text=status_txt, retrieved_at=retrieved_at,
                 store=store)


class Element14:
    base = "https://api.element14.com/catalog/products"

    def __init__(self, transport: Transport, store: str = NEWARK):
        self.t = transport
        self.name = store
        self.store_id, self.currency = E14_STORES[store]

    def lookup(self, mpn: str, maker: str | None = None, match: str = "exact"):
        when = now_iso()
        params = {"callInfo.responseDataFormat": "JSON", "callInfo.apiKey": _env("ELEMENT14_API_KEY"), "term": "manuPartNum:" + mpn,
                  "storeInfo.id": self.store_id, "resultsSettings.offset": 0, "resultsSettings.numberOfResults": 25,
                  "resultsSettings.responseGroup": "large"}
        r = self.t.request(self.name, "GET", self.base, params=params)
        if r.status != 200 or not isinstance(r.body, dict):
            raise SourcingError(f"{self.name}: HTTP {r.status}")
        if "Fault" in r.body or "fault" in r.body:
            raise SourcingError(f"{self.name}: API fault")
        ret = next((v for k, v in r.body.items() if k.endswith("Return")), {}) or {}
        prods = [p for p in ret.get("products") or []
                 if _matches(p.get("translatedManufacturerPartNumber"), mpn, match) and same_maker(maker, p.get("brandName") or p.get("vendorName"))]
        offers = [parse_element14_product(p, self.name, self.currency, self.store_id, when) for p in prods]
        return ("ok" if offers else "not_found"), offers


def default_clients(transport: Transport | None = None, which=None):
    from .config import config

    cfg = config()
    t = transport or Transport(min_interval_s=cfg["pacing_s"], retries=cfg["retries"], backoff_s=cfg["backoff_s"])
    all_ = {DIGIKEY: lambda: DigiKey(t), MOUSER: lambda: Mouser(t), NEWARK: lambda: Element14(t, NEWARK), FARNELL: lambda: Element14(t, FARNELL)}
    names = which or cfg["distributors"]
    return [all_[n]() for n in names if n in all_]
