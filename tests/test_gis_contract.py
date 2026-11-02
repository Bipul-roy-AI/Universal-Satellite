"""Adapter contract checks with test doubles, not native GIS integration tests."""

import importlib.machinery
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


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
    core.QgsProcessingAlgorithm = type("QgsProcessingAlgorithm", (), {})
    core.QgsProcessingException = type("QgsProcessingException", (Exception,), {})
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
        "QgsProcessingParameterString"
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
        dataset_parameter = next(
            call.args[0] for call in algorithm.addParameter.call_args_list
            if call.args[0].name == "DATASET"
        )
        options = dataset_parameter.kwargs["options"]
        toa = next(label for label in options if "[sentinel-2-l1c]" in label)
        sr = next(label for label in options if "[sentinel-2-l2a]" in label)
        self.assertIn("TOA", toa.upper())
        self.assertTrue("SURFACE REFLECTANCE" in sr.upper() or "SR" in sr.upper())
        self.assertNotEqual(toa, sr)

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

    def test_toolbox_registers_both_tools(self):
        self.assertEqual(self.module.Toolbox().tools, [self.module.SearchScenes, self.module.RasterIndex])

    def test_search_dropdown_exposes_toa_sr_as_separate_dataset_ids(self):
        from universal_satellite.catalog import list_datasets

        def parameter(**kwargs):
            return types.SimpleNamespace(**kwargs, filter=types.SimpleNamespace())

        self.arcpy.Parameter = parameter
        self.arcpy.SpatialReference = lambda code: code
        dataset = self.module.SearchScenes().getParameterInfo()[0]
        expected = [d.id for d in list_datasets() if d.status == "searchable"]
        self.assertEqual(dataset.filter.list, expected)
        self.assertIn("sentinel-2-l1c", dataset.filter.list)
        self.assertIn("sentinel-2-l2a", dataset.filter.list)
        self.assertIn("sentinel-2-l1c = TOA", dataset.displayName)
        self.assertIn("sentinel-2-l2a = SR", dataset.displayName)

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
        dataset = types.SimpleNamespace(id="cop-dem-glo-30", category="elevation")
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
