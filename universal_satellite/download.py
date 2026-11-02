"""Stream individual public or already signed STAC assets to local files."""

from __future__ import annotations

import hashlib
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
) -> Path:
    """Download one complete STAC asset with atomic publication.

    No provider credentials are guessed or loaded. Sign restricted provider URLs
    before calling this function. Existing files are preserved by default, and
    temporary downloads are removed after failure. Downloads are not resumed.
    """
    if timeout <= 0:
        raise ValueError("Download timeout must be positive.")
    entry = item.get("assets", {}).get(asset)
    if not isinstance(entry, dict) or not isinstance(entry.get("href"), str):
        raise ValueError(f"The scene has no downloadable asset named {asset!r}.")
    href = entry["href"]
    try:
        parsed = urlsplit(href)
        valid_http = parsed.scheme in {"https", "http"} and bool(parsed.hostname)
        has_credentials = parsed.username is not None or parsed.password is not None
    except ValueError:
        valid_http, has_credentials = False, False
    if not valid_http or has_credentials:
        raise ValueError(
            "Assets must use an HTTP(S) URL without embedded credentials. "
            "For s3:// assets, obtain a provider-supported HTTPS URL first."
        )
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

    temporary: Path | None = None
    try:
        request = Request(href, headers={"User-Agent": "Universal-Satellite/0.1"})
        with urlopen(request, timeout=timeout) as response:
            # Never save an unsolicited partial response as a complete asset.
            if response.status != 200:
                raise DownloadError(f"Asset server returned HTTP {response.status}; expected 200.")
            media_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            expected_type = entry.get("type", "").split(";")[0].strip().lower()
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
                while chunk := response.read(1024 * 1024):
                    target.write(chunk)
                    transferred += len(chunk)
                target.flush()
                os.fsync(target.fileno())
            if expected is not None and transferred != expected:
                raise DownloadError("Asset download was incomplete; no final file was written.")
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
