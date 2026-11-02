from io import BytesIO
from http.client import IncompleteRead
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from universal_satellite.http import ProviderError, Transport


class HTTPTests(unittest.TestCase):
    def test_transient_failure_retries_and_posts_json(self):
        with patch("universal_satellite.http.urlopen", side_effect=[HTTPError("https://example.test", 503, "Unavailable", {}, None), BytesIO(b'{"features": []}')]) as call, patch("universal_satellite.http.time.sleep"):
            value = Transport().request_json("https://example.test/search", method="POST", body={"limit": 2})
            self.assertEqual(value, {"features": []})
            self.assertEqual(call.call_count, 2)
            request = call.call_args.args[0]
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.data, b'{"limit": 2}')

    def test_network_and_http_errors_do_not_leak_query_tokens(self):
        for error in [URLError("sig=secret"), HTTPError("https://example.test?sig=secret", 403, "sig=secret", {}, None)]:
            with patch("universal_satellite.http.urlopen", side_effect=error):
                with self.assertRaises(ProviderError) as context:
                    Transport().request_json("https://example.test/search?sig=secret")
                self.assertNotIn("secret", str(context.exception))

    def test_invalid_json_and_insecure_scheme_rejected(self):
        with patch("universal_satellite.http.urlopen", return_value=BytesIO(b'not json')):
            with self.assertRaisesRegex(ProviderError, "JSON"):
                Transport().request_json("https://example.test")
        with self.assertRaisesRegex(ProviderError, "HTTPS"):
            Transport().request_json("http://example.test")

    def test_interrupted_payload_is_provider_error(self):
        with patch("universal_satellite.http.urlopen", side_effect=IncompleteRead(b"partial", 10)):
            with self.assertRaises(ProviderError):
                Transport().request_json("https://example.test")


if __name__ == "__main__":
    unittest.main()
