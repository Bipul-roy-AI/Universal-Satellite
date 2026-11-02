from copy import deepcopy
import unittest
from urllib.parse import parse_qs, urlsplit

from universal_satellite import Client
from universal_satellite.catalog import datasets, get_dataset
from universal_satellite.client import validate_bbox, validate_dates
from universal_satellite.http import ProviderError


def item(identifier="scene", cloud=5):
    props = {"datetime": "2024-01-02T10:00:00Z", "platform": "sentinel-2a"}
    if cloud is not None:
        props["eo:cloud_cover"] = cloud
    return {"type": "Feature", "id": identifier, "collection": "sentinel-2-l2a",
            "geometry": {"type": "Point", "coordinates": [90.4, 23.8]},
            "properties": props, "assets": {"red": {"href": "https://example.test/red.tif"}}}


def page(items, links=None):
    return {"type": "FeatureCollection", "features": items, "links": links or []}


class FakeTransport:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def request_json(self, url, *, method="GET", body=None):
        self.calls.append((url, method, deepcopy(body)))
        if not self.responses:
            raise AssertionError("Unexpected provider request")
        return deepcopy(self.responses.pop(0))


class SearchTests(unittest.TestCase):
    def search(self, transport, **kwargs):
        return Client(transport=transport).search(**{
            "dataset": "sentinel-2-l2a", "bbox": [90.2, 23.6, 90.5, 23.9],
            "start": "2024-01-01", "end": "2024-03-31", **kwargs})

    def test_query_cloud_filter_excludes_unknown_and_high_cloud(self):
        transport = FakeTransport(page([item("ok"), item("cloudy", 90), item("unknown", None)]))
        result = self.search(transport, cloud=20)
        self.assertEqual([v["id"] for v in result["features"]], ["ok"])
        self.assertEqual(transport.calls[0][2]["query"], {"eo:cloud_cover": {"lte": 20}})
        self.assertTrue(result["universal_satellite"]["search_complete"])

    def test_post_merge_pagination_and_duplicate_items(self):
        url = "https://earth-search.aws.element84.com/v1/search"
        transport = FakeTransport(
            page([item("one")], [{"rel": "next", "href": url, "method": "POST", "merge": True, "body": {"token": "page2"}}]),
            page([item("one"), item("two")]))
        result = self.search(transport, limit=10)
        self.assertEqual([v["id"] for v in result["features"]], ["one", "two"])
        self.assertIn("bbox", transport.calls[1][2])
        self.assertEqual(transport.calls[1][2]["token"], "page2")
        self.assertEqual(result["universal_satellite"]["pages"], 2)

    def test_get_relative_next_link(self):
        transport = FakeTransport(page([item("one")], [{"rel": "next", "href": "?token=two"}]), page([item("two")]))
        self.search(transport)
        self.assertEqual(transport.calls[1][0], "https://earth-search.aws.element84.com/v1/search?token=two")
        self.assertIsNone(transport.calls[1][2])

    def test_get_then_post_merge_keeps_original_search_parameters(self):
        transport = FakeTransport(
            page([item("one")], [{"rel": "next", "href": "?token=two"}]),
            page([item("two")], [{"rel": "next", "href": "/v1/search", "method": "POST", "merge": True, "body": {"token": "three"}}]),
            page([item("three")]))
        result = self.search(transport)
        self.assertEqual(len(result["features"]), 3)
        self.assertEqual(transport.calls[2][2]["token"], "three")
        self.assertIn("bbox", transport.calls[2][2])

    def test_static_inventory_does_not_send_date_or_date_sort(self):
        for dataset in ["cop-dem-glo-30", "nasadem", "jrc-gsw"]:
            with self.subTest(dataset=dataset):
                transport = FakeTransport(page([item()]))
                result = self.search(transport, dataset=dataset)
                self.assertNotIn("datetime", transport.calls[0][2])
                self.assertNotIn("sortby", transport.calls[0][2])
                self.assertFalse(result["universal_satellite"]["temporal_filter_applied"])
                self.assertEqual(result["universal_satellite"]["requested_dates"], ["2024-01-01", "2024-03-31"])

    def test_limit_is_total_and_marks_truncation(self):
        transport = FakeTransport(page([item("one"), item("two")]))
        result = self.search(transport, limit=1)
        self.assertEqual(len(result["features"]), 1)
        self.assertFalse(result["universal_satellite"]["search_complete"])

    def test_repeating_next_link_fails(self):
        transport = FakeTransport(page([], [{"rel": "next", "href": "/v1/search", "method": "POST", "body": {}}]),
                                  page([], [{"rel": "next", "href": "/v1/search", "method": "POST", "body": {}}]))
        with self.assertRaisesRegex(ProviderError, "repeated"):
            self.search(transport)

    def test_foreign_pagination_origin_refused(self):
        transport = FakeTransport(page([], [{"rel": "next", "href": "https://untrusted.test/search"}]))
        with self.assertRaisesRegex(ProviderError, "origin"):
            self.search(transport)

    def test_empty_search_is_valid(self):
        result = self.search(FakeTransport(page([])))
        self.assertEqual(result["features"], [])
        self.assertTrue(result["universal_satellite"]["search_complete"])

    def test_reference_sources_are_explicitly_rejected(self):
        with self.assertRaisesRegex(ValueError, "reference"):
            self.search(FakeTransport(), dataset="landsat-mss")

    def test_radar_query_does_not_apply_optical_cloud_filter(self):
        transport = FakeTransport(page([item(cloud=None)]))
        self.search(transport, dataset="sentinel-1-grd", cloud=20)
        self.assertNotIn("query", transport.calls[0][2])

    def test_bad_bbox_dates_limits_fail_before_network(self):
        for kwargs in [{"bbox": [180, 0, -180, 1]}, {"bbox": [0, 0, float("nan"), 2]},
                       {"start": "2024-03-31", "end": "2024-01-01"}, {"start": "bad"},
                       {"limit": 0}, {"limit": True}, {"limit": 1001}, {"cloud": float("nan")}, {"cloud": -1}, {"cloud": True}, {"start": "20240101"}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.search(FakeTransport(), **kwargs)

    def test_invalid_provider_response_fails(self):
        with self.assertRaises(ProviderError):
            self.search(FakeTransport({"error": "provider error"}))

    def test_catalog_ids_are_unique_and_adapters_have_endpoints(self):
        sources = datasets()
        self.assertEqual(len(sources), len({v.id for v in sources}))
        for source in sources:
            if source.status == "searchable":
                self.assertTrue(source.endpoint.startswith("https://"))
                self.assertTrue(source.collection)
            self.assertIs(get_dataset(source.id), source)

    def test_toa_sr_and_dn_collections_remain_distinct_in_search_and_provenance(self):
        expected = {
            "sentinel-2-l1c": ("sentinel-2-l1c", "L1C", "TOA"),
            "sentinel-2-l2a": ("sentinel-2-l2a", "L2A", "Surface reflectance"),
            "landsat-c2-l1": ("landsat-c2l1", "L1", "Digital numbers"),
            "landsat-c2-ard-toa": ("landsat-c2ard-ta", "ARD", "TOA"),
            "landsat-c2-l2": ("landsat-c2-l2", "L2", "Surface reflectance"),
        }
        for dataset, (collection, level, measurement) in expected.items():
            with self.subTest(dataset=dataset):
                feature = item()
                feature["collection"] = collection
                transport = FakeTransport(page([feature]))
                result = self.search(transport, dataset=dataset, cloud=20)
                self.assertEqual(transport.calls[0][2]["collections"], [collection])
                self.assertIn(get_dataset(dataset).endpoint, transport.calls[0][0])
                self.assertEqual(result["universal_satellite"]["processing_level"], level)
                self.assertIn(measurement, result["universal_satellite"]["measurement"])
                self.assertEqual(result["features"][0]["assets"], feature["assets"])


class WeatherAndSigningTests(unittest.TestCase):
    def test_weather_requests_era5_utc_and_preserves_units(self):
        raw = {"hourly": {"time": ["1981-01-01T00:00"], "temperature_2m": [20], "precipitation": [0]},
               "hourly_units": {"temperature_2m": "°C", "precipitation": "mm"}}
        transport = FakeTransport(raw)
        value = Client(transport=transport).weather(latitude=23.8, longitude=90.4, start="1981-01-01", end="1981-01-01")
        query = parse_qs(urlsplit(transport.calls[0][0]).query)
        self.assertEqual(query["models"], ["era5"])
        self.assertEqual(query["timezone"], ["UTC"])
        self.assertEqual(value["hourly_units"]["precipitation"], "mm")
        self.assertIn("attribution", value["universal_satellite"])

    def test_weather_rejects_invalid_variable_and_window(self):
        for kwargs in [{"variables": ["invented"]}, {"start": "1939-01-01"},
                       {"end": "1983-01-01"}, {"latitude": 91}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Client(transport=FakeTransport()).weather(**{"latitude": 20, "longitude": 70,
                    "start": "1981-01-01", "end": "1981-01-02", **kwargs})

    def test_weather_empty_or_inconsistent_response_rejected(self):
        with self.assertRaises(ProviderError):
            Client(transport=FakeTransport({"hourly": {}})).weather(latitude=20, longitude=70, start="1981-01-01", end="1981-01-01")

    def test_weather_accepts_boundary_coordinates_and_rejects_all_null(self):
        raw = {"hourly": {"time": ["1981-01-01T00:00"], "temperature_2m": [None], "precipitation": [1]}}
        result = Client(transport=FakeTransport(raw)).weather(latitude=90, longitude=180, start="1981-01-01", end="1981-01-01")
        self.assertEqual(result["hourly"]["precipitation"], [1])
        raw["hourly"]["precipitation"] = [None]
        with self.assertRaisesRegex(ProviderError, "no observations"):
            Client(transport=FakeTransport(raw)).weather(latitude=90, longitude=180, start="1981-01-01", end="1981-01-01")

    def test_signing_returns_copy_and_preserves_provider_origin(self):
        source = item()
        href = "https://data.blob.core.windows.net/container/red.tif"
        source["assets"]["red"]["href"] = href
        transport = FakeTransport({"href": href + "?sig=temporary"})
        result = Client(transport=transport).sign_item(source)
        self.assertEqual(source["assets"]["red"]["href"], href)
        self.assertIn("?sig=", result["assets"]["red"]["href"])
        self.assertEqual(parse_qs(urlsplit(transport.calls[0][0]).query)["href"], [href])

    def test_signing_rejects_wrong_origin(self):
        source = item()
        source["assets"]["red"]["href"] = "https://data.blob.core.windows.net/red.tif"
        with self.assertRaises(ProviderError):
            Client(transport=FakeTransport({"href": "https://other.test/file"})).sign_item(source)


if __name__ == "__main__":
    unittest.main()
