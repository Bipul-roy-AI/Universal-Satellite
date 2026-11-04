"""Provider-backed environmental discovery. Never synthesize observations."""
from datetime import date, timedelta
from html.parser import HTMLParser
import re
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import urlopen
from .http import ProviderError


def inventory(source, items, query, complete):
    return {'type':'FeatureCollection','features':items,'universal_satellite':{
        'dataset':source.id,'endpoint':source.endpoint,'query':query,
        'returned':len(items),'search_complete':complete,'attribution':source.provider,
        'access':source.access,'temporal_filter_applied':source.temporal,
        'note':'Provider metadata and native assets; no derived measurements are invented.'}}


def cmr_search(transport, source, bbox, start, end, limit):
    query={'short_name':source.collection,'bounding_box':','.join(map(str,bbox)),
           'temporal':f'{start}T00:00:00Z,{end}T23:59:59.999Z','page_size':min(limit,100),
           'sort_key':'-start_date'}
    items=[];seen=set();complete=False
    for page in range(1,101):
        data=transport.request_json(source.endpoint+'?'+urlencode({**query,'page_num':page}))
        entries=data.get('feed',{}).get('entry') if isinstance(data.get('feed'),dict) else None
        if not isinstance(entries,list): raise ProviderError('CMR returned invalid granule metadata')
        if not entries: complete=True;break
        added=0
        for entry in entries:
            if not isinstance(entry,dict) or not isinstance(entry.get('id'),str): raise ProviderError('Invalid CMR granule')
            if entry['id'] in seen: continue
            seen.add(entry['id']);added+=1
            assets={}
            links=entry.get('links',[])
            if not isinstance(links,list): raise ProviderError('Invalid CMR links')
            for link in links:
                if not isinstance(link,dict): raise ProviderError('Invalid CMR asset link')
                href=link.get('href','')
                if not isinstance(href,str) or not href.startswith('https://') or link.get('inherited'): continue
                # CMR also advertises documentation, browse and service URLs.
                if not str(link.get('rel','')).endswith('/data#'): continue
                key='data' if not assets else f'data_{len(assets)+1}'
                assets[key]={'href':href,'type':link.get('type','application/octet-stream'),'title':link.get('title',key),'roles':['data']}
            props={'datetime':entry.get('time_start'),'end_datetime':entry.get('time_end'),
                   'provider':source.provider,'cmr:metadata':entry,'license':'See collection/provider data policy'}
            geometry=None;bounds=None
            boxes=entry.get('boxes',[])
            if boxes:
                try:
                    south,west,north,east=map(float,boxes[0].split())
                    if -180 <= west < east <= 180 and -90 <= south < north <= 90:
                        bounds=[west,south,east,north]
                        geometry={'type':'Polygon','coordinates':[[[west,south],[east,south],[east,north],[west,north],[west,south]]]}
                except (ValueError,TypeError,AttributeError): pass
            item={'type':'Feature','id':entry['id'],'collection':source.id,'geometry':geometry,'properties':props,'assets':assets}
            if bounds: item['bbox']=bounds
            items.append(item)
            if len(items)==limit: break
        if len(items)>=limit: break
        if len(entries)<query['page_size']: complete=True;break
        if not added: raise ProviderError('CMR pagination did not advance')
    return inventory(source,items,query,complete)


