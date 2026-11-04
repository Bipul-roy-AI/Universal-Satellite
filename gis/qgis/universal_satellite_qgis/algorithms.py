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


def _download_assets(manifest, asset_text, output, sign_planetary, overwrite, feedback, **options):
    try:
        from universal_satellite.download import download_manifest
    except ImportError as exc:
        raise QgsProcessingException(
            "Install or upgrade the universal-satellite core SDK in QGIS's Python environment to download images."
        ) from exc
    feedback.pushInfo(_manifest_asset_help(manifest))
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
        progress=progress, cancelled=feedback.isCanceled, **options,
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
        ) + _source_help() + _asset_help()

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
            "DOWNLOAD_ASSETS", "Download asset keys (see Help; * = all; DEM: data)",
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
                **({"resume":self.parameterAsBool(parameters,"RESUME",context), "workers":self.parameterAsInt(parameters,"WORKERS",context), "retries":2} if "WORKERS" in parameters else {}),
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
        ) + _asset_help()

    def createInstance(self):
        return DownloadAssets()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(
            "MANIFEST", "Scene manifest from Search satellite scenes (.geojson)", extension="geojson"
        ))
        self.addParameter(QgsProcessingParameterString(
            "ASSETS", "Asset keys (see Help for meanings; * = all; DEM: data)", defaultValue="red,nir"
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
        self.addParameter(QgsProcessingParameterBoolean("RESUME", "Resume interrupted downloads", defaultValue=True))
        self.addParameter(QgsProcessingParameterNumber("WORKERS", "Concurrent asset downloads", type=QgsProcessingParameterNumber.Integer, defaultValue=4, minValue=1, maxValue=16))
        self.addOutput(QgsProcessingOutputString("SUMMARY", "Download result summary"))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            return _download_assets(
                self.parameterAsFile(parameters, "MANIFEST", context),
                self.parameterAsString(parameters, "ASSETS", context),
                self.parameterAsString(parameters, "OUTPUT_DIR", context),
                self.parameterAsBool(parameters, "SIGN_PLANETARY", context),
                self.parameterAsBool(parameters, "OVERWRITE", context), feedback,
                **({"resume":self.parameterAsBool(parameters,"RESUME",context), "workers":self.parameterAsInt(parameters,"WORKERS",context), "retries":2} if "WORKERS" in parameters else {}),
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


def _index_catalog():
    return json.loads(Path(__file__).with_name("indices.json").read_text(encoding="utf-8"))


class SpectralIndex(QgsProcessingAlgorithm):
    def name(self): return "spectral_index"
    def displayName(self): return "Compute spectral index (full catalog)"
    def group(self): return "Raster analysis"
    def groupId(self): return "analysis"
    def createInstance(self): return SpectralIndex()
    def shortHelpString(self):
        return "Choose an index; the menu lists its required bands. Supply only those aligned, calibrated single-band rasters. Coefficients are JSON; sensor wavelengths and scene-specific coefficients must be explicit. See docs/indices.md."

    def initAlgorithm(self, config=None):
        catalog = _index_catalog()
        self.addParameter(QgsProcessingParameterEnum("INDEX", "Index — required bands", options=[k + " — " + ", ".join(v) for k,v in catalog["indices"].items()]))
        self.addParameter(QgsProcessingParameterString("CONSTANTS", "Coefficient overrides (JSON)", defaultValue="{}", optional=True))
        for key in catalog["bands"]:
            self.addParameter(QgsProcessingParameterFile(key, key + " (only if required by index)", extension="tif", optional=True))
        self.addParameter(QgsProcessingParameterFileDestination("OUTPUT", "Index raster", fileFilter="GeoTIFF (*.tif)"))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            from universal_satellite.raster import compute_index
            if feedback.isCanceled(): return {}
            catalog = _index_catalog()
            name = list(catalog["indices"])[self.parameterAsEnum(parameters,"INDEX",context)]
            bands = {k:self.parameterAsFile(parameters,k,context) for k in catalog["indices"][name]}
            bands = {k:v for k,v in bands.items() if v}
            output = self.parameterAsFileOutput(parameters,"OUTPUT",context)
            compute_index(name, output, constants=json.loads(self.parameterAsString(parameters,"CONSTANTS",context) or "{}"), **bands)
            feedback.setProgress(100)
            return {"OUTPUT":output}
        except Exception as exc:
            raise QgsProcessingException(str(exc)) from exc


class EnvironmentalProfile(QgsProcessingAlgorithm):
    def name(self): return 'environmental_profile'
    def displayName(self): return 'Download weather, air-quality or soil point profile'
    def group(self): return 'Environmental data'
    def groupId(self): return 'environment'
    def createInstance(self): return EnvironmentalProfile()
    def shortHelpString(self): return 'Actual model/soil point profiles in JSON with native units. SoilGrids REST may be unavailable. These are not satellite images.'
    def initAlgorithm(self,config=None):
        self.addParameter(QgsProcessingParameterEnum('KIND','Profile',options=['forecast','air-quality','soil']))
        self.addParameter(QgsProcessingParameterNumber('LATITUDE','Latitude (WGS84)',type=QgsProcessingParameterNumber.Double,minValue=-90,maxValue=90))
        self.addParameter(QgsProcessingParameterNumber('LONGITUDE','Longitude (WGS84)',type=QgsProcessingParameterNumber.Double,minValue=-180,maxValue=180))
        self.addParameter(QgsProcessingParameterEnum('MODEL','Forecast model',options=['ecmwf_ifs','gfs_seamless']))
        self.addParameter(QgsProcessingParameterEnum('DEPTH','Soil depth',options=['0-5cm','5-15cm','15-30cm','30-60cm','60-100cm','100-200cm']))
        self.addParameter(QgsProcessingParameterFileDestination('OUTPUT','Profile JSON',fileFilter='JSON (*.json)'))
    def processAlgorithm(self,parameters,context,feedback):
        try:
            from universal_satellite.client import Client
            from universal_satellite.export import write_json
            if feedback.isCanceled():return {}
            data=Client().environment(['forecast','air-quality','soil'][self.parameterAsEnum(parameters,'KIND',context)],latitude=self.parameterAsDouble(parameters,'LATITUDE',context),longitude=self.parameterAsDouble(parameters,'LONGITUDE',context),model=['ecmwf_ifs','gfs_seamless'][self.parameterAsEnum(parameters,'MODEL',context)],depth=['0-5cm','5-15cm','15-30cm','30-60cm','60-100cm','100-200cm'][self.parameterAsEnum(parameters,'DEPTH',context)])
            output=self.parameterAsFileOutput(parameters,'OUTPUT',context)
            write_json(data,output);feedback.pushInfo(data['universal_satellite']['attribution'])
            return {'OUTPUT':output}
        except Exception as exc: raise QgsProcessingException(str(exc)) from exc


class CropRaster(QgsProcessingAlgorithm):
    def name(self): return 'crop_raster'
    def displayName(self): return 'Crop raster or remote COG to polygon'
    def group(self): return 'Raster analysis'
    def groupId(self): return 'analysis'
    def createInstance(self): return CropRaster()
    def shortHelpString(self): return 'Crop a local raster or public/signed HTTPS COG using WGS84 GeoJSON or a Shapefile with CRS. Source grid and masks are retained. Maximum 25 million band-pixels. Protected products must be downloaded first.'
    def initAlgorithm(self,config=None):
        self.addParameter(QgsProcessingParameterString('SOURCE','Local raster path or HTTPS COG URL'))
        self.addParameter(QgsProcessingParameterFile('BOUNDARY','Polygon GeoJSON or Shapefile'))
        self.addParameter(QgsProcessingParameterFileDestination('OUTPUT','Clipped raster',fileFilter='GeoTIFF (*.tif)'))
    def processAlgorithm(self,parameters,context,feedback):
        try:
            from universal_satellite.raster import crop_raster
            if feedback.isCanceled():return {}
            output=self.parameterAsFileOutput(parameters,'OUTPUT',context)
            crop_raster(self.parameterAsString(parameters,'SOURCE',context),self.parameterAsFile(parameters,'BOUNDARY',context),output)
            return {'OUTPUT':output}
        except Exception as exc:raise QgsProcessingException(str(exc)) from exc
