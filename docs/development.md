> Version note: this page describes the original 0.2 workflows. For the 0.3 feature set, expanded menus and current limitations, use [README](../README.md), [indices](indices.md), [downloads](downloads.md) and [providers](providers.md).

# Development and validation

Universal Satellite is an independent implementation inspired by the scope of
[OmniEarth](https://github.com/lokeshsk/omniearth). The Python core has no third-party
runtime dependencies for search and downloads. Raster analysis uses optional
NumPy and Rasterio dependencies.

From the repository root, with your development virtual environment active:

```bash
python -m pip install -e ".[raster,dev]"
python -m pytest -q
python -m build
python tools/package_qgis.py --force
python tools/package_arcgis.py --force
```

The wheel contains the Python SDK/CLI. The source distribution also contains the
GIS adapters and documentation. Both desktop ZIPs contain adapters; install or
upgrade the core SDK separately inside the Python environment used by the GIS. Downloading assets afterward runs
from the GUI and does not require a separate CLI environment.

## What has been checked

The suite covers TOA calibration, separate TOA/SR dataset selection, all 13
toolbox menu choices with missing or older SDKs, and shared manifest-download
behavior including progress, cancellation and per-asset failures. GUI adapters
expose optional downloads after search and a separate manifest-download tool;
these are checked through API stubs rather than native desktop execution.
An HTTP smoke check served a synthetic 2 × 2 GeoTIFF locally and downloaded it
through the shared worker into an operator-selected folder; bytes, pixels, CRS
and final progress were verified. This checks the download backend, not native
desktop execution or authenticated imagery retrieval.
Initial validation also passed a CLI NDVI smoke check. Tests use
deterministic STAC fixtures, simulated downloads, synthetic GeoTIFFs and GIS API
stubs. The Python wheel and source distribution built successfully, and the core
wheel was installed and exercised in a separate environment without raster extras.
The CI workflow is configured for Python 3.10 and 3.12; this does not establish
that the remote CI run has completed.

Native QGIS and ArcGIS Pro execution is still pending. Their contract tests do
not replace testing the plugin/toolbox inside the desktop applications. Record
versions and actual outcomes using the [screenshot walkthrough](screenshots.md).

## Live access

Initial cloud requests were blocked by network policy. After access became
available, live SDK metadata smoke checks succeeded on 2026-11-02 for Sentinel-2
L1C TOA, Sentinel-2 L2A SR, Landsat Level-1 DN, Landsat Level-2 SR (Dhaka), and
Landsat US ARD TOA (California). Each query requested and returned one scene for
2024-01-01 through 2024-03-31 with cloud cover at most 20 percent. These checks
establish metadata search, not authenticated imagery retrieval or native GIS use.
See the [source evidence and access notes](sources.md#observed-metadata-checks).

The environment draft contains installation/startup instructions. Required API hosts:

- `earth-search.aws.element84.com`
- `planetarycomputer.microsoft.com`
- `landsatlook.usgs.gov`
- `archive-api.open-meteo.com`

Saving a draft does not apply or publish it. The observed runtime now allows these
metadata requests. Asset download hosts vary by returned
item and may need additional network access. Keep system proxy and TLS verification
settings intact. Public metadata does not guarantee public downloads; provider
accounts, signed URLs, requester-pays access, rate limits and terms vary. The
HTTP downloader rejects unexpected HTML login pages rather than saving them as
raster/JSON data. An HTTP/provider error is not
an empty successful query, and the CLI does not substitute demo results.

## GUI download workflow

The search checkbox defaults to false. When enabled, or when the separate
**Download satellite image assets** tool is run, the shared SDK processes the
requested asset keys for each manifest scene into the chosen folder. Jobs use
the GIS host's normal Processing/geoprocessing execution and progress controls;
there is no custom detached worker queue. A cancellation keeps completed files
and removes an interrupted temporary partial file. Per-asset failures continue
with warnings; zero successful downloads after attempted failures is an error.

Native host responsiveness, cancellation timing and authenticated imagery access
remain to be validated. HTTP(S) public/presigned assets and Planetary Computer
Azure signing are supported; native S3 requester-pays and interactive USGS login
are not implemented. The [GIS guide](gis.md#download-behavior-and-access-limits)
describes operator-visible behavior and access limits.

## Interpretation and future work

Scene counts are inventories, not pixel time series. Scene cloud percentages do
not replace pixel QA. Static DEM/JRC sources omit temporal filtering explicitly;
WorldCover retains annual date filtering. Multi-sensor studies need calibration,
alignment and harmonization beyond an index formula.

Possible future additions include dedicated MSS and NASA Earthdata retrieval adapters,
QA-aware clipping/mosaics, harmonized pixel time series, change detection and
native GIS release testing. These are not implemented features.
