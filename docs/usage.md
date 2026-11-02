# Usage guide

## Install and inspect the source directory

From the repository root, create a virtual environment and install the package:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install -e .
universal-satellite doctor
universal-satellite sources
universal-satellite sources --category optical
```

Core discovery and download workflows use Python's standard library. Raster calculations need the optional raster dependencies:

```bash
python -m pip install -e ".[raster]"
```

QGIS and ArcGIS use their own managed Python environments: follow the GIS guide instead of replacing their bundled packages.

The source directory includes implemented STAC adapters and reference-only archives. ERA5 also has a separate weather adapter described below. Read each entry's `status`, `access` and notes. For the long record from the 1960s/1970s, read [Data sources](sources.md); these early archives have separate retrieval and processing workflows. Landsat Level-1 search can expose historical MSS scenes, but the current TOA converter does not support MSS.

## Search an area and date range

The examples use a small area around Dhaka, Bangladesh, in longitude/latitude (WGS84 / EPSG:4326). A bbox is **west,south,east,north**, not latitude/longitude. Draw or transform the area of interest to WGS84 before supplying it. Split a region that crosses the antimeridian into two boxes.

```bash
universal-satellite search \
  --dataset sentinel-2-l2a \
  --bbox 90.2,23.6,90.5,23.9 \
  --start 2024-01-01 --end 2024-03-31 \
  --cloud 20 --limit 10 \
  --output scenes.geojson

universal-satellite summary scenes.geojson
```

Search requires ISO start/end dates; `--end` defaults to today when omitted. For static sources `cop-dem-glo-30`, `nasadem` and `jrc-gsw`, the client validates those dates but **does not apply them to STAC**. These searches return spatial inventories, not historical snapshots selected by your dates. The result metadata records `temporal_filter_applied: false`, `requested_dates` and a note under `universal_satellite`. The dates shown in the source directory describe acquisition/record eras rather than catalog timestamps. WorldCover keeps its annual temporal filter.

The result is a GeoJSON FeatureCollection of scene footprints and STAC properties/assets, suitable for inspection in GIS. It is **not** a raster mosaic or a stack of image pixels. Ten results is a bounded sample, not proof that only ten scenes exist. Scene cloud cover is an optical metadata filter; scenes lacking cloud-cover metadata are excluded when the filter is requested. Clouds and shadows must still be masked per pixel for analysis. A successful empty query is different from a failed provider request: broaden dates/cloud cover only after checking that the request succeeded.

To retrieve an older period, choose a collection that covers it:

```bash
universal-satellite search \
  --dataset landsat-c2-l2 \
  --bbox 90.2,23.6,90.5,23.9 \
  --start 1990-01-01 --end 1990-03-31 \
  --cloud 30 --limit 10 \
  --output landsat-1990.geojson
```

There is no guarantee that this particular region and interval contains usable acquisitions. Search nearby seasons/years when appropriate and preserve the final query with your analysis. Compare like seasons before attributing differences to land change.

## Choose TOA or surface reflectance

Use **surface reflectance (SR)** for most land/vegetation comparisons when a suitable product exists. Use **top-of-atmosphere (TOA)** reflectance when the analysis calls for it and account for atmospheric effects. These measurements are not interchangeable.

- `sentinel-2-l2a` and `landsat-c2-l2` provide surface-reflectance products.
- `sentinel-2-l1c` provides scaled TOA reflectance. Read each asset's actual scale/offset and processing baseline; do not assume a universal DN / 10000 conversion.
- `landsat-c2-l1` provides calibrated Level-1 **digital numbers**, which must be converted before being treated as physical TOA reflectance.
- `landsat-c2-ard-toa` provides provider-produced TOA reflectance on regional US ARD tiles. It is not a global alternative for Dhaka or other places outside that coverage.

Search TOA-related sources with the same interface:

```bash
universal-satellite search \
  --dataset sentinel-2-l1c \
  --bbox 90.2,23.6,90.5,23.9 \
  --start 2024-01-01 --end 2024-03-31 \
  --cloud 20 --limit 5 --output sentinel-toa-scenes.geojson

