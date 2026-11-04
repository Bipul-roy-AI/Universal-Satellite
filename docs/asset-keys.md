# Asset keys: operator guide

[Back to the quick start](../README.md)


Asset keys are case-sensitive names of files/links inside each scene, not API keys or index names. Enter exact keys separated by commas. Enter * alone for all advertised assets in each returned scene (including metadata, previews and possibly service links); this does not mean all historical scenes or only raster bands. A key such as data_2 is used only when present. Provider access rules still apply. Downloading does not calculate indices, clip full tiles, or apply reflectance scaling. Scene limits still apply. If * is reported as a missing literal key, update the core SDK in this GIS application’s Python environment and restart the application; updating ArcGIS does not update QGIS.

Quick examples: Copernicus DEM `data`; NASADEM `elevation`; WorldCover `map`; Sentinel-2 L2A `red,green,blue,nir`; Landsat L2 `red,green,blue,nir08`. These select files, without calculating an index.

In ArcGIS Pro open the tool help; in QGIS read the algorithm Help panel. Both Search and Download include this guide offline. Download messages list actual manifest keys, provider titles and media types. Install the complete updated toolbox/plugin ZIP, update the core separately in **each** GIS Python environment, and restart the application.

### Landsat 4–9 Collection 2 Level-2 surface reflectance (SR) (`landsat-c2-l2`)

Surface reflectance and available surface temperature. Covers TM, ETM+, OLI/TIRS; QA, scaling and sensor harmonization matter. Assets are HTTPS Azure blobs, so enable Planetary Computer signing when downloading. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; Azure assets commonly need temporary SAS signing

| Value to enter | Meaning |
| --- | --- |
| `ang` | Angle Coefficients File |
| `red` | Red Band |
| `blue` | Blue Band |
| `green` | Green Band |
| `nir08` | Near Infrared Band 0.8 |
| `swir16` | Short-wave Infrared Band 1.6 |
| `swir22` | Short-wave Infrared Band 2.2 |
| `coastal` | Coastal/Aerosol Band |
| `mtl.txt` | Product Metadata File (txt) |
| `mtl.xml` | Product Metadata File (xml) |
| `mtl.json` | Product Metadata File (json) |
| `qa_pixel` | Pixel Quality Assessment Band |
| `qa_radsat` | Radiometric Saturation and Terrain Occlusion Quality Assessment Band |
| `qa_aerosol` | Aerosol Quality Assessment Band |
| `tilejson` | Map tile-service description (JSON), not an analysis raster. |
| `rendered_preview` | Rendered preview; display preview, not calibrated measurement data. |

Provider reference: [landsat-c2-l2](https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items?limit=1)

### Sentinel-2 Level-2A surface reflectance (SR) (`sentinel-2-l2a`)

Multispectral surface reflectance. 2015 is the mission era, not guaranteed L2A catalog coverage at every location. Band resolutions and processing baselines differ. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; many public COG assets

| Value to enter | Meaning |
| --- | --- |
| `aot` | Aerosol optical thickness (AOT) |
| `blue` | Blue - 10m |
| `cloud` | Cloud Probabilities |
| `coastal` | Coastal - 60m |
| `granule_metadata` | metadata |
| `green` | Green - 10m |
| `nir` | NIR 1 - 10m |
| `nir08` | NIR 2 - 20m |
| `nir09` | NIR 3 - 60m |
| `product_metadata` | metadata |
| `red` | Red - 10m |
| `rededge1` | Red Edge 1 - 20m |
| `rededge2` | Red Edge 2 - 20m |
| `rededge3` | Red Edge 3 - 20m |
| `scl` | Scene classification map (SCL) |
| `snow` | Snow Probabilities |
| `swir16` | SWIR 1.6μm - 20m |
| `swir22` | SWIR 2.2μm - 20m |
| `tileinfo_metadata` | metadata |
| `visual` | True color image |
| `wvp` | Water Vapour (WVP) |
| `thumbnail` | Thumbnail of preview image; display preview, not calibrated measurement data. |
| `aot-jp2` | Aerosol optical thickness (AOT); JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `blue-jp2` | Blue - 10m; JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `coastal-jp2` | Coastal - 60m; JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `green-jp2` | Green - 10m; JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `nir-jp2` | NIR 1 - 10m; JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `nir08-jp2` | NIR 2 - 20m; JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `nir09-jp2` | NIR 3 - 60m; JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `red-jp2` | Red - 10m; JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `rededge1-jp2` | Red Edge 1 - 20m; JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `rededge2-jp2` | Red Edge 2 - 20m; JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `rededge3-jp2` | Red Edge 3 - 20m; JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `scl-jp2` | Scene classification map (SCL); JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `swir16-jp2` | SWIR 1.6μm - 20m; JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `swir22-jp2` | SWIR 2.2μm - 20m; JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `visual-jp2` | True color image; JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |
| `wvp-jp2` | Water Vapour (WVP); JPEG2000 alternative, possibly S3/requester-pays; HTTP downloader cannot retrieve s3:// links. |

