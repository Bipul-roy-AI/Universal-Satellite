"""Stream individual public or already signed STAC assets to local files."""

from __future__ import annotations

import hashlib
import math
from http.client import HTTPException
import os
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class DownloadError(RuntimeError):
    """An asset could not be retrieved; messages never include signed URLs."""


class DownloadCancelled(DownloadError):
    """The caller cancelled a transfer before its final file was published."""


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._-")[:90]
    return slug or "asset"


def download_asset(
    item: dict,
    asset: str,
    output_dir: str | Path,
    *,
    overwrite: bool = False,
    timeout: float = 60,
    cancelled=None,
    resume=False,
    retries=0,
) -> Path:
    """Download one complete STAC asset with atomic publication.

    No provider credentials are guessed or loaded. Sign restricted provider URLs
    before calling this function. Existing files are preserved by default, and
    temporary downloads are removed after failure. Downloads are not resumed.
    """
    if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Download timeout must be positive.")
    if cancelled is not None and cancelled():
        raise DownloadCancelled("Download cancelled; no final file was written.")
    entries = item.get("assets", {})
    entry = entries.get(asset) if isinstance(entries, dict) else None
    if not isinstance(entry, dict) or not isinstance(entry.get("href"), str):
        raise ValueError(f"The scene has no downloadable asset named {asset!r}.")
    href = entry["href"]
    parsed = None
    try:
        parsed = urlsplit(href)
        valid_http = parsed.scheme in {"https", "http"} and bool(parsed.hostname)
        has_credentials = parsed.username is not None or parsed.password is not None
    except ValueError:
        valid_http, has_credentials = False, False
    if not valid_http or has_credentials:
        message = (
            "Assets must use an HTTP(S) URL without embedded credentials. "
            "For s3:// assets, obtain a provider-supported HTTPS URL first."
        )
        if parsed is not None and parsed.scheme == "s3":
            message += (
                " This scene's link is s3:// (requester-pays AWS storage), which this tool "
                "cannot fetch. Choose a source with public HTTPS assets, such as Sentinel-2 L2A, "
                "Landsat 4-9 L2 or Sentinel-1 GRD, or retrieve this product through its provider."
            )
        raise ValueError(message)
    identifier = str(item.get("id", "scene"))
    # Include a stable digest so sanitizing two distinct IDs cannot collide.
    digest = hashlib.sha256(f"{identifier}\0{asset}".encode()).hexdigest()[:10]
    suffix = Path(parsed.path).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
        suffix = ".bin"
    directory = Path(output_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{_slug(identifier)}__{_slug(asset)}_{digest}{suffix}"
    if destination.exists() or destination.is_symlink():
        if not overwrite:
            raise FileExistsError(f"Download already exists: {destination}")
        if destination.is_dir():
            raise IsADirectoryError(str(destination))

    if resume or retries:
        from .transfer import transfer
        return transfer(href, destination, timeout=timeout, overwrite=overwrite,
                        resume=resume, retries=retries, cancelled=cancelled)

    temporary: Path | None = None
    try:
        request = Request(href, headers={"User-Agent": "Universal-Satellite/0.2.0"})
        with urlopen(request, timeout=timeout) as response:
            # Never save an unsolicited partial response as a complete asset.
            if response.status != 200:
                raise DownloadError(f"Asset server returned HTTP {response.status}; expected 200.")
            media_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            expected_type = entry.get("type", "")
            expected_type = expected_type.split(";")[0].strip().lower() if isinstance(expected_type, str) else ""
            if media_type in {"text/html", "application/xhtml+xml"} and expected_type not in {"text/html", "application/xhtml+xml"}:
                raise DownloadError("Asset server returned an HTML page instead of data; provider sign-in may be required. No file was written.")
            length = response.headers.get("Content-Length")
            try:
                expected = int(length) if length is not None else None
            except ValueError as error:
                raise DownloadError("Asset server returned an invalid Content-Length.") from error
            if expected is not None and expected < 0:
                raise DownloadError("Asset server returned a negative Content-Length.")
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=directory, prefix=".download-", suffix=".part", delete=False
            ) as target:
                temporary = Path(target.name)
                transferred = 0
                while True:
                    if cancelled is not None and cancelled():
                        raise DownloadCancelled("Download cancelled; no final file was written.")
                    chunk = response.read(1024 * 1024)
                    if cancelled is not None and cancelled():
                        raise DownloadCancelled("Download cancelled; no final file was written.")
                    if not chunk:
                        break
                    target.write(chunk)
                    transferred += len(chunk)
                target.flush()
                os.fsync(target.fileno())
            if expected is not None and transferred != expected:
                raise DownloadError("Asset download was incomplete; no final file was written.")
        if cancelled is not None and cancelled():
            raise DownloadCancelled("Download cancelled; no final file was written.")
        if overwrite:
            os.replace(temporary, destination)
        else:
            # Unlike exists()+replace(), link refuses a competing writer's file.
            os.link(temporary, destination)
            temporary.unlink()
        return destination
    except HTTPError as error:
        raise DownloadError(
            f"Asset server returned HTTP {error.code}. "
            "Check provider access requirements and refresh expired signed links."
        ) from None
    except URLError:
        raise DownloadError("Asset connection failed. Check network access and provider availability.") from None
    except (TimeoutError, ConnectionError, HTTPException):
        raise DownloadError("Asset transfer failed or timed out; no final file was written.") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def download_manifest(
    manifest_path: str | Path,
    asset_keys: list[str],
    output_dir: str | Path,
    *,
    sign_planetary: bool = False,
    overwrite: bool = False,
    progress=None,
    cancelled=None,
    workers=1,
    resume=False,
    retries=0,
) -> dict:
    """Download selected assets for every scene in a saved GeoJSON inventory.

    This synchronous worker belongs on the desktop GIS host's background task or
    geoprocessing thread. ``progress(percent, message)`` runs before and after
    each transfer. ``cancelled()`` is checked between transfers and while bytes
    stream. Completed files survive cancellation; incomplete files are removed.
    Individual asset failures are collected while remaining transfers continue.
    Signed links stay in memory and are never written back to the manifest.
    """
    if isinstance(workers,bool) or not isinstance(workers,int) or not 1 <= workers <= 16:
        raise ValueError("workers must be an integer from 1 through 16")
    from .export import read_geojson
    from .http import ProviderError

    if not isinstance(asset_keys, (list, tuple)) or not asset_keys:
        raise ValueError("Select at least one asset key to download.")
    if any(not isinstance(key, str) or not key.strip() for key in asset_keys):
        raise ValueError("Asset keys must be nonempty strings.")
    keys = [key.strip() for key in asset_keys]
    if len(keys) != len(set(keys)):
        raise ValueError("Select each asset key only once.")
    if not isinstance(output_dir, (str, Path)) or (isinstance(output_dir, str) and not output_dir.strip()):
        raise ValueError("Choose an output directory for downloaded images.")
    directory = Path(output_dir).expanduser()
    if directory.exists() and not directory.is_dir():
        raise ValueError("The output directory is an existing file; choose a folder instead.")
    manifest = read_geojson(manifest_path)
    items = manifest["features"]
    if not items:
        raise ValueError("Manifest contains no scenes to download.")
    result = {"downloaded": [], "failed": [], "cancelled": False}
    total = len(items) * len(keys)
    completed = 0

    def report(message):
        if progress is not None:
            progress(100.0 * completed / total, message)

    def stop():
        if cancelled is not None and cancelled():
            result["cancelled"] = True
            report("Download cancelled; completed files were retained.")
            return True
        return False

    if stop():
        return result
    directory.mkdir(parents=True, exist_ok=True)
    signer = None
    if sign_planetary:
        from .client import Client
        signer = Client()
    def attempt(item, key):
        try:
            assets = item.get("assets", {})
            if key not in assets or not isinstance(assets[key], dict) or not isinstance(assets[key].get("href"), str):
                raise ValueError("Scene has no valid downloadable link for the selected asset. Available keys: " + ", ".join(assets) + ". Enter * alone to select all advertised assets.")
            selected = {**item, "assets": {key: assets[key]}}
            if signer is not None:
                selected = signer.sign_item(selected)
            options = {"overwrite":overwrite, "cancelled":cancelled}
            if resume or retries:
                options.update(resume=resume,retries=retries)
            return ("downloaded", str(download_asset(selected,key,directory,**options)))
        except DownloadCancelled:
            return ("cancelled", None)
        except (ValueError, DownloadError, ProviderError, OSError) as error:
            message = re.sub(r"(?i)(?:https?|s3)://[^\s'\"<>]+", "[redacted URL]", str(error))
            return ("failed", {"scene":item["id"], "asset":key, "error":message})

    def collect(outcome):
        nonlocal completed
        kind, value = outcome
        if kind == "cancelled": result["cancelled"] = True
        else: result[kind].append(value)
        completed += 1
        report(f"Completed {completed} of {total} asset attempts.")

    tasks = [(item,key) for item in items for key in (list(item.get("assets",{})) if keys == ["*"] else keys)]
    total = len(tasks)
    if not total: raise ValueError("Manifest contains no downloadable assets")
    if workers == 1:
        for number,(item,key) in enumerate(tasks,1):
            if stop(): return result
            report(f"Downloading asset {number} of {total}.")
            collect(attempt(item,key))
            if result["cancelled"]: return result
    else:
        from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
        # Bound queued work as well as active threads; progress stays on caller thread.
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending = set()
            iterator = iter(tasks)
            exhausted = False
            while pending or not exhausted:
                if stop():
                    for future in pending: future.cancel()
                    exhausted = True
                while not exhausted and len(pending) < workers:
                    try: item,key = next(iterator)
                    except StopIteration: exhausted = True; break
                    pending.add(pool.submit(attempt,item,key))
                if not pending: break
                done,pending = wait(pending,timeout=0.1,return_when=FIRST_COMPLETED)
                for future in done:
                    if not future.cancelled(): collect(future.result())
    return result
