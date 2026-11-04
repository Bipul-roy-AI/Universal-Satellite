"""Opt-in environment credentials scoped to exact HTTPS hosts.

Redirects never inherit Authorization. A redirected host receives only its own
configured credential. No credential values are logged or written to manifests.
"""
import base64
import json
import os
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener


def headers_for(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https': return {}
    host = parsed.hostname or ''
    token = None
    if host.endswith('.earthdata.nasa.gov'):
        token = os.environ.get('EARTHDATA_TOKEN')
    elif host in ('download.dataspace.copernicus.eu','zipper.dataspace.copernicus.eu'):
        token = os.environ.get('CDSE_ACCESS_TOKEN')
    # Optional map is host -> environment-variable NAME, never token values.
    config = os.environ.get('UNIVERSAL_SATELLITE_TOKEN_HOSTS','{}')
    try:
        mapping = json.loads(config)
        if not isinstance(mapping,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in mapping.items()): raise ValueError()
    except ValueError:
        raise ValueError('UNIVERSAL_SATELLITE_TOKEN_HOSTS must map exact hostnames to token environment-variable names') from None
    if host in mapping: token = os.environ.get(mapping[host])
    if token: return {'Authorization':'Bearer '+token}
    if host == 'download.geoservice.dlr.de':
        user,password = os.environ.get('DLR_USERNAME'),os.environ.get('DLR_PASSWORD')
        if user and password:
            encoded = base64.b64encode((user+':'+password).encode()).decode()
            return {'Authorization':'Basic '+encoded}
    return {}


class ScopedRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != 'https' and ('Authorization' in req.headers or urlsplit(req.full_url).scheme == 'https'):
            raise ValueError('Refusing an HTTPS download redirect to an insecure scheme')
        redirected = super().redirect_request(req,fp,code,msg,headers,newurl)
        if redirected is not None:
            redirected.remove_header('Authorization')
            for key,value in headers_for(newurl).items(): redirected.add_header(key,value)
        return redirected


def open_asset(request, timeout=60):
    for key,value in headers_for(request.full_url).items(): request.add_header(key,value)
    return build_opener(ScopedRedirect()).open(request,timeout=timeout)