Provider reference: [sentinel-2-l2a](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items?limit=1)

### Sentinel-1 ground range detected (`sentinel-1-grd`)

C-band SAR acquisitions. Pixel spacing is not effective spatial resolution. GRD is not interchangeable with calibrated, terrain-corrected backscatter. Assets are HTTPS Azure blobs, so enable Planetary Computer signing when downloading. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; Azure assets commonly need temporary SAS signing

| Value to enter | Meaning |
| --- | --- |
| `vh` | VH: vertical transmit, horizontal receive |
| `vv` | VV: vertical transmit, vertical receive |
| `thumbnail` | Preview Image; display preview, not calibrated measurement data. |
| `safe-manifest` | Manifest File |
| `schema-noise-vh` | VH Noise Schema |
| `schema-noise-vv` | VV Noise Schema |
| `schema-product-vh` | VH Product Schema |
| `schema-product-vv` | VV Product Schema |
| `schema-calibration-vh` | VH Calibration Schema |
| `schema-calibration-vv` | VV Calibration Schema |
| `tilejson` | Map tile-service description (JSON), not an analysis raster. |
| `rendered_preview` | Rendered preview; display preview, not calibrated measurement data. |

Provider reference: [sentinel-1-grd](https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-grd/items?limit=1)

### Sentinel-1 radiometrically terrain-corrected (`sentinel-1-rtc`)

Terrain-corrected SAR for backscatter analysis. Actual archive start, polarization and regional coverage depend on the provider. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; Azure assets commonly need temporary SAS signing

| Value to enter | Meaning |
| --- | --- |
| `vh` | VH: vertical transmit, horizontal receive |
| `vv` | VV: vertical transmit, vertical receive |
| `tilejson` | Map tile-service description (JSON), not an analysis raster. |
| `rendered_preview` | Rendered preview; display preview, not calibrated measurement data. |

Provider reference: [sentinel-1-rtc](https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-rtc/items?limit=1)

### Copernicus DEM GLO-30 (`cop-dem-glo-30`)

Static digital surface model based mainly on TanDEM-X acquisitions from 2011–2015. Not a continuously updated terrain time series. Assets are HTTPS Azure blobs, so enable Planetary Computer signing when downloading. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; Azure assets commonly need temporary SAS signing; provider terms apply

| Value to enter | Meaning |
| --- | --- |
| `data` | Elevation / digital surface model raster (includes vegetation and buildings). |
| `tilejson` | Map tile-service description (JSON), not an analysis raster. |
| `rendered_preview` | Rendered preview; display preview, not calibrated measurement data. |

