# Universal Satellite for ArcGIS Pro

1. Extract this ZIP to a normal folder. Keep `UniversalSatellite.pyt` there;
   do not try to add a toolbox directly from inside the ZIP.
2. Install the Universal Satellite core package into the Python environment used
   by ArcGIS Pro. Download and extract the full repository from
   https://github.com/Bipul-roy-AI/Universal-Satellite, clone/activate your Pro
   environment in Package Manager, then open its Python Command Prompt and run:

   ```text
   python -m pip install "C:\path\to\Universal-Satellite-main"
   ```

   The toolbox ZIP contains the `.pyt`, an offline dataset list and these
   instructions; it does not contain the core SDK or an ArcGIS runtime.
   Requires Python 3.10 or newer, not ArcMap.
3. In ArcGIS Pro, choose **Catalog > Toolboxes > Add Toolbox**, then select the
   extracted `UniversalSatellite.pyt`.
4. Open **Search satellite scenes (GeoJSON manifest)**. Choose a named source
   and its dataset ID from the dropdown. The bundled list remains visible even
   without the core SDK; install the SDK before running a search. Start with Sentinel-2
   L2A (SR) or L1C (TOA), a small extent with its actual coordinate system, ISO
   dates, cloud cover 20, limit 5 and an output `.geojson` outside a geodatabase.
   Search returns scene footprints and asset links. To also download images,
   check **Download images after search**, enter asset keys (Sentinel-2 `red,nir`;
   Landsat `red,nir08`) and select an **Image output folder**. For an existing
   GeoJSON, use **Download satellite image assets**. Downloads run through the
   GIS geoprocessing job with progress and cancellation; no per-download terminal
   commands are needed. Install or upgrade the core SDK to version 0.2.0 or newer
   once when updating this toolbox. Native desktop execution remains unverified.
5. For **Compute normalized-difference raster index**, also install compatible
   NumPy and Rasterio into the Pro environment. See the full guide before
   changing Pro's geospatial dependencies.

Full instructions and source/TOA notes:
https://github.com/Bipul-roy-AI/Universal-Satellite/blob/main/docs/gis.md

Native ArcGIS Pro testing remains pending. Provider access and imagery downloads
may require authentication; a successful metadata query does not grant downloads.
