"""Generate offline toolbox dataset menus from the authoritative core catalog."""

from dataclasses import asdict
import json
from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]


def write_catalog(destination):
    # Load only the dependency-free catalog; packaging does not need an SDK install.
    catalog = runpy.run_path(str(ROOT / "universal_satellite/catalog.py"))
    records = [asdict(source) for source in catalog["list_datasets"]() if source.status == "searchable"]
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "datasets": records}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    for directory in [ROOT / "gis/arcgis", ROOT / "gis/qgis/universal_satellite_qgis"]:
        print(write_catalog(directory / "datasets.json"))