def cdse_search(transport,source,bbox,start,end,limit,cloud=None):
    w,s,e,n=bbox
    polygon=f'POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))'
    expression=(f"Collection/Name eq '{source.collection}' and ContentDate/Start ge {start}T00:00:00.000Z "
                f"and ContentDate/Start lt {(date.fromisoformat(end)+timedelta(days=1)).isoformat()}T00:00:00.000Z "
                f"and OData.CSC.Intersects(area=geography'SRID=4326;{polygon}')")
    if cloud is not None:
        expression += f" and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {cloud})"
    query={'$filter':expression,'$top':min(limit,100),'$orderby':'ContentDate/Start desc'}
    url=source.endpoint+'?'+urlencode(query)
    items=[];seen=set();complete=False
    while url and len(items)<limit:
        if url in seen: raise ProviderError('Copernicus pagination did not advance')
        seen.add(url)
        if len(seen)>100: raise ProviderError('Copernicus exceeded 100 pages; narrow your query')
        if urlsplit(url).scheme!='https' or urlsplit(url).netloc!=urlsplit(source.endpoint).netloc:
            raise ProviderError('Refusing foreign Copernicus pagination URL')
        data=transport.request_json(url)
        if not isinstance(data.get('value'),list): raise ProviderError('Invalid Copernicus product catalog response')
        for row in data['value']:
            identifier=row.get('Id') if isinstance(row,dict) else None
            if not isinstance(identifier,str) or not re.fullmatch(r'[a-fA-F0-9-]{36}',identifier): raise ProviderError('Invalid Copernicus product identifier')
            items.append({'type':'Feature','id':identifier,'collection':source.id,'geometry':row.get('GeoFootprint'),
                'properties':{'datetime':row.get('ContentDate',{}).get('Start'),'title':row.get('Name'),'provider':source.provider},
                'assets':{'product':{'href':f'https://download.dataspace.copernicus.eu/odata/v1/Products({identifier})/$value',
                                     'title':'Native product archive; CDSE_ACCESS_TOKEN required','type':'application/zip','roles':['data']}}})
            if len(items)==limit: break
        url=data.get('@odata.nextLink')
        if url is not None and not isinstance(url,str): raise ProviderError('Invalid Copernicus next link')
        complete=not url and len(data['value'])<query['$top']
        if not url:break
    return inventory(source,items,query,complete)


class _Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a': self.links.extend(v for k,v in attrs if k=='href' and v)


def chirps_search(transport,source,bbox,start,end,limit):
    if bbox[1]>=50 or bbox[3]<=-50: return inventory(source,[],{},True)
    items=[];first,last=date.fromisoformat(start),date.fromisoformat(end)
    if last.year-first.year>10: raise ValueError('Request CHIRPS in windows of at most 11 calendar years')
    for year in range(max(1981,first.year),last.year+1):
        url=f'{source.endpoint}/{year}/'
        try:
            with urlopen(url,timeout=30) as response:
                body=response.read(4*1024*1024+1)
                if len(body)>4*1024*1024: raise ProviderError('CHIRPS directory exceeds safe size')
        except OSError: raise ProviderError('CHIRPS directory unavailable; verify publication dates/provider status') from None
        parser=_Links();parser.feed(body.decode('utf-8'))
        for link in sorted(set(parser.links)):
            match=re.fullmatch(r'chirps-v2\.0\.(\d{4})\.(\d{2})\.(\d{2})\.tif(?:\.gz)?',link)
            if not match:continue
            day=date(*map(int,match.groups()))
            if not first<=day<=last:continue
            items.append({'type':'Feature','id':link,'collection':source.id,
                'geometry':{'type':'Polygon','coordinates':[[[-180,-50],[180,-50],[180,50],[-180,50],[-180,-50]]]},
                'properties':{'datetime':day.isoformat()+'T00:00:00Z','provider':source.provider,'units':'mm/day'},
                'assets':{'precipitation':{'href':urljoin(url,link),'type':'application/gzip' if link.endswith('.gz') else 'image/tiff','roles':['data']}}})
            if len(items)==limit:return inventory(source,items,{'start':start,'end':end},False)
    return inventory(source,items,{'start':start,'end':end},True)


def search(transport,source,bbox,start,end,limit,cloud=None):
    handlers={'cmr':cmr_search,'cdse':cdse_search,'chirps':chirps_search,'firms':firms_search,'earthengine':dynamic_world_search}
    if source.adapter=='cdse': return cdse_search(transport,source,bbox,start,end,limit,cloud)
    return handlers[source.adapter](transport,source,bbox,start,end,limit)


