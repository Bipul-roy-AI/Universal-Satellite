from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from universal_satellite.cli import main
from universal_satellite.export import read_geojson, summarize, write_geojson


def fixture():
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": "one", "geometry": None,
         "properties": {"datetime": "2024-01-01T00:00:00Z", "platform": "landsat-8"},
         "collection": "landsat-c2-l2", "assets": {"red": {"href": "https://example.test/red.tif"}}}],
        "universal_satellite": {"search_complete": False}}


class ExportAndCLITests(unittest.TestCase):
    def test_geojson_roundtrip_and_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested/scenes.geojson"
            write_geojson(fixture(), path)
            value = read_geojson(path)
        result = summarize(value)
        self.assertEqual(result["scenes_by_month"], {"2024-01": 1})
        self.assertEqual(result["asset_scene_counts"], {"red": 1})
        self.assertFalse(result["search_complete"])

    def test_invalid_export_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file.geojson"
            path.write_text("keep")
            with self.assertRaises(ValueError):
                write_geojson({"features": []}, path)
            self.assertEqual(path.read_text(), "keep")

    def test_cli_search_writes_actual_geojson_and_nonzero_on_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory, patch("universal_satellite.cli.Client") as mocked:
            mocked.return_value.search.return_value = fixture()
            path = str(Path(directory) / "scene.geojson")
            with redirect_stdout(io.StringIO()):
                status = main(["search", "--dataset", "sentinel-2-l2a", "--bbox", "90.2,23.6,90.5,23.9", "--start", "2024-01-01", "--end", "2024-03-31", "--output", path])
            self.assertEqual(status, 0)
            self.assertEqual(read_geojson(path), fixture())
            mocked.return_value.search.assert_called_once_with(dataset="sentinel-2-l2a", bbox=[90.2, 23.6, 90.5, 23.9], start="2024-01-01", end="2024-03-31", cloud=None, limit=100)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["search", "--dataset", "landsat-mss", "--bbox", "0,0,1,1", "--start", "1980-01-01"]), 1)

    def test_download_failure_sets_exit_status_and_continues_other_scenes(self):
        value = fixture()
        value["features"].append({**value["features"][0], "id": "two"})
        with patch("universal_satellite.cli.read_geojson", return_value=value), patch("universal_satellite.cli.download_asset", side_effect=[ValueError("missing"), Path("ok.tif")]) as mock:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                status = main(["download", "scenes.geojson", "--asset", "red"])
            self.assertEqual(status, 1)
            self.assertEqual(mock.call_count, 2)

    def test_sources_json_lists_access_status(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(main(["sources", "--category", "optical", "--json"]), 0)
        values = json.loads(stream.getvalue())
        self.assertTrue(values)
        self.assertTrue(all(v["category"] == "optical" for v in values))
        self.assertTrue(any(v["status"] == "reference" for v in values))

    def test_toa_cli_passes_explicit_calibration_inputs(self):
        with patch("universal_satellite.raster.landsat_toa", return_value=Path("toa.tif")) as convert:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["toa", "--input", "B4.TIF", "--mtl", "MTL.json", "--band", "4", "--output", "toa.tif"]), 0)
            convert.assert_called_once_with("B4.TIF", "MTL.json", 4, "toa.tif")


if __name__ == "__main__":
    unittest.main()
