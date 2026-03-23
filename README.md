# london-data-store

Lightweight Python client for the [London Data Store](https://data.london.gov.uk/) dataset catalogue. It wraps the portal's v2 JSON export API to discover datasets, search with scored results, filter by topic/publisher/licence, download files, and load spatial layers into GeoPandas — with disk caching, typed models, and an async alternative.

## Features
- **Disk-cached catalogue** — the ~10 MB JSON feed is cached locally (24-hour TTL) so repeated calls are instant.
- **Scored search** — fuzzy slug matching returns `(slug, score)` pairs via SequenceMatcher similarity.
- **Rich metadata** — `Dataset` and `Resource` dataclasses expose 20+ fields (topics, publisher, licence, temporal coverage, file hashes, etc.).
- **Filtering** — filter datasets by topic, publisher, update frequency, licence, format, or keyword.
- **File downloads** — streaming downloads with progress callbacks, MD5 integrity verification, and atomic writes.
- **Spatial data** — pull GeoJSON/GeoPackage/Shapefile layers directly into GeoPandas (EPSG:4326).
- **Async client** — `AsyncLondonDataStore` using httpx for concurrent operations.
- **CLI** — subcommands for search, info, topics, download, and more.
- **Custom exceptions** — `DatasetNotFoundError`, `FormatNotAvailableError`, `DownloadError`, `CacheError`.

## Installation
Requires Python 3.11+.

### Poetry (recommended)
```bash
poetry install
poetry shell
```

### pip
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: Scripts\activate
pip install -e .
```

### Optional extras

#### poetry install
```bash
poetry install --extras "dev geo async"
```

#### pip install
```bash
pip install -e ".[geo]"     # spatial data support (geopandas)
pip install -e ".[async]"   # async client (httpx)
pip install -e ".[dev]"     # development tools (pytest, ruff, pre-commit)
```

## Quick Start
```python
from london_data_store import LondonDataStore

with LondonDataStore() as lds:
    # Scored search — returns (slug, score) tuples
    results = lds.search("population", limit=5)

    # Full dataset metadata
    dataset = lds.get_dataset("population-projections")
    print(dataset.title, dataset.publisher, dataset.topics)

    # Filter by topic, publisher, or licence
    transport = lds.filter_by_topic("transport")
    tfl_data = lds.filter_by_publisher("Transport for London")
    open_data = lds.filter_by_licence("open")

    # Browse all topics
    topics = lds.get_all_topics()

    # Download a file
    path = lds.download_file("population-projections", format="csv")

    # Legacy methods still work
    all_slugs = lds.get_all_slugs()
    cycling = lds.filter_slugs_for_keyword("cycling")
```

### Async
```python
from london_data_store import AsyncLondonDataStore

async with AsyncLondonDataStore() as lds:
    results = await lds.search("cycling")
    dataset = await lds.get_dataset("cycling-infrastructure")
    path = await lds.download_file("cycling-infrastructure", format="csv")
```

### Caching
The catalogue is cached to disk for 24 hours by default. Control caching via constructor arguments:
```python
lds = LondonDataStore(cache=False)          # disable caching
lds = LondonDataStore(cache_ttl=3600)       # 1-hour TTL
lds.clear_cache()                           # invalidate manually
```

## Working With Spatial Data
Requires the `geo` extra (`pip install london-data-store[geo]`). Native libraries (GEOS, GDAL) must be installed.

```python
with LondonDataStore() as lds:
    dat = lds.get_map_data_to_plot(slug="london-borough-profiles", extension="geojson")
    # GeoDataFrame in EPSG:4326, ready for Plotly / Folium / GeoPandas plotting
```

## CLI
```bash
london-data-store slugs                         # list all dataset slugs
london-data-store search "population"           # fuzzy search
london-data-store search "population" --scored  # with similarity scores
london-data-store info "cycling-infrastructure" # full dataset metadata
london-data-store topics                        # list all topic categories
london-data-store topics --filter transport     # datasets in a topic
london-data-store download "population-projections" --format csv --progress
london-data-store formats                       # list available formats
london-data-store urls "population-projections" # get download URLs
london-data-store keywords "cycling"            # search by keyword/tag
```

Global options: `--json`, `--format {table,plain}`, `--limit N`, `--no-cache`.

## Development

### Running tests
```bash
pytest tests/ -v
pytest tests/test_api.py -v                      # single file
pytest tests/test_api.py::TestGetAllSlugs -v     # single class
pytest --cov=london_data_store -v                # with coverage
```

### Linting and formatting
```bash
ruff check .          # lint
ruff check . --fix    # lint with auto-fix
ruff format .         # format
```

### Pre-commit hooks
```bash
pre-commit install
```
