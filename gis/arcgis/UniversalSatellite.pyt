"""ArcGIS Pro Python toolbox; requires the separately installed core package."""

import json
import os
import tempfile
from pathlib import Path

import arcpy


def _datasets():
    from universal_satellite.catalog import list_datasets

    return [item for item in list_datasets() if item.status == "searchable"]


def _parameter(name, label, datatype, direction="Input", required=True):
    return arcpy.Parameter(
        name=name, displayName=label, datatype=datatype, direction=direction,
        parameterType="Required" if required else "Optional"
    )


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
        self.tools = [SearchScenes, RasterIndex]


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
            "ignore requested dates and label that behavior in manifest metadata."
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        dataset = _parameter(
            "dataset", "Dataset ID (sentinel-2-l1c = TOA; sentinel-2-l2a = SR)", "GPString"
        )
        dataset.filter.type = "ValueList"
        try:
            dataset.filter.list = [item.id for item in _datasets()]
        except ImportError:
            dataset.filter.list = []
        dataset.value = "sentinel-2-l2a"
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
        return [dataset, extent, crs, start, end, cloud, limit, output]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        try:
            _datasets()
        except ImportError:
            parameters[0].setErrorMessage(
                "Install universal-satellite in this ArcGIS Pro Python environment; see docs/gis.md."
            )

    def execute(self, parameters, messages):
        try:
            from universal_satellite import Client

            dataset_id = parameters[0].valueAsText
            dataset = next((d for d in _datasets() if d.id == dataset_id), None)
            if dataset is None:
                raise ValueError(f"Unknown searchable dataset: {dataset_id}")
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
            messages.addMessage("Raster assets were not downloaded. Use the CLI download command for selected assets.")
        except Exception as exc:
            messages.addErrorMessage(str(exc))
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
