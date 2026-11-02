"""Windowed reflectance indices on aligned, single-band raster grids.

Band values are transformed with their raster scale and offset metadata before
calculation. If a product stores scaling only in separate STAC metadata, prepare
reflectance rasters first; the product's numeric encoding cannot be inferred.
Cloud/shadow masking must be applied by the caller before calculation.
"""

from __future__ import annotations

from contextlib import ExitStack
import json
import math
import os
from pathlib import Path
import tempfile


INDEX_BANDS = {
    "ndvi": ("nir", "red"),
    "ndwi": ("green", "nir"),
    "mndwi": ("green", "swir16"),
    "ndmi": ("nir", "swir16"),
    "nbr": ("nir", "swir22"),
    "evi": ("nir", "red", "blue"),
}


def landsat_toa(
    input_path: str | Path, mtl_path: str | Path, band: int, output: str | Path
) -> Path:
    """Convert one Landsat Collection 2 Level-1 DN band to TOA reflectance.

    Coefficients and scene-center sun elevation must come from the matching
    product's MTL JSON. Uses ``(M * DN + A) / sin(sun_elevation)``. This is
    solar-angle-corrected top-of-atmosphere reflectance, not surface reflectance,
    atmospheric correction, cloud masking, or per-pixel solar-angle correction.
    DN zero is Landsat Level-1 fill and is always masked. Landsat MSS and thermal
    bands are unsupported. Existing outputs and input aliases are preserved.
    """
    if isinstance(band, bool) or not isinstance(band, int):
        raise ValueError("Landsat band must be an integer band number.")
    source = Path(input_path).expanduser()
    metadata_path = Path(mtl_path).expanduser()
    destination = Path(output).expanduser()
    if destination.resolve() == source.resolve():
        raise ValueError("Output must not be an input raster or an alias of the input raster.")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Output already exists: {destination}")
    try:
        with metadata_path.open(encoding="utf-8") as handle:
            document = json.load(handle)
        metadata = document["LANDSAT_METADATA_FILE"]
        attributes = metadata["IMAGE_ATTRIBUTES"]
        calibration = metadata["LEVEL1_RADIOMETRIC_RESCALING"]
        spacecraft = attributes["SPACECRAFT_ID"]
        solar = float(attributes["SUN_ELEVATION"])
    except (KeyError, TypeError, ValueError, UnicodeError) as error:
        raise ValueError(
            "Use matching Landsat Level-1 MTL JSON containing IMAGE_ATTRIBUTES "
            "SPACECRAFT_ID/SUN_ELEVATION and LEVEL1_RADIOMETRIC_RESCALING "
            f"REFLECTANCE_MULT_BAND_{band}/REFLECTANCE_ADD_BAND_{band}."
        ) from error
    reflective_bands = {
        "LANDSAT_4": {1, 2, 3, 4, 5, 7},
        "LANDSAT_5": {1, 2, 3, 4, 5, 7},
        "LANDSAT_7": {1, 2, 3, 4, 5, 7, 8},
        "LANDSAT_8": set(range(1, 10)),
        "LANDSAT_9": set(range(1, 10)),
    }
    if not isinstance(spacecraft, str) or spacecraft not in reflective_bands:
        raise ValueError("TOA conversion supports reflective bands of Landsat 4, 5, 7, 8 and 9; MSS is unsupported.")
    if "MSS" in str(attributes.get("SENSOR_ID", "")).upper():
        raise ValueError("Landsat MSS TOA conversion is unsupported; use a mission-specific calibration workflow.")
    if band not in reflective_bands[spacecraft]:
        raise ValueError(f"Band {band} is not a supported reflective band for {spacecraft}; thermal bands are unsupported.")
    if not math.isfinite(solar) or not 0 < solar <= 90:
        raise ValueError("SUN_ELEVATION must be finite and greater than 0 through 90 degrees.")
    try:
        multiplier = float(calibration[f"REFLECTANCE_MULT_BAND_{band}"])
        addition = float(calibration[f"REFLECTANCE_ADD_BAND_{band}"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"MTL JSON must contain REFLECTANCE_MULT_BAND_{band} and REFLECTANCE_ADD_BAND_{band} coefficients.") from error
    if not math.isfinite(multiplier) or multiplier <= 0 or not math.isfinite(addition):
        raise ValueError("Reflectance coefficients must be finite and REFLECTANCE_MULT must be positive.")
    solar_correction = math.sin(math.radians(solar))
    try:
        import numpy as np
        import rasterio
        from rasterio.windows import Window
    except ImportError:
        raise RuntimeError(
            'Raster analysis requires optional dependencies: pip install "universal-satellite[raster]".'
        ) from None
    temporary: Path | None = None
    try:
        with rasterio.open(source) as reader:
            if reader.count != 1:
                raise ValueError("TOA input must be a single-band Level-1 DN raster.")
            if reader.crs is None:
                raise ValueError("TOA input raster must declare a CRS.")
            if reader.scales[0] != 1 or reader.offsets[0] != 0:
                raise ValueError("TOA input must contain raw DN with identity scale/offset; refusing double calibration.")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=destination.parent, prefix=".toa-", suffix=".tif", delete=False
            ) as handle:
                temporary = Path(handle.name)
            profile = {
                "driver": "GTiff", "height": reader.height, "width": reader.width,
                "count": 1, "dtype": "float32", "crs": reader.crs,
                "transform": reader.transform, "nodata": -9999.0,
                "compress": "deflate", "tiled": True, "BIGTIFF": "IF_SAFER",
            }
            with rasterio.open(temporary, "w", **profile) as writer:
                for row in range(0, reader.height, 512):
                    for col in range(0, reader.width, 512):
                        window = Window(col, row, min(512, reader.width-col), min(512, reader.height-row))
                        raw = reader.read(1, window=window, masked=True).astype("float64")
                        valid = ~np.ma.getmaskarray(raw) & np.isfinite(raw.data) & (raw.data != 0)
                        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                            reflectance = (multiplier * raw.data + addition) / solar_correction
                        valid &= np.isfinite(reflectance) & (np.abs(reflectance) <= np.finfo("float32").max)
                        writer.write(np.where(valid, reflectance, -9999.0).astype("float32"), 1, window=window)
                writer.set_band_description(1, f"Landsat band {band} TOA reflectance")
                writer.update_tags(
                    processing_level="TOA reflectance", spacecraft=spacecraft,
                    source_metadata=metadata_path.name, band_number=band,
                    sun_elevation=solar, reflectance_mult=multiplier,
                    reflectance_add=addition, solar_correction="scene-center elevation",
                    cloud_mask="not applied; input mask preserved",
                )
        os.link(temporary, destination)
        temporary.unlink()
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def compute_index(name: str, output: str | Path, **bands: str | Path) -> Path:
    """Write a float32 GeoTIFF index, preserving CRS, grid, and input masks.

    Only aligned single-band files are accepted; this function does not resample
    different-resolution bands or perform atmospheric/cloud correction. Invalid
    inputs, zero denominators, and non-finite results receive nodata (-9999).
    Existing output files and input aliases are never overwritten.
    """
    name = name.lower()
    if name not in INDEX_BANDS:
        raise ValueError(f"Unknown index {name!r}. Choose: {', '.join(INDEX_BANDS)}.")
    required = set(INDEX_BANDS[name])
    if set(bands) != required:
        raise ValueError(f"{name.upper()} requires exactly these bands: {', '.join(INDEX_BANDS[name])}.")
    destination = Path(output).expanduser()
    sources = {key: Path(path).expanduser() for key, path in bands.items()}
    if any(destination.resolve() == path.resolve() for path in sources.values()):
        raise ValueError("Output must not be an input raster or an alias of an input raster.")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Output already exists: {destination}")
    try:
        import numpy as np
        import rasterio
    except ImportError:
        raise RuntimeError(
            'Raster analysis requires optional dependencies: pip install "universal-satellite[raster]".'
        ) from None

    temporary: Path | None = None
    try:
        with ExitStack() as stack:
            readers = {key: stack.enter_context(rasterio.open(path)) for key, path in sources.items()}
            reference = next(iter(readers.values()))
            if reference.crs is None:
                raise ValueError("Input rasters must declare a CRS.")
            for key, reader in readers.items():
                if reader.count != 1:
                    raise ValueError(f"Band {key!r} must be a single-band raster.")
                if (
                    reader.width != reference.width
                    or reader.height != reference.height
                    or reader.crs != reference.crs
                    or reader.transform != reference.transform
                ):
                    raise ValueError("Input rasters must share dimensions, CRS, and pixel grid; align them first.")
                if not np.isfinite(reader.scales[0]) or not np.isfinite(reader.offsets[0]):
                    raise ValueError(f"Band {key!r} has invalid scale/offset metadata.")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=destination.parent, prefix=".index-", suffix=".tif", delete=False
            ) as handle:
                temporary = Path(handle.name)
            # Construct a clean profile rather than inheriting encoding or color
            # options (e.g. JPEG compression or RGB photometric interpretation).
            profile = {
                "driver": "GTiff", "height": reference.height, "width": reference.width,
                "count": 1, "dtype": "float32", "crs": reference.crs,
                "transform": reference.transform, "nodata": -9999.0,
                "compress": "deflate", "tiled": True, "BIGTIFF": "IF_SAFER",
            }
            with rasterio.open(temporary, "w", **profile) as writer:
                # Fixed windows bound memory even for striped or untiled inputs.
                from rasterio.windows import Window
                for row in range(0, reference.height, 512):
                    for col in range(0, reference.width, 512):
                        window = Window(col, row, min(512, reference.width-col), min(512, reference.height-row))
                        values = {}
                        valid = None
                        for key, reader in readers.items():
                            raw = reader.read(1, window=window, masked=True).astype("float64")
                            value = raw.data * reader.scales[0] + reader.offsets[0]
                            good = ~np.ma.getmaskarray(raw) & np.isfinite(value)
                            valid = good if valid is None else valid & good
                            values[key] = value
                        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                            if name == "evi":
                                numerator = 2.5 * (values["nir"] - values["red"])
                                denominator = values["nir"] + 6 * values["red"] - 7.5 * values["blue"] + 1
                            else:
                                first, second = INDEX_BANDS[name]
                                numerator = values[first] - values[second]
                                denominator = values[first] + values[second]
                            result = numerator / denominator
                        valid &= (denominator != 0) & np.isfinite(result)
                        # Float64 results must also fit the float32 output type.
                        valid &= np.abs(result) <= np.finfo("float32").max
                        writer.write(np.where(valid, result, -9999.0).astype("float32"), 1, window=window)
                writer.set_band_description(1, name.upper())
                writer.update_tags(index=name, input_scaling="raster scale and offset", cloud_mask="caller supplied")
        os.link(temporary, destination)
        temporary.unlink()
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
