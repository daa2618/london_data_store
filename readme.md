# Personal Python Projects

Analyses, automations, and dashboards that power my personal data workflows. The projects span household finance, travel research, sports and media tracking, civic datasets, and general experimentation with Plotly, Google APIs, and custom helper utilities.

## Highlights
- Pull structured and unstructured data from Google Sheets, Drive, public APIs, and local snapshots using reusable helper modules.
- Build Plotly dashboards for budgeting, travel planning, automotive research, streaming behaviour, and broader analytics experiments.
- Maintain notebooks for exploratory data analysis and reporting workflows across crime statistics, market surveys, Formula 1, TMDB, elections, and more.
- Centralize credential discovery and cross-project helpers so new pipelines can reuse the same environment.

## Directory Guide
| Path | Notes |
| --- | --- |
| `google_cloud_console/` | Google API clients, automation scripts, and dashboards (e.g. `household_finance`, `bills_and_utilities`, `car_trips`). |
| `Finance/` | Historical household expenditure and Yahoo Finance tooling. |
| `Data/`, `archive/`, `images/` | Local snapshots, exports, processed artefacts, and generated figures. |
| `notebooks/`, `<domain>/notebooks/` | Jupyter exploration per topic (NYC, crime stats, stock analysis, etc.). |
| `automotive_stuff/`, `netflix_viewing_figures/`, `stocks/`, `tmdb/`, `election24/`, ... | Topic-specific pipelines, dashboards, and datasets. |
| `utils/` | Local helpers like `creds_dir.py` for finding the shared credentials directory. |
| `pyproject.toml`, `poetry.lock`, `requirements.txt` | Dependency manifests (Poetry preferred for reproducibility). |

## Environment Setup
Use Python 3.11 to match the configured tooling.

### Option 1: Poetry (recommended)
```bash
poetry install
poetry shell
```

### Option 2: Virtualenv + pip
```bash
python -m venv .venv
source .venv/bin/activate  # Scripts\activate on Windows
pip install -r requirements.txt
```

### Private helper dependency
Install access to the private Bitbucket package referenced in `pyproject.toml` and `requirements.txt`:
```
helper-tools @ git+https://<token>@bitbucket.org/project-bike-sharing/helper_tools.git
```
Without this package, Google integrations and plotting utilities will not import correctly.

## Credentials & Secrets
- Google service-account credentials (`supple-rex-310505-cace3ef2016e.json`) must live under a OneDrive-backed `Documents/Creds/` directory. Discovery is handled by `helper_tools.onedrive_ops.find_one_drive_folder()` and `utils/creds_dir.py`.
- Project-specific tokens (travel APIs, TMDB keys, etc.) can be stored in the same `Creds` folder or surfaced via `.env` files referenced by individual scripts.
- Keep all secret files outside of version control. If you introduce additional providers, document the expected locations here.

## Running Automations & Dashboards
- **Household finance plots** (`google_cloud_console/google_sheets/household_finance/plots.py`)
  ```bash
  poetry run python google_cloud_console/google_sheets/household_finance/plots.py
  ```
  Instantiate `OverviewPlots(save_plot=True)` to export PNGs to `household_finance/images/`.

- **Household data ingestion**  
  Modules such as `expenses.py`, `income.py`, and `savings.py` wrap Google Sheets fetch-and-clean routines. They rely on the spreadsheet URL defined in `household_finance/__init__.py` and the credentials outlined above.

- **Notebook workflows**  
  Launch with `poetry run jupyter lab` (or `notebook`). Notebooks live under the top-level `notebooks/` directory and within topic subfolders.

For new scripts, reuse helpers from the `helper_tools` package (Plotly theming, Drive utilities, request wrappers) to stay consistent.

## Data Management
- Large or sensitive datasets are excluded from Git. Scripts generally expect local CSVs within `Data/` or project folders; confirm required inputs before execution.
- Generated artefacts (reports, charts, PDFs) typically land in sibling `images/` or `archive/` directories. Remove temporary outputs before committing unless they are intentional results.

## Development Workflow
- Target Python 3.11 features and typing conventions used across the repo.
- Formatting and linting are optional; run your preferred tooling (`ruff`, `black`, etc.) before committing changes.
- When introducing new domains or automations, update the directory table and capture any new external dependencies or credential requirements in this README.
