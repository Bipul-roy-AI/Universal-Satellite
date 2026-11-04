# Reliable downloads

CLI downloads use four asset workers, two retries and HTTP resumption by default:

```sh
universal-satellite download scenes.geojson --asset red,nir --output imagery --workers 4 --retries 2
universal-satellite download scenes.geojson --asset '*' --output imagery --sign-planetary
```

The standalone GIS download tools provide **Resume interrupted downloads** and
**Concurrent asset downloads** controls. The original search-and-download action
retains its sequential behavior. Use the standalone download tool for large jobs.
Python callers opt in with `download_manifest(..., workers=4, resume=True, retries=2)`.

Resumption uses a strong ETag and If-Range, checks Content-Range/length and only
publishes complete files. Servers that ignore Range restart from byte zero.
Changed URLs or missing validators also restart safely. HTTP 416 clears the
partial file and retries; it is never assumed to mean the file is complete.
Transient 429/5xx failures retry with bounded backoff. Per-destination locks
prevent competing writers. Remove a stale `.lock` only after verifying that no
job owns it. `.part.json` stores a URL hash and validator, not credentials.

Cancellation preserves completed files. With resume enabled, partial files may
remain; rerun the same command to continue. Existing complete files are protected
unless overwrite is explicitly requested. `*` means every asset in each scene,
including QA, metadata and previews; it can download much more than selected bands.
Failures remain per asset. CLI returns nonzero on any failure or cancellation.
Parallelism is across assets, not multiple ranges within one asset.
