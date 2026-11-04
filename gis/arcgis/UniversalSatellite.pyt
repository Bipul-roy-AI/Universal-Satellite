"""ArcGIS Pro Python toolbox; requires the separately installed core package."""

import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import arcpy


def _datasets():
    """Use the live SDK catalog, or display bundled choices before installation."""
    try:
        from universal_satellite.catalog import list_datasets
    except ImportError:
        sources = []
    else:
        sources = [item for item in list_datasets() if item.status == "searchable"]
    try:
        snapshot = json.loads(Path(__file__).with_name("datasets.json").read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        if sources:
            return sources
        raise RuntimeError(
            "Install the universal-satellite core SDK or reinstall the complete toolbox ZIP including datasets.json."
        ) from exc
    if snapshot.get("schema_version") != 1:
        raise ValueError("Unsupported bundled source catalog; reinstall the complete toolbox package.")
    known = {source.id for source in sources}
    sources.extend(SimpleNamespace(**item) for item in snapshot["datasets"] if item["status"] == "searchable" and item["id"] not in known)
    return sources


def _dataset_label(source):
    return f"{source.title} [{source.id}]"


def _resolve_dataset(value, choices):
    for source in choices:
        if value in (source.id, _dataset_label(source)):
            return source
    raise ValueError(f"Unknown searchable dataset: {value}")



def _asset_help(dataset_id=None):
    """Offline operator guide, independent of the installed SDK version."""
    path = Path(__file__).with_name("asset_guide.json")
    if not path.is_file():
        return "\nAsset guide missing: reinstall the complete toolbox ZIP; see README Asset keys."
    guide = json.loads(path.read_text(encoding="utf-8"))
    lines = ["Asset keys: what to enter", guide["intro"]]
    for identifier, record in guide["datasets"].items():
        if dataset_id and identifier != dataset_id:
            continue
        lines.extend([record["title"] + " [" + identifier + "]", record["note"], "Access: " + record["access"]])
        lines.extend(key + " = " + meaning for key, meaning in record["keys"].items())
    return "\n\n" + "\n\n".join(lines)


def _manifest_asset_help(manifest):
    """Describe actual advertised keys without exposing signed URLs."""
    try:
        data = json.loads(Path(manifest).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "Asset preview unavailable; the downloader will validate the manifest."
    lines = ["Available assets in this manifest (keys are case-sensitive):"]
    seen = set()
    for item in data.get("features", []):
        for key, asset in item.get("assets", {}).items():
            if not isinstance(asset, dict):
                continue
            description = str(asset.get("title") or "Provider asset")
            entry = (key, description, str(asset.get("type", "unspecified media type")))
            if entry not in seen:
                lines.append(" = ".join(entry))
                seen.add(entry)
    if not seen:
        lines.append("No downloadable assets; point observations may already be stored in the GeoJSON.")
    return "\n".join(lines)


def _source_help():
    lines = []
    for source in _datasets():
        end = source.end or "ongoing (provider coverage varies)"
        static = " Static inventory: requested dates are not filtered." if not source.temporal else ""
        lines.append(f"{_dataset_label(source)} — source era {source.start} to {end}.{static} {source.description}")
    return "\n\nAvailable searchable sources (source eras are not guaranteed catalog coverage):\n" + "\n\n".join(lines)


def _parameter(name, label, datatype, direction="Input", required=True):
    return arcpy.Parameter(
        name=name, displayName=label, datatype=datatype, direction=direction,
        parameterType="Required" if required else "Optional"
    )


def _boolean(parameters, index):
    return len(parameters) > index and str(parameters[index].valueAsText).lower() in {"true", "1"}


def _download(manifest, assets, directory, signing, overwrite, messages, **options):
    try:
        from universal_satellite.download import download_manifest
    except ImportError as exc:
        raise RuntimeError("Install or upgrade universal-satellite in ArcGIS Pro's Python environment to use image downloads.") from exc
    if not directory:
        raise ValueError("Choose an image output folder.")
    keys = [key.strip() for key in (assets or "").split(",") if key.strip()]
    messages.addMessage(_manifest_asset_help(manifest))
    environment = getattr(arcpy, "env", None)
    auto_cancel = getattr(environment, "autoCancelling", None)
    if auto_cancel is not None:
        environment.autoCancelling = False

    def progress(percent, message):
        arcpy.SetProgressorPosition(int(percent))
        arcpy.SetProgressorLabel(message)
        messages.addMessage(message)

    try:
        arcpy.SetProgressor("step", "Downloading satellite image assets", 0, 100, 1)
        result = download_manifest(
            manifest, keys, directory, sign_planetary=signing, overwrite=overwrite,
            progress=progress, cancelled=lambda: bool(getattr(environment, "isCancelled", False)), **options,
        )
    finally:
        arcpy.ResetProgressor()
        if auto_cancel is not None:
            environment.autoCancelling = auto_cancel
    for failure in result["failed"]:
        messages.addWarningMessage(f"{failure['scene']} / {failure['asset']}: {failure['error']}")
    messages.addMessage(f"Downloaded {len(result['downloaded'])} image asset(s) to {directory}; {len(result['failed'])} failed.")
    if result["cancelled"]:
        messages.addWarningMessage("Download cancelled. Completed files were retained; resumable partial files may remain.")
    elif result["failed"] and not result["downloaded"]:
        raise RuntimeError("No image assets were downloaded. See the provider/access errors above.")
    return result


def _write_manifest(result, path):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".tmp", dir=target.parent, delete=False
        ) as stream:
            temporary = stream.name
            json.dump(result, stream, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, target)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def _wgs84_bbox(extent, source_crs):
    """Densify the rectangle edges before projecting its enclosing envelope."""
    if not source_crs or source_crs.name == "Unknown":
        raise ValueError("Choose the coordinate system of the input extent.")
    west, south, east, north = extent.XMin, extent.YMin, extent.XMax, extent.YMax
    if west >= east or south >= north:
        raise ValueError("Choose a non-empty, non-wrapping input extent.")
    points = []
    for x1, y1, x2, y2 in (
        (west, south, east, south), (east, south, east, north),
        (east, north, west, north), (west, north, west, south)
    ):
        for step in range(21):
            ratio = step / 20
            points.append(arcpy.Point(x1 + (x2 - x1) * ratio, y1 + (y2 - y1) * ratio))
    points.append(points[0])
    polygon = arcpy.Polygon(arcpy.Array(points), source_crs)
    target = arcpy.SpatialReference(4326)
    transformations = arcpy.ListTransformations(source_crs, target)
    if transformations:
        projected = polygon.projectAs(target, transformations[0])
    else:
        projected = polygon.projectAs(target)
    bounds = projected.extent
    return [bounds.XMin, bounds.YMin, bounds.XMax, bounds.YMax]


def _extent_value(parameter):
    value = parameter.value
    if all(hasattr(value, name) for name in ("XMin", "YMin", "XMax", "YMax")):
        return value
    # ArcGIS versions may expose a GPExtent as GP text rather than an Extent.
    values = parameter.valueAsText.split()
    if len(values) < 4:
        raise ValueError("Choose a valid input extent.")
    return arcpy.Extent(*(float(value) for value in values[:4]))


class Toolbox:
    def __init__(self):
        self.label = "Universal Satellite"
        self.alias = "universal_satellite"
        self.tools = [CropRaster, EnvironmentalProfile, SpectralIndex, SearchScenes, RasterIndex, DownloadAssets]


class SearchScenes:
    def __init__(self):
        self.label = "Search satellite scenes (GeoJSON manifest)"
        self.description = (
            "Search a STAC archive by extent and ISO dates. Choose separate "
            "Sentinel-2 Level-1C top-of-atmosphere (TOA) and Level-2A "
            "surface reflectance (SR) choices; this tool does not convert TOA to SR. "
            "Landsat Level-1 delivers DN requiring calibration; Landsat US ARD TOA "
            "has regional U.S. coverage. Other sources have their own measurements. "
            "The output contains scene footprints and asset links, not imagery. Split areas crossing "
            "the antimeridian. Specify the input extent's coordinate system. "
            "Static Copernicus DEM, NASADEM and JRC Global Surface Water inventories "
            "ignore requested dates and label that behavior in manifest metadata. "
            "The bundled catalog is visible before the core SDK is installed; "
            "install the SDK before running a search. Enable Download images after "
            "search and choose an output folder to retrieve selected image assets "
            "in the same geoprocessing job, or use Download satellite image assets "
            "with a saved manifest. Downloads respect provider authentication and "
            "do not bypass requester-pays S3 requirements."
        ) + _source_help() + _asset_help()
        self.canRunInBackground = False

    def getParameterInfo(self):
        dataset = _parameter("dataset", "Data source (name [dataset ID])", "GPString")
        dataset.filter.type = "ValueList"
        choices = _datasets()
        dataset.filter.list = [_dataset_label(item) for item in choices]
        default = next((item for item in choices if item.id == "sentinel-2-l2a"), None)
        if default is not None:
            dataset.value = _dataset_label(default)
        extent = _parameter("extent", "Area of interest", "GPExtent")
        crs = _parameter("extent_crs", "Coordinate system of input extent", "GPSpatialReference")
        crs.value = arcpy.SpatialReference(4326)
        start = _parameter("start", "Start date (YYYY-MM-DD)", "GPString")
        end = _parameter("end", "End date (YYYY-MM-DD)", "GPString")
        cloud = _parameter("cloud", "Maximum scene cloud cover (%) — optical only", "GPDouble")
        cloud.value = 100
        cloud.filter.type = "Range"
        cloud.filter.list = [0, 100]
        limit = _parameter("limit", "Maximum number of scenes", "GPLong")
        limit.value = 10
        limit.filter.type = "Range"
        limit.filter.list = [1, 1000]
        output = _parameter("output", "Output scene manifest (.geojson)", "DEFile", direction="Output")
        output.filter.list = ["geojson"]
        download = _parameter("download_images", "Download images after search", "GPBoolean", required=False)
        download.value = False
        assets = _parameter("download_assets", "Asset keys (see tool Help for meanings; * = all; DEM: data)", "GPString", required=False)
        assets.value = "red,nir"
        folder = _parameter("download_folder", "Image output folder", "DEFolder", required=False)
        signing = _parameter("sign_planetary", "Sign Planetary Computer Azure asset URLs", "GPBoolean", required=False)
        signing.value = False
        overwrite = _parameter("overwrite_images", "Overwrite existing downloaded files", "GPBoolean", required=False)
        overwrite.value = False
        for parameter in (assets, folder, signing, overwrite):
            parameter.enabled = False
        return [dataset, extent, crs, start, end, cloud, limit, output, download, assets, folder, signing, overwrite]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # Normalize legacy raw-ID inputs before native ValueList validation.
        selected = parameters[0].valueAsText
        for source in _datasets():
            if selected == source.id:
                parameters[0].value = _dataset_label(source)
                break
        if len(parameters) > 8:
            for parameter in parameters[9:13]:
                parameter.enabled = _boolean(parameters, 8)

    def updateMessages(self, parameters):
        try:
            from universal_satellite import Client
        except ImportError:
            parameters[0].setErrorMessage(
                "Install universal-satellite in this ArcGIS Pro Python environment; see docs/gis.md."
            )
        if _boolean(parameters, 8):
            if not parameters[10].valueAsText:
                parameters[10].setErrorMessage("Choose an image output folder when downloading images.")
            try:
                from universal_satellite.download import download_manifest
            except ImportError:
                parameters[8].setErrorMessage("Upgrade the universal-satellite core SDK to use image downloads.")

    def execute(self, parameters, messages):
        try:
            try:
                from universal_satellite import Client
            except ImportError as exc:
                raise RuntimeError(
                    "Install universal-satellite in this ArcGIS Pro Python environment before running the tool; see docs/gis.md."
                ) from exc
            dataset = _resolve_dataset(parameters[0].valueAsText, _datasets())
            dataset_id = dataset.id
            if _boolean(parameters, 8) and not parameters[10].valueAsText:
                raise ValueError("Choose an image output folder before running the search with image downloads enabled.")
            bbox = _wgs84_bbox(_extent_value(parameters[1]), parameters[2].value)
            result = Client().search(
                dataset=dataset_id, bbox=bbox, start=parameters[3].valueAsText,
                end=parameters[4].valueAsText,
                cloud=float(parameters[5].valueAsText) if dataset.category == "optical" else None,
                limit=int(parameters[6].valueAsText),
            )
            output = parameters[7].valueAsText
            _write_manifest(result, output)
            if getattr(dataset, "measurement", None):
                messages.addMessage(f"Selected measurement: {dataset.measurement}. Assets retain the provider's encoding.")
            metadata = result.get("universal_satellite", {})
            if metadata.get("temporal_filter_applied") is False:
                messages.addMessage(metadata.get("temporal_note", "Static dataset: requested dates were not applied."))
            messages.addMessage(f"Wrote {len(result['features'])} scene footprints to {output}.")
            if _boolean(parameters, 8) and result["features"]:
                _download(output, parameters[9].valueAsText, parameters[10].valueAsText,
                          _boolean(parameters, 11), _boolean(parameters, 12), messages)
            elif _boolean(parameters, 8):
                messages.addWarningMessage("No scenes matched; no image assets were downloaded.")
            else:
                messages.addMessage("Image downloading was not selected. Use Download satellite image assets to retrieve bands to a folder.")
        except Exception as exc:
            message = str(exc)
            if isinstance(exc, ValueError) and message.startswith("Unknown dataset"):
                message += " Upgrade the universal-satellite core SDK in ArcGIS Pro's Python environment to use this bundled source."
            messages.addErrorMessage(message)
            raise arcpy.ExecuteError from exc


class RasterIndex:
    INDICES = {"ndvi": ("nir", "red"), "ndwi": ("green", "nir"), "nbr": ("nir", "swir22")}

    def __init__(self):
        self.label = "Compute normalized-difference raster index"
        self.description = (
            "NDVI: A=NIR, B=red; NDWI: A=green, B=NIR; NBR: A=NIR, B=SWIR2. "
            "Requires local single-band rasters with matching CRS and grids and "
            "the universal-satellite[raster] extra. Embedded raster scale/offset "
            "metadata is applied; ensure it matches provider calibration. "
            "Use consistently processed TOA or SR inputs and calibrate raw DN first; "
            "this tool does not convert TOA to SR. "
            "No Spatial Analyst extension is used."
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        index = _parameter("index", "Index", "GPString")
        index.filter.type = "ValueList"
        index.filter.list = list(self.INDICES)
        index.value = "ndvi"
        first = _parameter("band_a", "Band A (local single-band GeoTIFF)", "DEFile")
        second = _parameter("band_b", "Band B (local single-band GeoTIFF)", "DEFile")
        for parameter in (first, second):
            parameter.filter.list = ["tif", "tiff"]
        output = _parameter("output", "Index raster (.tif)", "DEFile", direction="Output")
        output.filter.list = ["tif"]
        return [index, first, second, output]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        try:
            from universal_satellite.raster import compute_index

            name = parameters[0].valueAsText
            first, second = self.INDICES[name]
            output = parameters[3].valueAsText
            compute_index(name, output, **{
                first: parameters[1].valueAsText, second: parameters[2].valueAsText
            })
            messages.addMessage(f"Wrote {name.upper()} to {output}.")
        except Exception as exc:
            messages.addErrorMessage(str(exc))
            raise arcpy.ExecuteError from exc


class DownloadAssets:
    def __init__(self):
        self.label = "Download satellite image assets"
        self.description = (
            "Download image assets from a saved scene GeoJSON into your chosen folder "
            "as a geoprocessing job, without terminal commands. Select exact asset "
            "keys: Sentinel-2 red,nir; Landsat red,nir08. All scenes in the manifest "
            "are processed. Existing files are preserved unless overwrite is selected. "
            "Optional signing supports Planetary Computer Azure assets only. "
            "Provider credentials may be configured in the process environment; native "
            "S3 requester-pays is unsupported. Progress and individual failures "
            "are reported; cancellation retains completed files and, when resumption "
            "is enabled, partial downloads. Requires the current core SDK."
        ) + _asset_help()
        self.canRunInBackground = True

    def getParameterInfo(self):
        manifest = _parameter("manifest", "Scene manifest (.geojson)", "DEFile")
        manifest.filter.list = ["geojson", "json"]
        assets = _parameter("assets", "Asset keys (see tool Help for meanings; * = all; DEM: data)", "GPString")
        assets.value = "red,nir"
        folder = _parameter("folder", "Image output folder", "DEFolder")
        signing = _parameter("sign_planetary", "Sign Planetary Computer Azure asset URLs", "GPBoolean", required=False)
        signing.value = False
        overwrite = _parameter("overwrite", "Overwrite existing downloaded files", "GPBoolean", required=False)
        overwrite.value = False
        resume = _parameter("resume", "Resume interrupted downloads", "GPBoolean", required=False)
        resume.value = True
        workers = _parameter("workers", "Concurrent asset downloads (1–16)", "GPLong", required=False)
        workers.value = 4
        return [manifest, assets, folder, signing, overwrite, resume, workers]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        try:
            from universal_satellite.download import download_manifest
        except ImportError:
            parameters[0].setErrorMessage("Install or upgrade universal-satellite in ArcGIS Pro's Python environment to download images.")

    def execute(self, parameters, messages):
        try:
            _download(parameters[0].valueAsText, parameters[1].valueAsText,
                      parameters[2].valueAsText, _boolean(parameters, 3),
                      _boolean(parameters, 4), messages, **({"resume":_boolean(parameters,5), "workers":int(parameters[6].valueAsText or 4), "retries":2} if len(parameters)>6 else {}))
        except Exception as exc:
            messages.addErrorMessage(str(exc))
            raise arcpy.ExecuteError from exc


def _index_catalog():
    return json.loads(Path(__file__).with_name("indices.json").read_text(encoding="utf-8"))


class SpectralIndex:
    def __init__(self):
        self.label = "Compute spectral index (full catalog)"
        self.description = "Choose an index, supply its named calibrated bands and any required constants. All rasters must be aligned. See docs/indices.md for formulas, units and sensor compatibility."
        self.canRunInBackground = False

    def getParameterInfo(self):
        catalog = _index_catalog()
        index = _parameter("index", "Index", "GPString")
        index.filter.type = "ValueList"
        index.filter.list = list(catalog["indices"])
        index.value = "ndvi"
        output = _parameter("output", "Index raster (.tif)", "DEFile", direction="Output")
        output.filter.list = ["tif"]
        constants = _parameter("constants", 'Coefficient overrides (JSON, e.g. {"L":0.5})', "GPString", required=False)
        constants.value = "{}"
        result = [index, output, constants]
        for key in catalog["bands"]:
            band = _parameter(key, key + " (aligned single-band raster)", "DEFile", required=False)
            band.filter.list = ["tif", "tiff"]
            result.append(band)
        return result

    def isLicensed(self): return True

    def updateParameters(self, parameters):
        catalog = _index_catalog()
        required = catalog["indices"].get(parameters[0].valueAsText, [])
        for key, parameter in zip(catalog["bands"], parameters[3:]):
            parameter.enabled = key in required

    def updateMessages(self, parameters): return

    def execute(self, parameters, messages):
        try:
            from universal_satellite.raster import compute_index
            catalog = _index_catalog()
            name = parameters[0].valueAsText
            required = catalog["indices"][name]
            bands = {key:p.valueAsText for key,p in zip(catalog["bands"],parameters[3:]) if key in required and p.valueAsText}
            compute_index(name, parameters[1].valueAsText, constants=json.loads(parameters[2].valueAsText or "{}"), **bands)
            messages.addMessage("Wrote " + name.upper())
        except Exception as exc:
            messages.addErrorMessage(str(exc))
            raise arcpy.ExecuteError from exc


class EnvironmentalProfile:
    def __init__(self):
        self.label = "Download weather, air-quality or soil point profile"
        self.description = "Download actual provider model values as JSON with units and attribution. SoilGrids REST may be unavailable. These are point profiles, not satellite images."
        self.canRunInBackground = True
    def isLicensed(self): return True
    def getParameterInfo(self):
        kind=_parameter('kind','Profile','GPString');kind.filter.type='ValueList';kind.filter.list=['forecast','air-quality','soil'];kind.value='forecast'
        lat=_parameter('latitude','Latitude (WGS84)','GPDouble')
        lon=_parameter('longitude','Longitude (WGS84)','GPDouble')
        model=_parameter('model','Forecast model','GPString',required=False);model.filter.type='ValueList';model.filter.list=['ecmwf_ifs','gfs_seamless'];model.value='ecmwf_ifs'
        depth=_parameter('depth','Soil depth','GPString',required=False);depth.filter.type='ValueList';depth.filter.list=['0-5cm','5-15cm','15-30cm','30-60cm','60-100cm','100-200cm'];depth.value='0-5cm'
        output=_parameter('output','Profile JSON','DEFile',direction='Output');output.filter.list=['json']
        return [kind,lat,lon,model,depth,output]
    def updateParameters(self,parameters):
        parameters[3].enabled=parameters[0].valueAsText=='forecast'
        parameters[4].enabled=parameters[0].valueAsText=='soil'
    def updateMessages(self,parameters): return
    def execute(self,parameters,messages):
        try:
            from universal_satellite.client import Client
            from universal_satellite.export import write_json
            data=Client().environment(parameters[0].valueAsText,latitude=float(parameters[1].valueAsText),longitude=float(parameters[2].valueAsText),model=parameters[3].valueAsText or 'ecmwf_ifs',depth=parameters[4].valueAsText or '0-5cm')
            write_json(data,parameters[5].valueAsText)
            messages.addMessage(data['universal_satellite']['attribution'])
        except Exception as exc:
            messages.addErrorMessage(str(exc));raise arcpy.ExecuteError from exc


class CropRaster:
    def __init__(self):
        self.label = "Crop raster or remote COG to polygon"
        self.description = "Clip a local raster or public/signed HTTPS COG with a WGS84 GeoJSON or a Shapefile with CRS. Preserves source grid and masks. Default maximum: 25 million band-pixels. Protected products must be downloaded first."
        self.canRunInBackground = True
    def isLicensed(self): return True
    def getParameterInfo(self):
        source=_parameter('source','Local raster path or HTTPS COG URL','GPString')
        boundary=_parameter('boundary','Polygon boundary (GeoJSON/Shapefile)','DEFile');boundary.filter.list=['geojson','json','shp']
        output=_parameter('output','Clipped GeoTIFF','DEFile',direction='Output');output.filter.list=['tif']
        return [source,boundary,output]
    def execute(self,parameters,messages):
        try:
            from universal_satellite.raster import crop_raster
            crop_raster(parameters[0].valueAsText,parameters[1].valueAsText,parameters[2].valueAsText)
            messages.addMessage('Wrote clipped raster')
        except Exception as exc:
            messages.addErrorMessage(str(exc));raise arcpy.ExecuteError from exc
