# Data sources: historical records through recent acquisitions

Universal Satellite is a search and processing client, not a mirror of every Earth observation archive. This directory identifies **13 searchable STAC collections** and **11 reference sources**. Reference entries describe useful archives and link to their providers; they have no dedicated STAC adapter here. The generic Landsat Level-1 collection may expose historical MSS scenes, but the separate MSS entry remains a reference to its specialist retrieval/processing workflow. ERA5 additionally has a separate weather time-series adapter through Open-Meteo, described below. Other reference sources have no implemented adapter.

`start` and `end` describe indicative mission/product record years, or acquisition periods for static products. January 1 and December 31 often serve as year anchors; they are **not verified first/last scene dates**. Actual catalog coverage varies by place, processing level, product version and ingestion history. A missing `end` means that no fixed ending is asserted; it does not mean the feed is operational or up to date. Search your own area and dates to establish availability. The catalog is a curated starting point, not an exhaustive inventory.

The historical timeline includes ERA5 reanalysis from 1940, declassified photographs from the 1960s, Landsat MSS from 1972, Landsat surface-reflectance products from the 1980s, MODIS from 2000 and recent Sentinel missions. ERA5 is a model/data-assimilation record, not satellite imagery; these records cannot be treated as equivalent observations.

## Searchable collections

