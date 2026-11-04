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


from .indices import INDEX_BANDS, evaluate, definition, parameters, normalize



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


def compute_index(name: str, output: str | Path, *, constants=None, **bands: str | Path) -> Path:
    """Write a float32 GeoTIFF index, preserving CRS, grid, and input masks.

    Only aligned single-band files are accepted; this function does not resample
    different-resolution bands or perform atmospheric/cloud correction. Invalid
    inputs, zero denominators, and non-finite results receive nodata (-9999).
    Existing output files and input aliases are never overwritten.
    """
    name = normalize(name)
    if name not in INDEX_BANDS:
        raise ValueError(f"Unknown index {name!r}. Choose: {', '.join(INDEX_BANDS)}.")
    required = set(INDEX_BANDS[name])
    if set(bands) != required:
        raise ValueError(f"{name.upper()} requires exactly these bands: {', '.join(INDEX_BANDS[name])}.")
    parameters(name, constants)
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
                            result = evaluate(name, values, constants=constants)
                        valid &= np.isfinite(result)
                        # Float64 results must also fit the float32 output type.
                        valid &= np.abs(result) <= np.finfo("float32").max
                        writer.write(np.where(valid, result, -9999.0).astype("float32"), 1, window=window)
                writer.set_band_description(1, definition(name)["short_name"])
                writer.update_tags(index=name, formula=definition(name)["formula"], reference=definition(name)["reference"], parameters=json.dumps(parameters(name, constants)), input_scaling="raster scale and offset", cloud_mask="caller supplied")
        os.link(temporary, destination)
        temporary.unlink()
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def crop_raster(source, boundary, output, *, max_pixels=25000000):
    """Crop/mask a local raster or remote COG with GeoJSON/Shapefile polygons.

    Rasterio/GDAL uses HTTP range reads when the provider supports them. A pixel
    budget prevents accidental whole-scene memory allocation. GeoJSON is WGS84;
    Shapefiles must declare a CRS. No reprojection of the source pixel grid.
    """
    import numpy as np
    import rasterio
    from rasterio.mask import mask, raster_geometry_mask
    from rasterio.warp import transform_geom
    from urllib.parse import urlsplit
    if isinstance(max_pixels,bool) or not isinstance(max_pixels,int) or max_pixels<=0:
        raise ValueError('max_pixels must be a positive integer')
    destination=Path(output).expanduser()
    if destination.exists() or destination.is_symlink():raise FileExistsError(str(destination))
    if urlsplit(str(source)).scheme not in ('','https'):
        # Windows drive letters are local paths, not URL protocols.
        if not (len(str(source))>2 and str(source)[1:3] in (':\\',':/')):
            raise ValueError('Crop source must be a local raster or HTTPS COG')
    boundary=Path(boundary)
    if boundary.suffix.lower()=='.shp':
        try: import fiona
        except ImportError: raise RuntimeError('Shapefile clipping requires the vector extra (Fiona)') from None
        with fiona.open(boundary) as collection:
            vector_crs=collection.crs_wkt or collection.crs
            if not vector_crs: raise ValueError('Shapefile must declare a CRS')
            geometries=[dict(f['geometry']) for f in collection if f['geometry']]
    else:
        data=json.loads(boundary.read_text(encoding='utf-8'))
        if data.get('crs'):raise ValueError('Use RFC 7946 WGS84 GeoJSON without a legacy crs member')
        vector_crs='EPSG:4326'
        geometries=[f.get('geometry') for f in data['features']] if data.get('type')=='FeatureCollection' else [data.get('geometry') if data.get('type')=='Feature' else data]
    if not geometries or any(not isinstance(g,dict) or g.get('type') not in ('Polygon','MultiPolygon') for g in geometries):
        raise ValueError('Boundary must contain Polygon or MultiPolygon geometries')
    temporary=None
    try:
        with rasterio.open(source) as reader:
            if not reader.crs:raise ValueError('Source raster must declare a CRS')
            shapes=[transform_geom(vector_crs,reader.crs,g) for g in geometries]
            # geometry_window checks overlap without allocating a mask.
            from rasterio.features import geometry_window
            window=geometry_window(reader,shapes)
            if window.width*window.height*reader.count>max_pixels:
                raise ValueError('Crop exceeds max_pixels; reduce the AOI or explicitly increase the budget')
            values, transform=mask(reader,shapes,crop=True,filled=False)
            destination.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=destination.parent,prefix='.crop-',suffix='.tif',delete=False) as handle:
                temporary=Path(handle.name)
            profile={'driver':'GTiff','height':values.shape[1],'width':values.shape[2],'count':reader.count,'dtype':'float32',
                'crs':reader.crs,'transform':transform,'nodata':float('nan'),'compress':'deflate','tiled':True}
            with rasterio.open(temporary,'w',**profile) as writer:
                writer.write(values.astype('float32').filled(np.nan))
                writer.scales=reader.scales;writer.offsets=reader.offsets
                writer.update_tags(processing='polygon crop and mask; source grid and scale/offset retained')
        os.link(temporary,destination)
        return destination
    finally:
        if temporary:temporary.unlink(missing_ok=True)
