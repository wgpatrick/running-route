"""HTTP for the distributor clients: pacing, retry with backoff, and error messages that never carry a credential.

Mouser and element14 take their API key in the query string and Digi-Key returns a bearer token, so a URL, a request
object or a `requests` exception text can hold a secret. Nothing here logs, prints or raises any of them: errors are
`SourcingError("<distributor>: HTTP 429")`-style messages built only from the distributor name, the status code and
the exception class name.

`Transport` is the real one (requests). Tests pass a fake with the same `request()` signature that returns recorded
responses, so no test needs the network or a key.
"""
from __future__ import annotations

import time


class SourcingError(RuntimeError):
    """A distributor call failed. The message is safe to print (no URL, no key, no token)."""


class RateLimited(SourcingError):
    pass


class Response:
    def __init__(self, status: int, body, headers: dict | None = None):
        self.status = status
        self.body = body              # parsed JSON (dict/list) or text
        self.headers = headers or {}


class Transport:
    """requests-based transport with per-distributor pacing and retries on 429 / 5xx / connection errors."""

    def __init__(self, min_interval_s: dict | None = None, retries: int = 4, backoff_s: float = 2.0, timeout_s: float = 30.0,
                 sleep=time.sleep):
        self.min_interval = dict(min_interval_s or {})
        self.retries, self.backoff, self.timeout = retries, backoff_s, timeout_s
        self._last: dict[str, float] = {}
        self._sleep = sleep
        self.calls: dict[str, int] = {}

    def _pace(self, who: str) -> None:
        gap = self.min_interval.get(who, 0.0)
        if gap:
            wait = self._last.get(who, 0.0) + gap - time.monotonic()
            if wait > 0:
                self._sleep(wait)
        self._last[who] = time.monotonic()

    def request(self, who: str, method: str, url: str, *, params=None, json=None, data=None, headers=None,
                retry_on=lambda r: False) -> Response:
        """One call with retries. `retry_on(response)` lets a client retry on a 200 that carries a rate-limit error
        (Mouser does this)."""
        import requests  # lazy: the rest of mechloop does not need it

        attempt = 0
        while True:
            attempt += 1
            self._pace(who)
            self.calls[who] = self.calls.get(who, 0) + 1
            try:
                r = requests.request(method, url, params=params, json=json, data=data, headers=headers, timeout=self.timeout)
            except requests.RequestException as e:            # str(e) can contain the URL with its key: never use it
                if attempt > self.retries:
                    raise SourcingError(f"{who}: {type(e).__name__} after {attempt} attempts") from None
                self._sleep(self.backoff * 2 ** (attempt - 1))
                continue
            try:
                body = r.json()
            except ValueError:
                body = r.text
            resp = Response(r.status_code, body, {k.lower(): v for k, v in r.headers.items()
                                                   if k.lower() in ("retry-after", "x-ratelimit-remaining", "x-burstlimit-remaining")})
            again = r.status_code == 429 or r.status_code >= 500 or (r.status_code == 200 and retry_on(resp))
            if again and attempt <= self.retries:
                ra = resp.headers.get("retry-after")
                try:
                    wait = float(ra) if ra else self.backoff * 2 ** (attempt - 1)
                except ValueError:
                    wait = self.backoff * 2 ** (attempt - 1)
                self._sleep(min(wait, 90.0))
                continue
            if r.status_code == 429 or (r.status_code == 200 and retry_on(resp)):
                raise RateLimited(f"{who}: rate limited after {attempt} attempts")
            return resp
