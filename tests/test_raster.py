"""Numerical and geospatial correctness on small synthetic raster fixtures."""

from importlib.util import find_spec
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from universal_satellite.raster import INDEX_BANDS, compute_index, landsat_toa

RASTER_AVAILABLE = find_spec("numpy") is not None and find_spec("rasterio") is not None


@unittest.skipUnless(RASTER_AVAILABLE, "Install universal-satellite[raster] to run raster tests")
class RasterTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        import rasterio
        from rasterio.transform import from_origin
        self.np = np
        self.rasterio = rasterio
        self.transform = from_origin(90, 24, 0.0001, 0.0001)
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def raster(self, name, data, *, transform=None, crs="EPSG:4326", scale=1, offset=0, count=1):
        path = self.root / f"{name}.tif"
        data = self.np.array(data, dtype="float32")
        with self.rasterio.open(
            path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1], count=count,
            dtype="float32", crs=crs, transform=transform or self.transform, nodata=-9999,
        ) as writer:
            for i in range(1, count+1):
                writer.write(data, i)
            writer.scales = (scale,) * count
            writer.offsets = (offset,) * count
        return path

    def test_ndvi_mask_divide_by_zero_and_grid_preserved(self):
        nir = self.raster("nir", [[0.8, 0], [-9999, 0.6]])
        red = self.raster("red", [[0.2, 0], [0.2, 0.4]])
        output = compute_index("ndvi", self.root / "ndvi.tif", nir=nir, red=red)
        with self.rasterio.open(output) as reader:
            self.assertEqual(reader.crs, self.rasterio.crs.CRS.from_epsg(4326))
            self.assertEqual(reader.transform, self.transform)
            self.assertEqual(reader.dtypes, ("float32",))
            self.np.testing.assert_allclose(reader.read(1), [[0.6, -9999], [-9999, 0.2]], atol=1e-6)
            self.assertEqual(reader.read_masks(1).tolist(), [[255, 0], [0, 255]])

    def test_all_formula_values(self):
        values = {"nir": 0.8, "red": 0.2, "green": 0.4, "swir16": 0.3, "swir22": 0.1, "blue": 0.05}
        expected = {
            "ndvi": 0.6, "ndwi": -1/3, "mndwi": 1/7,
            "ndmi": 5/11, "nbr": 7/9, "evi": 2.5*0.6/(0.8+6*0.2-7.5*0.05+1),
        }
        paths = {key: self.raster(key, [[value]]) for key, value in values.items()}
        for name in expected:
            keys = INDEX_BANDS[name]
            with self.subTest(name=name):
                output = compute_index(name, self.root/f"{name}.tif", **{key: paths[key] for key in keys})
                with self.rasterio.open(output) as reader:
                    self.assertAlmostEqual(float(reader.read(1)[0, 0]), expected[name], places=6)

    def test_scale_and_offset_applied_before_evi(self):
        nir = self.raster("nir", [[10000]], scale=0.0001, offset=-0.2)
        red = self.raster("red", [[4000]], scale=0.0001, offset=-0.2)
        blue = self.raster("blue", [[2500]], scale=0.0001, offset=-0.2)
        output = compute_index("evi", self.root/"evi.tif", nir=nir, red=red, blue=blue)
        with self.rasterio.open(output) as reader:
            self.assertAlmostEqual(float(reader.read(1)[0, 0]), 2.5*0.6/(0.8+1.2-0.375+1), places=6)

    def test_misaligned_bands_rejected_without_output(self):
        from rasterio.transform import from_origin
        nir = self.raster("nir", [[1]])
        red = self.raster("red", [[1]], transform=from_origin(90.1, 24, 0.0001, 0.0001))
        output = self.root/"index.tif"
        with self.assertRaisesRegex(ValueError, "pixel grid"):
            compute_index("ndvi", output, nir=nir, red=red)
        self.assertFalse(output.exists())
        self.assertFalse(list(self.root.glob(".index-*")))

    def test_multiband_input_rejected(self):
        nir = self.raster("nir", [[1]], count=2)
        red = self.raster("red", [[1]])
        with self.assertRaisesRegex(ValueError, "single-band"):
            compute_index("ndvi", self.root/"index.tif", nir=nir, red=red)

    def test_existing_output_and_input_alias_preserved(self):
        nir = self.raster("nir", [[1]])
        red = self.raster("red", [[0]])
        with self.assertRaisesRegex(ValueError, "alias"):
            compute_index("ndvi", nir, nir=nir, red=red)
        output = self.root/"existing.tif"
        output.write_bytes(b"keep me")
        with self.assertRaises(FileExistsError):
            compute_index("ndvi", output, nir=nir, red=red)
        self.assertEqual(output.read_bytes(), b"keep me")

    def test_nonfinite_input_becomes_nodata(self):
        nir = self.raster("nir", [[float("nan"), float("inf")]])
        red = self.raster("red", [[0.2, 0.2]])
        output = compute_index("ndvi", self.root/"index.tif", nir=nir, red=red)
        with self.rasterio.open(output) as reader:
            self.assertEqual(reader.read(1).tolist(), [[-9999, -9999]])


