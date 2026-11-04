"""Curated source directory; dates describe records, not guaranteed catalog extents.

Collection identifiers are grounded in provider-maintained Earth Search and
Planetary Computer documentation. Reference entries intentionally have no adapter.
"""
from dataclasses import dataclass

EARTH_SEARCH = "https://earth-search.aws.element84.com/v1"
PLANETARY_COMPUTER = "https://planetarycomputer.microsoft.com/api/stac/v1"
USGS_LANDSAT = "https://landsatlook.usgs.gov/stac-server"


@dataclass(frozen=True)
class Dataset:
    id: str
    title: str
    category: str
    start: str
    end: str | None
    resolution: str
    provider: str
    endpoint: str | None
    collection: str | None
    access: str
    description: str
    docs_url: str
    status: str = "searchable"
    temporal: bool = True
    processing_level: str | None = None
    measurement: str | None = None
    adapter: str = "stac"


_DATASETS = (
    Dataset(
        "corona", "Declassified CORONA reconnaissance photography", "historical",
        "1960-01-01", "1972-12-31", "Variable; film photography", "USGS",
        None, None, "USGS EarthExplorer; account and scanning availability vary",
        "Historical photographs; georeferencing, orthorectification and some scans require additional work.",
        "https://www.usgs.gov/centers/eros/science/usgs-eros-archive-declassified-data-declassified-satellite-imagery-1", "reference",
    ),
    Dataset(
        "landsat-mss", "Landsat 1–5 MSS archive", "optical",
        "1972-01-01", "2013-12-31", "About 60–80 m", "USGS",
        None, None, "USGS EarthExplorer / Landsat archive; account may be required",
        "Early Landsat record. MSS is not included in the Collection 2 Level-2 adapter; processing differs from modern surface reflectance.",
        "https://www.usgs.gov/landsat-missions/landsat-collection-2", "reference",
    ),
    Dataset(
        "landsat-c2-l2", "Landsat 4–9 Collection 2 Level-2 surface reflectance (SR)", "optical",
        "1982-01-01", None, "30 m reflectance; thermal varies", "Microsoft Planetary Computer / USGS",
        PLANETARY_COMPUTER, "landsat-c2-l2", "Public metadata; Azure assets commonly need temporary SAS signing",
        "Surface reflectance and available surface temperature. Covers TM, ETM+, OLI/TIRS; QA, scaling and sensor harmonization matter. Assets are HTTPS Azure blobs, so enable Planetary Computer signing when downloading.",
        "https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2",
        processing_level="L2", measurement="Surface reflectance (SR); available surface temperature",
    ),
    Dataset(
        "sentinel-2-l2a", "Sentinel-2 Level-2A surface reflectance (SR)", "optical",
        "2015-01-01", None, "10 / 20 / 60 m", "Element 84 Earth Search / Copernicus",
        EARTH_SEARCH, "sentinel-2-l2a", "Public metadata; many public COG assets",
        "Multispectral surface reflectance. 2015 is the mission era, not guaranteed L2A catalog coverage at every location. Band resolutions and processing baselines differ.",
        "https://github.com/Element84/earth-search/blob/main/docs/collections/sentinel-2-l2a.md",
        processing_level="L2A", measurement="Surface reflectance (SR)",
    ),
    Dataset(
        "sentinel-1-grd", "Sentinel-1 ground range detected", "radar",
        "2014-01-01", None, "Mode-dependent; commonly 10 m pixel spacing", "Microsoft Planetary Computer / Copernicus",
        PLANETARY_COMPUTER, "sentinel-1-grd", "Public metadata; Azure assets commonly need temporary SAS signing",
        "C-band SAR acquisitions. Pixel spacing is not effective spatial resolution. GRD is not interchangeable with calibrated, terrain-corrected backscatter. Assets are HTTPS Azure blobs, so enable Planetary Computer signing when downloading.",
        "https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-grd",
    ),
    Dataset(
        "sentinel-1-rtc", "Sentinel-1 radiometrically terrain-corrected", "radar",
        "2014-01-01", None, "10 m pixel spacing", "Microsoft Planetary Computer / Copernicus",
        PLANETARY_COMPUTER, "sentinel-1-rtc", "Public metadata; Azure assets commonly need temporary SAS signing",
        "Terrain-corrected SAR for backscatter analysis. Actual archive start, polarization and regional coverage depend on the provider.",
        "https://github.com/microsoft/PlanetaryComputerExamples/tree/main/datasets/sentinel-1-rtc",
    ),
    Dataset(
        "cop-dem-glo-30", "Copernicus DEM GLO-30", "elevation",
        "2011-01-01", "2015-12-31", "1 arc-second (about 30 m)", "Microsoft Planetary Computer / Copernicus",
        PLANETARY_COMPUTER, "cop-dem-glo-30", "Public metadata; Azure assets commonly need temporary SAS signing; provider terms apply",
        "Static digital surface model based mainly on TanDEM-X acquisitions from 2011–2015. Not a continuously updated terrain time series. Assets are HTTPS Azure blobs, so enable Planetary Computer signing when downloading.",
        "https://planetarycomputer.microsoft.com/api/stac/v1/collections/cop-dem-glo-30",
        temporal=False,
    ),
    Dataset(
        "nasadem", "NASADEM (reprocessed SRTM)", "elevation",
        "2000-02-01", "2000-02-29", "1 arc-second (about 30 m)", "Microsoft Planetary Computer / NASA",
        PLANETARY_COMPUTER, "nasadem", "Public metadata; Azure assets commonly need temporary SAS signing",
        "Static elevation from the February 2000 SRTM mission, reprocessed later. Not global polar coverage and not a current elevation observation.",
        "https://github.com/microsoft/PlanetaryComputerExamples/tree/main/datasets/nasadem",
        temporal=False,
    ),
    Dataset(
        "esa-worldcover", "ESA WorldCover", "landcover",
        "2020-01-01", "2021-12-31", "10 m", "Microsoft Planetary Computer / ESA",
        PLANETARY_COMPUTER, "esa-worldcover", "Public metadata; Azure assets commonly need temporary SAS signing",
        "2020 and 2021 global land-cover maps; not an annual current feed. Algorithm/version changes complicate direct change detection.",
        "https://github.com/microsoft/PlanetaryComputerExamples/tree/main/datasets/esa-worldcover",
    ),
    Dataset(
        "jrc-gsw", "JRC Global Surface Water", "water",
        "1984-01-01", "2021-12-31", "30 m", "Microsoft Planetary Computer / European Commission JRC",
        PLANETARY_COMPUTER, "jrc-gsw", "Public metadata; Azure assets commonly need temporary SAS signing",
        "Landsat-derived surface-water statistics. The provider's release determines covered years; aggregate products are not individual dated scenes.",
        "https://github.com/microsoft/PlanetaryComputerExamples/tree/main/datasets/jrc-gsw",
        temporal=False,
    ),
    Dataset(
        "modis-surface-reflectance", "MODIS Terra MOD09A1 Version 6.1", "optical",
        "2000-01-01", None, "500 m; 8-day composites", "Microsoft Planetary Computer / NASA",
        PLANETARY_COMPUTER, "modis-09A1-061", "Public metadata; Azure assets commonly need temporary SAS signing",
        "Moderate-resolution surface reflectance composites. QA and composite intervals differ from Landsat/Sentinel scenes; check current ingestion lag.",
        "https://github.com/microsoft/PlanetaryComputerExamples/blob/main/datasets/modis/modis-imagery-example.ipynb",
    ),
    Dataset(
        "modis-vegetation", "MODIS Terra MOD13A1 Version 6.1", "vegetation",
        "2000-01-01", None, "500 m; 16-day composites", "Microsoft Planetary Computer / NASA",
        PLANETARY_COMPUTER, "modis-13A1-061", "Public metadata; Azure assets commonly need temporary SAS signing",
        "Precomputed NDVI/EVI composite products. Apply product scale factors and QA before comparing values; current ingestion is provider-dependent.",
        "https://github.com/microsoft/PlanetaryComputerExamples/blob/main/datasets/modis/modis-vegetation-example.ipynb",
    ),
    Dataset(
        "era5", "ERA5 historical climate reanalysis", "climate",
        "1940-01-01", None, "About 0.25 degrees; variable-dependent", "ECMWF / Copernicus Climate Data Store",
        None, None, "CDS account/API terms; Open-Meteo offers selected derived variables under its own terms",
        "Model/data-assimilation reanalysis extending before satellites. No STAC adapter; Client.weather provides selected ERA5 variables through Open-Meteo. ERA5 and ERA5-Land differ; final data have a publication lag.",
        "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels", "reference",
    ),
    Dataset(
        "chirps", "CHIRPS precipitation", "precipitation",
        "1981-01-01", None, "0.05 degrees; product-dependent daily/monthly", "UC Santa Barbara Climate Hazards Center",
        None, None, "Public downloads; distinguish preliminary/final and product versions",
        "Station-and-satellite rainfall record, mainly 50 degrees S–50 degrees N. Check the chosen CHIRPS version, latency, missing values and accumulation units.",
        "https://www.chc.ucsb.edu/data/chirps", "reference",
    ),
    Dataset(
        "avhrr", "NOAA AVHRR climate data records", "historical",
        "1981-01-01", None, "Product-dependent; typically several km", "NOAA NCEI",
        None, None, "Public NOAA archive; choose a specific CDR and version",
        "Long-term vegetation/reflectance and related climate records. A family of products, not a single uniform collection or current raw-image feed.",
        "https://www.ncei.noaa.gov/products/climate-data-records", "reference",
    ),
    Dataset(
        "smap", "SMAP soil moisture", "soil",
        "2015-01-01", None, "Product-dependent; about 9–36 km", "NASA / NSIDC",
        None, None, "NASA Earthdata login commonly required for protected downloads",
        "L-band soil-moisture products. Grid spacing is not footprint size; surface and modeled root-zone products differ.",
        "https://nsidc.org/data/smap", "reference",
    ),
    Dataset(
        "emit", "EMIT imaging spectroscopy", "hyperspectral",
        "2022-01-01", None, "About 60 m; hundreds of spectral bands", "NASA LP DAAC",
        None, None, "NASA Earthdata login commonly required for protected downloads",
        "ISS hyperspectral observations with targeted, non-global acquisition coverage; select level/version and geolocation handling explicitly.",
        "https://earth.jpl.nasa.gov/emit/data/data-portal/coverage-and-forecasts/", "reference",
    ),
    Dataset(
        "viirs-nightlights", "VIIRS / NASA Black Marble night lights", "nightlights",
        "2012-01-01", None, "Product-dependent; about 500–750 m", "NASA / NOAA",
        None, None, "NASA Earthdata login commonly required for protected Black Marble downloads",
        "Nighttime radiance products; daily, monthly and annual composites have different temporal coverage and correction methods.",
        "https://blackmarble.gsfc.nasa.gov/", "reference",
    ),
    Dataset(
        "firms", "NASA FIRMS active fire detections", "fire",
        "2000-01-01", None, "MODIS about 1 km; VIIRS about 375 m", "NASA FIRMS",
        None, None, "FIRMS API MAP_KEY; archive downloads and near-real-time products differ",
        "Thermal hotspot detections, not burned-area polygons. MODIS record begins around 2000 and VIIRS around 2012; near-real-time data have latency and quality limits.",
        "https://firms.modaps.eosdis.nasa.gov/api/", "reference",
    ),
    Dataset(
        "sentinel-5p", "Sentinel-5P TROPOMI atmospheric products", "atmosphere",
        "2018-01-01", None, "Several km; gas/product-dependent", "Copernicus Data Space / ESA",
        None, None, "Public catalog; account/token commonly required for product downloads",
        "Trace-gas and aerosol products. Choose near-real-time, offline or reprocessed stream and apply product quality flags.",
        "https://dataspace.copernicus.eu/explore-data/data-collections/sentinel-data/sentinel-5p", "reference",
    ),
    Dataset(
        "sentinel-3", "Sentinel-3 OLCI / SLSTR ocean and land products", "ocean",
        "2016-01-01", None, "OLCI about 300 m; SLSTR about 500 m–1 km", "Copernicus Data Space / ESA / EUMETSAT",
        None, None, "Public catalog; account/token commonly required for product downloads",
        "Ocean colour, surface temperature and related products. Instrument, processing level, access service and delivery timeliness vary.",
        "https://dataspace.copernicus.eu/explore-data/data-collections/sentinel-data/sentinel-3", "reference",
    ),
    Dataset(
        "sentinel-2-l1c", "Sentinel-2 Level-1C TOA reflectance", "optical",
        "2015-06-27", None, "10 / 20 / 60 m", "Element 84 Earth Search / Copernicus",
        EARTH_SEARCH, "sentinel-2-l1c", "Public metadata; JP2 imagery on requester-pays S3 may require AWS/provider retrieval",
        "Top-of-atmosphere reflectance product, not surface reflectance. Bands use encoded integers; read per-asset scale/offset and processing baseline. Current S3 band links are not supported by the HTTP-only downloader.",
        "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l1c",
        processing_level="L1C", measurement="Top-of-atmosphere (TOA) reflectance",
    ),
    Dataset(
        "landsat-c2-l1", "Landsat Collection 2 Level-1 DN (TOA calibration required)", "optical",
        "1972-07-25", None, "Sensor-dependent; commonly 30 m reflective bands", "USGS LandsatLook",
        USGS_LANDSAT, "landsat-c2l1", "Public metadata; USGS EROS login or requester-pays AWS access may be required for bands and MTL",
        "Global Level-1 archive delivered as digital numbers, not calibrated TOA reflectance. Use the matching MTL coefficients and solar elevation for supported reflective bands. MSS/thermal require other calibration workflows.",
        "https://www.usgs.gov/landsat-missions/using-usgs-landsat-level-1-data-product",
        processing_level="L1", measurement="Digital numbers (DN); TOA conversion required",
    ),
    Dataset(
        "landsat-c2-ard-toa", "Landsat Collection 2 US ARD TOA reflectance", "optical",
        "1982-08-22", None, "30 m reflective bands; regional ARD grid", "USGS LandsatLook",
        USGS_LANDSAT, "landsat-c2ard-ta", "Public metadata; USGS EROS login or requester-pays AWS access may be required",
        "TOA reflectance ARD product with regional U.S. coverage (CONUS, Alaska, Hawaii), not a global archive. Read product scale/offset and QA; the ARD grid differs from ordinary scenes. Do not treat it as SR or apply Level-1 DN calibration again.",
        "https://www.usgs.gov/landsat-missions/landsat-collection-2-us-analysis-ready-data",
        processing_level="ARD", measurement="Top-of-atmosphere (TOA) reflectance",
    ),
)


