"""ArcGIS download contracts; no native ArcGIS runtime is installed here."""

import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch


class Parameter:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.value = None
        self.enabled = True
        self.filter = types.SimpleNamespace()
        self.setErrorMessage = Mock()

    @property
    def valueAsText(self):
        return None if self.value is None else str(self.value)


class ArcGISDownloadTests(unittest.TestCase):
    def setUp(self):
        self.arcpy = types.ModuleType("arcpy")
        self.arcpy.Parameter = Parameter
        self.arcpy.SpatialReference = lambda code: code
        self.arcpy.ExecuteError = type("ExecuteError", (Exception,), {})
        self.arcpy.env = types.SimpleNamespace(autoCancelling=True, isCancelled=False)
        for name in ("SetProgressor", "SetProgressorPosition", "SetProgressorLabel", "ResetProgressor"):
            setattr(self.arcpy, name, Mock())
        self.modules = patch.dict("sys.modules", {"arcpy": self.arcpy})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        path = Path(__file__).resolve().parents[1] / "gis/arcgis/UniversalSatellite.pyt"
        loader = importlib.machinery.SourceFileLoader("arcgis_download_test", str(path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.toolbox = importlib.util.module_from_spec(spec)
        loader.exec_module(self.toolbox)

    def parameters(self, **changes):
        params = self.toolbox.DownloadAssets().getParameterInfo()
        values = {"manifest": "scenes.geojson", "assets": "red, nir08", "folder": "images", **changes}
        for parameter in params:
            if parameter.name in values:
                parameter.value = values[parameter.name]
        return params

    def test_gui_uses_operator_folder_and_optional_signing_with_progress(self):
        def helper(manifest, keys, directory, **kwargs):
            self.assertFalse(self.arcpy.env.autoCancelling)
            self.assertFalse(kwargs["cancelled"]())
            kwargs["progress"](50, "Downloaded asset 1 of 2")
            return {"downloaded": ["images/red.tif"], "failed": [], "cancelled": False}

        messages = Mock()
        with patch("universal_satellite.download.download_manifest", side_effect=helper) as transfer:
            self.toolbox.DownloadAssets().execute(self.parameters(sign_planetary=True, overwrite=True), messages)
        self.assertEqual(transfer.call_args.args, ("scenes.geojson", ["red", "nir08"], "images"))
        self.assertTrue(transfer.call_args.kwargs["sign_planetary"])
        self.assertTrue(transfer.call_args.kwargs["overwrite"])
        self.arcpy.SetProgressorPosition.assert_called_with(50)
        self.arcpy.ResetProgressor.assert_called_once()
        self.assertTrue(self.arcpy.env.autoCancelling)

    def test_partial_success_warns_and_keeps_completed_results(self):
        result = {"downloaded": ["red.tif"], "failed": [{"scene": "scene", "asset": "nir08", "error": "HTTP 403"}], "cancelled": False}
        messages = Mock()
        with patch("universal_satellite.download.download_manifest", return_value=result):
            self.toolbox.DownloadAssets().execute(self.parameters(), messages)
        messages.addWarningMessage.assert_called_once_with("scene / nir08: HTTP 403")
        messages.addErrorMessage.assert_not_called()

    def test_all_failed_is_a_geoprocessing_error(self):
        result = {"downloaded": [], "failed": [{"scene": "scene", "asset": "red", "error": "Access required"}], "cancelled": False}
        messages = Mock()
        with patch("universal_satellite.download.download_manifest", return_value=result):
            with self.assertRaises(self.arcpy.ExecuteError):
                self.toolbox.DownloadAssets().execute(self.parameters(), messages)
        self.assertIn("No image assets", messages.addErrorMessage.call_args.args[0])
        self.assertTrue(self.arcpy.env.autoCancelling)

    def test_cancellation_callback_and_environment_restoration(self):
        def helper(*args, **kwargs):
            self.arcpy.env.isCancelled = True
            self.assertTrue(kwargs["cancelled"]())
            return {"downloaded": ["finished.tif"], "failed": [], "cancelled": True}

        messages = Mock()
        with patch("universal_satellite.download.download_manifest", side_effect=helper):
            self.toolbox.DownloadAssets().execute(self.parameters(), messages)
        self.assertIn("cancelled", messages.addWarningMessage.call_args.args[0])
        self.assertTrue(self.arcpy.env.autoCancelling)
        self.arcpy.ResetProgressor.assert_called_once()

    def test_missing_folder_fails_before_transfer(self):
        with patch("universal_satellite.download.download_manifest") as helper:
            with self.assertRaises(self.arcpy.ExecuteError):
                self.toolbox.DownloadAssets().execute(self.parameters(folder=None), Mock())
        helper.assert_not_called()

    def test_transfer_exception_restores_cancellation_environment(self):
        with patch("universal_satellite.download.download_manifest", side_effect=OSError("Disk full")):
            with self.assertRaises(self.arcpy.ExecuteError):
                self.toolbox.DownloadAssets().execute(self.parameters(), Mock())
        self.assertTrue(self.arcpy.env.autoCancelling)
        self.arcpy.ResetProgressor.assert_called_once()

    def test_search_download_controls_are_disabled_until_checked(self):
        tool = self.toolbox.SearchScenes()
        params = tool.getParameterInfo()
        self.assertEqual([p.name for p in params[:8]], ["dataset", "extent", "extent_crs", "start", "end", "cloud", "limit", "output"])
        self.assertFalse(params[8].value)
        self.assertTrue(all(not p.enabled for p in params[9:]))
        params[8].value = True
        tool.updateParameters(params)
        self.assertTrue(all(p.enabled for p in params[9:]))

    def test_search_then_downloads_to_operator_folder_in_same_job(self):
        tool = self.toolbox.SearchScenes()
        params = tool.getParameterInfo()
        with tempfile.TemporaryDirectory() as directory:
            values = {"start": "2024-01-01", "end": "2024-03-31", "output": str(Path(directory) / "scenes.geojson"),
                      "download_images": True, "download_assets": "red,nir", "download_folder": str(Path(directory) / "images")}
            for parameter in params:
                if parameter.name in values:
                    parameter.value = values[parameter.name]
            client = Mock()
            client.search.return_value = {"type": "FeatureCollection", "features": [{"type": "Feature", "id": "scene", "properties": {}, "geometry": None}]}
            with patch("universal_satellite.Client", return_value=client), patch.object(self.toolbox, "_wgs84_bbox", return_value=[90, 23, 91, 24]), patch.object(self.toolbox, "_extent_value"), patch.object(self.toolbox, "_download") as helper:
                tool.execute(params, Mock())
                self.assertTrue(Path(values["output"]).exists())
                self.assertEqual(helper.call_args.args[:5], (values["output"], "red,nir", values["download_folder"], False, False))

    def test_automatic_download_missing_folder_is_rejected_before_search(self):
        tool = self.toolbox.SearchScenes()
        params = tool.getParameterInfo()
        params[8].value = True
        with patch("universal_satellite.Client") as client:
            with self.assertRaises(self.arcpy.ExecuteError):
                tool.execute(params, Mock())
        client.return_value.search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
