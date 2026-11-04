"""Point forecasts, CAMS air quality and SoilGrids queries with provenance."""
import math
from urllib.parse import urlencode
from .http import ProviderError


def profile(transport, kind, *, latitude, longitude, model='ecmwf_ifs', variables=None, depth='0-5cm'):
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (latitude,longitude)) or not (-90<=latitude<=90 and -180<=longitude<=180):
        raise ValueError('Use finite WGS84 latitude/longitude')
    if variables is not None and (not isinstance(variables,(list,tuple)) or not variables or any(not isinstance(v,str) for v in variables)):
        raise ValueError('variables must be a nonempty list of names')
    if kind=='forecast':
        if model not in ('ecmwf_ifs','gfs_seamless'): raise ValueError('model must be ecmwf_ifs or gfs_seamless')
        allowed={'temperature_2m','relative_humidity_2m','precipitation','wind_speed_10m','shortwave_radiation','et0_fao_evapotranspiration','vapour_pressure_deficit'}
        variables=variables or ['temperature_2m','precipitation','et0_fao_evapotranspiration','vapour_pressure_deficit','shortwave_radiation']
        endpoint='https://api.open-meteo.com/v1/forecast'
        params={'latitude':latitude,'longitude':longitude,'hourly':','.join(variables),'models':model,'timezone':'UTC','forecast_days':7}
        attribution='Open-Meteo / ECMWF IFS' if model=='ecmwf_ifs' else 'Open-Meteo / NOAA GFS'
    elif kind=='air-quality':
        allowed={'pm2_5','pm10','carbon_monoxide','nitrogen_dioxide','sulphur_dioxide','ozone','aerosol_optical_depth','dust'}
        variables=variables or ['pm2_5','nitrogen_dioxide','carbon_monoxide','aerosol_optical_depth']
        endpoint='https://air-quality-api.open-meteo.com/v1/air-quality'
        params={'latitude':latitude,'longitude':longitude,'hourly':','.join(variables),'timezone':'UTC','domains':'cams_global'}
        attribution='Open-Meteo / Copernicus Atmosphere Monitoring Service (CAMS)'
    elif kind=='soil':
        allowed={'phh2o','soc','clay','sand','silt','nitrogen','cec','bdod','cfvo','ocd','ocs'}
        variables=variables or ['phh2o','soc','clay','sand','nitrogen','cec']
        if depth not in ('0-5cm','5-15cm','15-30cm','30-60cm','60-100cm','100-200cm'): raise ValueError('Unsupported SoilGrids depth')
        endpoint='https://rest.isric.org/soilgrids/v2.0/properties/query'
        params={'lat':latitude,'lon':longitude,'property':variables,'depth':depth,'value':'mean'}
        attribution='ISRIC SoilGrids 250 m; model predictions, not field measurements'
    else: raise ValueError('kind must be forecast, air-quality or soil')
    if not isinstance(variables,(list,tuple)) or not variables or any(not isinstance(v,str) or v not in allowed for v in variables):
        raise ValueError('Unsupported variables; choose '+', '.join(sorted(allowed)))
    try: result=transport.request_json(endpoint+'?'+urlencode(params,doseq=True))
    except ProviderError:
        if kind=='soil': raise ProviderError('SoilGrids REST is unavailable. ISRIC reports a service pause; use its raster/WCS service or retry after restoration. No substitute values were generated.') from None
        raise
    if kind=='soil':
        props=result.get('properties',{})
        if not isinstance(props,dict) or not isinstance(props.get('layers'),list) or not props['layers']:
            raise ProviderError('SoilGrids returned no layers')
    else:
        hourly=result.get('hourly',{})
        if not isinstance(hourly,dict) or not isinstance(hourly.get('time'),list) or not hourly['time']:
            raise ProviderError('Environment provider returned no time series')
        if any(not isinstance(hourly.get(v),list) or len(hourly[v])!=len(hourly['time']) for v in variables):
            raise ProviderError('Environment provider returned inconsistent time series')
        if all(x is None for v in variables for x in hourly[v]): raise ProviderError('Environment provider returned only missing values')
    result['universal_satellite']={'kind':kind,'endpoint':endpoint,'attribution':attribution,'query':params,
        'note':'Native provider values and units retained. This is a point/model profile, not a satellite image.'}
    return result