# Native provider adapters. Credentials are optional until restricted downloads.
_CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
_CDSE = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
_EXTRA = (
    ("smap-l4", "SMAP L4 surface and root-zone soil moisture", "hydrology", "2015-03-31", "9 km", "SPL4SMGP"),
    ("gpm-imerg", "GPM IMERG Final daily precipitation", "precipitation", "2000-06-01", "0.1 degree", "GPM_3IMERGDF"),
    ("viirs-black-marble", "VIIRS Black Marble VNP46A2", "nightlights", "2012-01-19", "500 m", "VNP46A2"),
    ("emit-l2a", "EMIT L2A reflectance", "hyperspectral", "2022-08-01", "About 60 m", "EMITL2ARFL"),
    ("viirs-active-fire", "VIIRS VNP14IMG active-fire product", "fire", "2012-01-19", "375 m", "VNP14IMG"),
    ("jason-3", "Jason-3 L2 OSTM OGDR", "altimetry", "2016-02-12", "Along-track", "JASON_3_L2_OST_OGDR_GPS"),
    ("sentinel-6", "Sentinel-6A L2 high-rate standard NTC G01", "altimetry", "2020-11-21", "Along-track", "JASON_CS_S6A_L2_ALT_HR_STD_OST_NTC_G01"),
)
_DATASETS += tuple(Dataset(id, title, category, start, None, resolution,
    "NASA Earthdata / originating mission", _CMR, short_name,
    "Public CMR metadata; native product downloads commonly require EARTHDATA_TOKEN. Files may be HDF5/NetCDF, not GeoTIFF.",
    "Queries real granules and returns only provider-advertised data links. Inspect units, QA and product version before analysis.",
    "https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html", adapter="cmr")
    for id,title,category,start,resolution,short_name in _EXTRA)
