# Universal Satellite

Discover Earth-observation data, download native assets and compute georeferenced
spectral indices from Python, a typed Node/TypeScript client, QGIS or ArcGIS Pro.
Version **0.3.0** provides **280 referenced spectral formulas**, **30 searchable
source choices**, parallel/resumable downloads, environmental point profiles,
polygon clipping and local NumPy/PyTorch/JAX dataset access.

No global API key is required. Individual providers may require accounts/tokens.
Read the [provider coverage and limitations](docs/providers.md): PRISMA discovery
is not implemented; SoilGrids REST is currently reported paused, and archive or
credential-dependent access is not guaranteed. No observations are fabricated.

## Install

Requires Python 3.10+. From this repository:

```sh
python -m pip install -e '.[raster]'
# Optional Shapefile or Earth Engine support:
python -m pip install -e '.[raster,vector,earthengine]'
```

Install into the Python environment actually used by QGIS or an ArcGIS Pro cloned
environment, then restart the application. Packages below contain GIS adapters;
they do not bundle the Python SDK or a desktop runtime.

| Download | Install |
| --- | --- |
| [QGIS plugin ZIP](gis/qgis/universal_satellite_qgis.zip) | Plugins → Manage and Install Plugins → Install from ZIP |
| [ArcGIS Pro toolbox ZIP](gis/arcgis/universal_satellite_arcgis.zip) | Extract → Catalog → Toolboxes → Add Toolbox → UniversalSatellite.pyt |

Both provide scene search, image download, the full index catalog, environmental
point-profile download and polygon cropping. The original two-band index tool is
retained for compatibility. QGIS 3.28+ / ArcGIS Pro are the intended desktop hosts;
automated contract tests are not native desktop certification.

## Search and download

```sh
universal-satellite sources --json
universal-satellite search --dataset sentinel-2-l2a --bbox 9,48,9.1,48.1 --start 2025-06-01 --end 2025-06-30 --limit 2 --output scenes.geojson
universal-satellite download scenes.geojson --asset red,nir --output images --workers 4 --retries 2
```

In either GIS, open **Search satellite scenes**, save the original GeoJSON manifest,
then open **Download satellite image assets**. Choose exact asset keys and an output
folder. Enable Planetary Computer signing for its Azure assets. Use `*` only when
you want every advertised asset, including metadata and QA. Missing assets and
provider failures are reported individually. Native files may be NetCDF/HDF/ZIP,
not GeoTIFF. FIRMS manifests contain hotspot points and need no asset download.

[Download behavior, resumption and cancellation](docs/downloads.md) ·
[Provider-specific access](docs/providers.md)

## Spectral indices and raster analysis

```sh
universal-satellite indices
universal-satellite index --name evi --nir nir.tif --red red.tif --blue blue.tif --output evi.tif
universal-satellite crop --source image.tif --boundary aoi.geojson --output clipped.tif
```

In **Compute spectral index (full catalog)** select the formula and supply its named
bands. Inputs must be calibrated and aligned; cloud masking and missing calibration
are not inferred. The registry covers vegetation, water, burn, soil, urban, snow,
radar and kernel indices where suitable inputs exist. Case-sensitive names `BAI` /
`BaI` and `MSR705` / `mSR705` are distinct formulas. Formula references, constants
and caveats are in [the index guide](docs/indices.md).

```python
from universal_satellite import Client
from universal_satellite.indices import evaluate
print(evaluate('ndvi', {'nir': 0.8, 'red': 0.2}))
weather = Client().environment('forecast', latitude=48, longitude=9)
```

See [local GeoAI datasets](docs/geoai.md) for NumPy, PyTorch and JAX samples.

## TypeScript / Node

```sh
npm install ./javascript
# or: pnpm add ./javascript
```

The [typed SDK](javascript/README.md) computes indices natively in JavaScript.
Network/raster methods and its CLI use the installed Python engine through a
structured subprocess protocol. It is not a Python-free or browser SDK. Set
`UNIVERSAL_SATELLITE_PYTHON` if the core is installed in a different environment.
Neither the Python nor npm package is published by this repository update.

## Verification and development

```sh
python -m pip install -e '.[raster,dev]'
python -m pytest -q
node --test javascript/test/*.test.js
python -m build
python tools/package_indices.py
python tools/package_qgis.py --force
python tools/package_arcgis.py --force
```

Tests cover malformed provider data, formula arithmetic and masks, GIS adapter
contracts, range resumption, parallel downloads and credential scoping. Provider
outages and missing credentials produce errors, not synthetic results. See
[verification scope and live checks](docs/providers.md#evidence-and-upstream-comparison).

Spectral formula data is from [Awesome Spectral Indices](https://github.com/awesome-spectral-indices/awesome-spectral-indices),
with its MIT copyright/license notice bundled. Each provider retains its own data
terms and required attribution. Review the recorded product provenance before
using data in reports, research or commercial workflows.