universal-satellite search \
  --dataset landsat-c2-l1 \
  --bbox 90.2,23.6,90.5,23.9 \
  --start 2024-01-01 --end 2024-03-31 \
  --cloud 20 --limit 5 --output landsat-level1-scenes.geojson

# US ARD example: California, with negative west coordinate.
universal-satellite search \
  --dataset landsat-c2-ard-toa \
  --bbox=-122.5,37.5,-122.2,37.8 \
  --start 2024-01-01 --end 2024-03-31 \
  --limit 5 --output us-ard-toa-scenes.geojson
```

These commands discover footprints and asset metadata, not calibrated raster pixels. Some Earth Search Sentinel-2 L1C assets use requester-pays `s3://` JP2 links; the HTTP(S) downloader does not retrieve native S3 assets. Use the provider-supported AWS access route when needed. USGS Level-1/ARD imagery and MTL metadata may require USGS EROS/EarthExplorer authentication; an HTTP 200 login HTML page is not a successful image download. The project does not implement an interactive USGS login or assume NASA Earthdata credentials apply.

## Use the Python client

```python
import json
from universal_satellite import Client

scenes = Client().search(
    dataset="sentinel-2-l2a",
    bbox=[90.2, 23.6, 90.5, 23.9],
    start="2024-01-01",
    end="2024-03-31",
    cloud=20,
    limit=10,
)
with open("scenes.geojson", "w", encoding="utf-8") as stream:
    json.dump(scenes, stream, indent=2)

for scene in scenes["features"]:
    print(scene["id"], scene["properties"].get("datetime"))
    print("Available asset keys:", list(scene.get("assets", {})))
```

The client returns source STAC fields to preserve provenance. Asset keys are provider-specific: Sentinel `nir` and Landsat `nir08`, for example, need not match. Consult the scene's assets rather than guessing band names. Asset media type and roles also matter: a metadata XML, thumbnail and reflectance raster are different things.

## Download selected assets

For scenes containing a `red` asset:

```bash
universal-satellite download scenes.geojson --asset red --output downloads
```

This requests an asset for each returned scene; check the size and scene count first. Files can be large and provider hosting/credentials differ. A missing asset should be resolved by inspecting the result, not by substituting another spectral band. Preserve source scene IDs and metadata. Some assets require signed URLs or provider authentication even though the search itself is public. For Planetary Computer Azure assets, pass `--sign-planetary` to generate temporary signed URLs in memory:

```bash
universal-satellite download scenes.geojson --asset red --output downloads --sign-planetary
```

Sign only at download time; original metadata stays reusable. This option does not supply NASA/USGS credentials or make every provider asset public. See [Data sources](sources.md) for access differences.

For raster processing, download all required bands and quality masks for the **same acquisition**. Do not pair red from one scene with NIR from another.

## Convert Landsat Level-1 DN to TOA reflectance

After retrieving a Landsat Level-1 band and the matching acquisition's **MTL JSON** through an authorized provider route, install the raster extras and run:

```bash
# Landsat 8/9 example: band 4 is red, band 5 is NIR.
universal-satellite toa \
  --input B4.TIF --mtl MTL.json --band 4 --output red-toa.tif
universal-satellite toa \
  --input B5.TIF --mtl MTL.json --band 5 --output nir-toa.tif

universal-satellite index \
  --name ndvi --nir nir-toa.tif --red red-toa.tif --output ndvi-toa.tif
```

```python
from universal_satellite.raster import landsat_toa

landsat_toa("B4.TIF", "MTL.json", 4, "red-toa.tif")
```

The converter uses that band's `REFLECTANCE_MULT_BAND_x`, `REFLECTANCE_ADD_BAND_x` and scene-center `SUN_ELEVATION` from MTL JSON. It accepts reflective bands for Landsat 4/5/7/8/9; it does not convert MSS, thermal or QA bands. For Landsat 4/5 use reflective bands 1–5 and 7; Landsat 7 also has panchromatic band 8; Landsat 8/9 use reflective bands 1–9. Band numbers are sensor-specific: Landsat 4/5/7 red/NIR are bands 3/4, rather than the 8/9 example's bands 4/5.

