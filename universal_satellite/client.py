"""STAC discovery with bounded pagination and reproducible query metadata."""
from copy import deepcopy
from datetime import date, datetime, timezone
import math
import json
from urllib.parse import urlencode, urljoin, urlsplit

from .catalog import get_dataset
from .http import ProviderError, Transport


def validate_bbox(bbox):
    try:
        values = [float(v) for v in bbox]
    except (TypeError, ValueError):
        raise ValueError("bbox must contain west,south,east,north in EPSG:4326") from None
    if len(values) != 4 or not all(math.isfinite(v) for v in values):
        raise ValueError("bbox must contain four finite coordinates")
    w, s, e, n = values
    if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
        raise ValueError("bbox must satisfy -180 <= west < east <= 180 and -90 <= south < north <= 90; split antimeridian queries")
    return values


def validate_dates(start, end):
    try:
        a, b = date.fromisoformat(start), date.fromisoformat(end)
    except (TypeError, ValueError):
        raise ValueError("start and end must be ISO dates (YYYY-MM-DD)") from None
    if a > b:
        raise ValueError("start must be on or before end")
    if a.isoformat() != start or b.isoformat() != end:
        raise ValueError("start and end must use YYYY-MM-DD")
    return a.isoformat(), b.isoformat()


class Client:
    def __init__(self, *, transport=None, timeout=60):
        self.transport = transport or Transport(timeout=timeout)

    def search(self, *, dataset, bbox, start, end, cloud=None, limit=100):
        source = get_dataset(dataset)
        if source.status != "searchable" or not source.endpoint or not source.collection:
            raise ValueError(f"{dataset} is a reference source, not an implemented search adapter; see {source.docs_url}")
        bounds = validate_bbox(bbox)
        start, end = validate_dates(start, end)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be an integer from 1 to 1000")
        if cloud is not None and (isinstance(cloud, bool) or not isinstance(cloud, (int, float)) or not math.isfinite(cloud) or not 0 <= cloud <= 100):
            raise ValueError("cloud must be between 0 and 100")
        # Scene-level optical metadata is not a valid filter for SAR/DEM products.
        apply_cloud = cloud is not None and source.category == "optical"
        body = {
            "collections": [source.collection], "bbox": bounds,
            "limit": min(limit, 100),
        }
        if source.temporal:
            body["datetime"] = f"{start}T00:00:00Z/{end}T23:59:59.999999Z"
        # All catalog adapters below implement STAC Sort and Query extensions.
        if source.temporal:
            body["sortby"] = [{"field": "properties.datetime", "direction": "desc"}]
        if apply_cloud:
            body["query"] = {"eo:cloud_cover": {"lte": cloud}}
        url, method = source.endpoint.rstrip("/") + "/search", "POST"
        initial_body = deepcopy(body)
        features, seen_items, seen_pages = [], set(), set()
        complete = False
        pages = 0
        # Bound pathological or non-progressing provider pagination.
        while pages < 100:
            key = (url, method, json.dumps(body, sort_keys=True))
            if key in seen_pages:
                raise ProviderError("Provider repeated a pagination link; narrow the date range")
            seen_pages.add(key)
            page = self.transport.request_json(url, method=method, body=body)
            pages += 1
            if page.get("type") != "FeatureCollection" or not isinstance(page.get("features"), list):
                raise ProviderError("STAC provider returned an invalid FeatureCollection")
            accepted = []
            for item in page["features"]:
                if not isinstance(item, dict) or item.get("type") != "Feature" or not item.get("id"):
                    raise ProviderError("STAC provider returned an invalid item")
                identity = (item.get("collection", source.collection), item["id"])
                if identity in seen_items:
                    continue
                seen_items.add(identity)
                if apply_cloud:
                    value = item.get("properties", {}).get("eo:cloud_cover")
                    # Missing cloud metadata cannot establish that a scene passes.
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= cloud:
                        continue
                accepted.append(item)
            remaining = limit - len(features)
            features.extend(accepted[:remaining])
            next_link = next((link for link in page.get("links", []) if link.get("rel") == "next"), None)
            if len(features) >= limit:
                complete = next_link is None and len(accepted) <= remaining
                break
            if not next_link:
                complete = True
                break
            if not isinstance(next_link.get("href"), str):
                raise ProviderError("STAC next link has no URL")
            next_url = urljoin(url, next_link["href"])
            if urlsplit(next_url).scheme != "https" or urlsplit(next_url).netloc != urlsplit(source.endpoint).netloc:
                raise ProviderError("Refusing a pagination link outside the catalog's HTTPS origin")
            method = next_link.get("method", "GET").upper()
            if method not in ("GET", "POST"):
                raise ProviderError("Unsupported STAC pagination method")
            if method == "POST":
                link_body = next_link.get("body", {})
                if not isinstance(link_body, dict):
                    raise ProviderError("Invalid STAC pagination body")
                body = {**(body if body is not None else initial_body), **link_body} if next_link.get("merge") else link_body
            else:
                body = None
            url = next_url
        if pages == 100 and not complete and len(features) < limit:
            raise ProviderError("Provider exceeded 100 pages; narrow the date range")
        return {
            "type": "FeatureCollection", "features": features,
            "universal_satellite": {
                "dataset": dataset, "endpoint": source.endpoint,
                "processing_level": source.processing_level, "measurement": source.measurement,
                "query": initial_body, "requested_limit": limit, "returned": len(features),
                "search_complete": complete, "pages": pages,
                "cloud_filter_applied": apply_cloud,
                "temporal_filter_applied": source.temporal,
                "requested_dates": [start, end],
                "temporal_note": "Inclusive date filter applied" if source.temporal else "Static spatial inventory: requested dates were not applied; source dates describe the acquisition/record era.",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    def sign_item(self, item):
        """Explicitly obtain short-lived Planetary Computer asset URLs in memory."""
        result = deepcopy(item)
        for asset in result.get("assets", {}).values():
            href = asset.get("href", "")
            host = urlsplit(href).hostname or ""
            if urlsplit(href).scheme == "https" and host.endswith(".blob.core.windows.net"):
                response = self.transport.request_json(
                    "https://planetarycomputer.microsoft.com/api/sas/v1/sign?" + urlencode({"href": href})
                )
                signed = response.get("href", "")
                if urlsplit(signed).scheme != "https" or urlsplit(signed).hostname != host:
                    raise ProviderError("Invalid Planetary Computer signing response")
                asset["href"] = signed
        return result

    def weather(self, *, latitude, longitude, start, end, variables=None):
        """Hourly Open-Meteo historical reanalysis (not satellite observations)."""
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (latitude, longitude)) or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("latitude must be -90 to 90 and longitude -180 to 180 (finite WGS84 coordinates)")
        start, end = validate_dates(start, end)
        if start < "1940-01-01":
            raise ValueError("Historical weather starts in 1940")
        if date.fromisoformat(end) > datetime.now(timezone.utc).date():
            raise ValueError("Historical weather cannot request future dates")
        allowed = {"temperature_2m", "precipitation", "relative_humidity_2m", "wind_speed_10m", "et0_fao_evapotranspiration"}
        variables = list(variables or ["temperature_2m", "precipitation"])
        if not variables or set(variables) - allowed:
            raise ValueError("Unsupported weather variable; choose: " + ", ".join(sorted(allowed)))
        if (date.fromisoformat(end) - date.fromisoformat(start)).days > 366:
            raise ValueError("Request weather in windows of at most 367 days")
        params = {"latitude": latitude, "longitude": longitude, "start_date": start,
                  "end_date": end, "hourly": ",".join(variables), "timezone": "UTC", "models": "era5"}
        result = self.transport.request_json("https://archive-api.open-meteo.com/v1/archive?" + urlencode(params))
        hourly = result.get("hourly", {})
        if not isinstance(hourly, dict):
            raise ProviderError("Weather provider returned invalid hourly data")
        times = hourly.get("time", [])
        if not isinstance(times, list) or not times or any(not isinstance(hourly.get(v), list) or len(hourly[v]) != len(times) for v in variables):
            raise ProviderError("Weather provider returned missing or inconsistent hourly data")
        if all(value is None for variable in variables for value in hourly[variable]):
            raise ProviderError("Weather provider returned no observations; check coverage and publication lag")
        result["universal_satellite"] = {"provider": "Open-Meteo / ERA5", "requested": params,
            "note": "Model reanalysis; recent dates may be unavailable due to publication lag.",
            "attribution": "Weather data by Open-Meteo.com; ERA5 by Copernicus Climate Change Service (C3S)."}
        return result
