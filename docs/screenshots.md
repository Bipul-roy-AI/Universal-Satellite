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
footprints and asset links, **not downloaded satellite pixels**. Cloud cover is a
scene metadata filter, not a pixel cloud mask. Reference-only sources listed in
the data catalog do not appear in the toolboxes' searchable-dataset dropdowns.

## QGIS screenshot

1. Enable **Universal Satellite Processing**, then open **Processing Toolbox →
   Universal Satellite → Search satellite scenes (GeoJSON manifest)**.
2. Select the dataset and enter the settings above. For the QGIS extent widget or
   Processing console, the same area is
   `90.2,90.5,23.6,23.9 [EPSG:4326]`: QGIS uses **xmin, xmax, ymin, ymax**.
   Ensure the extent CRS is WGS84, even if the map uses a different CRS.
3. Save to a new file such as `dhaka-qgis-scenes.geojson` and run. In the tool's
   log, check the actual message `Wrote N scene footprints. Raster assets were
   not downloaded.` A completed run with `N > 0` is needed for a successful
   search screenshot.
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
2. Set **Dataset ID** to `sentinel-2-l2a`. Enter the area as XMin `90.2`, YMin
   `23.6`, XMax `90.5`, YMax `23.9`. Explicitly set **Coordinate system of input
   extent** to **GCS WGS 1984 / EPSG:4326**. Enter the dates, cloud threshold and
   maximum scene count from the table above.
3. Choose a new `.geojson` file outside a geodatabase, for example
   `dhaka-arcgis-scenes.geojson`, and run. Inspect the Geoprocessing messages for
   `Wrote N scene footprints to ...` and verify `N > 0`.
4. Run ArcGIS Pro's **JSON To Features** on that GeoJSON. Choose **Polygon** as
   the geometry type and save the feature class in a geodatabase. Add it to the
   map, zoom to it, and compare its attribute-table count with `N`. Keep the
   original GeoJSON: conversion can omit nested STAC asset metadata.
5. Arrange the map, resulting layer and Geoprocessing History details to show the
   inputs and successful messages. Capture the application window as
   `docs/images/arcgis-search.png`. Retain a separate parameter capture or record
   the inputs in the caption if the full tool panel does not fit.

## Optional NDVI screenshot

After a search, download appropriate red and NIR assets and prepare **aligned,
single-band reflectance GeoTIFFs** with matching grid, CRS and valid calibration.
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
count**. For example, fill in this template using observed values:

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
