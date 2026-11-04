"""Adapter contract checks with test doubles, not native GIS integration tests."""

import importlib.machinery
import importlib.util
import builtins
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SEARCHABLE_IDS = [
    "landsat-c2-l2", "sentinel-2-l2a", "sentinel-1-grd", "sentinel-1-rtc",
    "cop-dem-glo-30", "nasadem", "esa-worldcover", "jrc-gsw",
    "modis-surface-reflectance", "modis-vegetation", "sentinel-2-l1c",
    "landsat-c2-l1", "landsat-c2-ard-toa",
    "smap-l4", "gpm-imerg", "viirs-black-marble", "emit-l2a", "viirs-active-fire", "jason-3", "sentinel-6", "enmap-l2a", "chirps-daily", "sentinel-3-products", "sentinel-5p-products", "sentinel-2-products", "3dep-seamless", "dynamic-world", "hyperion", "firms-viirs", "firms-modis",
]


def without_sdk(name, *args, **kwargs):
    if name == "universal_satellite" or name.startswith("universal_satellite."):
        raise ModuleNotFoundError("SDK intentionally unavailable in adapter contract test")
    return ORIGINAL_IMPORT(name, *args, **kwargs)


ORIGINAL_IMPORT = builtins.__import__


class DatasetChoiceStabilityTests(unittest.TestCase):
    def test_new_products_do_not_change_existing_qgis_enum_positions(self):
        from universal_satellite.catalog import list_datasets
        choices = [source.id for source in list_datasets() if source.status == "searchable"]
        self.assertEqual(choices[:10], [
            "landsat-c2-l2", "sentinel-2-l2a", "sentinel-1-grd", "sentinel-1-rtc",
            "cop-dem-glo-30", "nasadem", "esa-worldcover", "jrc-gsw",
            "modis-surface-reflectance", "modis-vegetation",
        ])


