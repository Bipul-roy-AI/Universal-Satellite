# JavaScript / TypeScript SDK

Install from this repository: `npm install ./javascript` or `pnpm add ./javascript`.
This package is not yet published to npm. Requires Node 20+.

Spectral math is native JavaScript with TypeScript declarations and the same
280 pinned formulas as Python. Discovery, downloads, profiles and raster I/O
use a JSON-over-stdin bridge to the installed Python core. This keeps provider
validation and scientific raster behavior consistent; this is **not** an
independent browser SDK or a Python-free implementation. Set
`UNIVERSAL_SATELLITE_PYTHON` to the correct Python executable when necessary.
No shell command strings or credential files are generated.

```typescript
import {Client, computeIndex} from '@bipul-roy-ai/universal-satellite';
const client = new Client();
console.log(computeIndex('ndvi', {nir: 0.8, red: 0.2}));
const scenes = await client.search({dataset:'sentinel-2-l2a',bbox:[9,48,9.1,48.1],start:'2025-06-01',end:'2025-06-30',limit:2});
```

`client.download({manifest_path,asset_keys,output_dir,resume:true,retries:2,workers:4})`
returns downloaded files and per-asset failures; check both, not just promise
resolution. `rasterIndex`, `weather`, `environment`, `summary` and `toa` share the
Python behavior. `universal-satellite-js` exposes the same CLI as Python.
An AbortSignal terminates the Python child; an abrupt termination can leave a
stale download lock. Confirm the job stopped before removing that lock.

See `docs/indices.md` for units, coefficients, masks and limitations. Invalid
spectral math returns NaN, not a fabricated measurement. Registry data is MIT
licensed; its original copyright notice is bundled under `data/`.
