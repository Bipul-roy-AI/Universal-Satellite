# Local GeoAI samples

`RasterDataset` returns calibrated channel/height/width arrays and validity masks.
It supports NumPy, PyTorch tensors and JAX arrays. Install the appropriate torch
or jax build separately for your CPU/GPU; neither is a mandatory dependency.

```python
from universal_satellite.geoai import RasterDataset
samples = [{'optical':['red.tif','nir.tif'], 'radar':['vv.tif','vh.tif']}]
dataset = RasterDataset(samples, backend='torch')
sample = dataset[0]
# sample['optical']['data'], sample['optical']['valid']
```

It implements `__len__` and `__getitem__` for PyTorch DataLoader compatibility.
Each modality's bands must have matching grids. Different modalities may retain
different grids; you must align them when the model requires spatial correspondence.
Prepare consistent chip sizes for batching. Invalid pixels are zero-filled and
identified by the separate validity mask. Apply cloud masks, temporal matching,
normalization and train/validation splits yourself. No training data is fetched
implicitly and no labels are generated. Embedded scale/offset metadata is applied.
