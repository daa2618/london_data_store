# london_data_store

**london_data_store** is a Python API to work with [data.london.gov.uk](https://data.london.gov.uk) easily and reliably. It simplifies accessing the london data store data via their API, helping you fetch, filter, and analyze available data with minimal setup.

---

## 🚀 Features

- 🔍 Search
- 🗺️ Fetch
- 🧑‍✈️ Access
- 🧩 Fetch geographical and neighbourhood boundary data
- ⚙️ Simple Pythonic interface around the raw API
- 🧪 Designed for analysts, data scientists, and developers

---

## 🧪 Prerequisites

- Python 3.11+
- refer to requirements.txt or pyproject.toml

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 📦 Installation

Clone and install locally:

```bash
git clone https://github.com/daa2618/london_data_store.git
cd london_data_store
pip install .
```

Or install directly using pip (once published on PyPI):

```bash
pip install london_data_store
```

---

## 🎯 Usage

Here’s how to get started:

```python
from london_data_store.api import LondonDataStore

client = LondonDataStore()

# Get all slugs
slugs = client.get_all_slugs()

---
# Filter slugs using sequence matching
search_result = client.filter_slugs_for_string("housing")
print(search_result)

# Fetch url to download data
download_url = client.get_download_url_for_slug(slug, get_description=True)
print(download_url)

---
```

---

## 🧾 Contributing

Contributions welcome! You can help by:

- Submitting bug reports or feature requests via Issues
- Improving documentation
- Writing tests or fixing bugs
- Extending API support (e.g., stop-and-search, priorities)

Please open a PR or reach out via GitHub Issues.

---

## ⚖️ License

This project is licensed under the [MIT License](LICENSE).
