"""JSON-over-stdin protocol for Node/TypeScript; no shell interpolation."""
import json
import sys
from dataclasses import asdict
from .client import Client
from .catalog import list_datasets
from .download import download_manifest
from .export import read_geojson, summarize


def dispatch(request):
    if not isinstance(request,dict) or not isinstance(request.get('params',{}),dict):raise ValueError('Expected request object with params')
    action=request.get('action');params=request.get('params',{})
    if action=='search':return Client().search(**params)
    if action=='environment':return Client().environment(**params)
    if action=='weather':return Client().weather(**params)
    if action=='sources':return [asdict(x) for x in list_datasets(**params)]
    if action=='download':return download_manifest(**params)
    if action=='summary':return summarize(read_geojson(params['manifest']))
    if action=='index':
        from .raster import compute_index
        return str(compute_index(params['name'],params['output'],constants=params.get('constants'),**params['bands']))
    if action=='crop':
        from .raster import crop_raster
        return str(crop_raster(**params))
    if action=='toa':
        from .raster import landsat_toa
        return str(landsat_toa(**params))
    raise ValueError('Unknown RPC action')


def main():
    try:
        payload=sys.stdin.buffer.read(1024*1024+1)
        if len(payload)>1024*1024:raise ValueError('RPC request exceeds 1 MiB')
        print(json.dumps({'result':dispatch(json.loads(payload))},allow_nan=False))
        return 0
    except Exception as exc:
        # Only a message, no traceback/environment dump.
        print(json.dumps({'error':str(exc)}))
        return 1

if __name__=='__main__':raise SystemExit(main())
