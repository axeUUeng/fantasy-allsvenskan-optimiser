# Fantasy Allsvenskan Optimiser

Scripts for optimising fantasy Allsvenskan teams using player history, forecasting, and integer linear programming.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 18+

## Setup

**1. Install dependencies**
```bash
uv sync
```

**2. Configure the database**

Create a `.env` file in the project root:
```
DATABASE_URL=postgresql://<user>:<password>@localhost:5432/fantasy_allsvenskan
```

**3. Create tables**
```bash
uv run python scripts/init_db.py
```

**4. Ingest data**
```bash
uv run python scripts/ingest.py           # uses local JSON cache for player histories
uv run python scripts/ingest.py --refresh # force re-fetch everything from the API
```

## Jupyter Notebooks

The venv is registered as a Jupyter kernel named **"Fantasy Allsvenskan"**.

```bash
uv run jupyter notebook
```

Select the **Fantasy Allsvenskan** kernel in the notebook interface.

## Workflow

Run these scripts in order after each gameweek:

```bash
# 1. Refresh the database
uv run python scripts/ingest.py

# 2. Build forecasts
uv run python scripts/build_forecasts.py

# 3. Run the optimiser
uv run python scripts/optimize_team.py --team-file data/curr_team/myteam.json
```

## Project Structure

```
fantasy_optimizer/       # Core library
  api_client.py          # API fetching with local JSON cache
  db/                    # Database layer (SQLAlchemy models, upsert helpers)
  models/                # Pydantic models for API data validation

scripts/
  ingest.py              # All data ingestion (players, teams, fixtures, histories)
  init_db.py             # Creates database tables (run once on new setup)
  build_forecasts.py     # Builds per-player expected points forecasts
  optimize_team.py       # Team optimisation (CVXPY integer linear programming)
  data_fetching/         # Fetch helpers called by ingest.py

data/                    # Local JSON cache (gitignored)
notebooks/               # Jupyter notebooks
```

## Development

Install pre-commit hooks (runs `isort`, `black`, `ruff` on each commit):
```bash
uv run pre-commit install
```
