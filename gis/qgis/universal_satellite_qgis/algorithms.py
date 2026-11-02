"""Thin Processing adapters. Network and raster behavior live in the core SDK."""

import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterFolderDestination,
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


def _datasets():
    """Keep discovery choices visible before the separately installed SDK exists."""
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


def _source_help():
    lines = []
    for source in _datasets():
        end = source.end or "ongoing (provider coverage varies)"
        static = " Static inventory: requested dates are not filtered." if not source.temporal else ""
        lines.append(f"{source.title} [{source.id}] — source era {source.start} to {end}.{static} {source.description}")
    return "\n\nAvailable searchable sources (source eras are not guaranteed catalog coverage):\n" + "\n\n".join(lines)


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


def _download_assets(manifest, asset_text, output, sign_planetary, overwrite, feedback):
    try:
        from universal_satellite.download import download_manifest
    except ImportError as exc:
        raise QgsProcessingException(
            "Install or upgrade the universal-satellite core SDK in QGIS's Python environment to download images."
        ) from exc
    keys = [key.strip() for key in asset_text.split(",") if key.strip()]
    if not keys:
        raise ValueError("Enter at least one asset key from the scene manifest.")
    if not output.strip():
        raise ValueError("Choose a folder for downloaded satellite images.")

    def progress(percent, message):
        feedback.setProgress(percent)
        if message:
            feedback.pushInfo(message)

    result = download_manifest(
        manifest, keys, output, sign_planetary=sign_planetary, overwrite=overwrite,
        progress=progress, cancelled=feedback.isCanceled,
    )
    downloaded = len(result["downloaded"])
    failures = result["failed"]
    for failure in failures:
        feedback.reportError(
            f"Scene {failure['scene']}, asset {failure['asset']}: {failure['error']}",
            fatalError=False,
        )
    if result["cancelled"]:
        status = "Cancelled; completed files retained"
    elif failures:
        status = "Partial download" if downloaded else "Download failed"
    elif downloaded:
        status = "Download completed"
    else:
        status = "No assets downloaded"
    summary = f"{status}: {downloaded} downloaded, {len(failures)} failed. Output folder: {output}"
    feedback.pushInfo(summary)
    if failures and not downloaded and not result["cancelled"]:
        raise QgsProcessingException("No image assets were downloaded; see the provider errors above.")
    if not result["cancelled"]:
        feedback.setProgress(100)
    return {"OUTPUT_DIR": output, "SUMMARY": summary}


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
            "links, not raster pixels. Add the GeoJSON as a vector layer, then run "
            "Download satellite image assets to save selected images to a folder. "
            "Alternatively, enable Download images after search and choose a "
            "folder and collection-specific asset keys for a single-run workflow. "
            "Automatic download is off by default; downloaded files are not clipped. "
            "Cloud cover filters scene metadata, "
            "not individual pixels. Static inventories (Copernicus DEM, NASADEM and "
            "JRC Global Surface Water) ignore the requested dates and record this "
            "in manifest metadata. Requires universal-satellite in QGIS's Python. "
            "The bundled catalog remains visible before that SDK is installed."
        ) + _source_help()

    def createInstance(self):
        return SearchScenes()

    def initAlgorithm(self, config=None):
        self.datasets = _datasets()
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
        self.addParameter(QgsProcessingParameterBoolean(
            "DOWNLOAD", "Download images after search", defaultValue=False
        ))
        self.addParameter(QgsProcessingParameterString(
            "DOWNLOAD_ASSETS", "Download asset keys (Sentinel-2: red,nir; Landsat: red,nir08)",
            defaultValue="red,nir"
        ))
        self.addParameter(QgsProcessingParameterFolderDestination(
            "DOWNLOAD_DIR", "Folder for images (required when downloading)",
            optional=True, createByDefault=False
        ))
        self.addParameter(QgsProcessingParameterBoolean(
            "SIGN_PLANETARY", "Sign Planetary Computer assets when downloading", defaultValue=False
        ))
        self.addParameter(QgsProcessingParameterBoolean(
            "OVERWRITE", "Overwrite existing downloaded files", defaultValue=False
        ))
        self.addOutput(QgsProcessingOutputString("DOWNLOAD_SUMMARY", "Image download result summary"))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            Client, _ = _core()
            dataset = self.datasets[self.parameterAsEnum(parameters, "DATASET", context)]
            auto_download = "DOWNLOAD" in parameters and self.parameterAsBool(parameters, "DOWNLOAD", context)
            download_dir = self.parameterAsString(parameters, "DOWNLOAD_DIR", context) if auto_download else None
            if auto_download and not download_dir.strip():
                raise ValueError("Choose a folder for images when Download images after search is enabled.")
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
            feedback.pushInfo(f"Wrote {len(result['features'])} scene footprints. Raster assets are downloaded only when enabled.")
            outputs = {"OUTPUT": output}
            if auto_download:
                download_result = _download_assets(
                    output, self.parameterAsString(parameters, "DOWNLOAD_ASSETS", context), download_dir,
                    self.parameterAsBool(parameters, "SIGN_PLANETARY", context),
                    self.parameterAsBool(parameters, "OVERWRITE", context), feedback,
                )
                outputs.update({"DOWNLOAD_DIR": download_dir, "DOWNLOAD_SUMMARY": download_result["SUMMARY"]})
            else:
                feedback.setProgress(100)
            return outputs
        except QgsProcessingException:
            raise
        except Exception as exc:
            message = str(exc)
            if isinstance(exc, ValueError) and message.startswith("Unknown dataset"):
                message += " Upgrade the universal-satellite core SDK in QGIS's Python environment to use this bundled source."
            raise QgsProcessingException(message) from exc


