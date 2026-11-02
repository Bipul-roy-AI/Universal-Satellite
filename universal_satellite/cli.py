"""Command line interface shared with the Python and desktop GIS workflows."""
import argparse
from dataclasses import asdict
from datetime import date
import importlib.util
import json
import sys

from . import __version__
from .catalog import list_datasets
from .client import Client
from .download import DownloadError, download_asset
from .export import read_geojson, summarize, write_geojson, write_json
from .http import ProviderError


def _bbox(value):
    try:
        result = [float(v) for v in value.split(",")]
        if len(result) != 4:
            raise ValueError()
        return result
    except ValueError:
        raise argparse.ArgumentTypeError("Use west,south,east,north (EPSG:4326)") from None


def parser():
    root = argparse.ArgumentParser(description="Universal Satellite: discover archives, download assets, analyze rasters")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    sources = commands.add_parser("sources", help="List dated data sources and adapter/access status")
    sources.add_argument("--category")
    sources.add_argument("--json", action="store_true", help="Print complete machine-readable catalog")
    search = commands.add_parser("search", help="Search STAC; save scene footprints and original asset links")
    search.add_argument("--dataset", required=True)
    search.add_argument("--bbox", type=_bbox, required=True, help="west,south,east,north in EPSG:4326; use --bbox=-90,20,-89,21 for negative west")
    search.add_argument("--start", required=True, help="Inclusive date YYYY-MM-DD")
    search.add_argument("--end", default=date.today().isoformat(), help="Inclusive date; default today")
    search.add_argument("--cloud", type=float, help="Maximum optical scene cloud percentage, 0–100; excludes unknown cloud metadata")
    search.add_argument("--limit", type=int, default=100, help="Total scenes, not page size (1–1000)")
    search.add_argument("--output", help="GeoJSON manifest; default standard output")
    summary = commands.add_parser("summary", help="Summarize a saved scene inventory by month, platform and asset")
    summary.add_argument("manifest")
    download = commands.add_parser("download", help="Download a named asset from every item in a saved manifest")
    download.add_argument("manifest")
    download.add_argument("--asset", required=True, help="Exact STAC asset key; use summary to inspect available keys")
    download.add_argument("--output", default="downloads", help="Directory")
    download.add_argument("--overwrite", action="store_true")
    download.add_argument("--sign-planetary", action="store_true", help="Request short-lived Planetary Computer Azure asset SAS links in memory")
    index = commands.add_parser("index", help="Compute a georeferenced spectral index from aligned single-band GeoTIFFs")
    index.add_argument("--name", required=True, choices=["ndvi", "ndwi", "mndwi", "ndmi", "nbr", "evi"])
    for band in ["nir", "red", "green", "blue", "swir16", "swir22"]:
        index.add_argument("--" + band, help="Local single-band raster (with correct reflectance scale/offset metadata)")
    index.add_argument("--output", required=True)
    toa = commands.add_parser("toa", help="Calibrate a Landsat Level-1 reflective DN band to TOA reflectance using its MTL JSON")
    toa.add_argument("--input", required=True, help="Local Level-1 DN GeoTIFF (not SR or an ARD TOA product)")
    toa.add_argument("--mtl", required=True, help="Matching Landsat MTL JSON file")
    toa.add_argument("--band", type=int, required=True, help="Reflective band number; thermal/MSS unsupported")
    toa.add_argument("--output", required=True, help="New float32 TOA reflectance GeoTIFF")
    weather = commands.add_parser("weather", help="Historical ERA5 hourly reanalysis via Open-Meteo (1940 onward)")
    weather.add_argument("--latitude", type=float, required=True)
    weather.add_argument("--longitude", type=float, required=True)
    weather.add_argument("--start", required=True)
    weather.add_argument("--end", required=True)
    weather.add_argument("--variables", default="temperature_2m,precipitation")
    weather.add_argument("--output")
    commands.add_parser("doctor", help="Report installed local capabilities; does not test external services")
    return root


def _emit(value, output=None, geojson=False):
    if output:
        (write_geojson if geojson else write_json)(value, output)
        print(output)
    else:
        print(json.dumps(value, indent=2, allow_nan=False))


def run(args):
    if args.command == "sources":
        entries = list_datasets(args.category)
        if args.json:
            _emit([asdict(v) for v in entries])
        else:
            print(f"{'DATASET':27} {'CATEGORY':14} {'RECORD':24} {'ADAPTER':12} RESOLUTION / PROCESSING")
            for source in entries:
                record = source.start[:4] + "–" + (source.end[:4] if source.end else "ongoing*")
                product = f"; {source.processing_level}: {source.measurement}" if source.processing_level else ""
                print(f"{source.id:27} {source.category:14} {record:24} {source.status:12} {source.resolution}{product}")
            print("* Ongoing record does not establish current catalog ingestion. Dates are indicative; sources --json has access notes.")
    elif args.command == "search":
        value = Client().search(dataset=args.dataset, bbox=args.bbox, start=args.start, end=args.end, cloud=args.cloud, limit=args.limit)
        if value.get("universal_satellite", {}).get("temporal_filter_applied") is False:
            print(value["universal_satellite"]["temporal_note"], file=sys.stderr)
        _emit(value, args.output, geojson=True)
    elif args.command == "summary":
        _emit(summarize(read_geojson(args.manifest)))
    elif args.command == "download":
        value = read_geojson(args.manifest)
        failures = 0
        for item in value["features"]:
            try:
                if args.asset not in item.get("assets", {}):
                    raise ValueError(f"asset {args.asset!r} not present")
                if args.sign_planetary:
                    # Sign only the selected asset, never persist signed links.
                    item = Client().sign_item({**item, "assets": {args.asset: item["assets"][args.asset]}})
                print(download_asset(item, args.asset, args.output, overwrite=args.overwrite))
            except (ValueError, DownloadError, ProviderError, OSError) as exc:
                print(f"Download failed for {item['id']}: {exc}", file=sys.stderr)
                failures += 1
        if not value["features"]:
            raise ValueError("Manifest contains no scenes to download")
        return 1 if failures else 0
    elif args.command == "index":
        from .raster import compute_index
        bands = {v: getattr(args, v) for v in ["nir", "red", "green", "blue", "swir16", "swir22"] if getattr(args, v)}
        print(compute_index(args.name, args.output, **bands))
    elif args.command == "weather":
        value = Client().weather(latitude=args.latitude, longitude=args.longitude, start=args.start, end=args.end, variables=args.variables.split(","))
        _emit(value, args.output)
    elif args.command == "toa":
        from .raster import landsat_toa
        print(landsat_toa(args.input, args.mtl, args.band, args.output))
    elif args.command == "doctor":
        _emit({"version": __version__, "python": sys.version.split()[0],
            "stac_search": "installed; live connectivity not checked",
            "raster_dependencies": {v: importlib.util.find_spec(v) is not None for v in ["numpy", "rasterio"]},
            "native_gis_hosts": {v: importlib.util.find_spec(v) is not None for v in ["qgis", "arcpy"]},
            "note": "QGIS and ArcGIS Pro tools run inside their respective installed desktop hosts."})
    return 0


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return run(args)
    except (ValueError, ProviderError, DownloadError, OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
