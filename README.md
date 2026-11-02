# Universal Satellite

Find historical and recent satellite scenes, download image bands, and calculate vegetation, water and burn-sensitive indices. Use the command line, **QGIS Processing tools**, or an **ArcGIS Pro Python toolbox**.

## 1. Which data should I use?

### Searchable with these tools

These 13 collections have search adapters and appear as named choices with their dataset IDs in both toolboxes. The bundled menus remain visible without the core SDK; running a search still requires it. Dates below describe approximate record eras; actual coverage and the latest available scenes depend on the provider.

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

| Download | How to open it |
| --- | --- |
| [QGIS plugin ZIP](https://github.com/Bipul-roy-AI/Universal-Satellite/raw/refs/heads/main/gis/qgis/universal_satellite_qgis.zip) | QGIS → Plugins → Manage and Install Plugins → Install from ZIP |
| [ArcGIS Pro toolbox ZIP](https://github.com/Bipul-roy-AI/Universal-Satellite/raw/refs/heads/main/gis/arcgis/universal_satellite_arcgis.zip) | Extract ZIP → Catalog → Toolboxes → Add Toolbox → `UniversalSatellite.pyt` |

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
4. Open the **Processing Toolbox → Universal Satellite**. You should see scene-search, image-download and raster-index tools.

### ArcGIS Pro

1. Clone and activate your ArcGIS Pro Python environment in Package Manager. Open its Python Command Prompt and install the repository:

   ```text
   python -m pip install "C:\path\to\Universal-Satellite"
   ```

2. Extract the **ArcGIS Pro toolbox ZIP** from the download table. Open **Catalog → Toolboxes → Add Toolbox** and select `UniversalSatellite/UniversalSatellite.pyt` from the extracted folder. The source [`gis/arcgis/UniversalSatellite.pyt`](gis/arcgis/UniversalSatellite.pyt) can also be added directly.
3. Open the **Universal Satellite** toolbox to find scene-search, image-download and raster-index tools. ArcMap/Python 2 is not supported.

For raster indices, the GIS Python environment also needs compatible **NumPy and Rasterio** packages. Follow the [full GIS installation guide](docs/gis.md) for the optional raster extra and dependency guidance.

**Updating an existing installation:** install the new adapter ZIP and upgrade the core SDK once in the GIS Python environment with `python -m pip install --upgrade "C:\path\to\Universal-Satellite"`, using your updated local repository path. Restart the GIS afterward. You do not need terminal commands for each download.

Both ZIPs contain the GIS adapter, not the core SDK or a GIS runtime. To rebuild the ArcGIS ZIP from source, run `python tools/package_arcgis.py --force`; the rebuilt file is written to `dist/universal_satellite_arcgis.zip`.

## 3. Download imagery directly in QGIS or ArcGIS Pro

1. Open **Search satellite scenes (GeoJSON manifest)** and set your search inputs.
2. Check **Download images after search**. It is off by default, so an ordinary search only saves scene footprints and asset links.
3. Enter the exact **Asset keys** you want, separated by commas. For Sentinel-2 L2A, start with `red,nir`; Landsat commonly uses `red,nir08`. Other products use different keys: check the scene manifest. Every returned scene is processed for every requested key, so keep the scene limit small while testing.
4. Choose an **Image output folder** on your computer. Enable **Sign Planetary Computer Azure asset URLs** when those assets need temporary signed links. Leave overwrite off to preserve existing files.
5. Run the tool. The GIS Processing/geoprocessing job reports download progress and errors; use its **Cancel** control if needed. Completed downloads remain in your chosen folder; an interrupted file's temporary `.part` is removed. These jobs use the GIS application's normal background-processing controls; native desktop behavior still needs verification.

**Already have a search result?** Open **Download satellite image assets**, choose the original **Scene manifest (.geojson)**, enter asset keys and choose your output folder. Run it directly in the GIS—no separate download command or terminal environment is needed. Keep the original manifest because converting footprints to a feature class can lose their nested asset metadata.

Downloads can be large. Individual asset failures are reported and the remaining assets are attempted; partial success produces warnings. If every attempted download fails, the job reports an error. The tool supports public or already authorized **HTTP(S)** assets and optional Planetary Computer signing. It does not supply USGS login or requester-pays AWS access: Sentinel-2 L1C `s3://` JP2 assets and protected USGS Landsat assets still need a separate provider-supported retrieval route. A metadata search does not grant image access.

### Display the images and calculate an index

Add downloaded GeoTIFFs to your map using **Add Raster Layer** in QGIS or **Add Data** in ArcGIS Pro. Then open **Compute normalized-difference raster index**:

| Index | Band A | Band B | Useful for |
| --- | --- | --- | --- |
| NDVI | NIR | Red | Vegetation contrast |
| NDWI | Green | NIR | Open-water contrast |
| NBR | NIR | SWIR2 | Burn-sensitive vegetation contrast |

Choose two bands from the **same acquisition**, with matching CRS, dimensions and pixel grid. Apply pixel QA/cloud masks first and check reflectance scaling. The tool applies embedded scale/offset tags but does not infer missing calibration from STAC metadata. Save to a new `.tif` file, then add it to the map.

Landsat Level-1 DN needs calibration before it can be treated as TOA reflectance; downloading does not perform that calibration or atmospheric correction. See the [advanced TOA, CLI and Python workflows](docs/usage.md#choose-toa-or-surface-reflectance), including historical weather and additional indices.

## 4. Screenshots and checking your installation

You can capture real screenshots after installing the toolboxes. Follow the [screenshot walkthrough](docs/screenshots.md) to show a completed search, scene footprints, an optional download folder/result and an index map, with the dataset and dates visible.

No native QGIS or ArcGIS screenshots are included yet. Their adapter contracts are tested, and live metadata searches for the new TOA collections have succeeded. Native desktop testing and provider-authenticated imagery downloads remain pending. See [development and validation notes](docs/development.md).