class DownloadAssets(QgsProcessingAlgorithm):
    def name(self):
        return "download_assets"

    def displayName(self):
        return "Download satellite image assets"

    def group(self):
        return "Downloads"

    def groupId(self):
        return "downloads"

    def shortHelpString(self):
        return (
            "Download actual image assets from a saved Search satellite scenes "
            "GeoJSON manifest into a folder you choose. No terminal commands are "
            "needed. Enter comma-separated asset keys from the manifest, such as "
            "red,nir for Sentinel-2 SR or red,nir08 for Landsat SR. Keys vary by "
            "collection; inspect each scene's assets map. Each selected key is "
            "requested for every scene in the manifest; missing keys and failed "
            "transfers are reported separately. These are provider files, potentially "
            "full scenes, not automatically clipped or reprojected rasters. Enable "
            "Planetary Computer signing for its restricted Azure assets; it does "
            "not supply USGS EROS credentials or requester-pays access. HTTP(S) "
            "assets are supported; s3:// assets require provider-supported retrieval. "
            "Existing files are preserved unless Overwrite is enabled. Cancellation "
            "keeps completed files and stops remaining transfers. Add downloaded "
            "GeoTIFFs with Add Raster Layer. Requires the updated universal-satellite "
            "core SDK in QGIS's Python environment."
        )

    def createInstance(self):
        return DownloadAssets()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(
            "MANIFEST", "Scene manifest from Search satellite scenes (.geojson)", extension="geojson"
        ))
        self.addParameter(QgsProcessingParameterString(
            "ASSETS", "Asset keys (comma-separated; collection-specific)", defaultValue="red,nir"
        ))
        self.addParameter(QgsProcessingParameterFolderDestination(
            "OUTPUT_DIR", "Folder for downloaded satellite images"
        ))
        self.addParameter(QgsProcessingParameterBoolean(
            "SIGN_PLANETARY", "Sign Planetary Computer assets", defaultValue=False
        ))
        self.addParameter(QgsProcessingParameterBoolean(
            "OVERWRITE", "Overwrite existing downloaded files", defaultValue=False
        ))
        self.addOutput(QgsProcessingOutputString("SUMMARY", "Download result summary"))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            return _download_assets(
                self.parameterAsFile(parameters, "MANIFEST", context),
                self.parameterAsString(parameters, "ASSETS", context),
                self.parameterAsString(parameters, "OUTPUT_DIR", context),
                self.parameterAsBool(parameters, "SIGN_PLANETARY", context),
                self.parameterAsBool(parameters, "OVERWRITE", context), feedback,
            )
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