class RasterArgumentTests(unittest.TestCase):
    def test_unknown_index_and_missing_bands(self):
        with self.assertRaisesRegex(ValueError, "Unknown index"):
            compute_index("wrong", "out.tif")
        with self.assertRaisesRegex(ValueError, "requires exactly"):
            compute_index("evi", "out.tif", nir="nir.tif", red="red.tif")


@unittest.skipUnless(RASTER_AVAILABLE, "Install universal-satellite[raster] to run raster tests")
class LandsatToaTests(unittest.TestCase):
    setUp = RasterTests.setUp
    raster = RasterTests.raster

    def mtl(self, *, spacecraft="LANDSAT_8", sensor=None, solar=30, band=4, multiplier=0.00002, addition=-0.1):
        attributes = {"SPACECRAFT_ID": spacecraft, "SUN_ELEVATION": solar}
        if sensor is not None:
            attributes["SENSOR_ID"] = sensor
        self.metadata = {"LANDSAT_METADATA_FILE": {
            "IMAGE_ATTRIBUTES": attributes,
            "LEVEL1_RADIOMETRIC_RESCALING": {
                f"REFLECTANCE_MULT_BAND_{band}": multiplier,
                f"REFLECTANCE_ADD_BAND_{band}": addition,
            },
        }}
        path = self.root / "product_MTL.json"
        path.write_text(json.dumps(self.metadata))
        return path

    def test_conversion_uses_coefficients_solar_angle_fill_and_mask(self):
        raw = self.raster("raw", [[20000, 0], [10000, -9999]])
        original = raw.read_bytes()
        mtl = self.mtl()
        output = landsat_toa(raw, mtl, 4, self.root/"toa.tif")
        with self.rasterio.open(output) as result:
            self.np.testing.assert_allclose(result.read(1), [[0.6, -9999], [0.2, -9999]], atol=1e-6)
            self.assertEqual(result.read_masks(1).tolist(), [[255, 0], [255, 0]])
            self.assertEqual(result.crs, self.rasterio.crs.CRS.from_epsg(4326))
            self.assertEqual(result.transform, self.transform)
            self.assertEqual(result.dtypes, ("float32",))
            self.assertEqual(result.tags()["processing_level"], "TOA reflectance")
            self.assertEqual(result.tags()["source_metadata"], mtl.name)
        self.assertEqual(raw.read_bytes(), original)
        self.assertFalse(list(self.root.glob(".toa-*")))

    def test_thermal_bands_and_mss_rejected(self):
        raw = self.raster("raw", [[10000]])
        for spacecraft, band in [("LANDSAT_4", 6), ("LANDSAT_5", 6), ("LANDSAT_7", 6), ("LANDSAT_8", 10), ("LANDSAT_9", 11)]:
            with self.subTest(spacecraft=spacecraft, band=band):
                with self.assertRaisesRegex(ValueError, "thermal"):
                    landsat_toa(raw, self.mtl(spacecraft=spacecraft), band, self.root/"toa.tif")
        with self.assertRaisesRegex(ValueError, "MSS"):
            landsat_toa(raw, self.mtl(spacecraft="LANDSAT_1"), 4, self.root/"toa.tif")
        with self.assertRaisesRegex(ValueError, "MSS"):
            landsat_toa(raw, self.mtl(spacecraft="LANDSAT_5", sensor="MSS"), 4, self.root/"toa.tif")

    def test_all_supported_missions_use_explicit_reflectance_coefficients(self):
        raw = self.raster("raw", [[10000]])
        for spacecraft, band in [("LANDSAT_4", 7), ("LANDSAT_5", 1), ("LANDSAT_7", 8), ("LANDSAT_8", 9), ("LANDSAT_9", 4)]:
            with self.subTest(spacecraft=spacecraft, band=band):
                output = landsat_toa(raw, self.mtl(spacecraft=spacecraft, band=band, solar=90), band, self.root/f"{spacecraft}.tif")
                with self.rasterio.open(output) as result:
                    self.assertAlmostEqual(float(result.read(1)[0, 0]), 0.1, places=6)

    def test_invalid_solar_angles_and_coefficients_rejected(self):
        raw = self.raster("raw", [[10000]])
        for solar in [0, -1, 91, "NaN", "Infinity"]:
            with self.subTest(solar=solar):
                with self.assertRaisesRegex(ValueError, "SUN_ELEVATION"):
                    landsat_toa(raw, self.mtl(solar=solar), 4, self.root/"toa.tif")
        for multiplier, addition in [(0, 0), (-1, 0), ("NaN", 0), (1, "Infinity")]:
            with self.subTest(multiplier=multiplier, addition=addition):
                with self.assertRaisesRegex(ValueError, "coefficients"):
                    landsat_toa(raw, self.mtl(multiplier=multiplier, addition=addition), 4, self.root/"toa.tif")
        self.assertFalse((self.root/"toa.tif").exists())

    def test_nonidentity_scale_and_offset_rejected(self):
        for name, scale, offset in [("scale", 0.001, 0), ("offset", 1, -0.2)]:
            with self.subTest(name=name):
                raw = self.raster(name, [[10000]], scale=scale, offset=offset)
                with self.assertRaisesRegex(ValueError, "double calibration"):
                    landsat_toa(raw, self.mtl(), 4, self.root/"toa.tif")

    def test_input_alias_and_existing_output_preserved(self):
        raw = self.raster("raw", [[10000]])
        with self.assertRaisesRegex(ValueError, "alias"):
            landsat_toa(raw, self.mtl(), 4, raw)
        output = self.root/"existing.tif"
        output.write_bytes(b"keep me")
        with self.assertRaises(FileExistsError):
            landsat_toa(raw, self.mtl(), 4, output)
        self.assertEqual(output.read_bytes(), b"keep me")

    def test_missing_coefficients_not_guessed(self):
        raw = self.raster("raw", [[10000]])
        with self.assertRaisesRegex(ValueError, "REFLECTANCE_MULT_BAND_5"):
            landsat_toa(raw, self.mtl(band=4), 5, self.root/"toa.tif")

    def test_multiband_or_unreferenced_input_rejected(self):
        for name, options in [("multi", {"count": 2}), ("no_crs", {"crs": None})]:
            with self.subTest(name=name):
                raw = self.raster(name, [[10000]], **options)
                with self.assertRaises(ValueError):
                    landsat_toa(raw, self.mtl(), 4, self.root/"toa.tif")

    def test_window_edges_and_partial_final_blocks(self):
        data = self.np.full((513, 515), 10000, dtype="float32")
        data[512, 514] = 0
        raw = self.raster("raw", data)
        output = landsat_toa(raw, self.mtl(), 4, self.root/"toa.tif")
        with self.rasterio.open(output) as result:
            values = result.read(1)
            self.assertEqual(values.shape, (513, 515))
            self.assertAlmostEqual(float(values[511, 511]), 0.2, places=6)
            self.assertAlmostEqual(float(values[512, 513]), 0.2, places=6)
            self.assertEqual(values[512, 514], -9999)


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(RASTER_AVAILABLE, 'Raster dependencies required')
class CropTests(unittest.TestCase):
    setUp = RasterTests.setUp
    raster = RasterTests.raster
    def test_crop_masks_preserves_grid_and_respects_budget(self):
        from universal_satellite.raster import crop_raster
        source=self.raster('input',[[1,2],[3,4]],scale=0.1)
        boundary=self.root/'aoi.geojson'
        boundary.write_text(json.dumps({'type':'Polygon','coordinates':[[[90,24],[90.0000999,24],[90.0000999,23.9998],[90,23.9998],[90,24]]]}))
        output=crop_raster(source,boundary,self.root/'crop.tif')
        with self.rasterio.open(output) as reader:
            self.assertEqual(reader.width,1)
            self.assertEqual(reader.height,2)
            self.assertEqual(reader.scales,(0.1,))
            self.np.testing.assert_allclose(reader.read(1),[[1],[3]])
        with self.assertRaises(ValueError):crop_raster(source,boundary,self.root/'too-big.tif',max_pixels=1)
        with self.assertRaises(FileExistsError):crop_raster(source,boundary,output)
