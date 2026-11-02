# QGIS and ArcGIS Pro toolboxes

| Application | Toolbox ZIP | Install |
| --- | --- | --- |
| QGIS | [universal_satellite_qgis.zip](../gis/qgis/universal_satellite_qgis.zip) | Install the ZIP directly through QGIS's **Install from ZIP**. |
| ArcGIS Pro | [universal_satellite_arcgis.zip](../gis/arcgis/universal_satellite_arcgis.zip) | Extract the ZIP, then add `UniversalSatellite/UniversalSatellite.pyt` as a toolbox. |

On GitHub, open the ZIP link and use **Download raw file** to save the archive.
Both ZIPs contain desktop adapters; **install the core Python SDK separately in
your GIS's Python environment** using the steps below. Neither ZIP bundles or
automatically installs the SDK or its optional raster dependencies.

Both integrations use the same Python SDK as the CLI. They provide three tools:
**Search satellite scenes (GeoJSON manifest)**, **Download satellite image assets**
and **Compute normalized-difference raster index**. Search saves scene footprints,
metadata and asset URLs; an optional checkbox also downloads selected assets to
a folder. The separate download tool uses an existing manifest. Neither workflow
mosaics images. Raster index reads two prepared local, single-band GeoTIFFs and
writes NDVI, NDWI or NBR.

Both search tools list all 13 searchable data sources by name and exact dataset
ID, including TOA, SR, radar, DEM, land-cover, water and MODIS products. The bundled
dataset menus remain visible when the core SDK is missing; the SDK is still
required to run a search. Tool help lists the record eras and source notes.

Search dates filter temporal imagery collections. **Static inventories**
(`cop-dem-glo-30`, `nasadem`, `jrc-gsw`) ignore the requested dates: their source
dates describe the acquisition or record era, rather than newly observed scenes.
Both toolboxes report this in their output messages. The saved manifest includes
`temporal_filter_applied: false`, the requested dates and a `temporal_note` in its
`universal_satellite` metadata. WorldCover's annual products retain date filtering.

These adapters are a first implementation. Their Python contracts are checked with
test doubles; they have **not been run inside native QGIS or ArcGIS Pro** in this
Linux environment. Use a small area and two aligned sample rasters to verify them
in your GIS version before batch work.

## Updating an existing installation

Install the new adapter ZIP and upgrade the core SDK **once** in the Python
environment used by the GIS, using the path to the updated local checkout:

```bash
python -m pip install --upgrade "/path/to/Universal-Satellite"
```

Restart the GIS afterward. Updating just the ZIP does not update the shared
download implementation. Downloading imagery from the tool dialogs does not
require a terminal command for each scene or a separate virtual environment.

## QGIS 3.28 or newer

1. Install the core package into the **Python environment used by QGIS**. From a
   shell configured for that installation, run the following commands, replacing
   the path with this checkout. On Windows, use the QGIS/OSGeo4W shell. On other
   platforms, use your QGIS distribution's documented Python environment.

   ```bash
   python -m pip install "/path/to/Universal-Satellite"
   # Optional, for the raster-index tool:
   python -m pip install "/path/to/Universal-Satellite[raster]"
   ```

   Installing with a system Python or an unrelated virtual environment will not
   make the package available to QGIS. Managed QGIS environments may require a
   user package installation or an administrator-managed deployment. Avoid
   replacing QGIS's own GDAL, NumPy or Qt packages; use compatible wheels or the
   distribution's packages. In QGIS's Python console, verify:

   ```python
   from universal_satellite import Client
   from universal_satellite.catalog import list_datasets
   print(len(list_datasets()))
   ```

2. Download the QGIS ZIP from the table above. In QGIS, open **Plugins → Manage
   and Install Plugins → Install from ZIP** and select
   `universal_satellite_qgis.zip`; do not extract it first. The ZIP includes the
   plugin directory at its root and requires the core SDK installed in step 1.

   For a manual source install, open **Settings → User Profiles → Open Active
   Profile Folder** and copy the whole `gis/qgis/universal_satellite_qgis`
   directory to the profile's `python/plugins/` directory. Keep the
   `universal_satellite_qgis` folder name. To rebuild the ZIP from source, run
   these commands from the repository root:

   ```bash
   python tools/package_qgis.py
   # To replace a previous package after changes:
   python tools/package_qgis.py --force
   ```

   Install `dist/universal_satellite_qgis.zip` with **Plugins → Manage and Install
   Plugins → Install from ZIP**. The ZIP includes the plugin directory at its root;
   it does not include the separately installed core SDK.
3. Restart QGIS. Enable **Universal Satellite Processing** under Plugins. In the
   Processing Toolbox, expand **Universal Satellite**.
