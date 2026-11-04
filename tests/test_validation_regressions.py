import unittest
from tempfile import TemporaryDirectory
from universal_satellite.download import download_asset
from universal_satellite.client import Client
from universal_satellite.export import validate_geojson
from universal_satellite.http import ProviderError

class ValidationRegressions(unittest.TestCase):
    def test_bad_asset_url_is_validation_error(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                download_asset({'id':'x','assets':{'red':{'href':'https://[broken'}}},'red',d)
    def test_malformed_provider_links(self):
        for links in ([None], None, [{'rel':'next','href':'?page=2','method':None}]):
            class Transport:
                def request_json(self,*a,**k):
                    return {'type':'FeatureCollection','features':[],'links':links}
            with self.subTest(links=links), self.assertRaises(ProviderError):
                Client(transport=Transport()).search(dataset='sentinel-2-l2a',bbox=[1,1,2,2],start='2024-01-01',end='2024-01-02')
    def test_invalid_manifest_assets(self):
        with self.assertRaises(ValueError):
            validate_geojson({'type':'FeatureCollection','features':[{'type':'Feature','id':'x','properties':{},'assets':None}]})
