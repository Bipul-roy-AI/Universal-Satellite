"""Exercise publication, input validation, and interrupted transfer behavior."""

from io import BytesIO
from http.client import IncompleteRead
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from universal_satellite.download import DownloadCancelled, DownloadError, download_asset, download_manifest


class Response(BytesIO):
    status = 200

    def __init__(self, body=b"raster bytes", length=None):
        super().__init__(body)
        self.headers = {"Content-Length": str(len(body) if length is None else length)}


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.item = {
            "id": "../../scene/unsafe",
            "assets": {"red": {"href": "https://data.example.test/image.tif?token=secret"}},
        }

    def download(self, response=None, **kwargs):
        with patch("universal_satellite.download.urlopen", return_value=response or Response()):
            return download_asset(self.item, "red", self.root, **kwargs)

    def test_safe_filename_atomic_complete_file(self):
        result = self.download()
        self.assertEqual(result.parent, self.root)
        self.assertEqual(result.read_bytes(), b"raster bytes")
        self.assertEqual(result.suffix, ".tif")
        self.assertNotIn("secret", result.name)
        self.assertEqual(list(self.root.glob("*.part")), [])

    def test_existing_file_preserved_until_explicit_overwrite(self):
        result = self.download()
        with self.assertRaises(FileExistsError):
            self.download(Response(b"different"))
        self.assertEqual(result.read_bytes(), b"raster bytes")
        self.download(Response(b"different"), overwrite=True)
        self.assertEqual(result.read_bytes(), b"different")

    def test_short_download_removes_staging_and_final(self):
        with self.assertRaisesRegex(DownloadError, "incomplete"):
            self.download(Response(b"short", length=100))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_failed_overwrite_preserves_previous_file(self):
        result = self.download()
        with self.assertRaises(DownloadError):
            self.download(Response(b"short", length=100), overwrite=True)
        self.assertEqual(result.read_bytes(), b"raster bytes")
        self.assertEqual(list(self.root.iterdir()), [result])

    def test_transport_interruption_cleans_partial_file(self):
        response = Response()
        response.read = unittest.mock.Mock(side_effect=[b"partial", IncompleteRead(b"short", 100)])
        with self.assertRaisesRegex(DownloadError, "transfer failed"):
            self.download(response)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_partial_http_response_not_published(self):
        response = Response()
        response.status = 206
        with self.assertRaisesRegex(DownloadError, "206"):
            self.download(response)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_http_error_message_does_not_disclose_url(self):
        error = HTTPError(self.item["assets"]["red"]["href"], 403, "secret", {}, None)
        with patch("universal_satellite.download.urlopen", side_effect=error):
            with self.assertRaises(DownloadError) as caught:
                download_asset(self.item, "red", self.root)
        self.assertIn("403", str(caught.exception))
        self.assertNotIn("secret", str(caught.exception))

    def test_network_error_is_actionable_and_redacted(self):
        with patch("universal_satellite.download.urlopen", side_effect=URLError("token=secret")):
            with self.assertRaisesRegex(DownloadError, "network access") as caught:
                download_asset(self.item, "red", self.root)
        self.assertNotIn("secret", str(caught.exception))

    def test_local_files_s3_and_embedded_credentials_rejected(self):
        for href in ["file:///etc/passwd", "s3://bucket/image.tif", "https://user:secret@host/image.tif"]:
            with self.subTest(href=href):
                self.item["assets"]["red"]["href"] = href
                with self.assertRaisesRegex(ValueError, "HTTP"):
                    download_asset(self.item, "red", self.root)

    def test_missing_asset_diagnosed(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            download_asset(self.item, "missing", self.root)

    def test_login_html_cannot_be_saved_as_raster_or_json(self):
        for media_type in ["image/tiff", "application/json"]:
            with self.subTest(media_type=media_type):
                response = Response(b"<html>Sign in</html>")
                response.headers["Content-Type"] = "text/html; charset=UTF-8"
                self.item["assets"]["red"]["type"] = media_type
                with self.assertRaisesRegex(DownloadError, "provider sign-in"):
                    self.download(response)
                self.assertEqual(list(self.root.iterdir()), [])

    def test_explicit_html_metadata_can_be_downloaded(self):
        response = Response(b"<html>Provider documentation</html>")
        response.headers["Content-Type"] = "text/html"
        self.item["assets"]["red"]["type"] = "text/html"
        result = self.download(response)
        self.assertIn(b"documentation", result.read_bytes())

    def test_sanitized_id_collisions_get_distinct_names(self):
        self.item["id"] = "scene/a"
        first = self.download()
        self.item["id"] = "scene_a"
        second = self.download()
        self.assertNotEqual(first, second)

    def test_cancellation_removes_staging_and_preserves_existing_output(self):
        result = self.download()
        stop = Event()
        response = Response()
        response.read = unittest.mock.Mock(side_effect=lambda size: (stop.set(), b"partial")[1])
        with self.assertRaises(DownloadCancelled):
            self.download(response, overwrite=True, cancelled=stop.is_set)
        self.assertEqual(result.read_bytes(), b"raster bytes")
        self.assertEqual(list(self.root.iterdir()), [result])


class ManifestDownloadTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.output = self.root / "images"
        self.manifest = self.root / "scenes.geojson"
        self.features = [{
            "type": "Feature", "id": f"scene-{i}", "properties": {}, "geometry": None,
            "assets": {
                "red": {"href": "https://data.example.test/red.tif?token=secret"},
                "nir": {"href": "https://data.example.test/nir.tif?token=secret"},
            },
        } for i in [1, 2]]
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps({"type": "FeatureCollection", "features": self.features}))

    def test_all_scenes_and_selected_assets_download_to_folder(self):
        progress = []
        with patch("universal_satellite.download.urlopen", side_effect=[Response(bytes([i])) for i in range(4)]):
            result = download_manifest(self.manifest, ["red", "nir"], self.output, progress=lambda n, m: progress.append((n, m)))
        self.assertEqual(len(result["downloaded"]), 4)
        self.assertFalse(result["failed"])
        self.assertFalse(result["cancelled"])
        self.assertEqual([Path(p).read_bytes() for p in result["downloaded"]], [bytes([i]) for i in range(4)])
        self.assertEqual({Path(p).parent for p in result["downloaded"]}, {self.output})
        self.assertEqual([n for n, _ in progress], [0, 25, 25, 50, 50, 75, 75, 100])
        self.assertTrue(all("https://" not in m and "secret" not in m and "token=" not in m for _, m in progress))

    def test_missing_asset_failure_continues_other_scenes(self):
        del self.features[0]["assets"]["red"]
        self.save()
        with patch("universal_satellite.download.urlopen", return_value=Response()):
            result = download_manifest(self.manifest, ["red"], self.output)
        self.assertEqual(len(result["downloaded"]), 1)
        self.assertEqual(len(result["failed"]), 1)
        self.assertEqual(result["failed"][0]["scene"], "scene-1")
        self.assertEqual(result["failed"][0]["asset"], "red")

    def test_invalid_asset_metadata_becomes_failure_with_signing_enabled(self):
        self.features[0]["assets"]["red"] = None
        self.features = self.features[:1]
        self.save()
        with patch("universal_satellite.client.Client") as client:
            result = download_manifest(self.manifest, ["red"], self.output, sign_planetary=True)
        client.return_value.sign_item.assert_not_called()
        self.assertEqual(len(result["failed"]), 1)

    def test_http_and_s3_failures_collected_without_token_exposure(self):
        self.features[1]["assets"]["red"]["href"] = "s3://private-bucket/data.tif"
        self.save()
        error = HTTPError("https://data.example.test/red.tif?token=secret", 403, "denied", {}, None)
        with patch("universal_satellite.download.urlopen", side_effect=error):
            result = download_manifest(self.manifest, ["red"], self.output)
        self.assertEqual(len(result["failed"]), 2)
        self.assertIn("403", result["failed"][0]["error"])
        self.assertIn("HTTPS URL", result["failed"][1]["error"])
        self.assertFalse(result["downloaded"])
        self.assertNotIn("secret", json.dumps(result))

    def test_cancel_during_chunk_keeps_previous_success_and_removes_partial(self):
        stop = Event()
        interrupted = Response()
        interrupted.read = unittest.mock.Mock(side_effect=lambda size: (stop.set(), b"partial")[1])
        with patch("universal_satellite.download.urlopen", side_effect=[Response(b"first complete"), interrupted]):
            result = download_manifest(self.manifest, ["red"], self.output, cancelled=stop.is_set)
        self.assertTrue(result["cancelled"])
        self.assertFalse(result["failed"])
        self.assertEqual(len(result["downloaded"]), 1)
        self.assertEqual(Path(result["downloaded"][0]).read_bytes(), b"first complete")
        self.assertEqual(list(self.output.iterdir()), [Path(result["downloaded"][0])])

    def test_cancel_before_work_makes_no_requests_or_output_folder(self):
        with patch("universal_satellite.download.urlopen") as request:
            result = download_manifest(self.manifest, ["red"], self.output, cancelled=lambda: True)
        request.assert_not_called()
        self.assertEqual(result, {"downloaded": [], "failed": [], "cancelled": True})
        self.assertFalse(self.output.exists())

    def test_existing_file_failure_does_not_stop_later_transfers(self):
        with patch("universal_satellite.download.urlopen", return_value=Response(b"previous")):
            previous = download_asset(self.features[0], "red", self.output)
        with patch("universal_satellite.download.urlopen", return_value=Response(b"new")):
            result = download_manifest(self.manifest, ["red"], self.output)
        self.assertEqual(previous.read_bytes(), b"previous")
        self.assertEqual(len(result["failed"]), 1)
        self.assertEqual(len(result["downloaded"]), 1)

    def test_sign_only_selected_asset_in_memory_and_preserve_manifest(self):
        self.features = self.features[:1]
        self.save()
        original = self.manifest.read_bytes()
        selected_calls = []
        def sign(selected):
            selected_calls.append(deepcopy(selected))
            selected = deepcopy(selected)
            selected["assets"]["red"]["href"] += "&sas=temporary-secret"
            return selected
        with patch("universal_satellite.client.Client") as client:
            client.return_value.sign_item.side_effect = sign
            with patch("universal_satellite.download.urlopen", return_value=Response()) as request:
                result = download_manifest(self.manifest, ["red"], self.output, sign_planetary=True)
        self.assertEqual(len(selected_calls), 1)
        self.assertEqual(set(selected_calls[0]["assets"]), {"red"})
        self.assertIn("sas=temporary-secret", request.call_args.args[0].full_url)
        self.assertEqual(self.manifest.read_bytes(), original)
        self.assertNotIn("temporary-secret", json.dumps(result))

    def test_invalid_selections_output_or_empty_manifest_rejected(self):
        for keys in [[], "red", [" "], ["red", " red "], [None]]:
            with self.subTest(keys=keys):
                with self.assertRaises(ValueError):
                    download_manifest(self.manifest, keys, self.output)
        with self.assertRaises(ValueError):
            download_manifest(self.manifest, ["red"], "")
        with self.assertRaises(ValueError):
            download_manifest(self.manifest, ["red"], self.manifest)
        self.features = []
        self.save()
        with self.assertRaisesRegex(ValueError, "no scenes"):
            download_manifest(self.manifest, ["red"], self.output)

    def test_trimmed_asset_selection_works(self):
        self.features = self.features[:1]
        self.save()
        with patch("universal_satellite.download.urlopen", return_value=Response()):
            result = download_manifest(self.manifest, [" red "], self.output)
        self.assertEqual(len(result["downloaded"]), 1)
        self.assertFalse(result["failed"])


if __name__ == "__main__":
    unittest.main()
