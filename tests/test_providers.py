import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit, parse_qs
from universal_satellite.client import Client
from universal_satellite.http import ProviderError, Transport
from universal_satellite.auth import ScopedRedirect, headers_for
from urllib.request import Request

class ProviderTests(unittest.TestCase):
    def test_cmr_uses_returned_data_links_only(self):
        transport=Mock()
        transport.request_json.return_value={'feed':{'entry':[{'id':'G1','time_start':'2025-01-01T00:00:00Z','boxes':['10 20 11 21'],'links':[
            {'rel':'http://esipfed.org/ns/fedsearch/1.1/data#','href':'https://data.example/a.h5'},
            {'rel':'http://esipfed.org/ns/fedsearch/1.1/documentation#','href':'https://example/doc'},
            {'rel':'http://esipfed.org/ns/fedsearch/1.1/data#','href':'https://example/inherited','inherited':True}]}]}}
        result=Client(transport=transport).search(dataset='smap-l4',bbox=[20,10,21,11],start='2025-01-01',end='2025-01-02',limit=2)
        item=result['features'][0]
        self.assertEqual(list(item['assets']),['data'])
        self.assertEqual(item['bbox'],[20,10,21,11])
        self.assertNotIn('hydrology_metrics',item['properties'])
        self.assertTrue(result['universal_satellite']['search_complete'])
        query=parse_qs(urlsplit(transport.request_json.call_args.args[0]).query)
        self.assertEqual(query['short_name'],['SPL4SMGP'])
    def test_cmr_invalid_response_and_unimplemented_cloud(self):
        t=Mock();t.request_json.return_value={'feed':None}
        with self.assertRaises(ProviderError): Client(transport=t).search(dataset='gpm-imerg',bbox=[1,1,2,2],start='2025-01-01',end='2025-01-02')
        with self.assertRaises(ValueError): Client(transport=t).search(dataset='gpm-imerg',bbox=[1,1,2,2],start='2025-01-01',end='2025-01-02',cloud=20)
    def test_cdse_real_product_id_and_filter(self):
        t=Mock();t.request_json.return_value={'value':[{'Id':'12345678-1234-1234-1234-123456789abc','Name':'product','ContentDate':{'Start':'2025-01-01T00:00:00Z'},'GeoFootprint':None}]}
        result=Client(transport=t).search(dataset='sentinel-2-products',bbox=[1,1,2,2],start='2025-01-01',end='2025-01-02',cloud=20,limit=1)
        self.assertIn('12345678-1234-1234-1234-123456789abc',result['features'][0]['assets']['product']['href'])
        self.assertIn('cloudCover',parse_qs(urlsplit(t.request_json.call_args.args[0]).query)['$filter'][0])
    def test_enmap_uses_get_items_without_post(self):
        t=Mock();t.request_json.return_value={'type':'FeatureCollection','features':[]}
        Client(transport=t).search(dataset='enmap-l2a',bbox=[1,1,2,2],start='2025-01-01',end='2025-01-02')
        self.assertEqual(t.request_json.call_args.kwargs['method'],'GET')
        self.assertIn('/collections/ENMAP_HSI_L2A/items?',t.request_json.call_args.args[0])
    def test_forecast_retains_provider_units(self):
        t=Mock();t.request_json.return_value={'hourly':{'time':['t'],'temperature_2m':[19]},'hourly_units':{'temperature_2m':'°C'}}
        result=Client(transport=t).environment('forecast',latitude=48,longitude=9,variables=['temperature_2m'])
        self.assertEqual(result['hourly']['temperature_2m'],[19])
        self.assertEqual(result['hourly_units']['temperature_2m'],'°C')
        self.assertIn('ECMWF',result['universal_satellite']['attribution'])
    def test_soil_outage_not_fabricated(self):
        t=Mock();t.request_json.side_effect=ProviderError('down')
        with self.assertRaisesRegex(ProviderError,'No substitute values'):
            Client(transport=t).environment('soil',latitude=48,longitude=9)
    def test_auth_does_not_follow_foreign_redirects(self):
        with patch.dict('os.environ',{'EARTHDATA_TOKEN':'secret','UNIVERSAL_SATELLITE_TOKEN_HOSTS':'{}'}):
            self.assertEqual(headers_for('https://data.earthdata.nasa.gov/a')['Authorization'],'Bearer secret')
            self.assertEqual(headers_for('https://data.earthdata.nasa.gov.evil.test/a'),{})
            request=Request('https://data.earthdata.nasa.gov/a',headers={'Authorization':'Bearer secret'})
            redirected=ScopedRedirect().redirect_request(request,None,302,'',{},'https://example.test/a')
            self.assertIsNone(redirected.get_header('Authorization'))
            with self.assertRaises(ValueError): ScopedRedirect().redirect_request(request,None,302,'',{},'http://example.test/a')
    def test_get_does_not_claim_json_request_body(self):
        from io import BytesIO
        response=BytesIO(b'{}')
        with patch('universal_satellite.http.urlopen',return_value=response) as request:
            Transport().request_json('https://example.test')
        self.assertIsNone(request.call_args.args[0].get_header('Content-type'))
    def test_firms_key_never_enters_manifest(self):
        import io
        body=b'latitude,longitude,acq_date,acq_time,frp\n48.1,9.1,2025-01-01,0310,8.4\n'
        with patch.dict('os.environ',{'FIRMS_MAP_KEY':'secret'}),patch('universal_satellite.providers.urlopen',return_value=io.BytesIO(body)):
            result=Client().search(dataset='firms-viirs',bbox=[9,48,10,49],start='2025-01-01',end='2025-01-01',limit=10)
        import json
        self.assertNotIn('secret',json.dumps(result))
        self.assertEqual(result['features'][0]['properties']['frp'],'8.4')
        self.assertEqual(result['features'][0]['geometry']['coordinates'],[9.1,48.1])
    def test_chirps_uses_listed_files_not_guessed_dates(self):
        import io
        html=b'<a href="chirps-v2.0.2024.01.01.tif.gz">file</a><a href="https://evil.test/data">ignore</a>'
        with patch('universal_satellite.providers.urlopen',return_value=io.BytesIO(html)):
            result=Client().search(dataset='chirps-daily',bbox=[9,48,10,49],start='2024-01-01',end='2024-01-02',limit=10)
        self.assertEqual(len(result['features']),1)
        self.assertTrue(result['features'][0]['assets']['precipitation']['href'].endswith('/2024/chirps-v2.0.2024.01.01.tif.gz'))
    def test_dynamic_world_requires_explicit_project(self):
        import sys,types
        with patch.dict(sys.modules,{'ee':types.ModuleType('ee')}),patch.dict('os.environ',{'EE_PROJECT':''}):
            with self.assertRaisesRegex(ProviderError,'EE_PROJECT'):
                Client().search(dataset='dynamic-world',bbox=[9,48,9.001,48.001],start='2024-01-01',end='2024-01-02',limit=1)
