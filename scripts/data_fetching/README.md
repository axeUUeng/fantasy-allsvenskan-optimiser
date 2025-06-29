# Data Fetching Scripts

Utilities for retrieving raw data from the Fantasy Allsvenskan API. The scripts save JSON or Parquet files under the project `data` directory.

- **fetch_bootstrap.py** – downloads the bootstrap-static metadata.
- **fetch_fixtures.py** – retrieves upcoming and past fixtures and stores them as parquet.
- **fetch_player_histories.py** – fetches per-player gameweek history files.
