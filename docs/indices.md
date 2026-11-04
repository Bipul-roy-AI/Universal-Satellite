# Spectral index catalog

Python, CLI and the **Compute spectral index (full catalog)** tool in both GIS
applications share 280 formulas from [Awesome Spectral Indices](https://github.com/awesome-spectral-indices/awesome-spectral-indices).
The original six-index API and the original two-band GIS tools remain compatible.

The bundled formula snapshot has Git blob SHA
`4b0a3799a4e8cc5de54b3bef004a2890784a29a0`; constants snapshot:
`960317666b5ac2d292e1eab354a2106fd3f33a20`. The MIT notice is included in
`universal_satellite/data/LICENSE-spectral-indices.txt`. Every record retains
its literature reference, contributor and applicable platforms. This is a
versioned collection, not a claim to contain every index ever published.

Names `BAI`/`BaI` and `MSR705`/`mSR705` are case-sensitive because they identify different published formulas. Other names accept case-insensitive aliases.

Run `universal-satellite indices` to inspect formulas, coefficient defaults and
band requirements. Example:

```sh
universal-satellite index --name savi --nir nir.tif --red red.tif --constants '{"L":0.5}' --output savi.tif
```

```python
from universal_satellite.indices import evaluate, definition
from universal_satellite.raster import compute_index
print(definition('evi'))
value = evaluate('ndvi', {'nir': 0.8, 'red': 0.2})  # NumPy scalar: 0.6
compute_index('savi', 'savi.tif', nir='nir.tif', red='red.tif', constants={'L': 0.5})
```

NIR = `nir`, narrow NIR = `nir08`, SWIR1/2 = `swir16`/`swir22`, red-edge bands =
`rededge`/`rededge2`/`rededge3`. Additional symbols appear in the catalog.
The software does not guess physical wavelengths from filenames. Wavelengths,
PAR and scene-derived RWI `n` must be supplied explicitly. Other coefficients
use the catalog defaults unless overridden. In particular, choose SAVI's `L`
for your method; the catalog's shared default is 1, not an automatic 0.5.

Inputs must be calibrated quantities in the formula's units. Optical formulas
normally require fractional reflectance, SAR formulas require their specified
backscatter units, thermal formulas their temperature units, and kernel indices
require precomputed kernel rasters. A band being named NIR does not establish
sensor compatibility. Review each index's reference and platforms before use.

All rasters must share grid, CRS and dimensions. Embedded scale/offset and masks
are applied; missing external calibration is not guessed. Invalid arithmetic,
nonfinite inputs, masked pixels and float32 overflow become nodata. Arrays must
have identical shapes. The interpreter permits only arithmetic, symbols and
numeric literals; formulas cannot execute Python code. Output TIFF tags retain
the formula, reference and coefficient values. Cloud masks remain caller-supplied.
