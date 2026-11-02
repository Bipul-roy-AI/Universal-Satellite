"""Thin Processing adapters. Network and raster behavior live in the core SDK."""

import json
import os
import tempfile
from pathlib import Path

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)


def _core():
    try:
        from universal_satellite import Client
        from universal_satellite.catalog import list_datasets
    except ImportError as exc:
        raise QgsProcessingException(
            "Install universal-satellite in QGIS's Python environment; see docs/gis.md."
        ) from exc
    return Client, list_datasets


def _atomic_geojson(result, destination):
    target = Path(destination)
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


class SearchScenes(QgsProcessingAlgorithm):
    def name(self):
        return "search_scenes"

    def displayName(self):
        return "Search satellite scenes (GeoJSON manifest)"

    def group(self):
        return "Discovery"

    def groupId(self):
        return "discovery"

    def shortHelpString(self):
        return (
            "Search one STAC archive using an area and ISO dates (YYYY-MM-DD). "
            "Choose Sentinel-2 Level-1C for top-of-atmosphere (TOA) reflectance or "
            "Level-2A for atmospherically corrected surface reflectance (SR). "
            "These are separate datasets; this tool does not convert TOA to SR. "
            "Landsat Level-1 delivers DN requiring calibration; Landsat US ARD TOA "
            "has regional U.S. coverage. Other sources have their own measurements. "
            "The input extent is transformed to EPSG:4326; split areas crossing "
            "the antimeridian. Output contains scene footprints and original asset "
            "links, not raster pixels. Add the GeoJSON as a vector layer, then use "
            "the CLI to download selected assets. Cloud cover filters scene metadata, "
            "not individual pixels. Static inventories (Copernicus DEM, NASADEM and "
            "JRC Global Surface Water) ignore the requested dates and record this "
            "in manifest metadata. Requires universal-satellite in QGIS's Python."
        )

    def createInstance(self):
        return SearchScenes()

    def initAlgorithm(self, config=None):
        _, list_datasets = _core()
        self.datasets = [item for item in list_datasets() if item.status == "searchable"]
        self.addParameter(QgsProcessingParameterEnum(
            "DATASET", "Dataset / measurement (TOA, SR, DN or other)",
            options=[f"{d.title} [{d.id}]" for d in self.datasets]
        ))
        self.addParameter(QgsProcessingParameterExtent("EXTENT", "Area of interest (with CRS)"))
        self.addParameter(QgsProcessingParameterString("START", "Start date (YYYY-MM-DD)"))
        self.addParameter(QgsProcessingParameterString("END", "End date (YYYY-MM-DD)"))
        self.addParameter(QgsProcessingParameterNumber(
            "CLOUD", "Maximum scene cloud cover (%)", type=QgsProcessingParameterNumber.Double,
            defaultValue=100, minValue=0, maxValue=100
        ))
        self.addParameter(QgsProcessingParameterNumber(
            "LIMIT", "Maximum number of scenes", type=QgsProcessingParameterNumber.Integer,
            defaultValue=10, minValue=1, maxValue=1000
        ))
        self.addParameter(QgsProcessingParameterFileDestination(
            "OUTPUT", "Scene manifest", fileFilter="GeoJSON (*.geojson)"
        ))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            Client, _ = _core()
            dataset = self.datasets[self.parameterAsEnum(parameters, "DATASET", context)]
            extent = self.parameterAsExtent(
                parameters, "EXTENT", context, QgsCoordinateReferenceSystem("EPSG:4326")
            )
            if extent.isNull() or extent.isEmpty():
                raise ValueError("Choose a non-empty area of interest.")
            if feedback.isCanceled():
                return {}
            # Cloud cover is only meaningful for optical imagery.
            cloud = self.parameterAsDouble(parameters, "CLOUD", context) if dataset.category == "optical" else None
            result = Client().search(
                dataset=dataset.id,
                bbox=[extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()],
                start=self.parameterAsString(parameters, "START", context),
                end=self.parameterAsString(parameters, "END", context),
                cloud=cloud,
                limit=self.parameterAsInt(parameters, "LIMIT", context),
            )
            if feedback.isCanceled():
                return {}
            output = self.parameterAsFileOutput(parameters, "OUTPUT", context)
            _atomic_geojson(result, output)
            if getattr(dataset, "measurement", None):
                feedback.pushInfo(f"Selected measurement: {dataset.measurement}. Assets retain the provider's encoding.")
            metadata = result.get("universal_satellite", {})
            if metadata.get("temporal_filter_applied") is False:
                feedback.pushInfo(metadata.get("temporal_note", "Static dataset: requested dates were not applied."))
            feedback.pushInfo(f"Wrote {len(result['features'])} scene footprints. Raster assets were not downloaded.")
            feedback.setProgress(100)
            return {"OUTPUT": output}
        except QgsProcessingException:
            raise
        except Exception as exc:
            raise QgsProcessingException(str(exc)) from exc


class RasterIndex(QgsProcessingAlgorithm):
    INDICES = (
        ("ndvi", "NDVI: A = NIR, B = red", "nir", "red"),
        ("ndwi", "NDWI: A = green, B = NIR", "green", "nir"),
        ("nbr", "NBR: A = NIR, B = SWIR2", "nir", "swir22"),
    )

    def name(self):
        return "raster_index"

    def displayName(self):
        return "Compute normalized-difference raster index"

    def group(self):
        return "Raster analysis"

    def groupId(self):
        return "analysis"

    def createInstance(self):
        return RasterIndex()

    def shortHelpString(self):
        return (
            "Compute NDVI, NDWI or NBR from two local single-band GeoTIFFs. "
            "Inputs must have matching grids, transforms and CRS. Embedded raster "
            "scale/offset metadata is applied. Ensure it matches the provider's "
            "reflectance calibration and use consistently processed TOA or SR inputs; "
            "calibrate raw DN first. The tool does not convert TOA to SR. "
            "Scene cloud cover is not a cloud mask. Requires the raster "
            "extra: pip install 'universal-satellite[raster]'."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterEnum(
            "INDEX", "Index and band order", options=[row[1] for row in self.INDICES]
        ))
        self.addParameter(QgsProcessingParameterFile(
            "A", "Band A (local single-band GeoTIFF)", extension="tif"
        ))
        self.addParameter(QgsProcessingParameterFile(
            "B", "Band B (local single-band GeoTIFF)", extension="tif"
        ))
        self.addParameter(QgsProcessingParameterFileDestination(
            "OUTPUT", "Index raster", fileFilter="GeoTIFF (*.tif)"
        ))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            from universal_satellite.raster import compute_index

            if feedback.isCanceled():
                return {}
            name, _, first, second = self.INDICES[self.parameterAsEnum(parameters, "INDEX", context)]
            output = self.parameterAsFileOutput(parameters, "OUTPUT", context)
            compute_index(name, output, **{
                first: self.parameterAsFile(parameters, "A", context),
                second: self.parameterAsFile(parameters, "B", context),
            })
            feedback.setProgress(100)
            return {"OUTPUT": output}
        except Exception as exc:
            raise QgsProcessingException(str(exc)) from exc