def load_module(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def fake_qgis():
    core = types.ModuleType("qgis.core")
    core.QgsProcessingAlgorithm = type("QgsProcessingAlgorithm", (), {"addOutput": lambda self, output: None})
    core.QgsProcessingException = type("QgsProcessingException", (Exception,), {})
    core.QgsProcessingProvider = type("QgsProcessingProvider", (), {})
    class Parameter:
        Integer = 0
        Double = 1

        def __init__(self, name, description="", **kwargs):
            self.name = name
            self.description = description
            self.kwargs = kwargs

    for name in (
        "QgsCoordinateReferenceSystem", "QgsProcessingParameterEnum",
        "QgsProcessingParameterExtent", "QgsProcessingParameterFile",
        "QgsProcessingParameterFileDestination", "QgsProcessingParameterNumber",
        "QgsProcessingParameterString", "QgsProcessingParameterBoolean",
        "QgsProcessingParameterFolderDestination", "QgsProcessingOutputString"
    ):
        setattr(core, name, Parameter)
    core.QgsCoordinateReferenceSystem = lambda code: code
    return {"qgis": types.ModuleType("qgis"), "qgis.core": core}


class QgisContractTests(unittest.TestCase):
    def setUp(self):
        self.modules = patch.dict(sys.modules, fake_qgis())
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.module = load_module(
            "universal_satellite_qgis_algorithms_test",
            ROOT / "gis/qgis/universal_satellite_qgis/algorithms.py"
        )

    def test_search_dropdown_preserves_sources_and_distinguishes_toa_sr(self):
        from universal_satellite.catalog import list_datasets

        expected = [d for d in list_datasets() if d.status == "searchable"]
        algorithm = self.module.SearchScenes()
        algorithm.addParameter = Mock()
        algorithm.initAlgorithm()
        self.assertEqual([d.id for d in algorithm.datasets], [d.id for d in expected])
        self.assertEqual([d.id for d in algorithm.datasets], SEARCHABLE_IDS)
        dataset_parameter = next(
            call.args[0] for call in algorithm.addParameter.call_args_list
            if call.args[0].name == "DATASET"
        )
        options = dataset_parameter.kwargs["options"]
        self.assertEqual(options, [f"{d.title} [{d.id}]" for d in expected])
        toa = next(label for label in options if "[sentinel-2-l1c]" in label)
        sr = next(label for label in options if "[sentinel-2-l2a]" in label)
        self.assertIn("TOA", toa.upper())
        self.assertTrue("SURFACE REFLECTANCE" in sr.upper() or "SR" in sr.upper())
        self.assertNotEqual(toa, sr)

    def test_catalog_choices_and_help_stay_visible_without_sdk(self):
        with patch("builtins.__import__", side_effect=without_sdk):
            algorithm = self.module.SearchScenes()
            algorithm.addParameter = Mock()
            algorithm.initAlgorithm()
            self.assertEqual([d.id for d in algorithm.datasets], SEARCHABLE_IDS)
            help_text = algorithm.shortHelpString()
            for source in algorithm.datasets:
                self.assertIn(f"[{source.id}]", help_text)
                self.assertIn(source.start, help_text)
                self.assertIn(source.description, help_text)
            with self.assertRaisesRegex(self.module.QgsProcessingException, "Install universal-satellite"):
                self.module._core()

    def test_older_sdk_catalog_retains_all_bundled_choices(self):
        import universal_satellite.catalog

        sources = [d for d in universal_satellite.catalog.list_datasets() if d.status == "searchable"]
        with patch.object(universal_satellite.catalog, "list_datasets", return_value=sources[:10]):
            self.assertEqual([d.id for d in self.module._datasets()], SEARCHABLE_IDS)

    def test_missing_snapshot_uses_installed_sdk_or_reports_incomplete_zip(self):
        with patch.object(self.module.Path, "read_text", side_effect=FileNotFoundError("snapshot absent")):
            self.assertEqual([d.id for d in self.module._datasets()], SEARCHABLE_IDS)
            with patch("builtins.__import__", side_effect=without_sdk):
                with self.assertRaisesRegex(RuntimeError, "complete toolbox ZIP"):
                    self.module._datasets()

    def test_all_thirteen_selected_sources_route_to_matching_sdk_dataset(self):
        from universal_satellite.catalog import list_datasets

        algorithm = self.module.SearchScenes()
        algorithm.datasets = [d for d in list_datasets() if d.status == "searchable"]
        algorithm.parameterAsEnum = Mock()
        extent = Mock()
        extent.isNull.return_value = extent.isEmpty.return_value = False
        extent.xMinimum.return_value, extent.yMinimum.return_value = 90.2, 23.6
        extent.xMaximum.return_value, extent.yMaximum.return_value = 90.5, 23.9
        algorithm.parameterAsExtent = Mock(return_value=extent)
        algorithm.parameterAsString = lambda p, key, ctx: p[key]
        algorithm.parameterAsDouble = Mock(return_value=20)
        algorithm.parameterAsInt = Mock(return_value=5)
        algorithm.parameterAsFileOutput = Mock(return_value="scenes.geojson")
        feedback = Mock()
        feedback.isCanceled.return_value = False
        client = Mock()
        client.search.return_value = {"type": "FeatureCollection", "features": []}
        with patch.object(self.module, "_core", return_value=(lambda: client, None)), patch.object(
            self.module, "_atomic_geojson"
        ):
            for index, dataset_id in enumerate(SEARCHABLE_IDS):
                with self.subTest(dataset=dataset_id):
                    algorithm.parameterAsEnum.return_value = index
                    algorithm.processAlgorithm({"START": "2024-01-01", "END": "2024-03-31"}, None, feedback)
                    self.assertEqual(client.search.call_args.kwargs["dataset"], dataset_id)
        self.assertEqual(client.search.call_count, len(SEARCHABLE_IDS))

    def test_search_transforms_extent_and_preserves_assets(self):
        algorithm = self.module.SearchScenes()
        algorithm.datasets = [types.SimpleNamespace(id="sentinel-2-l2a", category="optical")]
        algorithm.parameterAsEnum = Mock(return_value=0)
        extent = Mock()
        extent.isNull.return_value = False
        extent.isEmpty.return_value = False
        extent.xMinimum.return_value, extent.yMinimum.return_value = 90.2, 23.6
        extent.xMaximum.return_value, extent.yMaximum.return_value = 90.5, 23.9
        algorithm.parameterAsExtent = Mock(return_value=extent)
        algorithm.parameterAsString = lambda p, key, ctx: p[key]
        algorithm.parameterAsDouble = Mock(return_value=20)
        algorithm.parameterAsInt = Mock(return_value=5)
        algorithm.parameterAsFileOutput = lambda p, key, ctx: p[key]
        result = {"type": "FeatureCollection", "features": [
            {"id": "scene", "assets": {"red": {"href": "https://example.org/red.tif"}}}
        ]}
        client = Mock()
        client.search.return_value = result
        feedback = Mock()
        feedback.isCanceled.return_value = False
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "scenes.geojson")
            params = {"START": "2024-01-01", "END": "2024-02-01", "OUTPUT": path}
            with patch.object(self.module, "_core", return_value=(lambda: client, None)):
                self.assertEqual(algorithm.processAlgorithm(params, None, feedback), {"OUTPUT": path})
            self.assertEqual(json.loads(Path(path).read_text()), result)
        algorithm.parameterAsExtent.assert_called_once_with(params, "EXTENT", None, "EPSG:4326")
        client.search.assert_called_once_with(
            dataset="sentinel-2-l2a", bbox=[90.2, 23.6, 90.5, 23.9],
            start="2024-01-01", end="2024-02-01", cloud=20, limit=5
        )

    def test_nbr_delegates_correct_provider_band_names(self):
        algorithm = self.module.RasterIndex()
        algorithm.parameterAsEnum = Mock(return_value=2)
        algorithm.parameterAsFileOutput = Mock(return_value="nbr.tif")
        algorithm.parameterAsFile = lambda p, key, ctx: {"A": "nir.tif", "B": "swir.tif"}[key]
        feedback = Mock()
        feedback.isCanceled.return_value = False
        raster = types.ModuleType("universal_satellite.raster")
        raster.compute_index = Mock()
        with patch.dict(sys.modules, {"universal_satellite.raster": raster}):
            self.assertEqual(algorithm.processAlgorithm({}, None, feedback), {"OUTPUT": "nbr.tif"})
        raster.compute_index.assert_called_once_with("nbr", "nbr.tif", nir="nir.tif", swir22="swir.tif")

    def test_errors_surface_as_processing_errors(self):
        algorithm = self.module.SearchScenes()
        feedback = Mock()
        with patch.object(self.module, "_core", side_effect=ValueError("provider unavailable")):
            with self.assertRaisesRegex(self.module.QgsProcessingException, "provider unavailable"):
                algorithm.processAlgorithm({}, None, feedback)

    def _download_algorithm(self):
        algorithm = self.module.DownloadAssets()
        algorithm.parameterAsFile = lambda p, key, ctx: p[key]
        algorithm.parameterAsString = lambda p, key, ctx: p[key]
        algorithm.parameterAsBool = lambda p, key, ctx: p.get(key, False)
        return algorithm

    def _download_parameters(self):
        return {
            "MANIFEST": "scenes.geojson", "ASSETS": " red, nir08 ",
            "OUTPUT_DIR": "/chosen/images", "SIGN_PLANETARY": True, "OVERWRITE": False,
        }

    def _prepared_search(self):
        algorithm = self.module.SearchScenes()
        algorithm.datasets = [types.SimpleNamespace(id="sentinel-2-l2a", category="optical")]
        algorithm.parameterAsEnum = Mock(return_value=0)
        extent = Mock()
        extent.isNull.return_value = extent.isEmpty.return_value = False
        extent.xMinimum.return_value, extent.yMinimum.return_value = 90.2, 23.6
        extent.xMaximum.return_value, extent.yMaximum.return_value = 90.5, 23.9
        algorithm.parameterAsExtent = Mock(return_value=extent)
        algorithm.parameterAsString = lambda p, key, ctx: p.get(key, "")
        algorithm.parameterAsDouble = Mock(return_value=20)
        algorithm.parameterAsInt = Mock(return_value=5)
        algorithm.parameterAsFileOutput = lambda p, key, ctx: p[key]
        algorithm.parameterAsBool = lambda p, key, ctx: p.get(key, False)
        client = Mock()
        client.search.return_value = {"type": "FeatureCollection", "features": []}
        feedback = Mock()
        feedback.isCanceled.return_value = False
        return algorithm, client, feedback

    def test_provider_registers_gui_downloader(self):
        package_name = "qgis_provider_registration_contract"
        package = types.ModuleType(package_name)
        package.__path__ = []
        with patch.dict(sys.modules, {package_name: package, f"{package_name}.algorithms": self.module}):
            module = load_module(f"{package_name}.provider", ROOT / "gis/qgis/universal_satellite_qgis/provider.py")
            provider = module.UniversalSatelliteProvider()
            provider.addAlgorithm = Mock()
            provider.loadAlgorithms()
        self.assertEqual(
            [call.args[0].name() for call in provider.addAlgorithm.call_args_list],
            ["search_scenes", "download_assets", "raster_index", "spectral_index", "environmental_profile", "crop_raster"],
        )

    def test_download_gui_has_manifest_keys_folder_and_safe_defaults(self):
        algorithm = self.module.DownloadAssets()
        algorithm.addParameter, algorithm.addOutput = Mock(), Mock()
        algorithm.initAlgorithm()
        parameters = {call.args[0].name: call.args[0] for call in algorithm.addParameter.call_args_list}
        self.assertEqual(set(parameters), {"MANIFEST", "ASSETS", "OUTPUT_DIR", "SIGN_PLANETARY", "OVERWRITE", "RESUME", "WORKERS"})
        self.assertEqual(parameters["ASSETS"].kwargs["defaultValue"], "red,nir")
        self.assertFalse(parameters["SIGN_PLANETARY"].kwargs["defaultValue"])
        self.assertFalse(parameters["OVERWRITE"].kwargs["defaultValue"])
        self.assertEqual(algorithm.addOutput.call_args.args[0].name, "SUMMARY")

    def test_download_gui_delegates_folder_keys_signing_and_callbacks(self):
        algorithm = self._download_algorithm()
        feedback = Mock()
        feedback.isCanceled.return_value = False

        def download(*args, **kwargs):
            kwargs["progress"](50, "First asset transferred")
            self.assertFalse(kwargs["cancelled"]())
            return {"downloaded": ["red.tif", "nir.tif"], "failed": [], "cancelled": False}

        with patch("universal_satellite.download.download_manifest", side_effect=download) as helper:
            result = algorithm.processAlgorithm(self._download_parameters(), None, feedback)
        self.assertEqual(helper.call_args.args, ("scenes.geojson", ["red", "nir08"], "/chosen/images"))
        self.assertTrue(helper.call_args.kwargs["sign_planetary"])
        self.assertFalse(helper.call_args.kwargs["overwrite"])
        self.assertEqual(result["OUTPUT_DIR"], "/chosen/images")
        self.assertIn("2 downloaded, 0 failed", result["SUMMARY"])
        feedback.pushInfo.assert_any_call("First asset transferred")
        feedback.setProgress.assert_any_call(50)
        feedback.reportError.assert_not_called()

    def test_download_gui_reports_partial_failures_with_completed_count(self):
        feedback = Mock()
        result = {
            "downloaded": ["red.tif"], "cancelled": False,
            "failed": [{"scene": "scene-2", "asset": "nir08", "error": "HTTP 403"}],
        }
        with patch("universal_satellite.download.download_manifest", return_value=result):
            output = self._download_algorithm().processAlgorithm(self._download_parameters(), None, feedback)
        self.assertIn("Partial download: 1 downloaded, 1 failed", output["SUMMARY"])
        feedback.reportError.assert_called_once_with("Scene scene-2, asset nir08: HTTP 403", fatalError=False)

    def test_download_gui_all_failed_is_processing_error_not_success(self):
        feedback = Mock()
        result = {
            "downloaded": [], "cancelled": False,
            "failed": [{"scene": "scene-1", "asset": "red", "error": "HTTP 403"}],
        }
        with patch("universal_satellite.download.download_manifest", return_value=result):
            with self.assertRaisesRegex(self.module.QgsProcessingException, "No image assets were downloaded"):
                self._download_algorithm().processAlgorithm(self._download_parameters(), None, feedback)
        feedback.reportError.assert_called_once_with("Scene scene-1, asset red: HTTP 403", fatalError=False)
        self.assertIn("Download failed: 0 downloaded, 1 failed", feedback.pushInfo.call_args.args[0])
        self.assertIn("Download failed: 0 downloaded, 1 failed", feedback.pushInfo.call_args.args[0])
        feedback.setProgress.assert_not_called()

    def test_download_gui_cancellation_retains_count_without_forcing_completion(self):
        feedback = Mock()
        result = {"downloaded": ["red.tif"], "failed": [], "cancelled": True}
        with patch("universal_satellite.download.download_manifest", return_value=result):
            output = self._download_algorithm().processAlgorithm(self._download_parameters(), None, feedback)
        self.assertIn("Cancelled; completed files retained: 1 downloaded, 0 failed", output["SUMMARY"])
        feedback.reportError.assert_not_called()
        feedback.setProgress.assert_not_called()

    def test_download_gui_missing_sdk_gives_install_or_upgrade_message(self):
        with patch("builtins.__import__", side_effect=without_sdk):
            with self.assertRaisesRegex(self.module.QgsProcessingException, "Install or upgrade"):
                self._download_algorithm().processAlgorithm(self._download_parameters(), None, Mock())

    def test_search_does_not_download_unless_requested(self):
        algorithm, client, feedback = self._prepared_search()
        params = {"START": "2024-01-01", "END": "2024-03-31", "OUTPUT": "scenes.geojson"}
        with patch.object(self.module, "_core", return_value=(lambda: client, None)), patch.object(
            self.module, "_atomic_geojson"
        ), patch.object(self.module, "_download_assets") as downloader:
            result = algorithm.processAlgorithm(params, None, feedback)
        self.assertEqual(result, {"OUTPUT": "scenes.geojson"})
        downloader.assert_not_called()

    def test_search_download_uses_saved_manifest_and_operator_folder(self):
        algorithm, client, feedback = self._prepared_search()
        with tempfile.TemporaryDirectory() as directory:
            manifest = str(Path(directory) / "scenes.geojson")
            folder = str(Path(directory) / "images")
            params = {
                "START": "2024-01-01", "END": "2024-03-31", "OUTPUT": manifest,
                "DOWNLOAD": True, "DOWNLOAD_DIR": folder, "DOWNLOAD_ASSETS": "red,nir",
                "SIGN_PLANETARY": False, "OVERWRITE": False,
            }

            def download(path, keys, output, **kwargs):
                self.assertEqual(json.loads(Path(path).read_text()), client.search.return_value)
                self.assertEqual((keys, output), (["red", "nir"], folder))
                return {"downloaded": ["red.tif"], "failed": [], "cancelled": False}

            with patch.object(self.module, "_core", return_value=(lambda: client, None)), patch(
                "universal_satellite.download.download_manifest", side_effect=download
            ):
                result = algorithm.processAlgorithm(params, None, feedback)
        self.assertEqual(result["OUTPUT"], manifest)
        self.assertEqual(result["DOWNLOAD_DIR"], folder)
        self.assertIn("1 downloaded, 0 failed", result["DOWNLOAD_SUMMARY"])

    def test_search_download_requires_folder_before_network_search(self):
        algorithm, client, feedback = self._prepared_search()
        with patch.object(self.module, "_core", return_value=(lambda: client, None)):
            with self.assertRaisesRegex(self.module.QgsProcessingException, "Choose a folder"):
                algorithm.processAlgorithm({"DOWNLOAD": True, "DOWNLOAD_DIR": ""}, None, feedback)
        client.search.assert_not_called()


