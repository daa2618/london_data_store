# london-data-store

Lightweight Python client for the [London Data Store](https://data.london.gov.uk/) dataset catalogue. It wraps the portal's `export.json` feed so you can discover dataset slugs, filter by file type or keyword, and resolve download URLs (including spatial layers) with minimal boilerplate. Utilities for string similarity, stemming, and logging are bundled to support fuzzy searches and clean diagnostics.

## Features
- Fetch and cache the full dataset catalogue via a single JSON endpoint.
- Search dataset slugs with Snowball stemming or similarity scoring to handle imperfect queries.
- Filter datasets by format (CSV, GeoPackage, GeoJSON, Shapefile, etc.) and surface their download URLs.
- Pull spatial resources directly into GeoPandas and normalise coordinates to EPSG:4326.
- Shared helpers for resilient HTTP requests, string conversions, and structured logging.

## Project Layout
| Path | Description |
| --- | --- |
| `london_data_store/api.py` | `LondonDataStore` class with catalogue fetch, slug search, download resolution, and spatial helpers. |
| `london_data_store/utils/response.py` | HTTP wrappers with automatic headers, retries, and JSON handling. |
| `london_data_store/utils/strings_and_lists.py` | Snowball-based list search, similarity scoring, and numeric string conversion helpers. |
| `london_data_store/utils/logging_helper.py` | Configurable logger utilities used across the package. |
| `requirements.txt`, `pyproject.toml` | Dependency manifests (Poetry preferred). |
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

### NLTK data
The Snowball stemmer ships with `nltk`, so no extra downloads are needed. If you expand the utilities to use tokenisers, install the required corpora with `nltk.download(...)`.

## Quick Start
```python
from london_data_store.api import LondonDataStore

lds = LondonDataStore()

# List every dataset slug available on the portal
all_slugs = lds.get_all_slugs()

# Fuzzy match slugs containing "population"
population_slugs = lds.filter_slugs_for_string("population")

# Only keep datasets that publish GeoJSON layers
geojson_slugs = lds.filter_slug_for_d_type("geojson")

# Inspect download URLs and metadata for a chosen slug
urls = lds.get_download_url_for_slug(slug="population-projections", get_description=True)
```

## Working With Spatial Data
`LondonDataStore.get_map_data_to_plot` wraps GeoPandas to fetch map layers and reproject them for plotting:
```python
dat = lds.get_map_data_to_plot(slug="london-borough-profiles", extension="geojson")
# dat is a GeoDataFrame in EPSG:4326 and ready for Plotly / Folium / GeoPandas plotting
```
If multiple files match your criteria, the method returns a list of URLs so you can choose the appropriate layer.

## String & List Helper Examples
```python
from london_data_store.utils.strings_and_lists import StringOperations, ListOperations

value = StringOperations("1.2M residents").convert_to_integer()  # 1200000

search = ListOperations(["Road Safety", "cycling journeys", "Bus usage"], search_string="cycle")
matches = search.search_list_by_snowball()  # -> ["cycling journeys"]
```

## Logging & Diagnostics
`logging_helper.BasicLogger` provides consistent console/file logging with rotation support. Pass `verbose=True` when debugging to surface HTTP requests, match decisions, and download metadata.

## Development Notes
- Target Python 3.11 and keep dependencies aligned with `pyproject.toml`.
- GeoPandas requires native libraries (GEOS, GDAL). Install platform-specific prerequisites before running the spatial helpers.
- Add automated tests or notebooks under a separate folder if you extend functionality, and document new endpoints or utilities in this README.