Searchable means an adapter is implemented against the published collection identifier. It does not imply a successful live check in every execution environment. Collection identifiers were cross-checked against the provider-maintained [Earth Search documentation](https://github.com/Element84/earth-search#collections), [Planetary Computer examples](https://github.com/microsoft/PlanetaryComputerExamples/tree/main/datasets) and [USGS Landsat STAC collections](https://landsatlook.usgs.gov/stac-server/collections). Provider availability, endpoint versions, authentication and asset URLs can change.

| Local dataset ID | Indicative record | Resolution / interval | Provider collection |
| --- | --- | --- | --- |
| `landsat-c2-l1` | 1972–open-ended; check catalog | Sensor-dependent; 15 / 30 / 60–80 m and thermal grids | [`landsat-c2l1`](https://landsatlook.usgs.gov/stac-server/collections/landsat-c2l1) — calibrated Level-1 DN, not ready-to-use reflectance |
| `landsat-c2-ard-toa` | 1982–open-ended; US ARD coverage | 30 m TOA reflectance tiles | [`landsat-c2ard-ta`](https://landsatlook.usgs.gov/stac-server/collections/landsat-c2ard-ta) |
| `landsat-c2-l2` | 1982–open-ended; check catalog | 30 m reflectance; thermal varies | [`landsat-c2-l2`](https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2) (Planetary Computer) |
| `sentinel-2-l1c` | 2015–open-ended; check catalog | 10 / 20 / 60 m; JP2 assets | [`sentinel-2-l1c`](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l1c) — scaled TOA reflectance |
| `sentinel-2-l2a` | 2015–open-ended; check catalog | 10 / 20 / 60 m | [`sentinel-2-l2a`](https://github.com/Element84/earth-search/blob/main/docs/collections/sentinel-2-l2a.md) |
| `sentinel-1-grd` | 2014–open-ended; check catalog | Mode-dependent; commonly 10 m pixel spacing | [`sentinel-1-grd`](https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-grd) (Planetary Computer) |
| `sentinel-1-rtc` | 2014–open-ended; check catalog | 10 m pixel spacing | [`sentinel-1-rtc`](https://github.com/microsoft/PlanetaryComputerExamples/tree/main/datasets/sentinel-1-rtc) |
| `cop-dem-glo-30` | 2011–2015 | 1 arc-second (about 30 m) | [`cop-dem-glo-30`](https://planetarycomputer.microsoft.com/api/stac/v1/collections/cop-dem-glo-30) (Planetary Computer) |
| `nasadem` | 2000–2000 | 1 arc-second (about 30 m) | [`nasadem`](https://github.com/microsoft/PlanetaryComputerExamples/tree/main/datasets/nasadem) |
| `esa-worldcover` | 2020–2021 | 10 m | [`esa-worldcover`](https://github.com/microsoft/PlanetaryComputerExamples/tree/main/datasets/esa-worldcover) |
| `jrc-gsw` | 1984–2021 | 30 m | [`jrc-gsw`](https://github.com/microsoft/PlanetaryComputerExamples/tree/main/datasets/jrc-gsw) |
| `modis-surface-reflectance` | 2000–open-ended; check catalog | 500 m; 8-day composites | [`modis-09A1-061`](https://github.com/microsoft/PlanetaryComputerExamples/blob/main/datasets/modis/modis-imagery-example.ipynb) |
| `modis-vegetation` | 2000–open-ended; check catalog | 500 m; 16-day composites | [`modis-13A1-061`](https://github.com/microsoft/PlanetaryComputerExamples/blob/main/datasets/modis/modis-vegetation-example.ipynb) |

Earth Search endpoint: `https://earth-search.aws.element84.com/v1`. Planetary Computer endpoint: `https://planetarycomputer.microsoft.com/api/stac/v1`. USGS endpoint: `https://landsatlook.usgs.gov/stac-server`.

- Public metadata does not guarantee anonymous download. USGS Landsat asset URLs may redirect to the USGS EROS/EarthExplorer login service (`ers.cr.usgs.gov`), even with a final HTTP 200 response; that HTML page is not imagery or MTL metadata. Alternate USGS S3 assets may be requester-pays. This is distinct from NASA Earthdata login. Some older asset links can also be stale. Inspect asset `href`, roles and media type before downloading.
- Sentinel-2 Level-1C band assets observed in Earth Search use requester-pays `s3://` JP2 URLs. The current downloader accepts HTTP(S), not native S3, and does not invent an HTTPS replacement. Use a provider-supported AWS retrieval workflow and any required requester-pays credentials. Public scene search does not make this a no-credentials imagery download.
- Planetary Computer Azure assets commonly require short-lived signed URLs (SAS). Pass `--sign-planetary` to the download command to sign supported Azure assets in memory. Preserve the original metadata and refresh signing near download time; never commit signed URLs or provider tokens to a public repository.
- Static sources `cop-dem-glo-30`, `nasadem` and `jrc-gsw` are **spatial-only inventories** (`temporal: false` in the catalog). Search requires a valid start/end pair for a consistent interface, but deliberately omits the STAC `datetime` filter for these three sources: requested dates do not select a DEM acquisition or a water-map year. Their catalog dates describe acquisition/record eras rather than actual STAC timestamps. The output records `temporal_filter_applied: false`, the `requested_dates` and an explanatory note under `universal_satellite`. ESA WorldCover retains date filtering because its 2020/2021 maps are separate annual products.
- `eo:cloud_cover` filters are supported for optical collections that expose the property. Items with missing cloud-cover metadata are excluded when a cloud filter is requested. Cloud cover is not a radar-quality filter and does not replace pixel cloud masks.
- Search limits cap returned results. They do not establish a complete archive inventory; split a large analysis into explicit spatial/temporal queries and retain the query metadata.

## TOA, surface reflectance and raw Level-1 data

| Source | What the band values mean | Preparation before an index |
| --- | --- | --- |
| Sentinel-2 L1C | Scaled top-of-atmosphere (TOA) reflectance | Apply the actual asset/baseline scale and offset; align band grids and apply QA. Do not assume every baseline is simply DN / 10000. |
| Sentinel-2 L2A | Scaled bottom-of-atmosphere / surface reflectance (SR) | Apply the actual product scale/offset and pixel QA. |
| Landsat C2 Level-1 | Calibrated digital numbers (DN) | Convert reflective bands with the matching MTL coefficients and solar angle before treating them as TOA reflectance. Thermal bands require a different conversion. |
| Landsat C2 ARD TA | Provider-produced, scaled TOA reflectance | Use product calibration/QA; regional US ARD tile coverage, not a substitute for global Level-1 scenes. |
| Landsat C2 Level-2 | Scaled surface reflectance and, where available, surface temperature | Apply each product's scale/offset and QA; temperature is not reflectance. |

TOA describes radiation above the atmosphere. SR includes atmospheric correction and is generally the better starting point for land/vegetation comparisons when a suitable validated product exists. They are different measurements: do not mix TOA and SR in a time series or interpret atmospheric differences as land change. The generic index tools do not perform atmospheric correction or turn Level-1 DN into TOA reflectance automatically.

The implemented `toa` command follows the [USGS Level-1 calibration guide](https://www.usgs.gov/landsat-missions/using-usgs-landsat-level-1-data-product):

`rho_TOA = (REFLECTANCE_MULT_BAND_x * DN + REFLECTANCE_ADD_BAND_x) / sin(SUN_ELEVATION)`

Solar elevation is read in degrees from the scene's MTL JSON and converted for the calculation. This uses the scene-center sun angle; it is not the provider's per-pixel angle-corrected ARD processing and is not atmospheric correction. The converter supports reflective Landsat 4/5/7/8/9 bands with matching MTL metadata; MSS, thermal and QA-band conversion are outside its scope. See [the usage example](usage.md#convert-landsat-level-1-dn-to-toa-reflectance).

### Observed metadata checks

These examples establish metadata availability in this development session, not future access or guaranteed global coverage:

- [USGS Level-1 collection](https://landsatlook.usgs.gov/stac-server/collections/landsat-c2l1) reports an archive interval starting `1972-07-25`. A metadata-only Dhaka query (`90.2,23.6,90.5,23.9`, 2024-01-01 to 2024-03-31, cloud ≤20) matched six items. One was `LC09_L1TP_137043_20240317_20240317_02_T1` (2024-03-17; cloud 6.77%), exposing `red`, `nir08`, `MTL.json` and QA assets. Its MTL asset redirected to the EROS login HTML page without authenticated access.
- [USGS ARD TA collection](https://landsatlook.usgs.gov/stac-server/collections/landsat-c2ard-ta) reports an interval starting `1982-08-22`. The same Dhaka 2024 Q1 query without a cloud filter returned no items; a California box (`-122.5,37.5,-122.2,37.8`) returned 29. Example `LC08_CU_001009_20240329_20240413_02_TOA` has region `CU` and 5000 × 5000, 30 m Albers-grid tiles. Do not infer global imagery coverage from the collection's broad extent or the word “UTM” in its current title.
- [Sentinel-2 L1C collection](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l1c) yielded Dhaka example `S2A_45QZG_20240326_0_L1C`. Its baseline 05.10 reflectance assets advertise STAC scale `0.0001` and offset `-0.1` and requester-pays S3 JP2 links. This illustrates why baseline-specific metadata and access routes matter; it is not a universal scaling rule.

## Reference directory: separate access required

| Local ID | Indicative record | Access route | Provider documentation |
| --- | --- | --- | --- |
| `corona` | 1960–1972 | USGS EarthExplorer; account and scanning availability vary | [Declassified CORONA reconnaissance photography](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-declassified-data-declassified-satellite-imagery-1) |
| `landsat-mss` | 1972–2013 | USGS EarthExplorer / Landsat archive; account may be required | [Landsat 1–5 MSS archive](https://www.usgs.gov/landsat-missions/landsat-collection-2) |
| `era5` | 1940–open-ended; check provider | CDS account/API terms; Open-Meteo offers selected derived variables under its own terms | [ERA5 historical climate reanalysis](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels) |
| `chirps` | 1981–open-ended; check provider | Public downloads; distinguish preliminary/final and product versions | [CHIRPS precipitation](https://www.chc.ucsb.edu/data/chirps) |
| `avhrr` | 1981–open-ended; check provider | Public NOAA archive; choose a specific CDR and version | [NOAA AVHRR climate data records](https://www.ncei.noaa.gov/products/climate-data-records) |
| `smap` | 2015–open-ended; check provider | NASA Earthdata login commonly required for protected downloads | [SMAP soil moisture](https://nsidc.org/data/smap) |
| `emit` | 2022–open-ended; check provider | NASA Earthdata login commonly required for protected downloads | [EMIT imaging spectroscopy](https://earth.jpl.nasa.gov/emit/data/data-portal/coverage-and-forecasts/) |
| `viirs-nightlights` | 2012–open-ended; check provider | NASA Earthdata login commonly required for protected Black Marble downloads | [VIIRS / NASA Black Marble night lights](https://blackmarble.gsfc.nasa.gov/) |
| `firms` | 2000–open-ended; check provider | FIRMS API MAP_KEY; archive downloads and near-real-time products differ | [NASA FIRMS active fire detections](https://firms.modaps.eosdis.nasa.gov/api/) |
| `sentinel-5p` | 2018–open-ended; check provider | Public catalog; account/token commonly required for product downloads | [Sentinel-5P TROPOMI atmospheric products](https://dataspace.copernicus.eu/explore-data/data-collections/sentinel-data/sentinel-5p) |
| `sentinel-3` | 2016–open-ended; check provider | Public catalog; account/token commonly required for product downloads | [Sentinel-3 OLCI / SLSTR ocean and land products](https://dataspace.copernicus.eu/explore-data/data-collections/sentinel-data/sentinel-3) |

Except for the separate ERA5 weather adapter, these sources need additional adapters, credentials and/or preprocessing. In particular, FIRMS API requests require a MAP_KEY; NASA protected downloads commonly require Earthdata authentication; Copernicus product access may require an account/token. Do not paste credentials into command examples, GeoJSON files, Git or support messages. Configure provider credentials through the provider-supported secure mechanism when using those sources outside this client.

## Choosing an archive

For land/vegetation monitoring around Dhaka, start with Sentinel-2 recent 10 m observations or Landsat for the longer 30 m record. For a 1990-to-2024 comparison use Landsat, then account for sensor differences, acquisition season, atmospheric processing, QA and grid alignment. Sentinel-2 cannot supply 1990 observations. A 1970s comparison may use raw MSS scenes discovered through the global Landsat Level-1 catalog, but requires appropriate retrieval and separate MSS preprocessing; the Level-2 SR adapter and current `toa` converter do not supply an MSS reflectance workflow.

For monsoon flooding, optical scenes may be cloud-obscured. Sentinel-1 RTC can be a useful radar input, but a flood model also needs orbit/polarization consistency, noise/terrain handling and validation. A downloaded radar asset is not an automatic flood map. For elevation, select a static DEM and understand surface-vs-terrain and vertical-datum differences. For CHIRPS rainfall, retrieve the actual product from its provider; its listing here is reference-only. For selected ERA5 hourly weather variables, use the implemented `weather` command through Open-Meteo. Full ERA5 gridded products and other variables still require a separate provider workflow.

## Scientific and access notes

- Earliest mission year does not imply global or cloud-free coverage from that year. Landsat 7 has scan-line gaps after 2003. Sensor changes, orbit availability and product reprocessing affect comparisons.
- Cloud metadata summarizes scenes; use pixel quality masks and remove shadows/snow where appropriate. Reflectance scale factors and additive offsets can change the computed indices. Read STAC `raster:bands` metadata and provider product guides.
- Data licenses remain with the original provider. Cite the mission/product/version, access date and the provider's required attribution. This project does not relicense upstream datasets.
- Near-real-time, preliminary, final and reprocessed streams have different latency and quality. Query results and source versions should be retained alongside outputs for reproducibility.
- Network-restricted environments must permit the STAC endpoint plus actual asset hostnames. Search access alone does not grant downloads; avoid broad wildcard permissions when the needed hosts can be identified.

## Implemented weather adapter

`universal-satellite weather` retrieves selected ERA5 hourly variables for a point through the [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api). This is separate from STAC scene search. Its record extends to 1940 for ERA5; the service has publication lag, rate limits and its own usage terms. The current client caps each request at 367 inclusive days. Temperature and precipitation are default variables; inspect returned units and timezone before aggregating. Open-Meteo interpolated point/model output is not a weather-station observation or a raster download. Check Open-Meteo licensing and commercial access terms for your application.