class ArcgisContractTests(unittest.TestCase):
    def setUp(self):
        self.arcpy = types.ModuleType("arcpy")
        self.arcpy.ExecuteError = type("ExecuteError", (Exception,), {})
        self.modules = patch.dict(sys.modules, {"arcpy": self.arcpy})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.module = load_module(
            "universal_satellite_arcgis_toolbox_test", ROOT / "gis/arcgis/UniversalSatellite.pyt"
        )

    def test_toolbox_registers_search_download_and_index_tools(self):
        self.assertEqual(self.module.Toolbox().tools, [self.module.CropRaster, self.module.EnvironmentalProfile, self.module.SpectralIndex, self.module.SearchScenes, self.module.RasterIndex, self.module.DownloadAssets])

    def test_search_dropdown_exposes_toa_sr_as_separate_dataset_ids(self):
        from universal_satellite.catalog import list_datasets

        def parameter(**kwargs):
            return types.SimpleNamespace(**kwargs, filter=types.SimpleNamespace())

        self.arcpy.Parameter = parameter
        self.arcpy.SpatialReference = lambda code: code
        dataset = self.module.SearchScenes().getParameterInfo()[0]
        sources = [d for d in list_datasets() if d.status == "searchable"]
        self.assertEqual([d.id for d in sources], SEARCHABLE_IDS)
        self.assertEqual(dataset.filter.list, [f"{d.title} [{d.id}]" for d in sources])
        self.assertTrue(any("[sentinel-2-l1c]" in label and "TOA" in label for label in dataset.filter.list))
        self.assertTrue(any("[sentinel-2-l2a]" in label and "surface reflectance" in label for label in dataset.filter.list))
        self.assertIn("name [dataset ID]", dataset.displayName)

    def test_catalog_choices_visible_without_sdk_but_execution_requires_it(self):
        self.arcpy.Parameter = lambda **kwargs: types.SimpleNamespace(**kwargs, filter=types.SimpleNamespace())
        self.arcpy.SpatialReference = lambda code: code
        with patch("builtins.__import__", side_effect=without_sdk):
            algorithm = self.module.SearchScenes()
            sources = self.module._datasets()
            self.assertEqual([d.id for d in sources], SEARCHABLE_IDS)
            choices = algorithm.getParameterInfo()[0].filter.list
            for source in sources:
                self.assertIn(f"{source.title} [{source.id}]", choices)
                self.assertIn(source.start, algorithm.description)
                self.assertIn(source.description, algorithm.description)
            parameters = [Mock()]
            algorithm.updateMessages(parameters)
            parameters[0].setErrorMessage.assert_called_once()
            messages = Mock()
            with self.assertRaises(self.arcpy.ExecuteError):
                algorithm.execute(parameters, messages)
            self.assertIn("Install universal-satellite", messages.addErrorMessage.call_args.args[0])

    def test_all_sources_route_from_friendly_choices_and_legacy_raw_ids(self):
        from universal_satellite.catalog import list_datasets

        sources = [d for d in list_datasets() if d.status == "searchable"]
        package = types.ModuleType("universal_satellite")
        client = Mock()
        client.search.return_value = {"type": "FeatureCollection", "features": []}
        package.Client = Mock(return_value=client)
        algorithm = self.module.SearchScenes()
        messages = Mock()
        with patch.dict(sys.modules, {"universal_satellite": package}), patch.object(
            self.module, "_datasets", return_value=sources
        ), patch.object(self.module, "_extent_value"), patch.object(
            self.module, "_wgs84_bbox", return_value=[90.2, 23.6, 90.5, 23.9]
        ), patch.object(self.module, "_write_manifest"):
            for source in sources:
                label = f"{source.title} [{source.id}]"
                for selection in (label, source.id):
                    with self.subTest(dataset=source.id, selection=selection):
                        values = [selection, "extent", "crs", "2024-01-01", "2024-03-31", "20", "5", "scenes.geojson"]
                        parameters = [types.SimpleNamespace(value=value, valueAsText=value) for value in values]
                        algorithm.execute(parameters, messages)
                        self.assertEqual(client.search.call_args.kwargs["dataset"], source.id)
                legacy = types.SimpleNamespace(value=source.id, valueAsText=source.id)
                algorithm.updateParameters([legacy])
                self.assertEqual(legacy.value, label)
        self.assertEqual(client.search.call_count, 2 * len(SEARCHABLE_IDS))

    def test_sdk_catalog_errors_do_not_silently_fall_back(self):
        import universal_satellite.catalog

        with patch.object(universal_satellite.catalog, "list_datasets", side_effect=RuntimeError("broken SDK catalog")):
            with self.assertRaisesRegex(RuntimeError, "broken SDK catalog"):
                self.module._datasets()

    def test_older_sdk_catalog_retains_all_bundled_choices(self):
        import universal_satellite.catalog

        sources = [d for d in universal_satellite.catalog.list_datasets() if d.status == "searchable"]
        with patch.object(universal_satellite.catalog, "list_datasets", return_value=sources[:10]):
            self.assertEqual([d.id for d in self.module._datasets()], SEARCHABLE_IDS)

    def test_missing_snapshot_uses_installed_sdk_or_reports_incomplete_zip(self):
        with patch.object(self.module.Path, "read_text", side_effect=FileNotFoundError("snapshot absent")):
            self.assertEqual([d.id for d in self.module._datasets()], SEARCHABLE_IDS)
            with patch("builtins.__import__", side_effect=without_sdk):
                with self.assertRaisesRegex(RuntimeError, "complete toolbox ZIP"):
                    self.module._datasets()

    def test_static_search_reports_unfiltered_dates(self):
        package = types.ModuleType("universal_satellite")
        client = Mock()
        client.search.return_value = {
            "type": "FeatureCollection", "features": [],
            "universal_satellite": {
                "temporal_filter_applied": False,
                "temporal_note": "Static inventory: requested dates were not applied."
            }
        }
        package.Client = Mock(return_value=client)
        from universal_satellite.catalog import get_dataset
        dataset = get_dataset("cop-dem-glo-30")
        values = ["cop-dem-glo-30", "extent", "crs", "2024-01-01", "2024-02-01", "20", "5", "scenes.geojson"]
        parameters = [types.SimpleNamespace(value=value, valueAsText=value) for value in values]
        messages = Mock()
        with patch.dict(sys.modules, {"universal_satellite": package}), patch.object(
            self.module, "_datasets", return_value=[dataset]
        ), patch.object(self.module, "_extent_value"), patch.object(
            self.module, "_wgs84_bbox", return_value=[90, 23, 91, 24]
        ), patch.object(self.module, "_write_manifest"):
            self.module.SearchScenes().execute(parameters, messages)
        messages.addMessage.assert_any_call("Static inventory: requested dates were not applied.")
        self.assertIsNone(client.search.call_args.kwargs["cloud"])

    def test_search_failure_becomes_arcpy_error(self):
        client = Mock(side_effect=ValueError("provider unavailable"))
        package = types.ModuleType("universal_satellite")
        package.Client = client
        messages = Mock()
        parameters = [types.SimpleNamespace(valueAsText="missing")]
        with patch.dict(sys.modules, {"universal_satellite": package}), patch.object(
            self.module, "_datasets", return_value=[]
        ):
            with self.assertRaises(self.arcpy.ExecuteError):
                self.module.SearchScenes().execute(parameters, messages)
        messages.addErrorMessage.assert_called_once_with("Unknown searchable dataset: missing")

    def test_projected_extent_densifies_edges_before_projection(self):
        extent = types.SimpleNamespace(XMin=0, YMin=0, XMax=10, YMax=20)
        source_crs = types.SimpleNamespace(name="Projected CRS")
        self.arcpy.Point = lambda x, y: (x, y)
        self.arcpy.Array = lambda points: points
        polygon = Mock()
        polygon.projectAs.return_value.extent = types.SimpleNamespace(XMin=90, YMin=23, XMax=91, YMax=24)
        self.arcpy.Polygon = Mock(return_value=polygon)
        self.arcpy.SpatialReference = lambda code: code
        self.arcpy.ListTransformations = Mock(return_value=["datum transform"])
        self.assertEqual(self.module._wgs84_bbox(extent, source_crs), [90, 23, 91, 24])
        points, actual_crs = self.arcpy.Polygon.call_args.args
        self.assertEqual(actual_crs, source_crs)
        self.assertEqual(len(points), 85)
        self.assertEqual(points[0], points[-1])
        polygon.projectAs.assert_called_once_with(4326, "datum transform")


if __name__ == "__main__":
    unittest.main()
