"""Operator guide coverage and actual manifest help, without a desktop GIS host."""
import json
from pathlib import Path
from unittest.mock import patch
from test_gis_contract import fake_qgis, load_module
from universal_satellite.catalog import list_datasets

ROOT = Path(__file__).resolve().parents[1]


def test_every_searchable_dataset_has_offline_help():
    guide = json.loads((ROOT / 'universal_satellite/asset_guide.json').read_text())
    assert set(guide['datasets']) == {s.id for s in list_datasets() if s.status == 'searchable'}
    for folder in ['gis/arcgis', 'gis/qgis/universal_satellite_qgis']:
        assert json.loads((ROOT / folder / 'asset_guide.json').read_text()) == guide
    assert 'data' in guide['datasets']['cop-dem-glo-30']['keys']
    assert 'elevation' in guide['datasets']['nasadem']['keys']
    assert not guide['datasets']['firms-viirs']['keys']


def test_help_lists_actual_custom_assets_without_signed_urls(tmp_path):
    with patch.dict('sys.modules', fake_qgis()):
        module = load_module('asset_guide_qgis_test', ROOT / 'gis/qgis/universal_satellite_qgis/algorithms.py')
    path = tmp_path / 'manifest.geojson'
    path.write_text(json.dumps({'features': [{'assets': {'custom': {
        'title': 'Custom quality mask', 'type': 'image/tiff', 'href': 'https://example.org/file?secret=TOKEN'
    }}}]}))
    help_text = module._manifest_asset_help(path)
    assert 'custom = Custom quality mask = image/tiff' in help_text
    assert 'TOKEN' not in help_text
    assert 'Copernicus DEM' in module.DownloadAssets().shortHelpString()
    assert 'elevation = Elevation' in module.SearchScenes().shortHelpString()
