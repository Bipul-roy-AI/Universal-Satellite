#!/usr/bin/env python3
"""Package the ArcGIS Pro Python toolbox and its extraction/install instructions."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
if __package__:
    from .package_catalog import write_catalog
else:
    from package_catalog import write_catalog


ROOT = Path(__file__).resolve().parents[1]
TOOLBOX = ROOT / "gis/arcgis"


def build(output, force=False):
    files = [TOOLBOX / "UniversalSatellite.pyt", TOOLBOX / "INSTALL.md", TOOLBOX / "indices.json", write_catalog(TOOLBOX / "datasets.json")]
    files.append(TOOLBOX / "asset_guide.json")
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(f"Missing toolbox package input: {path}")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w" if force else "x", compression=ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, arcname=Path("UniversalSatellite") / path.name)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/universal_satellite_arcgis.zip")
    parser.add_argument("--force", action="store_true", help="Replace an existing archive")
    args = parser.parse_args()
    try:
        print(build(args.output, force=args.force))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
