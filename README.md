# Universal Satellite

Find historical and recent satellite scenes, download image bands, and calculate vegetation, water and burn-sensitive indices. Use the command line, **QGIS Processing tools**, or an **ArcGIS Pro Python toolbox**.

## 1. Which data should I use?

### Searchable with these tools

These 13 collections have search adapters. Dates below describe approximate record eras; actual coverage and the latest available scenes depend on the provider.

| Data source / dataset ID | Record era | Useful for |
| --- | --- | --- |
| Landsat Level-1 — `landsat-c2-l1` | From 1972; sensor-dependent | Raw DN for custom processing; reflective bands need MTL-based TOA calibration |
| Landsat US ARD TOA — `landsat-c2-ard-toa` | From 1982; regional US coverage | TOA reflectance for algorithms designed for TOA; not global coverage |
| Landsat 4–9 SR — `landsat-c2-l2` | From 1982 | Surface reflectance for land, vegetation and urban change; available surface-temperature products |
| Sentinel-2 TOA — `sentinel-2-l1c` | From 2015; coverage varies | Level-1C top-of-atmosphere reflectance for TOA-based algorithms and custom atmospheric processing |
| Sentinel-2 SR — `sentinel-2-l2a` | Mission from 2015; L2A coverage varies | Level-2A surface reflectance for crop, vegetation, water and land mapping |
| Sentinel-1 GRD / RTC — `sentinel-1-grd`, `sentinel-1-rtc` | Mission from 2014; catalog coverage varies | Radar observations through cloud; inputs for flood and water analysis |
| Copernicus DEM — `cop-dem-glo-30` | Mainly 2011–2015 acquisitions | Elevation and surface shape; inputs for slope and terrain analysis |
| NASADEM — `nasadem` | February 2000 acquisitions | Elevation and terrain analysis |
| ESA WorldCover — `esa-worldcover` | 2020 and 2021 | Land-cover classes: trees, crops, water and built-up land |
| JRC Surface Water — `jrc-gsw` | Listed release: 1984–2021 | Historical water occurrence, seasonality and persistence |
| MODIS reflectance / vegetation — `modis-surface-reflectance`, `modis-vegetation` | From 2000; ingestion varies | Regional reflectance and vegetation trends using 8-day / 16-day composites |

Copernicus DEM, NASADEM and JRC water return **static spatial inventories**: the tools ignore your date filter for these sources and say so in the output. WorldCover keeps annual date filtering. Public search results can still contain assets that need a provider account or temporary signed link.

**TOA or SR?** Choose TOA for methods designed for top-of-atmosphere observations, atmospheric studies or your own atmospheric correction. Choose SR for many comparisons of surface vegetation and land across dates. They represent different quantities: do not mix TOA and SR inputs. Sentinel-2 L1C contains encoded TOA reflectance; apply its actual scale/offset. Landsat Level-1 contains DN and needs calibration before use as TOA reflectance.

### Historical weather

**ERA5 (`era5`): from 1940, with publication lag.** Use the separate `weather` command for selected hourly temperature, rain, humidity, wind and reference evapotranspiration through Open-Meteo. ERA5 is model reanalysis, not satellite imagery; the full gridded archive is not implemented here.

### Other sources included as references

These 10 entries provide links and notes for separate retrieval/processing workflows. They do not have dedicated adapters. Historical MSS scenes may also appear in the generic Landsat Level-1 search, but MSS calibration is not supported by the current converter.

| Source | Record era | Useful for |
| --- | --- | --- |
| CORONA | 1960–1972 | Historical landscapes; photographs need georeferencing |
| Landsat MSS | 1972–2013 | Early land-change studies; separate processing required |
| CHIRPS | From 1981, product-dependent | Rainfall variability, drought and seasonal rain |
| AVHRR records | From 1981, product-dependent | Long-term regional vegetation and climate studies |
| SMAP | From 2015 | Soil moisture and drought studies |
| EMIT | From 2022 | Hyperspectral studies of minerals and surface composition |
| VIIRS / Black Marble | From 2012 | Nighttime lighting and settlement activity |
| FIRMS | MODIS from 2000; VIIRS from 2012 | Active-fire hotspots, rather than burned-area maps |
| Sentinel-5P | Products from 2018 | Atmospheric trace gases and air-quality studies |
| Sentinel-3 | From 2016 | Ocean colour and land/sea surface temperature |

See [all source details, resolutions and provider links](docs/sources.md).

## 2. Install in QGIS or ArcGIS Pro

Requires Python 3.10 or newer. **Install the core package into the Python environment used by your GIS.** Installing into an unrelated terminal environment will not make it available in the desktop application.

### QGIS 3.28 or newer

