"""Exercise publication, input validation, and interrupted transfer behavior."""

from io import BytesIO
from http.client import IncompleteRead
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from universal_satellite.download import DownloadError, download_asset


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


if __name__ == "__main__":
    unittest.main()