def firms_search(transport,source,bbox,start,end,limit):
    import csv,io,os,math
    key=os.environ.get('FIRMS_MAP_KEY')
    if not key or not re.fullmatch(r'[A-Za-z0-9_-]+',key):
        raise ProviderError('Set FIRMS_MAP_KEY to your NASA FIRMS API key; no key is required for the separate CMR fire-product adapter')
    days=(date.fromisoformat(end)-date.fromisoformat(start)).days+1
    if not 1<=days<=10:raise ValueError('FIRMS requests must cover 1–10 days; archive availability depends on the selected source')
    url=f'{source.endpoint}/{key}/{source.collection}/{",".join(map(str,bbox))}/{days}/{start}'
    try:
        with urlopen(url,timeout=30) as response:
            payload=response.read(16*1024*1024+1)
        if len(payload)>16*1024*1024:raise ProviderError('FIRMS response exceeds 16 MiB; reduce the area/date window')
        rows=csv.DictReader(io.StringIO(payload.decode('utf-8-sig')))
        if not {'latitude','longitude','acq_date','acq_time'}.issubset(rows.fieldnames or []):
            raise ProviderError('FIRMS returned no valid CSV; check key, quota and source date availability')
        items=[];truncated=False
        for number,row in enumerate(rows):
            lat,lon=float(row['latitude']),float(row['longitude'])
            if not math.isfinite(lat) or not math.isfinite(lon):raise ValueError()
            if not bbox[0]<=lon<=bbox[2] or not bbox[1]<=lat<=bbox[3] or not start<=row['acq_date']<=end:continue
            if len(items)==limit:truncated=True;break
            hhmm=row['acq_time'].zfill(4)
            items.append({'type':'Feature','id':f'{source.collection}-{row["acq_date"]}-{hhmm}-{number}',
                'collection':source.id,'geometry':{'type':'Point','coordinates':[lon,lat]},
                'properties':{**row,'datetime':f'{row["acq_date"]}T{hhmm[:2]}:{hhmm[2:]}:00Z','provider':source.provider},'assets':{}})
    except (OSError,UnicodeError,ValueError):
        raise ProviderError('FIRMS request failed or returned invalid observations; verify key, quota and date availability') from None
    return inventory(source,items,{'bbox':bbox,'start':start,'end':end},not truncated)


def dynamic_world_search(transport,source,bbox,start,end,limit):
    import os,math
    from datetime import datetime,timezone
    try:import ee
    except ImportError:raise RuntimeError('Install universal-satellite[earthengine] and configure Earth Engine credentials plus EE_PROJECT') from None
    project=os.environ.get('EE_PROJECT')
    if not project:raise ProviderError('Set EE_PROJECT to your authorized Earth Engine Cloud project; authenticate outside this tool first')
    # Small synchronous downloads only; larger jobs need provider batch exports.
    width=(bbox[2]-bbox[0])*111320*max(0.01,math.cos(math.radians((bbox[1]+bbox[3])/2)))
    height=(bbox[3]-bbox[1])*111320
    if width*height/100*10*4>24*1024*1024 or max(width,height)/10>10000:
        raise ValueError('Dynamic World AOI exceeds the synchronous download budget; split it or use an Earth Engine batch export')
    if limit>20:raise ValueError('Dynamic World synchronous export is limited to 20 images per request')
    try:
        ee.Initialize(project=project)
        region=ee.Geometry.Rectangle(bbox,proj='EPSG:4326',geodesic=False)
        collection=ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1').filterBounds(region).filterDate(start,(date.fromisoformat(end)+timedelta(days=1)).isoformat()).sort('system:time_start',False).limit(limit)
        records=collection.getInfo().get('features',[])
        items=[]
        for record in records:
            identifier=record['id'];props=record.get('properties',{})
            image=ee.Image(identifier)
            href=image.getDownloadURL({'region':region,'scale':10,'format':'GEO_TIFF'})
            if not isinstance(href,str) or not href.startswith('https://'):raise ValueError('Invalid provider download URL')
            when=datetime.fromtimestamp(props['system:time_start']/1000,timezone.utc).isoformat()
            items.append({'type':'Feature','id':identifier,'collection':source.id,'geometry':record.get('geometry'),
                'properties':{**props,'datetime':when,'provider':source.provider,'note':'AOI-cropped label/probability image; provider download URL expires'},
                'assets':{'data':{'href':href,'type':'image/tiff','roles':['data']}}})
    except Exception:
        raise ProviderError('Earth Engine search/export failed; check credentials, project access, quota and AOI size') from None
    return inventory(source,items,{'bbox':bbox,'start':start,'end':end},len(items)<limit)