1. In the QGIS/OSGeo4W shell (or your distribution's QGIS Python environment), install the downloaded repository. Replace the example path:

   ```text
   python -m pip install "C:\path\to\Universal-Satellite"
   ```

2. Use the included [QGIS plugin ZIP](gis/qgis/universal_satellite_qgis.zip), or rebuild it from the repository folder:

   ```text
   python tools/package_qgis.py --force
   ```

3. In QGIS, open **Plugins → Manage and Install Plugins → Install from ZIP** and select the included ZIP (or rebuilt `dist/universal_satellite_qgis.zip`). Enable **Universal Satellite Processing**.
4. Open the **Processing Toolbox → Universal Satellite**. You should see scene-search and raster-index tools.

### ArcGIS Pro

1. Clone and activate your ArcGIS Pro Python environment in Package Manager. Open its Python Command Prompt and install the repository:

   ```text
   python -m pip install "C:\path\to\Universal-Satellite"
   ```

2. Open **Catalog → Toolboxes → Add Toolbox** and select [`gis/arcgis/UniversalSatellite.pyt`](gis/arcgis/UniversalSatellite.pyt).
3. Open the **Universal Satellite** toolbox to find scene-search and raster-index tools. ArcMap/Python 2 is not supported.

For raster indices, the GIS Python environment also needs compatible **NumPy and Rasterio** packages. Follow the [full GIS installation guide](docs/gis.md) for the optional raster extra and dependency guidance.

## 3. Run your first search

In either GIS, open **Search satellite scenes (GeoJSON manifest)** and use:

| Input | Example |
| --- | --- |
| Dataset | Sentinel-2 Level-2A / `sentinel-2-l2a` |
| Area | A small area around Dhaka: west 90.2, south 23.6, east 90.5, north 23.9 |
| Coordinate system | WGS84 / EPSG:4326; specify the actual CRS if using projected map coordinates |
| Start / end | `2024-01-01` / `2024-03-31` |
| Maximum cloud cover | `20` percent |
| Maximum scenes | `5` |
| Output | A file named `scenes.geojson`, outside a geodatabase |

For **TOA**, select **Sentinel-2 Level-1C TOA reflectance / `sentinel-2-l1c`** with the same area and dates. TOA and SR remain separate dataset choices in both toolboxes.

Draw the area in the extent control; do not paste the SDK bbox order into QGIS's extent text field. The [GIS guide](docs/gis.md) explains the different coordinate orders.

Run the tool. In QGIS, add the GeoJSON as a vector layer. In ArcGIS Pro, use **JSON To Features** with geometry type **Polygon** to create a footprint feature class.

**The result shows scene footprints and image links, not the satellite pixels.** Keep the original GeoJSON for downloading. The tool does not automatically make flood maps, classify land cover or calculate terrain derivatives.

## 4. Download imagery and calculate an index

For a separate command-line environment, open a terminal in the repository folder:

```text
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or `source .venv/bin/activate` on Linux/macOS, then run:

```text
python -m pip install -e ".[raster]"
universal-satellite summary scenes.geojson
universal-satellite download scenes.geojson --asset red --output downloads
universal-satellite download scenes.geojson --asset nir --output downloads
```

These band keys are for the Sentinel-2 example; inspect the manifest for other collections. For Planetary Computer assets, add `--sign-planetary` when a temporary signed URL is needed. Add downloaded GeoTIFFs to your GIS as raster layers.

Sentinel-2 L1C currently returns requester-pays `s3://` JP2 assets: retrieve them with a provider-supported AWS workflow; this downloader supports HTTP(S) only. USGS Landsat bands/MTL may require **USGS EROS** login or requester-pays AWS access. A successful metadata search does not grant image access.

After retrieving a supported Landsat Level-1 reflective band and its matching MTL JSON, create a calibrated TOA GeoTIFF:

```text
universal-satellite toa --input B4.TIF --mtl MTL.json --band 4 --output red-toa.tif
```

This uses the MTL reflectance coefficients and scene-center solar elevation for Landsat 4/5/7/8/9 reflective bands. It does not perform atmospheric correction. MSS and thermal conversion are not implemented. Do not apply it to SR or already-calibrated ARD TOA products. See the [TOA workflow](docs/usage.md#choose-toa-or-surface-reflectance) for details.

To run the desktop **Compute normalized-difference raster index** tool:

| Index | Band A | Band B | Useful for |
| --- | --- | --- | --- |
| NDVI | NIR | Red | Vegetation contrast |
| NDWI | Green | NIR | Open-water contrast |
| NBR | NIR | SWIR2 | Burn-sensitive vegetation contrast |

Choose two bands from the **same acquisition**, with matching CRS, dimensions and pixel grid. Apply pixel QA/cloud masks first and check reflectance scaling. The tool applies embedded scale/offset tags but does not infer missing calibration from STAC metadata. Save to a new `.tif` file, then add it to the map. The CLI also supports MNDWI, NDMI and EVI.

For historical weather:

```text
universal-satellite weather --latitude 23.8 --longitude 90.4 --start 1981-01-01 --end 1981-01-03 --output weather.json
```

See the [CLI and Python examples](docs/usage.md) for searching from a terminal and additional options.

## 5. Screenshots and checking your installation

You can capture real screenshots after installing the toolboxes. Follow the [screenshot walkthrough](docs/screenshots.md) to show a completed search, scene footprints and an optional index map, with the dataset and dates visible.

No native QGIS or ArcGIS screenshots are included yet. Their adapter contracts are tested, and live metadata searches for the new TOA collections have succeeded. Native desktop testing and provider-authenticated imagery downloads remain pending. See [development and validation notes](docs/development.md).