_DATASETS += (
    Dataset("enmap-l2a", "EnMAP L2A hyperspectral", "hyperspectral", "2022-04-01", None, "30 m", "DLR EnMAP",
        "https://geoservice.dlr.de/eoc/ogc/stac/v1", "ENMAP_HSI_L2A", "DLR account may be required for downloads",
        "Actual DLR STAC items; wavelength/bad-band metadata must be inspected.",
        "https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/ENMAP_HSI_L2A", adapter="stac_get"),
    Dataset("chirps-daily", "CHIRPS v2 daily precipitation", "precipitation", "1981-01-01", None, "0.05 degree", "UCSB Climate Hazards Center",
        "https://data.chc.ucsb.edu/products/CHIRPS/v2.0/global_daily/tifs/p05", "CHIRPS-2.0", "Public HTTPS; global files may be gzip-compressed",
        "Lists files actually present in the provider directory. Spatial coverage 50S–50N; bbox does not crop the global download.",
        "https://www.chc.ucsb.edu/data/chirps", adapter="chirps"),
)
_DATASETS += tuple(Dataset(id,title,category,start,None,resolution,"Copernicus Data Space / ESA / EUMETSAT",
    _CDSE,collection,"Public product metadata; CDSE_ACCESS_TOKEN required to download native archives",
    "Native mission products from the official OData catalog. Product level, instrument and variables vary; downloading does not derive measurements.",
    "https://documentation.dataspace.copernicus.eu/APIs/OData.html",adapter="cdse")
    for id,title,category,start,resolution,collection in (
        ("sentinel-3-products","Sentinel-3 OLCI / SLSTR native products","ocean","2016-01-01","Instrument-dependent","SENTINEL-3"),
        ("sentinel-5p-products","Sentinel-5P TROPOMI native products","atmosphere","2018-01-01","Product-dependent","SENTINEL-5P"),
        ("sentinel-2-products","Sentinel-2 native L1C / L2A archives","optical","2015-06-27","10 / 20 / 60 m","SENTINEL-2"),
    ))

