"""
Polite HTTP client with explicit 422 handling.

A 422 is a validation error - the request is malformed, so it fails identically
every time. Retrying wastes time and the eventual `None` silently drops whole
date windows. Transient failures (429, 5xx, network) retry; 422 raises.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

import config


class ApiValidationError(Exception):
    """HTTP 422 - the GOV.UK Search API rejected these parameters."""

    def __init__(self, message: str, params: dict | None = None, body: str = ""):
        super().__init__(message)
        self.params = params or {}
        self.body = body

    @property
    def offending(self) -> list[str]:
        hits, low = [], (self.body or "").lower()
        for key in self.params:
            base = key.replace("filter_", "").replace("reject_", "")
            if key.lower() in low or base.lower() in low:
                hits.append(key)
        return hits


_SESSION: requests.Session | None = None
_COUNT = 0


def session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        s = requests.Session()
        s.headers.update({"User-Agent": config.USER_AGENT,
                          "Accept-Language": "en-GB,en;q=0.9"})
        _SESSION = s
    return _SESSION


def _explain(body: str) -> str:
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return (body or "no detail")[:250]
    for key in ("message", "error", "errors", "detail"):
        if key in data:
            v = data[key]
            return "; ".join(map(str, v)) if isinstance(v, list) else str(v)
    return json.dumps(data)[:250]


def get(url: str, params: dict | None = None, binary: bool = False,
        raise_validation: bool = False):
    global _COUNT
    last = None
    for attempt in range(config.MAX_RETRIES):
        try:
            _COUNT += 1
            if _COUNT > config.MAX_REQUESTS:
                raise RuntimeError(f"request budget of {config.MAX_REQUESTS} exhausted")
            r = session().get(url, params=params, timeout=config.REQUEST_TIMEOUT)
            if r.status_code == 422:
                detail = _explain(r.text)
                if raise_validation:
                    raise ApiValidationError(detail, params, r.text)
                print(f"    ! 422 rejected: {detail}")
                return None
            if r.status_code == 404:
                return None
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"status {r.status_code}")
            r.raise_for_status()
            time.sleep(config.REQUEST_DELAY)
            return r.content if binary else r.text
        except ApiValidationError:
            raise
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(config.BACKOFF ** attempt)
    print(f"    ! giving up on {url} ({last})")
    return None


def get_json(url: str, params: dict, raise_validation: bool = True):
    raw = get(url, params=params, raise_validation=raise_validation)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:20]


def cached_get(url: str, folder: Path, suffix: str, binary: bool = False):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{cache_key(url)}{suffix}"
    if path.exists() and path.stat().st_size > 0:
        return path.read_bytes() if binary else path.read_text("utf-8", errors="ignore")
    payload = get(url, binary=binary)
    if payload is None:
        return None
    if binary:
        path.write_bytes(payload)
    else:
        path.write_text(payload, encoding="utf-8")
    return payload
