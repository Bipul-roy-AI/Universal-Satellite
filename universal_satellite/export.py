"""Portable STAC/GeoJSON manifests and scene-inventory summaries."""
from collections import Counter
import json
import os
from pathlib import Path
import tempfile


def write_json(value, path):
    """Replace a JSON output atomically, never leaving a partial manifest."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, delete=False) as stream:
            name = stream.name
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
        os.replace(name, target)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)
    return target


def validate_geojson(value):
    if not isinstance(value, dict) or value.get("type") != "FeatureCollection" or not isinstance(value.get("features"), list):
        raise ValueError("Expected a GeoJSON FeatureCollection")
    for feature in value["features"]:
        if not isinstance(feature, dict) or feature.get("type") != "Feature" or not feature.get("id") or not isinstance(feature.get("properties"), dict):
            raise ValueError("Expected STAC features with id and properties")
    return value


def read_geojson(path):
    return validate_geojson(json.loads(Path(path).read_text(encoding="utf-8")))


def write_geojson(value, path):
    return write_json(validate_geojson(value), path)


def summarize(value):
    validate_geojson(value)
    dates, months, collections, assets, platforms = [], Counter(), Counter(), Counter(), Counter()
    for item in value["features"]:
        props = item["properties"]
        when = props.get("datetime") or props.get("start_datetime")
        if when:
            dates.append(when)
            months[when[:7]] += 1
        collections[item.get("collection", "unknown")] += 1
        platforms[props.get("platform", "unknown")] += 1
        assets.update(item.get("assets", {}).keys())
    return {
        "scenes": len(value["features"]), "earliest": min(dates) if dates else None,
        "latest": max(dates) if dates else None, "scenes_by_month": dict(sorted(months.items())),
        "collections": dict(collections), "platforms": dict(platforms),
        "asset_scene_counts": dict(assets),
        "search_complete": value.get("universal_satellite", {}).get("search_complete"),
        "note": "Inventory of returned metadata only; not a pixel time series or proof of complete archive coverage.",
    }
