"""The normalised distributor offer and the price arithmetic on it.

One `Offer` is one orderable item at one distributor: a distributor part number at one packaging, with its stock, minimum
order quantity, order multiple and price breaks. Every client (Digi-Key, Mouser, element14) returns these, so the rest of
the module never reads a distributor's own JSON.
"""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field

STATUS_ACTIVE, STATUS_NRND, STATUS_OBSOLETE, STATUS_UNKNOWN = "active", "nrnd", "obsolete", "unknown"


@dataclass
class Offer:
    distributor: str                     # "Digi-Key" | "Mouser" | "Newark" | "Farnell"
    distributor_pn: str
    mpn: str
    maker: str
    stock: int = 0
    moq: int = 1
    multiple: int = 1
    price_breaks: list = field(default_factory=list)   # [[qty, unit_price], ...] ascending qty
    currency: str = "USD"
    packaging: str = ""
    factory_lead_weeks: float | None = None            # maker's lead time as the distributor states it, in weeks
    lead_time_text: str = ""                           # the distributor's own words ("28 Days", "26 weeks", "161 days")
    datasheet_url: str = ""
    media: list = field(default_factory=list)          # [{"type": "CAD Models", "title": ..., "url": ...}]
    product_url: str = ""
    status: str = STATUS_UNKNOWN                       # active | nrnd | obsolete | unknown
    status_text: str = ""
    marketplace: bool = False
    fees: float = 0.0                                  # per-order fee (Digi-Key Digi-Reel)
    retrieved_at: str = ""                             # ISO time the distributor answered
    store: str = ""                                    # element14 store id

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Offer":
        keys = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in d.items() if k in keys})


def norm_pn(s) -> str:
    """Part numbers compared without case, spaces, dashes, dots, commas or slashes ("BAT85,133" == "bat85133")."""
    return re.sub(r"[^A-Za-z0-9]", "", str(s or "")).upper()


def same_maker(a, b) -> bool:
    """Loose maker match: one name's first significant word appears in the other ("Omron" vs "Aratas (Formerly Omron
    Components)", "TE Connectivity AMP Connectors" vs "TE"). Empty on either side matches."""
    if not a or not b:
        return True
    A, B = str(a).lower(), str(b).lower()
    stop = {"the", "inc", "corp", "corporation", "co", "ltd", "llc", "gmbh", "ag", "electronics", "components", "formerly",
            "technologies", "technology", "industries", "connectivity", "products", "inc.", "&", "and", "contact", "group"}
    wa = [w for w in re.findall(r"[a-z0-9]+", A) if w not in stop]
    wb = [w for w in re.findall(r"[a-z0-9]+", B) if w not in stop]
    return any(w in wb for w in wa[:2]) or any(w in wa for w in wb[:2]) or A in B or B in A


def unit_price_at(breaks, qty: int) -> float | None:
    """Unit price for an order of `qty`: the highest break at or below qty. None below the first break."""
    best = None
    for q, p in sorted((int(q), float(p)) for q, p in breaks or ()):
        if q <= qty:
            best = p
    return best


def order_options(o: Offer, need: int) -> list[tuple[int, float, float]]:
    """(order qty, unit price, total incl. fees) for buying at least `need`: the smallest legal quantity, and each larger
    price break that would cost less in total. Respects MOQ and order multiple."""
    if not o.price_breaks:
        return []
    mult = max(1, int(o.multiple or 1))
    first = max(int(o.moq or 1), int(sorted(o.price_breaks)[0][0]))
    base = max(need, first)
    base = int(math.ceil(base / mult) * mult)
    cands = {base}
    for q, _ in o.price_breaks:
        q = int(q)
        if q > base:
            cands.add(int(math.ceil(q / mult) * mult))
    out = []
    for q in sorted(cands):
        u = unit_price_at(o.price_breaks, q)
        if u is not None:
            out.append((q, u, round(q * u + (o.fees or 0.0), 4)))
    best_total = min(t for _, _, t in out) if out else None
    # keep the minimum quantity always (it is what "buy what you need" means) and the cheapest option
    keep = [out[0]] + [x for x in out[1:] if x[2] == best_total and x[2] < out[0][2]]
    return keep


def best_order(o: Offer, need: int) -> dict | None:
    """Cheapest legal order of at least `need` from this offer: {qty, unit, total, currency}."""
    opts = order_options(o, need)
    if not opts:
        return None
    q, u, t = min(opts, key=lambda x: (x[2], x[0]))
    return {"order_qty": q, "unit_price": u, "total": t, "currency": o.currency, "min_qty_total": opts[0][2]}


def status_of(text) -> str:
    """Map a distributor's lifecycle words to active / nrnd / obsolete / unknown."""
    s = str(text or "").strip().lower()
    if not s:
        return STATUS_UNKNOWN
    if any(w in s for w in ("obsolete", "discontinued", "end of life", "eol", "no longer", "last time buy", "not available")):
        return STATUS_OBSOLETE
    if "not recommended" in s or "nrnd" in s or "not for new design" in s:
        return STATUS_NRND
    if any(w in s for w in ("active", "new product", "new at", "stocked", "in production", "direct_ship", "direct ship")):
        return STATUS_ACTIVE
    return STATUS_UNKNOWN


def money_text(s) -> float | None:
    """'$1,234.50' / '1,23 €' / '£0.95' -> float."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    t = re.sub(r"[^0-9.,]", "", str(s))
    if not t:
        return None
    if "," in t and "." in t:
        t = t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".") if len(t.split(",")[-1]) != 3 else t.replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def int_text(s) -> int:
    m = re.search(r"\d[\d,]*", str(s or ""))
    return int(m.group(0).replace(",", "")) if m else 0
