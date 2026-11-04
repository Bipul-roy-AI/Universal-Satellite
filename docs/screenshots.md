> Version note: this page describes the original 0.2 workflows. For the 0.3 feature set, expanded menus and current limitations, use [README](../README.md), [indices](indices.md), [downloads](downloads.md) and [providers](providers.md).

# Verify the desktop tools and capture screenshots

Native QGIS and ArcGIS Pro testing is **pending**. This environment has not run
either desktop application, so this guide contains no screenshots presented as
working evidence. Follow [GIS installation](gis.md) first, including installation
of the core package in the Python environment used by your GIS.

Use this small, repeatable search around Dhaka in both applications:

| Setting | Value |
| --- | --- |
| Dataset | Sentinel-2 L2A (`sentinel-2-l2a`) |
| Area in WGS84 / EPSG:4326 | West `90.2`, south `23.6`, east `90.5`, north `23.9` |
| Start date | `2024-01-01` |
| End date | `2024-03-31` |
| Maximum scene cloud cover | `20` percent |
| Maximum number of scenes | `5` |

Five is the requested limit, not a guaranteed result count. Search returns scene
footprints and asset links by default. Leave **Download images after search**
unchecked for these first search-only captures; enable it separately in the
optional download walkthrough below. Cloud cover is a scene metadata filter, not a pixel cloud mask. Reference-only sources listed in
the data catalog do not appear in the toolboxes' searchable-dataset dropdowns.

## QGIS screenshot

1. Enable **Universal Satellite Processing**, then open **Processing Toolbox →
   Universal Satellite → Search satellite scenes (GeoJSON manifest)**.
2. Select the dataset and enter the settings above. For the QGIS extent widget or
   Processing console, the same area is
   `90.2,90.5,23.6,23.9 [EPSG:4326]`: QGIS uses **xmin, xmax, ymin, ymax**.
   Ensure the extent CRS is WGS84, even if the map uses a different CRS.
3. Save to a new file such as `dhaka-qgis-scenes.geojson`, leave downloads
   disabled and run. Check the actual footprint count and completion message in
   the Processing log. A completed run with `N > 0` is needed for a successful
   search screenshot; this does not establish imagery downloads.
4. Add the saved GeoJSON using **Layer → Add Layer → Add Vector Layer**. Zoom to
   the layer and confirm features appear in the attribute table. Overlapping
   acquisition footprints can cover each other; the number of visible outlines
   need not equal the feature count. Use an unfilled polygon style to see them.
5. Arrange the map, layer list and tool dialog/history so the actual footprints,
   inputs and completion message are visible. Capture the application window and
   save it as `docs/images/qgis-search.png`. Create `docs/images/` if necessary.
   If one frame cannot show all inputs, retain a separate parameters capture or
   copy the exact inputs into its caption.

## ArcGIS Pro screenshot

1. Add `gis/arcgis/UniversalSatellite.pyt` to Catalog, then open **Universal
   Satellite → Search satellite scenes (GeoJSON manifest)**.
2. Choose the named **Sentinel-2 SR / Level-2A** source with dataset ID
   `sentinel-2-l2a` in brackets. Enter the area as XMin `90.2`, YMin
   `23.6`, XMax `90.5`, YMax `23.9`. Explicitly set **Coordinate system of input
   extent** to **GCS WGS 1984 / EPSG:4326**. Enter the dates, cloud threshold and
   maximum scene count from the table above.
3. Choose a new `.geojson` file outside a geodatabase, for example
   `dhaka-arcgis-scenes.geojson`, leave downloads disabled and run. Inspect the
   Geoprocessing messages for
   `Wrote N scene footprints to ...` and verify `N > 0`.
4. Run ArcGIS Pro's **JSON To Features** on that GeoJSON. Choose **Polygon** as
   the geometry type and save the feature class in a geodatabase. Add it to the
   map, zoom to it, and compare its attribute-table count with `N`. Keep the
   original GeoJSON: conversion can omit nested STAC asset metadata.
5. Arrange the map, resulting layer and Geoprocessing History details to show the
   inputs and successful messages. Capture the application window as
   `docs/images/arcgis-search.png`. Retain a separate parameter capture or record
   the inputs in the caption if the full tool panel does not fit.

## Optional direct-download screenshots

