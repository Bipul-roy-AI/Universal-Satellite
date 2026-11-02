"""Small HTTPS JSON transport; honors system proxies and TLS trust."""
import json
import time
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    """A provider or network request failed."""


class Transport:
    def __init__(self, timeout=60, retries=2):
        self.timeout = timeout
        self.retries = retries

    def request_json(self, url, *, method="GET", body=None):
        # Never include a full URL in errors: query strings may contain SAS tokens.
        host = urlsplit(url).hostname or "provider"
        if urlsplit(url).scheme != "https":
            raise ProviderError("Provider requests require HTTPS")
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(url, data=data, method=method, headers={
            "Accept": "application/geo+json, application/json",
            "Content-Type": "application/json", "User-Agent": "universal-satellite/0.2.0",
        })
        for attempt in range(self.retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    payload = response.read(32 * 1024 * 1024 + 1)
                if len(payload) > 32 * 1024 * 1024:
                    raise ProviderError(f"{host}: response exceeds 32 MiB; reduce page size")
                result = json.loads(payload)
                if not isinstance(result, dict):
                    raise ProviderError(f"{host}: expected a JSON object")
                return result
            except HTTPError as exc:
                status = exc.code
                retry_after = exc.headers.get("Retry-After", "1")
                exc.close()
                if status in (429, 502, 503, 504) and attempt < self.retries:
                    delay = float(retry_after) if retry_after.isdigit() else 2 ** attempt
                    time.sleep(min(delay, 5))
                    continue
                raise ProviderError(f"{host}: HTTP {status}; check provider access, rate limits and network policy") from None
            except (URLError, TimeoutError, OSError, HTTPException):
                raise ProviderError(f"Cannot reach {host}; check proxy, TLS trust and network allowlist") from None
            except (ValueError, UnicodeError):
                raise ProviderError(f"{host}: invalid JSON response") from None
