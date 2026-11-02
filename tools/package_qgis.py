#!/usr/bin/env python3
"""Build the native QGIS plugin ZIP; install the core SDK separately in QGIS."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
if __package__:
    from .package_catalog import write_catalog
else:
    from package_catalog import write_catalog


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "gis/qgis/universal_satellite_qgis"


def build(output, force=False):
    output = Path(output)
    if not (PLUGIN / "metadata.txt").is_file():
        raise FileNotFoundError(f"Plugin metadata is missing from {PLUGIN}")
    write_catalog(PLUGIN / "datasets.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w" if force else "x", compression=ZIP_DEFLATED) as archive:
        for path in sorted(PLUGIN.rglob("*")):
            if path.is_file() and path.suffix in (".py", ".txt", ".json") and "__pycache__" not in path.parts:
                archive.write(path, arcname=Path(PLUGIN.name) / path.relative_to(PLUGIN))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/universal_satellite_qgis.zip")
    parser.add_argument("--force", action="store_true", help="Replace an existing archive")
    args = parser.parse_args()
    try:
        print(build(args.output, force=args.force))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
