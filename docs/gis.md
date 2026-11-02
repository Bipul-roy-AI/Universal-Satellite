# QGIS and ArcGIS Pro toolboxes

Both integrations use the same Python SDK as the CLI. They provide **Search scenes**
and **Raster index** tools. Search returns a GeoJSON manifest containing scene
footprints, metadata and asset URLs. It does not download or mosaic imagery.
Raster index reads two local, single-band GeoTIFFs and writes NDVI, NDWI or NBR.

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

2. Open **Settings → User Profiles → Open Active Profile Folder**. Copy the whole
   `gis/qgis/universal_satellite_qgis` directory to that profile's
   `python/plugins/` directory. Keep the `universal_satellite_qgis` folder
   name. Alternatively, from the repository root run:

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
5. Add the saved GeoJSON through **Layer → Add Layer → Add Vector Layer** to inspect
   footprints. The manifest retains the original `assets` map for downloading:

   ```bash
   universal-satellite download scenes.geojson --asset red --output downloads
   ```

   Check the actual asset keys in the manifest; they vary between collections.
   Add downloaded GeoTIFFs with **Add Raster Layer**.

The tool IDs are `universal_satellite:search_scenes` and
`universal_satellite:raster_index`, so they also work in Processing models and
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
2. From **Catalog → Toolboxes → Add Toolbox**, select
   `gis/arcgis/UniversalSatellite.pyt`.
3. Open **Search satellite scenes (GeoJSON manifest)**. Select a dataset ID,
   provide an extent and explicitly set its input coordinate system. The default
   is EPSG:4326: change it when using map coordinates from a projected CRS. Enter
   dates as `YYYY-MM-DD`, set the maximum scene count, and choose a `.geojson`
   destination outside a geodatabase.
4. To convert footprints into an ArcGIS feature class, use **JSON To Features**
   with the GeoJSON as input and Polygon as the geometry type. The full nested
   STAC asset metadata remains in the original manifest; field conversion can
   flatten or omit nested objects. Keep that manifest for the CLI downloader.
5. Download selected assets with the CLI and add the GeoTIFFs to the map. Run
   **Compute normalized-difference raster index** on local prepared bands.

Search uses ordinary network access from the desktop. Configure your institution's
proxy/trust settings in that Python environment if needed. Public metadata access
does not imply unrestricted asset downloads: some providers require authentication
or signed asset URLs, and signed URLs expire.

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
- Long provider calls are bounded by the SDK's request timeout. The QGIS search
  checks cancellation before and after a request; it does not interrupt an
  in-flight HTTP request. Raster calculations finish their current operation.
- Empty results can mean missing archive coverage, dates outside the catalog,
  a restrictive cloud threshold, or a valid area with no scenes. Check
  [source coverage and access](sources.md) before increasing the limit.
- A Python import error normally means the package was installed into a different
  interpreter. Check the active GIS interpreter rather than modifying plugin code
  with a workspace-specific `sys.path`.
- Raster dependency conflicts must be resolved against the desktop GIS's supported
  versions. A standard CLI virtual environment is useful for raster processing
  when the desktop environment cannot accommodate compatible Rasterio packages.
