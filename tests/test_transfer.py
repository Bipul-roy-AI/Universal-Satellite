import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from universal_satellite.transfer import transfer
from universal_satellite.download import DownloadError, DownloadCancelled, download_manifest

class Response(io.BytesIO):
    def __init__(self, data, status=200, **headers):
        super().__init__(data)
        self.status=status
        self.headers=headers

class TransferTests(TestCase):
    def setUp(self):
        self.d=TemporaryDirectory();self.addCleanup(self.d.cleanup)
        self.path=Path(self.d.name)/'image.tif'
    def partial(self):
        response=Response(b'abc',ETag='"v1"',**{'Content-Length':'6'})
        with self.assertRaises(DownloadError):
            transfer('https://example.org/file',self.path,retries=0,opener=lambda *a,**k:response)
        self.assertEqual(self.path.with_suffix('.tif.part').read_bytes(),b'abc')
    def test_resume_checks_range_and_validator(self):
        self.partial()
        def open_request(request,**kwargs):
            self.assertEqual(request.get_header('Range'),'bytes=3-')
            self.assertEqual(request.get_header('If-range'),'"v1"')
            return Response(b'def',206,ETag='"v1"',**{'Content-Length':'3','Content-Range':'bytes 3-5/6'})
        transfer('https://example.org/file',self.path,retries=0,opener=open_request)
        self.assertEqual(self.path.read_bytes(),b'abcdef')
        self.assertEqual(list(Path(self.d.name).iterdir()),[self.path])
    def test_changed_server_restarts_on_200(self):
        self.partial()
        transfer('https://example.org/file',self.path,opener=lambda *a,**k:Response(b'NEW',ETag='"v2"',**{'Content-Length':'3'}))
        self.assertEqual(self.path.read_bytes(),b'NEW')
    def test_wrong_range_never_published(self):
        self.partial()
        with self.assertRaises(DownloadError):
            transfer('https://example.org/file',self.path,opener=lambda *a,**k:Response(b'def',206,**{'Content-Range':'bytes 2-4/6'}))
        self.assertFalse(self.path.exists())
        self.assertFalse(self.path.with_suffix('.tif.part').exists())
    def test_html_is_rejected(self):
        with self.assertRaises(DownloadError):
            transfer('https://example.org/file',self.path,opener=lambda *a,**k:Response(b'login',**{'Content-Type':'text/html'}))
        self.assertFalse(self.path.exists())
    def test_existing_and_cancelled_outputs(self):
        self.path.write_bytes(b'keep')
        with self.assertRaises(FileExistsError): transfer('https://example.org/file',self.path)
        self.path.unlink()
        with self.assertRaises(DownloadCancelled): transfer('https://example.org/file',self.path,cancelled=lambda:True)
        self.assertFalse(self.path.with_suffix('.tif.lock').exists())
    def test_parallel_and_all_assets(self):
        from threading import Barrier
        barrier=Barrier(2,timeout=2)
        manifest=Path(self.d.name)/'manifest.json'
        manifest.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','id':'a','properties':{},'assets':{'red':{'href':'https://a/red'},'nir':{'href':'https://a/nir'}}}]}))
        def download(item,key,*args,**kwargs):
            barrier.wait()
            return Path(self.d.name)/key
        with patch('universal_satellite.download.download_asset',side_effect=download):
            result=download_manifest(manifest,['*'],self.d.name,workers=2,resume=True,retries=2)
        self.assertEqual(len(result['downloaded']),2)
        self.assertFalse(result['failed'])
    def test_416_restarts_without_range(self):
        from urllib.error import HTTPError
        self.partial()
        calls=[]
        def request(req,**kwargs):
            calls.append(req)
            if len(calls)==1:raise HTTPError(req.full_url,416,'range',{},None)
            self.assertIsNone(req.get_header('Range'))
            return Response(b'NEW',**{'Content-Length':'3'})
        with patch('universal_satellite.transfer.time.sleep'):
            transfer('https://example.org/file',self.path,retries=1,opener=request)
        self.assertEqual(self.path.read_bytes(),b'NEW')
    def test_transient_http_error_retries(self):
        from urllib.error import HTTPError
        replies=[HTTPError('https://example.org/file',503,'temporary',{},None),Response(b'ok',**{'Content-Length':'2'})]
        def request(*args,**kwargs):
            value=replies.pop(0)
            if isinstance(value,Exception):raise value
            return value
        with patch('universal_satellite.transfer.time.sleep'):
            transfer('https://example.org/file',self.path,retries=1,opener=request)
        self.assertEqual(self.path.read_bytes(),b'ok')
