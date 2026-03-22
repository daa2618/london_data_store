"""Disk-based catalogue caching with TTL support."""

import contextlib
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import platformdirs

from .exceptions import CacheError
from .utils.logging_helper import BasicLogger

_bl = BasicLogger(verbose=False, log_directory=None, logger_name="CACHE")


class CatalogueCache:
    """Cache the London Data Store catalogue JSON to disk with TTL.

    Args:
        cache_dir: Directory for cache files. Defaults to platform-appropriate cache dir.
        ttl_seconds: Time-to-live in seconds. Defaults to 86400 (24 hours).
    """

    def __init__(self, cache_dir: Path | None = None, ttl_seconds: int = 86400):
        self._cache_dir = Path(cache_dir) if cache_dir else Path(platformdirs.user_cache_dir("london-data-store"))
        self._ttl_seconds = ttl_seconds

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def _cache_key(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def _cache_path(self, url: str) -> Path:
        return self._cache_dir / f"catalogue_{self._cache_key(url)}.json"

    def _meta_path(self, url: str) -> Path:
        return self._cache_dir / f"catalogue_{self._cache_key(url)}.meta.json"

    def get(self, url: str) -> list[dict] | None:
        """Return cached catalogue if fresh, else None."""
        cache_path = self._cache_path(url)
        meta_path = self._meta_path(url)

        if not cache_path.exists() or not meta_path.exists():
            return None

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            fetched_at = datetime.fromisoformat(meta["fetched_at"])
            age = (datetime.now(UTC) - fetched_at).total_seconds()

            if age > self._ttl_seconds:
                _bl.info(f"Cache expired (age: {age:.0f}s, ttl: {self._ttl_seconds}s)")
                return None

            data = json.loads(cache_path.read_text(encoding="utf-8"))
            _bl.info(f"Cache hit (age: {age:.0f}s)")
            return data
        except (json.JSONDecodeError, KeyError, OSError) as e:
            _bl.warning(f"Cache read failed, will re-fetch: {e}")
            return None

    def put(self, url: str, data: list[dict]) -> None:
        """Write catalogue to disk with timestamp metadata. Uses atomic writes."""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

            meta = {
                "url": url,
                "fetched_at": datetime.now(UTC).isoformat(),
                "ttl_seconds": self._ttl_seconds,
            }

            # Atomic write for cache data
            cache_path = self._cache_path(url)
            fd, tmp_path = tempfile.mkstemp(dir=self._cache_dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                os.replace(tmp_path, cache_path)
            except BaseException:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
                raise

            # Write metadata
            meta_path = self._meta_path(url)
            fd, tmp_path = tempfile.mkstemp(dir=self._cache_dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(meta, f)
                os.replace(tmp_path, meta_path)
            except BaseException:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
                raise

            _bl.info(f"Catalogue cached to {cache_path}")
        except OSError as e:
            raise CacheError(f"Failed to write cache: {e}") from e

    def invalidate(self, url: str | None = None) -> None:
        """Remove cached catalogue. If url is None, clear all cached catalogues."""
        try:
            if url is not None:
                for path in [self._cache_path(url), self._meta_path(url)]:
                    path.unlink(missing_ok=True)
                _bl.info(f"Cache invalidated for {url}")
            else:
                if self._cache_dir.exists():
                    for path in self._cache_dir.glob("catalogue_*"):
                        path.unlink(missing_ok=True)
                    _bl.info("All caches invalidated")
        except OSError as e:
            raise CacheError(f"Failed to invalidate cache: {e}") from e
