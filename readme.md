# london-data-store

Lightweight Python client for the [London Data Store](https://data.london.gov.uk/) dataset catalogue. It wraps the portal's `export.json` feed so you can discover dataset slugs, filter by file type or keyword, and resolve download URLs (including spatial layers) with minimal boilerplate. Utilities for string similarity, stemming, and logging are bundled to support fuzzy searches and clean diagnostics.

## Features
- Fetch and cache the full dataset catalogue via a single JSON endpoint.
- Search dataset slugs with Snowball stemming or similarity scoring to handle imperfect queries.
- Filter datasets by format (CSV, GeoPackage, GeoJSON, Shapefile, etc.) and surface their download URLs.
- Pull spatial resources directly into GeoPandas and normalise coordinates to EPSG:4326.
- Shared HTTP session with automatic retries and connection pooling.
- CLI tool for quick catalogue queries from the terminal.
- Typed dataclass models (`Dataset`, `Resource`) for structured access to catalogue data.

## Project Layout
| Path | Description |
| --- | --- |
| `london_data_store/api.py` | `LondonDataStore` class with catalogue fetch, slug search, download resolution, and spatial helpers. |
| `london_data_store/models.py` | `Dataset` and `Resource` dataclasses for typed API responses. |
| `london_data_store/cli.py` | CLI entry point with subcommands for slugs, search, formats, urls, and keywords. |
| `london_data_store/utils/response.py` | HTTP wrappers with automatic headers, session support, and JSON handling. |
| `london_data_store/utils/strings_and_lists.py` | Snowball-based list search, similarity scoring, and numeric string conversion helpers. |
| `london_data_store/utils/logging_helper.py` | Thin logging wrapper used across the package. |
| `tests/` | 114 unit tests with mocked HTTP responses. |
| `pyproject.toml` | Dependency manifest and tool configuration (Poetry). |
| `LICENSE` | MIT licence. |

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
pip install -r requirements.txt
```

### Optional extras
```bash
poetry install --extras geo    # spatial data support (geopandas)
poetry install --extras dev    # development tools (pytest, ruff, pre-commit)
```

### NLTK data
The Snowball stemmer ships with `nltk`, so no extra downloads are needed. If you expand the utilities to use tokenisers, install the required corpora with `nltk.download(...)`.

## Quick Start
```python
from london_data_store import LondonDataStore

with LondonDataStore() as lds:
    # List every dataset slug available on the portal
    all_slugs = lds.get_all_slugs()

    # Fuzzy match slugs containing "population"
    population_slugs = lds.filter_slugs_for_string("population")

    # Only keep datasets that publish GeoJSON layers
    geojson_slugs = lds.filter_slug_for_d_type("geojson")

    # Inspect download URLs and metadata for a chosen slug
    urls = lds.get_download_url_for_slug(slug="population-projections", get_description=True)

    # Search by keyword/tag with stemming
    cycling = lds.filter_slugs_for_keyword("cycling")
```

## Working With Spatial Data
`LondonDataStore.get_map_data_to_plot` wraps GeoPandas to fetch map layers and reproject them for plotting. Requires the `geo` extra (`pip install london-data-store[geo]`).

```python
with LondonDataStore() as lds:
    dat = lds.get_map_data_to_plot(slug="london-borough-profiles", extension="geojson")
    # dat is a GeoDataFrame in EPSG:4326, ready for Plotly / Folium / GeoPandas plotting
```
If multiple files match your criteria, the method returns a list of URLs so you can choose the appropriate layer.

## CLI
```bash
london-data-store slugs                    # list all dataset slugs
london-data-store search "population"      # fuzzy search slugs
london-data-store formats                  # list available data formats
london-data-store urls "population-projections"  # get download URLs
london-data-store keywords "cycling"       # search by keyword/tag
```

## String & List Helper Examples
```python
from london_data_store.utils.strings_and_lists import StringOperations, ListOperations

value = StringOperations("1.2M residents").convert_to_integer()  # 1200000

search = ListOperations(["Road Safety", "cycling journeys", "Bus usage"], search_string="cycle")
matches = search.search_list_by_snowball()  # -> ["cycling journeys"]
```

## Development

### Running tests
```bash
poetry run pytest tests/ -v
poetry run pytest tests/test_api.py -v                # single file
poetry run pytest tests/test_api.py::TestGetAllSlugs -v  # single class
```

### Linting and formatting
```bash
poetry run ruff check .          # lint
poetry run ruff check . --fix    # lint with auto-fix
poetry run ruff format .         # format
```

### Pre-commit hooks
```bash
pre-commit install
```

### Notes
- Target Python 3.11 and keep dependencies aligned with `pyproject.toml`.
- GeoPandas requires native libraries (GEOS, GDAL). Install platform-specific prerequisites before running the spatial helpers.
