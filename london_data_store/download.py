"""File download manager with progress and integrity verification."""

import hashlib
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

import requests

from .exceptions import DownloadError
from .utils.logging_helper import BasicLogger

_bl = BasicLogger(verbose=False, log_directory=None, logger_name="DOWNLOAD")


class DownloadManager:
    """Downloads files with optional progress reporting and integrity checks.

    Args:
        session: A requests.Session to use for HTTP requests.
    """

    def __init__(self, session: requests.Session):
        self._session = session

    def download_file(
        self,
        url: str,
        destination: Path,
        *,
        progress_callback: Callable[[int, int | None], None] | None = None,
        expected_hash: str | None = None,
        expected_size: int | None = None,
        chunk_size: int = 8192,
    ) -> Path:
        """Download a file with optional progress reporting and integrity checks.

        Args:
            url: The URL to download from.
            destination: Target file path. If a directory, filename is inferred from URL.
            progress_callback: Called with (bytes_downloaded, total_bytes) after each chunk.
            expected_hash: Expected MD5 hash (with optional version suffix like '-1').
            expected_size: Expected file size in bytes.
            chunk_size: Download chunk size in bytes.

        Returns:
            The final file path.

        Raises:
            DownloadError: On HTTP errors, hash mismatch, or size mismatch.
        """
        destination = Path(destination)

        # If destination is a directory, infer filename from URL
        if destination.is_dir():
            filename = urlsplit(url).path.split("/")[-1] or "download"
            destination = destination / filename

        destination.parent.mkdir(parents=True, exist_ok=True)
        part_path = destination.with_suffix(destination.suffix + ".part")

        try:
            response = self._session.get(url, stream=True, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise DownloadError(f"Failed to download {url}: {e}") from e

        total_size = int(response.headers.get("content-length", 0)) or None
        bytes_downloaded = 0
        md5_hash = hashlib.md5()

        try:
            fd, tmp_path = tempfile.mkstemp(dir=destination.parent, suffix=".tmp")
            try:
                with os.fdopen(fd, "wb") as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        if expected_hash:
                            md5_hash.update(chunk)
                        if progress_callback:
                            progress_callback(bytes_downloaded, total_size)

                os.replace(tmp_path, part_path)
            except BaseException:
                import contextlib

                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
                raise
        except DownloadError:
            raise
        except Exception as e:
            raise DownloadError(f"Failed to write file: {e}") from e

        # Verify integrity
        if expected_size is not None and bytes_downloaded != expected_size:
            part_path.unlink(missing_ok=True)
            raise DownloadError(f"Size mismatch: expected {expected_size} bytes, got {bytes_downloaded}")

        if expected_hash is not None:
            # Strip version suffix (e.g., 'abc123-1' -> 'abc123')
            clean_hash = expected_hash.split("-")[0] if "-" in expected_hash else expected_hash
            actual_hash = md5_hash.hexdigest()
            if actual_hash != clean_hash:
                part_path.unlink(missing_ok=True)
                raise DownloadError(f"Hash mismatch: expected {clean_hash}, got {actual_hash}")

        # Move from .part to final destination
        os.replace(part_path, destination)
        _bl.info(f"Downloaded {url} to {destination} ({bytes_downloaded} bytes)")
        return destination
