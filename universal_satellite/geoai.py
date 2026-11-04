"""Local calibrated multimodal samples for NumPy, PyTorch or JAX workflows."""

class RasterDataset:
    """Each sample maps modality names to ordered, aligned single-band rasters.

    Different modalities may have different grids; no resampling, normalization,
    cloud masking or temporal matching is guessed. Prepare those upstream. Array
    layout is channels/height/width. Invalid pixels are zero-filled with a separate
    boolean validity mask. The object implements the PyTorch Dataset protocol.
    """
    def __init__(self, samples, *, backend='numpy', max_pixels=25000000):
        if backend not in ('numpy','torch','jax'):raise ValueError('backend must be numpy, torch or jax')
        if isinstance(max_pixels,bool) or not isinstance(max_pixels,int) or max_pixels<=0:raise ValueError('max_pixels must be a positive integer')
        self.samples=list(samples);self.backend=backend;self.max_pixels=max_pixels
        if any(not isinstance(sample,dict) or not sample or any(not isinstance(name,str) or not isinstance(paths,(list,tuple)) or not paths for name,paths in sample.items()) for sample in self.samples):
            raise ValueError('Each sample must map modality names to nonempty lists of raster paths')
    def __len__(self):return len(self.samples)
    def __getitem__(self,index):
        import numpy as np
        import rasterio
        output={}
        for modality,paths in self.samples[index].items():
            arrays=[];masks=[];reference=None
            for path in paths:
                with rasterio.open(path) as reader:
                    grid=(reader.crs,reader.transform,reader.width,reader.height)
                    if reader.count!=1 or reader.crs is None:raise ValueError('Dataset inputs must be single-band rasters with CRS')
                    if reference is not None and grid!=reference:raise ValueError('Bands within each modality must have matching grids')
                    reference=grid
                    if reader.width*reader.height*len(paths)>self.max_pixels:raise ValueError('Sample exceeds pixel budget; use prepared chips')
                    data=reader.read(1,masked=True).astype('float64')
                    data=data*reader.scales[0]+reader.offsets[0]
                    valid=~np.ma.getmaskarray(data)&np.isfinite(data.data)&(np.abs(data.data)<=np.finfo('float32').max)
                    arrays.append(np.where(valid,data.data,0).astype('float32'));masks.append(valid)
            values=np.stack(arrays);valid=np.stack(masks)
            if self.backend=='torch':
                try:import torch
                except ImportError:raise RuntimeError('Install a platform-compatible PyTorch distribution for backend=torch') from None
                values,valid=torch.from_numpy(values),torch.from_numpy(valid)
            elif self.backend=='jax':
                try:import jax.numpy as jnp
                except ImportError:raise RuntimeError('Install a platform-compatible JAX distribution for backend=jax') from None
                values,valid=jnp.asarray(values),jnp.asarray(valid)
            output[modality]={'data':values,'valid':valid,'crs':str(reference[0]),'transform':tuple(reference[1])}
        return output