Provider reference: [cop-dem-glo-30](https://planetarycomputer.microsoft.com/api/stac/v1/collections/cop-dem-glo-30/items?limit=1)

### NASADEM (reprocessed SRTM) (`nasadem`)

Static elevation from the February 2000 SRTM mission, reprocessed later. Not global polar coverage and not a current elevation observation. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; Azure assets commonly need temporary SAS signing

| Value to enter | Meaning |
| --- | --- |
| `tilejson` | Map tile-service description (JSON), not an analysis raster. |
| `elevation` | Elevation |
| `rendered_preview` | Rendered preview; display preview, not calibrated measurement data. |

Provider reference: [nasadem](https://planetarycomputer.microsoft.com/api/stac/v1/collections/nasadem/items?limit=1)

### ESA WorldCover (`esa-worldcover`)

2020 and 2021 global land-cover maps; not an annual current feed. Algorithm/version changes complicate direct change detection. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; Azure assets commonly need temporary SAS signing

| Value to enter | Meaning |
| --- | --- |
| `map` | Land Cover Classes |
| `tilejson` | Map tile-service description (JSON), not an analysis raster. |
| `input_quality` | Classification Input Data Quality |
| `rendered_preview` | Rendered preview; display preview, not calibrated measurement data. |

Provider reference: [esa-worldcover](https://planetarycomputer.microsoft.com/api/stac/v1/collections/esa-worldcover/items?limit=1)

### JRC Global Surface Water (`jrc-gsw`)

Landsat-derived surface-water statistics. The provider's release determines covered years; aggregate products are not individual dated scenes. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; Azure assets commonly need temporary SAS signing

| Value to enter | Meaning |
| --- | --- |
| `change` | Water Occurrence Change |
| `extent` | Maximum Water Extent |
| `tilejson` | Map tile-service description (JSON), not an analysis raster. |
| `occurrence` | Water Occurrence |
| `recurrence` | Water Recurrence |
| `seasonality` | Water Seasonality |
| `transitions` | Water Transitions |
| `rendered_preview` | Rendered preview; display preview, not calibrated measurement data. |

Provider reference: [jrc-gsw](https://planetarycomputer.microsoft.com/api/stac/v1/collections/jrc-gsw/items?limit=1)

### MODIS Terra MOD09A1 Version 6.1 (`modis-surface-reflectance`)

Moderate-resolution surface reflectance composites. QA and composite intervals differ from Landsat/Sentinel scenes; check current ingestion lag. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; Azure assets commonly need temporary SAS signing

| Value to enter | Meaning |
| --- | --- |
| `hdf` | Source data containing all bands |
| `sur_refl_b01` | Surface Reflectance Band 1 (620-670 nm) |
| `sur_refl_b02` | Surface Reflectance Band 2 (841-876 nm) |
| `sur_refl_b03` | Surface Reflectance Band 3 (459-479 nm) |
| `sur_refl_b04` | Surface Reflectance Band 4 (545-565 nm) |
| `sur_refl_b05` | Surface Reflectance Band 5 (1230-1250 nm) |
| `sur_refl_b06` | Surface Reflectance Band 6 (1628-1652 nm) |
| `sur_refl_b07` | Surface Reflectance Band 7 (2105-2155 nm) |
| `sur_refl_raz` | MODIS relative azimuth angle |
| `sur_refl_szen` | MODIS solar zenith angle |
| `sur_refl_vzen` | MODIS view zenith angle |
| `sur_refl_qc_500m` | Surface reflectance 500m band quality control flags |
| `sur_refl_state_500m` | Surface reflectance 500m state flags |
| `sur_refl_day_of_year` | Day of the year for the pixel |

Provider reference: [modis-surface-reflectance](https://planetarycomputer.microsoft.com/api/stac/v1/collections/modis-09A1-061/items?limit=1)

### MODIS Terra MOD13A1 Version 6.1 (`modis-vegetation`)

Precomputed NDVI/EVI composite products. Apply product scale factors and QA before comparing values; current ingestion is provider-dependent. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; Azure assets commonly need temporary SAS signing

| Value to enter | Meaning |
| --- | --- |
| `hdf` | Source data containing all bands |
| `500m_16_days_EVI` | 500m 16 days EVI |
| `500m_16_days_NDVI` | 500m 16 days NDVI |
| `500m_16_days_VI_Quality` | VI quality indicators |
| `500m_16_days_MIR_reflectance` | Surface Reflectance Band 7 |
| `500m_16_days_NIR_reflectance` | Surface Reflectance Band 2 |
| `500m_16_days_red_reflectance` | Surface Reflectance Band 1 |
| `500m_16_days_blue_reflectance` | Surface Reflectance Band 3 |
| `500m_16_days_sun_zenith_angle` | Sun zenith angle of VI pixel |
| `500m_16_days_pixel_reliability` | Quality reliability of VI pixel |
| `500m_16_days_view_zenith_angle` | View zenith angle of VI Pixel |
| `500m_16_days_relative_azimuth_angle` | Relative azimuth angle of VI pixel |
| `500m_16_days_composite_day_of_the_year` | Day of year VI pixel |

Provider reference: [modis-vegetation](https://planetarycomputer.microsoft.com/api/stac/v1/collections/modis-13A1-061/items?limit=1)

### Sentinel-2 Level-1C TOA reflectance (`sentinel-2-l1c`)

Top-of-atmosphere reflectance product, not surface reflectance. Bands use encoded integers; read per-asset scale/offset and processing baseline. Current S3 band links are not supported by the HTTP-only downloader. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; JP2 imagery on requester-pays S3 may require AWS/provider retrieval

| Value to enter | Meaning |
| --- | --- |
| `blue` | Blue - 10m |
| `cirrus` | Cirrus - 60m |
| `coastal` | Coastal - 60m |
| `granule_metadata` | metadata |
| `green` | Green - 10m |
| `nir` | NIR 1 - 10m |
| `nir08` | NIR 2 - 20m |
| `nir09` | NIR 3 - 60m |
| `product_metadata` | metadata |
| `red` | Red - 10m |
| `rededge1` | Red Edge 1 - 20m |
| `rededge2` | Red Edge 2 - 20m |
| `rededge3` | Red Edge 3 - 20m |
| `swir16` | SWIR 1.6μm - 20m |
| `swir22` | SWIR 2.2μm - 20m |
| `tileinfo_metadata` | metadata |
| `visual` | True color image |

Provider reference: [sentinel-2-l1c](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l1c/items?limit=1)

### Landsat Collection 2 Level-1 DN (TOA calibration required) (`landsat-c2-l1`)

Global Level-1 archive delivered as digital numbers, not calibrated TOA reflectance. Use the matching MTL coefficients and solar elevation for supported reflective bands. MSS/thermal require other calibration workflows. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; USGS EROS login or requester-pays AWS access may be required for bands and MTL

| Value to enter | Meaning |
| --- | --- |
| `thumbnail` | Thumbnail image; display preview, not calibrated measurement data. |
| `reduced_resolution_browse` | Reduced resolution browse image; display preview, not calibrated measurement data. |
| `index` | HTML index page |
| `MTL.json` | Product Metadata File (json) |
| `coastal` | Coastal/Aerosol Band (B1) |
| `blue` | Blue Band (B2) |
| `green` | Green Band (B3) |
| `red` | Red Band (B4) |
| `nir08` | Near Infrared Band 0.8 (B5) |
| `swir16` | Short-wave Infrared Band 1.6 (B6) |
| `swir22` | Short-wave Infrared Band 2.2 (B7) |
| `pan` | Panchromatic Band (B8) |
| `cirrus` | Cirrus Band (B9) |
| `lwir11` | Thermal Infrared Band 10.9 (B10) |
| `lwir12` | Thermal Infrared Band 12.0 (B11) |
| `qa_pixel` | Pixel Quality Assessment Band |
| `qa_radsat` | Radiometric Saturation Quality Assessment Band |
| `ANG.txt` | Angle Coefficients File |
| `VAA` | Sensor Azimuth Angle Band |
| `VZA` | Sensor Zenith Angle Band |
| `SAA` | Solar Azimuth Angle Band |
| `SZA` | Solar Zenith Angle Band |
| `MTL.txt` | Product Metadata File |
| `MTL.xml` | Product Metadata File (xml) |

Provider reference: [landsat-c2-l1](https://landsatlook.usgs.gov/stac-server/collections/landsat-c2l1/items?limit=1)

### Landsat Collection 2 US ARD TOA reflectance (`landsat-c2-ard-toa`)

TOA reflectance ARD product with regional U.S. coverage (CONUS, Alaska, Hawaii), not a global archive. Read product scale/offset and QA; the ARD grid differs from ordinary scenes. Do not treat it as SR or apply Level-1 DN calibration again. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; USGS EROS login or requester-pays AWS access may be required

| Value to enter | Meaning |
| --- | --- |
| `thumbnail` | Thumbnail image; display preview, not calibrated measurement data. |
| `reduced_resolution_browse` | Reduced resolution browse image; display preview, not calibrated measurement data. |
| `index` | HTML index page |
| `coastal` | Coastal/Aerosol Band (B1) |
| `blue` | Blue Band (B2) |
| `green` | Green Band (B3) |
| `red` | Red Band (B4) |
| `nir08` | Near Infrared Band 0.8 (B5) |
| `swir16` | Short-wave Infrared Band 1.6 (B6) |
| `swir22` | Short-wave Infrared Band 2.2 (B7) |
| `cirrus` | Cirrus Band (B9) |
| `SZA` | Solar Zenith Angle Band |
| `SAA` | Solar Azimuth Angle Band |
| `VZA` | Sensor Zenith Angle Band |
| `VAA` | Sensor Azimuth Angle Band |
| `qa_pixel` | Pixel Quality Assessment Band |
| `qa_radsat` | Radiometric Saturation Quality Assessment Band |
| `qa_lineage` | Lineage Assessment Band |

Provider reference: [landsat-c2-ard-toa](https://landsatlook.usgs.gov/stac-server/collections/landsat-c2ard-ta/items?limit=1)

### SMAP L4 surface and root-zone soil moisture (`smap-l4`)

Queries real granules and returns only provider-advertised data links. Inspect units, QA and product version before analysis. Variables are inside the native HDF5/NetCDF or other product file; these asset keys do not select soil moisture, rainfall, radiance or individual spectral bands.

Access: Public CMR metadata; native product downloads commonly require EARTHDATA_TOKEN. Files may be HDF5/NetCDF, not GeoTIFF.

| Value to enter | Meaning |
| --- | --- |
| `data` | First HTTPS data link advertised by the granule; native product file, not a band name. |
| `data_2, data_3, …` | Additional advertised data links, if present. Numbering follows provider link order; inspect titles and filenames. |

Provider reference: [smap-l4](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)

### GPM IMERG Final daily precipitation (`gpm-imerg`)

Queries real granules and returns only provider-advertised data links. Inspect units, QA and product version before analysis. Variables are inside the native HDF5/NetCDF or other product file; these asset keys do not select soil moisture, rainfall, radiance or individual spectral bands.

Access: Public CMR metadata; native product downloads commonly require EARTHDATA_TOKEN. Files may be HDF5/NetCDF, not GeoTIFF.

| Value to enter | Meaning |
| --- | --- |
| `data` | First HTTPS data link advertised by the granule; native product file, not a band name. |
| `data_2, data_3, …` | Additional advertised data links, if present. Numbering follows provider link order; inspect titles and filenames. |

Provider reference: [gpm-imerg](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)

### VIIRS Black Marble VNP46A2 (`viirs-black-marble`)

Queries real granules and returns only provider-advertised data links. Inspect units, QA and product version before analysis. Variables are inside the native HDF5/NetCDF or other product file; these asset keys do not select soil moisture, rainfall, radiance or individual spectral bands.

Access: Public CMR metadata; native product downloads commonly require EARTHDATA_TOKEN. Files may be HDF5/NetCDF, not GeoTIFF.

| Value to enter | Meaning |
| --- | --- |
| `data` | First HTTPS data link advertised by the granule; native product file, not a band name. |
| `data_2, data_3, …` | Additional advertised data links, if present. Numbering follows provider link order; inspect titles and filenames. |

Provider reference: [viirs-black-marble](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)

### EMIT L2A reflectance (`emit-l2a`)

Queries real granules and returns only provider-advertised data links. Inspect units, QA and product version before analysis. Variables are inside the native HDF5/NetCDF or other product file; these asset keys do not select soil moisture, rainfall, radiance or individual spectral bands.

Access: Public CMR metadata; native product downloads commonly require EARTHDATA_TOKEN. Files may be HDF5/NetCDF, not GeoTIFF.

| Value to enter | Meaning |
| --- | --- |
| `data` | First HTTPS data link advertised by the granule; native product file, not a band name. |
| `data_2, data_3, …` | Additional advertised data links, if present. Numbering follows provider link order; inspect titles and filenames. |

Provider reference: [emit-l2a](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)

### VIIRS VNP14IMG active-fire product (`viirs-active-fire`)

Queries real granules and returns only provider-advertised data links. Inspect units, QA and product version before analysis. Variables are inside the native HDF5/NetCDF or other product file; these asset keys do not select soil moisture, rainfall, radiance or individual spectral bands.

Access: Public CMR metadata; native product downloads commonly require EARTHDATA_TOKEN. Files may be HDF5/NetCDF, not GeoTIFF.

| Value to enter | Meaning |
| --- | --- |
| `data` | First HTTPS data link advertised by the granule; native product file, not a band name. |
| `data_2, data_3, …` | Additional advertised data links, if present. Numbering follows provider link order; inspect titles and filenames. |

Provider reference: [viirs-active-fire](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)

### Jason-3 L2 OSTM OGDR (`jason-3`)

Queries real granules and returns only provider-advertised data links. Inspect units, QA and product version before analysis. Variables are inside the native HDF5/NetCDF or other product file; these asset keys do not select soil moisture, rainfall, radiance or individual spectral bands.

Access: Public CMR metadata; native product downloads commonly require EARTHDATA_TOKEN. Files may be HDF5/NetCDF, not GeoTIFF.

| Value to enter | Meaning |
| --- | --- |
| `data` | First HTTPS data link advertised by the granule; native product file, not a band name. |
| `data_2, data_3, …` | Additional advertised data links, if present. Numbering follows provider link order; inspect titles and filenames. |

Provider reference: [jason-3](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)

### Sentinel-6A L2 high-rate standard NTC G01 (`sentinel-6`)

Queries real granules and returns only provider-advertised data links. Inspect units, QA and product version before analysis. Variables are inside the native HDF5/NetCDF or other product file; these asset keys do not select soil moisture, rainfall, radiance or individual spectral bands.

Access: Public CMR metadata; native product downloads commonly require EARTHDATA_TOKEN. Files may be HDF5/NetCDF, not GeoTIFF.

| Value to enter | Meaning |
| --- | --- |
| `data` | First HTTPS data link advertised by the granule; native product file, not a band name. |
| `data_2, data_3, …` | Additional advertised data links, if present. Numbering follows provider link order; inspect titles and filenames. |

Provider reference: [sentinel-6](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)

### EnMAP L2A hyperspectral (`enmap-l2a`)

Actual DLR STAC items; wavelength/bad-band metadata must be inspected. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: DLR account may be required for downloads

| Value to enter | Meaning |
| --- | --- |
| `metadata` | Metadata |
| `image` | Spectral Image |
| `vnir` | Quicklook VNIR |
| `thumbnail` | Thumbnail VNIR; display preview, not calibrated measurement data. |
| `swir` | Quicklook SWIR |
| `quality_classes` | Quality classes |
| `quality_cloud` | Quality cloud |
| `quality_cloud_shadow` | Quality cloud shadow |
| `quality_haze` | Quality haze |
| `quality_cirrus` | Quality cirrus |
| `quality_snow` | Quality snow |
| `quality_testflags` | Quality test flags |
| `defective_pixel_mask` | Defective pixel mask |

Provider reference: [enmap-l2a](https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/ENMAP_HSI_L2A/items?limit=1)

### CHIRPS v2 daily precipitation (`chirps-daily`)

Lists files actually present in the provider directory. Spatial coverage 50S–50N; bbox does not crop the global download.

Access: Public HTTPS; global files may be gzip-compressed

| Value to enter | Meaning |
| --- | --- |
| `precipitation` | Daily precipitation grid; global TIFF or gzip-compressed TIFF. Decompress .gz before opening as a raster. |

Provider reference: [chirps-daily](https://www.chc.ucsb.edu/data/chirps)

### Sentinel-3 OLCI / SLSTR native products (`sentinel-3-products`)

Native mission products from the official OData catalog. Product level, instrument and variables vary; downloading does not derive measurements.

Access: Public product metadata; CDSE_ACCESS_TOKEN required to download native archives

| Value to enter | Meaning |
| --- | --- |
| `product` | Complete native product archive; open its internal bands/variables after downloading. Not a derived chlorophyll, temperature or gas-concentration raster. |

Provider reference: [sentinel-3-products](https://documentation.dataspace.copernicus.eu/APIs/OData.html)

### Sentinel-5P TROPOMI native products (`sentinel-5p-products`)

Native mission products from the official OData catalog. Product level, instrument and variables vary; downloading does not derive measurements.

Access: Public product metadata; CDSE_ACCESS_TOKEN required to download native archives

| Value to enter | Meaning |
| --- | --- |
| `product` | Complete native product archive; open its internal bands/variables after downloading. Not a derived chlorophyll, temperature or gas-concentration raster. |

Provider reference: [sentinel-5p-products](https://documentation.dataspace.copernicus.eu/APIs/OData.html)

### Sentinel-2 native L1C / L2A archives (`sentinel-2-products`)

Native mission products from the official OData catalog. Product level, instrument and variables vary; downloading does not derive measurements.

Access: Public product metadata; CDSE_ACCESS_TOKEN required to download native archives

| Value to enter | Meaning |
| --- | --- |
| `product` | Complete native product archive; open its internal bands/variables after downloading. Not a derived chlorophyll, temperature or gas-concentration raster. |

Provider reference: [sentinel-2-products](https://documentation.dataspace.copernicus.eu/APIs/OData.html)

### USGS 3DEP seamless DEM (`3dep-seamless`)

Static elevation inventory; acquisition dates vary by tile. Keys below were observed in a provider sample on 2026-11-04; other sensors, dates and scenes may expose different keys. The saved manifest is authoritative.

Access: Public metadata; Azure assets may need signing

| Value to enter | Meaning |
| --- | --- |
| `data` | Elevation DEM raster; inspect the tile metadata for actual resolution and vertical reference. |
| `gpkg` | metadata |
| `metadata` | metadata |
| `tilejson` | Map tile-service description (JSON), not an analysis raster. |
| `thumbnail` | thumbnail; display preview, not calibrated measurement data. |
| `rendered_preview` | Rendered preview; display preview, not calibrated measurement data. |

Provider reference: [3dep-seamless](https://planetarycomputer.microsoft.com/api/stac/v1/collections/3dep-seamless/items?limit=1)

### Google Dynamic World 10 m (`dynamic-world`)

Returns actual scene-specific AOI-cropped label/probability GeoTIFF links. Large areas require provider batch exports.

Access: Earth Engine credentials, authorized EE_PROJECT and optional earthengine extra required; small synchronous exports only

| Value to enter | Meaning |
| --- | --- |
| `data` | AOI-cropped GeoTIFF with land-cover label and class probabilities; download link expires. |

Provider reference: [dynamic-world](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1)

### EO-1 Hyperion archive metadata (`hyperion`)

Queries actual CMR granules if present. Empty results do not prove the USGS archive is empty. Variables are inside the native HDF5/NetCDF or other product file; these asset keys do not select soil moisture, rainfall, radiance or individual spectral bands.

Access: Archive may expose collection metadata without searchable granules; USGS retrieval may be required

| Value to enter | Meaning |
| --- | --- |
| `data` | First HTTPS data link advertised by the granule; native product file, not a band name. |
| `data_2, data_3, …` | Additional advertised data links, if present. Numbering follows provider link order; inspect titles and filenames. |

Provider reference: [hyperion](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-earth-observing-one-eo-1-hyperion)

### FIRMS VIIRS Suomi-NPP NRT hotspots (`firms-viirs`)

Actual hotspot observations as GeoJSON points; not a raster. The search manifest is the downloaded data; no asset download is needed. No asset key: leave image download disabled. Save the search GeoJSON, which contains the hotspot observations.

Access: FIRMS_MAP_KEY required; API windows limited to 10 days

| Value to enter | Meaning |
| --- | --- |
| No image asset | Use the search GeoJSON, or inspect the manifest if provider-specific links exist. |

Provider reference: [firms-viirs](https://firms.modaps.eosdis.nasa.gov/api/area/)

### FIRMS MODIS NRT hotspots (`firms-modis`)

Actual hotspot observations as GeoJSON points; not a raster. The search manifest is the downloaded data; no asset download is needed. No asset key: leave image download disabled. Save the search GeoJSON, which contains the hotspot observations.

Access: FIRMS_MAP_KEY required; API windows limited to 10 days

| Value to enter | Meaning |
| --- | --- |
| No image asset | Use the search GeoJSON, or inspect the manifest if provider-specific links exist. |

Provider reference: [firms-modis](https://firms.modaps.eosdis.nasa.gov/api/area/)

### Other catalog references and point-profile tools

Reference-only catalog entries are not downloadable scene datasets. Their provider/access notes remain in the source catalog; do not invent asset keys for them. Weather and soil profile tools return JSON variables rather than image assets: select the profile type and coordinates, not an asset key. Weather variables include the returned units; soil properties and depths are described in the returned provider JSON.
