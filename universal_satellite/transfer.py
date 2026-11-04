"""Validated HTTP range resumption with per-destination exclusive locks."""
import hashlib
import json
import os
from pathlib import Path
import re
import time
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def transfer(href, destination, *, timeout=60, overwrite=False, resume=True,
             retries=2, cancelled=None, headers=None, opener=None):
    from .download import DownloadError, DownloadCancelled
    from .auth import open_asset
    if isinstance(retries,bool) or not isinstance(retries,int) or not 0 <= retries <= 10:
        raise ValueError('retries must be an integer from 0 through 10')
    path = Path(destination)
    part = path.with_name(path.name + '.part')
    meta = path.with_name(path.name + '.part.json')
    lock = path.with_name(path.name + '.lock')
    identity = hashlib.sha256(href.encode()).hexdigest()
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise DownloadError('Another download owns this destination; remove its lock only after confirming it has stopped.') from None
    os.close(lock_fd)
    def check_cancel():
        if cancelled and cancelled():
            raise DownloadCancelled('Download cancelled; verified partial data retained for resumption.')
    def clear():
        part.unlink(missing_ok=True)
        meta.unlink(missing_ok=True)
    def state():
        try:
            value = json.loads(meta.read_text())
            if resume and part.is_file() and value.get('identity') == identity and value.get('etag'):
                return value,part.stat().st_size
        except (OSError,ValueError,AttributeError):
            pass
        clear()
        return {},0
    try:
        if not overwrite and (path.exists() or path.is_symlink()):
            raise FileExistsError(f'Download already exists: {path}')
        for attempt in range(retries + 1):
            check_cancel()
            saved, offset = state()
            request_headers = {'User-Agent':'Universal-Satellite/0.3.0','Accept-Encoding':'identity',**(headers or {})}
            if offset:
                request_headers.update({'Range':f'bytes={offset}-','If-Range':saved['etag']})
            try:
                with (opener or open_asset)(Request(href,headers=request_headers),timeout=timeout) as response:
                    status = response.status
                    if status not in (200,206):
                        raise DownloadError(f'Unexpected asset HTTP {status}')
                    if response.headers.get('Content-Encoding','identity') not in ('identity',''):
                        raise DownloadError('Encoded responses cannot be safely resumed')
                    if response.headers.get('Content-Type','').split(';')[0].lower() in ('text/html','application/xhtml+xml'):
                        raise DownloadError('Server returned a login/HTML page instead of image data')
                    etag = response.headers.get('ETag','')
                    etag = etag if etag and not etag.startswith('W/') else ''
                    length = response.headers.get('Content-Length')
                    try:
                        length = int(length) if length is not None else None
                        if length is not None and length < 0: raise ValueError()
                    except ValueError:
                        raise DownloadError('Invalid Content-Length') from None
                    if status == 206:
                        match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
                        if not offset or not match:
                            clear()
                            raise DownloadError('Invalid or unsolicited partial response')
                        start,end,total = map(int,match.groups())
                        if start != offset or end < start or end != total-1 or (length is not None and length != end-start+1) or (etag and etag != saved['etag']) or (saved.get('total') is not None and total != saved['total']):
                            clear()
                            raise DownloadError('Partial response does not match the saved file')
                        mode = 'ab'
                    else:
                        offset,total,mode = 0,length,'wb'
                        clear()
                    # Metadata contains only a URL hash and validator, never credentials.
                    meta.write_text(json.dumps({'identity':identity,'etag':etag or saved.get('etag','') if status==206 else etag,'total':total}))
                    written = offset
                    with part.open(mode) as target:
                        while True:
                            check_cancel()
                            chunk = response.read(1024*1024)
                            if not chunk: break
                            target.write(chunk)
                            written += len(chunk)
                            if total is not None and written > total:
                                raise DownloadError('Asset exceeds advertised size')
                        target.flush()
                        os.fsync(target.fileno())
                    if total is not None and written != total:
                        raise ConnectionError('Incomplete asset')
                check_cancel()
                if overwrite: os.replace(part,path)
                else:
                    os.link(part,path)
                    part.unlink()
                meta.unlink(missing_ok=True)
                return path
            except HTTPError as exc:
                code = exc.code
                exc.close()
                if code == 416:
                    clear()  # Never assume a local partial file is complete.
                elif code not in (429,500,502,503,504):
                    raise DownloadError(f'Asset HTTP {code}; check provider access or refresh its signed URL') from None
                if attempt == retries: raise DownloadError(f'Asset HTTP {code}; retry limit reached') from None
            except (URLError,TimeoutError,ConnectionError,HTTPException):
                if attempt == retries:
                    raise DownloadError('Transfer interrupted; resumable partial data retained when the server supplied a validator') from None
            if attempt < retries:
                # Short waits keep cancellation responsive.
                for _ in range(10 * min(2**attempt,4)):
                    check_cancel()
                    time.sleep(0.1)
    finally:
        if not resume: clear()
        lock.unlink(missing_ok=True)