_DATASETS += (Dataset("3dep-seamless", "USGS 3DEP seamless DEM", "elevation", "2000-01-01", None,
    "About 10 / 30 m; inspect collection assets", "USGS / Microsoft Planetary Computer", PLANETARY_COMPUTER,
    "3dep-seamless", "Public metadata; Azure assets may need signing", "Static elevation inventory; acquisition dates vary by tile.",
    "https://planetarycomputer.microsoft.com/api/stac/v1/collections/3dep-seamless", temporal=False),)

_DATASETS += (
    Dataset("dynamic-world", "Google Dynamic World 10 m", "landcover", "2015-06-27", None, "10 m", "Dynamic World Project: Google / National Geographic Society / World Resources Institute",
        "https://earthengine.googleapis.com", "GOOGLE/DYNAMICWORLD/V1", "Earth Engine credentials, authorized EE_PROJECT and optional earthengine extra required; small synchronous exports only",
        "Returns actual scene-specific AOI-cropped label/probability GeoTIFF links. Large areas require provider batch exports.",
        "https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1", adapter="earthengine"),
    Dataset("hyperion", "EO-1 Hyperion archive metadata", "hyperspectral", "2000-01-01", "2017-03-30", "30 m", "USGS / NASA CMR",
        _CMR, "USGS_EDC_EO1_Hyperion", "Archive may expose collection metadata without searchable granules; USGS retrieval may be required",
        "Queries actual CMR granules if present. Empty results do not prove the USGS archive is empty.",
        "https://www.usgs.gov/centers/eros/science/usgs-eros-archive-earth-observing-one-eo-1-hyperion", adapter="cmr"),
)
_DATASETS += tuple(Dataset(id,title,"fire",start,None,resolution,"NASA LANCE FIRMS",
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv",collection,"FIRMS_MAP_KEY required; API windows limited to 10 days",
    "Actual hotspot observations as GeoJSON points; not a raster. The search manifest is the downloaded data; no asset download is needed.",
    "https://firms.modaps.eosdis.nasa.gov/api/area/",adapter="firms")
    for id,title,start,resolution,collection in (
        ("firms-viirs","FIRMS VIIRS Suomi-NPP NRT hotspots","2012-01-01","375 m","VIIRS_SNPP_NRT"),
        ("firms-modis","FIRMS MODIS NRT hotspots","2000-01-01","1 km","MODIS_NRT"),
    ))


def datasets() -> list[Dataset]:
    """Return a new list of immutable directory entries."""
    return list(_DATASETS)


def get_dataset(id: str) -> Dataset:
    """Resolve a stable local identifier; never silently substitute a source."""
    for dataset in _DATASETS:
        if dataset.id == id:
            return dataset
    choices = ", ".join(dataset.id for dataset in _DATASETS)
    raise ValueError(f"Unknown dataset {id!r}. Available datasets: {choices}")


def list_datasets(category: str | None = None) -> list[Dataset]:
    """Filter by category; an unknown category returns an empty list."""
    return [dataset for dataset in _DATASETS if category is None or dataset.category == category]
