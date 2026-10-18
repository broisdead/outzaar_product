"""Tiny stdlib HTTP client with retry/backoff. No third-party dependency."""
from __future__ import annotations

import gzip
import json
import random
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; OutzaarDiscovery/0.1; +https://outzaar.com)"


class HttpError(Exception):
    def __init__(self, status: int, body: str = ""):
        super().__init__(f"HTTP {status}: {body[:200]}")
        self.status = status
        self.body = body


class AuthError(HttpError):
    """401/403: bad key, exhausted quota, or blocked. Not worth retrying."""


class HttpClient:
    def __init__(self, timeout: int = 20, retries: int = 3, backoff: float = 1.6):
        self.timeout, self.retries, self.backoff = timeout, retries, backoff

    def request(self, method: str, url: str, *, params: dict | None = None,
                headers: dict | None = None, json_body=None, form: dict | None = None) -> str:
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params, doseq=True)
        data = None
        hdrs = {"User-Agent": UA, "Accept-Encoding": "gzip", **(headers or {})}
        if json_body is not None:
            data = json.dumps(json_body).encode()
            hdrs["Content-Type"] = "application/json"
        elif form is not None:
            data = urllib.parse.urlencode(form).encode()
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"

        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    raw = r.read()
                    if r.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                    return raw.decode(r.headers.get_content_charset() or "utf-8", "replace")
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read()[:500].decode("utf-8", "replace")
                except Exception:
                    pass
                if e.code in (401, 403):
                    raise AuthError(e.code, body)
                last = HttpError(e.code, body)
                if e.code in (429, 500, 502, 503, 504) and attempt < self.retries:
                    ra = e.headers.get("Retry-After")
                    delay = float(ra) if ra and ra.isdigit() else self.backoff ** attempt
                    time.sleep(min(delay, 30) + random.random() * 0.3)
                    continue
                raise last
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
                last = HttpError(0, str(e))
                if attempt < self.retries:
                    time.sleep(self.backoff ** attempt + random.random() * 0.3)
                    continue
                raise last
        raise last or HttpError(0, "unknown")

    def get_text(self, url, **kw) -> str:
        return self.request("GET", url, **kw)

    def get_json(self, url, **kw):
        return json.loads(self.request("GET", url, **kw))

    def post_json(self, url, json_body, **kw):
        return json.loads(self.request("POST", url, json_body=json_body, **kw))
