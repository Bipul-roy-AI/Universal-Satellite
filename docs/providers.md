# Provider adapters and access

## Implemented interfaces

| Route | Data | Credentials / output |
| --- | --- | --- |
| Existing STAC adapters | Sentinel-1/2, Landsat, DEM, WorldCover, JRC, MODIS | Public metadata; Planetary Computer signing where needed |
| `3dep-seamless` | USGS 3DEP | Public metadata; optional PC signing |
| `enmap-l2a` | DLR EnMAP | Actual DLR STAC items; DLR download account may be required |
| `emit-l2a` | EMIT reflectance | NASA CMR; Earthdata access for protected assets |
| `smap-l4` | SMAP surface/root-zone moisture | NASA CMR; native HDF5 products |
| `gpm-imerg` | IMERG Final daily precipitation | NASA CMR; native product files |
| `viirs-black-marble` | VNP46A2 nighttime lights | NASA CMR; native HDF products |
| `viirs-active-fire` | VNP14IMG fire products | NASA CMR; native product files |
| `jason-3`, `sentinel-6` | Altimetry products | NASA CMR; native NetCDF products |
| `sentinel-3-products`, `sentinel-5p-products`, `sentinel-2-products` | Copernicus native product archives | CDSE access token for downloads; instrument/level varies |
| `chirps-daily` | CHIRPS v2 daily global rainfall files | Reads the provider's directory; may be unavailable during outages |
| `firms-viirs`, `firms-modis` | Actual FIRMS hotspot observations | FIRMS_MAP_KEY; output is GeoJSON points, not images |
| `dynamic-world` | Dynamic World label/probability imagery | Optional earthengine extra, existing credentials and EE_PROJECT; small AOIs only |
| `hyperion` | Hyperion granule discovery | CMR may expose only collection metadata; USGS archive retrieval may still be needed |
| `environment forecast` | IFS/GFS, ET0, VPD, solar radiation | Open-Meteo point/model JSON |
| `environment air-quality` | CAMS PM2.5, NO2, CO, AOD | Open-Meteo point/model JSON |
| `environment soil` | SoilGrids pH, SOC, texture, nitrogen, CEC | ISRIC REST point/model JSON; service currently reported paused |

A successful catalog query does not establish that a provider account can download
its products. A catalog entry does not imply every date, band, instrument or
processing level is available. Inspect asset keys and native product metadata.
CMR data links are named `data`, `data_2`, etc.; these are original files, not
invented single-variable GeoTIFFs. FIRMS point manifests are already the data;
do not request image downloads for them. NRT availability is provider-limited.

**PRISMA remains unimplemented:** no supported, verified public API/account route
was established during this change. Use ASI's portal and authorized exports.
The core can download an authorized HTTPS asset from a supplied STAC manifest,
but that is not PRISMA archive discovery. Historical reference-only entries
(CORONA, MSS, AVHRR and others) remain explicitly marked in `sources --json`.

## Credentials

No mandatory global API key. Configure only the provider you need in the desktop
GIS Python process environment before starting the application:

- `EARTHDATA_TOKEN`: NASA Earthdata bearer token for `*.earthdata.nasa.gov`.
- `CDSE_ACCESS_TOKEN`: bearer token for the Copernicus download/zipper hosts.
- `DLR_USERNAME` / `DLR_PASSWORD`: Basic authentication for `download.geoservice.dlr.de`.
- `FIRMS_MAP_KEY`: NASA FIRMS area API key.
- `EE_PROJECT`: an authorized Earth Engine project, with credentials already configured
  outside the tool. Install `.[earthengine]`. No interactive login is triggered.
- `UNIVERSAL_SATELLITE_TOKEN_HOSTS`: optional JSON mapping **exact hostnames to
  environment-variable names**, e.g. `{"protected.example.org":"MY_PROVIDER_TOKEN"}`.
  The mapping contains names, not secret values.

Authorization is scoped to HTTPS hosts and is removed on cross-host redirects;
the destination receives only its own configured credential. Expired tokens are
not silently refreshed: obtain a new token through the provider. Never commit
credentials. Native S3/requester-pays retrieval is still outside the HTTP downloader;
use the new Copernicus archive route for Sentinel-2 where appropriate.

## SoilGrids raster alternative and polygon clipping

ISRIC documents its VRT/WebDAV service separately from its paused REST service.
The **Crop raster or remote COG to polygon** tool accepts local rasters and
public/signed HTTPS sources. A SoilGrids example source is
`https://files.isric.org/soilgrids/latest/data/phh2o/phh2o_0-5cm_mean.vrt`.
Review the provider's encoded units (this pH product uses pH × 10); do not assume
missing scale metadata is physical reflectance. Remote VRT access depends on
GDAL's VRT/HTTP support and the availability of the referenced tiles.

```sh
universal-satellite crop --source input.tif --boundary aoi.geojson --output clipped.tif
```

GeoJSON must use WGS84; Shapefiles need a declared CRS and the `vector` extra.
Outputs retain the source grid, masks and scale/offset tags, using float32 and
NaN nodata. A 25-million band-pixel budget bounds memory. HTTPS COGs can use GDAL
range reads; there is no guarantee of sub-second access. Protected products should
be downloaded before clipping. Boundary clipping is not a reprojection operation.

## Evidence and upstream comparison

On 2026-11-04 live metadata queries returned products from SMAP, GPM, Black Marble,
EMIT, VIIRS fire, Jason-3, Sentinel-6, EnMAP, USGS 3DEP and the three Copernicus
archive routes. IFS and CAMS point queries returned provider time series. The CHIRPS v2 directory had moved to `/products/CHIRPS/v2.0/`; the adapter was updated to the current provider path. Hyperion returned no granules
for the selected window. These checks did not download large/protected science
products. FIRMS and Dynamic World live access was not tested without credentials.
Desktop GIS validation used contract doubles, not installed ArcGIS Pro/QGIS hosts.

OmniEarth's inspected main-branch hydrology, precipitation and altimetry adapters
contained hard-coded measurements and constructed asset links. This project does
not depend on or copy those adapters. Matching advertised categories is not proof
of upstream scientific correctness or complete product parity.

Provider documentation:
- https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html
- https://documentation.dataspace.copernicus.eu/APIs/OData.html
- https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/ENMAP_HSI_L2A
- https://www.chc.ucsb.edu/data/chirps
- https://firms.modaps.eosdis.nasa.gov/api/area/
- https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1
- https://open-meteo.com/en/docs
- https://docs.isric.org/globaldata/soilgrids/