Supply the raw Level-1 DN raster, not SR, already converted TOA or a manually rescaled image. The converter ignores input scale/offset tags to avoid applying DN calibration twice, treats DN zero as fill/nodata, and writes physical reflectance. You are responsible for matching the band, MTL file and acquisition; renaming unrelated files does not establish a match. It uses a scene-center sun angle, not a per-pixel angle field, and performs **no atmospheric correction**. Apply pixel cloud/shadow/saturation QA separately. The resulting NDVI is a TOA-based index, not an SR-based index; do not mix the two in a time series.

## Compute an index correctly

After installing the raster extras, you can compute an NDVI GeoTIFF:

```bash
universal-satellite index \
  --name ndvi \
  --nir nir.tif --red red.tif \
  --output ndvi.tif
```

NDVI is `(NIR - red) / (NIR + red)`. The inputs must represent comparable reflectance on the same CRS, transform, dimensions and pixel grid. The tool does not infer atmospheric correction, convert Level-1 DN to TOA, harmonize sensors or apply cloud masks. Reproject/resample and apply QA before analysis when necessary. The tool automatically applies the input GeoTIFF scale and offset tags through rasterio. If those tags are absent or incorrect, first create rasters containing physical reflectance. STAC `raster:bands` scale/offset values are not automatically copied into a downloaded GeoTIFF. If supplying physical reflectance already, ensure its TIFF tags do not apply the scale twice. A shared multiplicative scale cancels in NDVI, but additive offsets do not; EVI also depends on absolute reflectance units. Raw digital numbers are not a safe universal input.

Sentinel-2 bands have mixed resolutions and different processing baselines. Landsat Collection 2 surface reflectance commonly uses scale `0.0000275` and offset `-0.2`; verify these in the actual product metadata. Raster nodata is not the same as a cloud/shadow mask. Inspect outputs and validate against known areas before quantitative interpretation.

## Retrieve historical weather

The weather adapter requests selected hourly ERA5 variables from Open-Meteo at a WGS84 point. It is separate from STAC imagery search and can reach records before the satellite era:

```bash
universal-satellite weather \
  --latitude 23.8 --longitude 90.4 \
  --start 1981-01-01 --end 1981-01-03 \
  --output weather.json

# Explicit hourly variables:
universal-satellite weather \
  --latitude 23.8 --longitude 90.4 \
  --start 2024-01-01 --end 2024-01-07 \
  --variables temperature_2m,precipitation \
  --output weather-2024.json
```

```python
from universal_satellite import Client

weather = Client().weather(
    latitude=23.8,
    longitude=90.4,
    start="1981-01-01",
    end="1981-01-03",
    variables=["temperature_2m", "precipitation"],
)
print(weather["hourly_units"])
print(weather["hourly"]["time"][:3])
```

Temperature and precipitation are default variables. The adapter caps each request at 367 inclusive days; split longer intervals into dated requests. ERA5 availability through this API starts in 1940 and recent dates have a publication lag. Read returned units, timezone and null values before calculating statistics. Partial missing values can occur; an all-null requested series is treated as a provider error rather than usable weather data. These are model/reanalysis estimates at a point, not station measurements. Review [Open-Meteo terms](https://open-meteo.com/en/terms) and commercial access requirements before production use.

## QGIS and ArcGIS

Both GIS integrations share the Python core. Use the dedicated [GIS guide](gis.md) for installing the QGIS Processing provider and ArcGIS Pro `.pyt` toolbox. Search outputs provide footprint layers; download image assets separately for raster display or analysis. The GIS tools do not bundle proprietary ArcGIS runtimes or a QGIS desktop installation.

## Reproducible work

Save the exact dataset, bounding box, interval, filters, scene IDs, processing versions, asset keys and scaling choices with every derived output. Preserve stable metadata rather than a short-lived signed URL. Review each provider's terms and citation instructions. Keep credentials and signed query strings out of shared files. A first-pass index image is an analysis input; it is not a validated classification, crop-yield estimate or disaster map.