4. Run **Search satellite scenes (GeoJSON manifest)**. Select a dataset, draw or
   select an extent with its CRS, enter ISO dates, and choose a `.geojson` output.
   The algorithm transforms the extent to WGS84 before querying the provider.
   The cloud threshold applies to optical datasets; it is omitted for radar and
   other categories. Start with 5–10 scenes.
5. For direct image downloads, enable **Download images after search** (off by
   default), enter comma-separated **Asset keys**, and select an **Image output
   folder**. For Sentinel-2 L2A try `red,nir`; Landsat commonly uses `red,nir08`.
   Enable Planetary Computer signing if needed. Leave overwrite off to preserve
   existing files. This processes every requested asset for each returned scene.
6. Run the Processing job and inspect its progress/log. If downloads are disabled,
   only the manifest is saved. Add that GeoJSON through **Layer → Add Layer → Add
   Vector Layer** to inspect footprints, and add downloaded GeoTIFFs with **Add
   Raster Layer**. Image layers are not automatically added or calibrated.

To download from an earlier search, open **Download satellite image assets**.
Choose the original scene manifest, asset keys and output folder, set the optional
signing/overwrite controls, and run. No download CLI command is needed. Keep the
manifest's original `assets` map; another format's exported footprint table may
omit it. See [download behavior and access limits](#download-behavior-and-access-limits).

The tool IDs are `universal_satellite:search_scenes`,
`universal_satellite:download_assets` and `universal_satellite:raster_index`,
so they also work in Processing models and
the QGIS Python console:

```python
import processing
from universal_satellite.catalog import list_datasets

choices = [d for d in list_datasets() if d.status == "searchable"]
dataset_index = next(i for i, d in enumerate(choices) if d.id == "sentinel-2-l2a")
processing.run("universal_satellite:search_scenes", {
    "DATASET": dataset_index,
    "EXTENT": "90.2,90.5,23.6,23.9 [EPSG:4326]",
    "START": "2024-01-01", "END": "2024-03-31",
    "CLOUD": 20, "LIMIT": 5,
    "OUTPUT": "/absolute/path/scenes.geojson",
})
```

QGIS's extent string order above is **xmin, xmax, ymin, ymax**; the SDK and CLI
instead use **west, south, east, north**. The adapter handles this difference.

The separate downloader can also run from the QGIS Python console. The manifest
must already exist, and its exact asset keys must match your request:

```python
processing.run("universal_satellite:download_assets", {
    "MANIFEST": "/absolute/path/scenes.geojson",
    "ASSETS": "red,nir",
    "OUTPUT_DIR": "/absolute/path/images",
    "SIGN_PLANETARY": False,
    "OVERWRITE": False,
})
```

## ArcGIS Pro

The `.pyt` is for **ArcGIS Pro's Python 3 environment**, not ArcMap/Python 2.

1. In ArcGIS Pro's Package Manager, clone the Pro environment and activate the
   clone. Open the Python Command Prompt for that clone and install this project:

   ```bat
   python -m pip install "C:\path\to\Universal-Satellite"
   ```

   The raster tool also needs NumPy and Rasterio in that environment. Use versions
   compatible with Pro's pinned geospatial stack, then install
   `"C:\path\to\Universal-Satellite[raster]"` if they are not already available.
   The search tool does not need Rasterio. Check the interpreter by importing
   `universal_satellite` in Pro's Python window. Restart Pro after changing its
   environment.
2. Download the ArcGIS Pro ZIP from the table above and extract it to a permanent
   folder. It contains `UniversalSatellite/UniversalSatellite.pyt`,
   `UniversalSatellite/datasets.json` and `UniversalSatellite/INSTALL.md`.
   Keep those files together. From **Catalog → Toolboxes → Add Toolbox**,
   select that extracted `UniversalSatellite.pyt`. The SDK installed in step 1
   is still required. When using the source checkout instead, select
   `gis/arcgis/UniversalSatellite.pyt` directly.
3. Open **Search satellite scenes (GeoJSON manifest)**. Select a named data source
   with its dataset ID in brackets,
   provide an extent and explicitly set its input coordinate system. The default
   is EPSG:4326: change it when using map coordinates from a projected CRS. Enter
   dates as `YYYY-MM-DD`, set the maximum scene count, and choose a `.geojson`
   destination outside a geodatabase. To save imagery in the same run, enable
   **Download images after search** (off by default), enter exact comma-separated
   asset keys and choose an **Image output folder**. `red,nir` is a common
   Sentinel-2 L2A choice; use `red,nir08` for Landsat products exposing those keys.
   Set optional Planetary Computer signing and overwrite controls as needed.
   Run the geoprocessing job and inspect its progress/messages.
4. To convert footprints into an ArcGIS feature class, use **JSON To Features**
   with the GeoJSON as input and Polygon as the geometry type. The full nested
   STAC asset metadata remains in the original manifest; field conversion can
   flatten or omit nested objects. Keep the original manifest for downloads.
5. If search downloads were disabled or you want different assets later, open
   **Download satellite image assets**. Select **Scene manifest (.geojson)**,
   enter asset keys, choose the image output folder and run. Public/presigned
   HTTP(S) files download through the GIS job without a separate CLI command.
6. Add downloaded GeoTIFFs to the map with **Add Data**. Run
   **Compute normalized-difference raster index** on local prepared bands.

To rebuild the ArcGIS Pro ZIP from source, run the following command from the
repository root, then extract `dist/universal_satellite_arcgis.zip` and add its
`UniversalSatellite.pyt` as described above:

```bash
python tools/package_arcgis.py --force
```

Search uses ordinary network access from the desktop. Configure your institution's
proxy/trust settings in that Python environment if needed. Public metadata access
does not imply unrestricted asset downloads: some providers require authentication
or signed asset URLs, and signed URLs expire.

## Download behavior and access limits

- The **Download images after search** checkbox is opt-in and defaults to false.
  With it off, a search saves metadata/footprints only. An empty search produces
  no image downloads; inspect the search messages rather than assuming images
  exist.
- Asset keys are exact and provider-specific. Every requested key is attempted
  for every returned scene. Choose a small scene limit and enough disk space:
  a full scene band can be large. Downloads preserve separate scene/asset files;
  they do not create a clipped AOI mosaic.
- Downloads run in the GIS application's Processing/geoprocessing job, using its
  normal background execution, progress and Cancel controls. No custom detached
  queue is created. Host-specific behavior still needs native testing.
- A cancellation keeps already completed files and removes the interrupted
  temporary `.part` file. It does not roll back previous downloads. Cancellation
  is checked during streaming; an in-flight network operation may still need to
  return or time out before the job stops.
- Overwrite is off by default: an existing destination is preserved. Individual
  asset failures are warned about and remaining assets are attempted. Partial
  success is reported with warnings/counts; if all attempted downloads fail, the
  job reports an error. Check the job log and actual output folder.
- Public or already authorized HTTP(S) asset links are supported. Optional
  Planetary Computer signing obtains temporary Azure URLs in memory; it does not
  provide authentication for other services. Signed links expire.
- Sentinel-2 L1C requester-pays `s3://` JP2 assets are not supported by this HTTP(S)
  downloader. Protected USGS assets may require USGS EROS login or requester-pays
  AWS access. These dialogs do not add USGS login, AWS credentials or automatic
  access to protected images. A metadata search can succeed while image access
  remains unavailable. Unexpected HTML login pages are rejected as data files.
- Downloading preserves the asset; it does not apply pixel QA, cloud masks,
  reflectance scaling or TOA/SR conversion. Prepare science-ready input bands
  before running an index. For Landsat raw Level-1 conversion, use the
  [advanced TOA workflow](usage.md#convert-landsat-level-1-dn-to-toa-reflectance).

## Raster band order and interpretation

| Index | Band A | Band B | Purpose |
| --- | --- | --- | --- |
| NDVI | NIR | Red | Vegetation contrast |
| NDWI (McFeeters) | Green | NIR | Open-water contrast |
| NBR | NIR | SWIR2 | Burn-sensitive contrast |

Each index is `(A - B) / (A + B)`. Select **single-band, co-registered rasters**
with matching shape, transform and CRS. The raster engine applies embedded
scale/offset metadata. Ensure it matches the provider's calibration, or prepare
reflectance rasters with identity scale/offset to avoid applying calibration twice.
An additive offset does not cancel in a normalized difference. The tools do not reproject, resample or
apply scene-specific pixel QA/cloud masks. Cloud cover in the search tool is a
scene-level metadata filter. Use the provider's pixel QA for scientific analysis.

Input nodata and zero-denominator pixels are excluded by the core raster tool.
Add the output GeoTIFF to the map and set a suitable color ramp; a successful
index calculation does not establish vegetation health, flood extent or burn
severity without suitable observations and interpretation.

## Limits and troubleshooting

- Split areas that cross the antimeridian into two searches. An envelope of a
  projected extent may cover a larger area than its original polygon.
- Long provider calls are bounded by the SDK's request timeout. Search checks
  cancellation around provider requests; it does not interrupt an in-flight HTTP
  request. Downloads check cancellation during streaming as described above.
  Raster calculations finish their current operation.
- Empty results can mean missing archive coverage, dates outside the catalog,
  a restrictive cloud threshold, or a valid area with no scenes. Check
  [source coverage and access](sources.md) before increasing the limit.
- A Python import error normally means the package was installed into a different
  interpreter. Check the active GIS interpreter rather than modifying plugin code
  with a workspace-specific `sys.path`.
- Raster dependency conflicts must be resolved against the desktop GIS's supported
  versions. A standard CLI virtual environment is useful for raster processing
  when the desktop environment cannot accommodate compatible Rasterio packages.