These steps exercise actual GUI downloads rather than terminal commands. Use
public HTTP(S) Sentinel-2 L2A assets for a small first check; this is different
from Sentinel-2 L1C requester-pays S3 assets or protected USGS downloads.

1. Open **Search satellite scenes (GeoJSON manifest)** in either GIS. Reuse the
   small area/dates above, reduce the maximum scene count to **1**, and choose a
   new manifest file. Enable **Download images after search**, set **Asset keys**
   to `red,nir`, and choose a new **Image output folder**, for example a
   `UniversalSatellite/dhaka-images` folder under your Documents directory.
   Leave overwrite off. These are exact asset keys, not file paths.
2. Capture the parameter panel showing the enabled checkbox, asset keys, scene
   limit and your selected folder. Save an actual capture as
   `docs/images/qgis-download-panel.png` or
   `docs/images/arcgis-download-panel.png`. A panel capture alone documents inputs,
   not a successful download.
3. Run the Processing/geoprocessing job. Inspect progress, successful file counts
   and warnings. Open the chosen folder and verify that completed image files
   exist and can be opened as rasters. Capture the job's real completion messages
   alongside the resulting folder or loaded raster, using
   `docs/images/qgis-download-results.png` or
   `docs/images/arcgis-download-results.png`. Show actual generated filenames;
   do not rename an empty placeholder to look like a downloaded scene.
4. To check downloading an existing result instead, open **Download satellite
   image assets** and choose that original one-scene GeoJSON, asset keys and a
   different output folder. Capture its inputs and observed result. This tests
   the separate GUI tool without rerunning search or using a CLI download.

If testing Planetary Computer assets, record whether its signing checkbox was
enabled; omit the generated signed URLs from captures. Record partial failures,
existing files skipped/preserved and cancellation as such. Cancellation preserves
completed downloads and removes an interrupted temporary `.part` file; it does
not undo previously completed files. Native timing and background behavior still
need to be checked in each desktop application.

An all-failed job, an HTML login response or an empty folder is not a successful
imagery download. Keep the exact observed errors and provider/access requirements.
Downloading also does not apply cloud masks, scale reflectance or convert raw
Landsat DN into TOA/SR data; those preparations are separate from this screenshot.

## Optional NDVI screenshot

After downloading through either GUI workflow, prepare appropriate red and NIR
assets as **aligned, single-band reflectance GeoTIFFs** with matching grid, CRS and valid calibration.
Use the provider's pixel QA to mask invalid or cloudy observations; apply scale
and offset correctly. The raster engine applies embedded scale/offset metadata,
so do not also apply it manually without resetting the metadata to identity.

In QGIS, run **Compute normalized-difference raster index**, select **NDVI: A =
NIR, B = red**, choose the prepared local rasters and write a new `.tif`. Add the
output to the map and display a labeled color ramp. Capture the input filenames,
successful output and map as `docs/images/qgis-ndvi.png`. Describe the actual
acquisition date, calibration and QA preparation in the caption. A synthetic
raster demonstration should be labeled synthetic and cannot validate provider
imagery retrieval.

## Captions and failed runs

For each real screenshot, record the app version, run date, map CRS, input extent
CRS, dataset ID, date range, cloud threshold, requested limit and **actual returned
count**. For download captures also record the exact asset keys, selected folder,
signing/overwrite settings, completed/failed counts and actual output files.
For example, fill in this template using observed values:

> QGIS [version], run [date]. Dataset sentinel-2-l2a; WGS84 bbox
> [90.2, 23.6, 90.5, 23.9]; dates 2024-01-01 to 2024-03-31; cloud ≤20%;
> limit 5; returned [actual N] footprints; map CRS [actual CRS].

Exclude credentials, tokens and signed asset URLs from captures and captions.
Add image embeds to the README or documentation **only after the corresponding
image files exist**, with a caption that identifies the tested application.

If the package cannot be imported, check the GIS's active Python environment
against [installation instructions](gis.md). For provider or network errors, keep
the exact error and confirm desktop HTTPS/proxy access; a running tool dialog does
not establish a successful search. For zero results, verify the extent order and
CRS, then try a wider date range or higher cloud threshold. Record any changed
inputs, rerun and inspect the new output. Do not label a failed or empty run as a
working imagery search.
