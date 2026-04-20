# scripts/simulate_forecasts.py
from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_FILE = DATA_DIR / "player_gameweek_stats.parquet"
OUTPUT_FILE = DATA_DIR / "player_simulation_forecasts.parquet"
TOTAL_ROUNDS = 30  # Total number of rounds in the season


def simulate_rest_of_season(points: np.ndarray, rounds_left: int, n_sims: int = 1000) -> float:
    """Simulate remaining rounds using an empirical distribution."""
    if len(points) == 0 or rounds_left <= 0:
        return 0.0

    mu = points.mean()
    sigma = points.std(ddof=0)

    # Empirical distribution with extra high/low points
    dist = np.concatenate([points, [mu + sigma, mu - sigma]])

    sims = np.random.choice(dist, size=(n_sims, rounds_left), replace=True)
    totals = sims.sum(axis=1)
    return totals.mean()


def build_simulation_forecasts(df: pd.DataFrame, total_rounds: int = TOTAL_ROUNDS) -> pd.DataFrame:
    latest_round = df["round"].max()
    rounds_left = max(total_rounds - latest_round, 0)

    grouped = df.groupby("element")["total_points"].apply(list)
    results = []
    for player_id, history in grouped.items():
        expected = simulate_rest_of_season(np.array(history), rounds_left)
        results.append({"player_id": player_id, "expected_points": expected})

    return pd.DataFrame(results)


if __name__ == "__main__":
    print("📥 Loading player gameweek stats...")
    df = pd.read_parquet(INPUT_FILE)

    print("🎲 Running simple simulation forecasts...")
    forecast_df = build_simulation_forecasts(df)

    print(f"💾 Saving forecasts to {OUTPUT_FILE}")
    forecast_df.to_parquet(OUTPUT_FILE, index=False)
    print(forecast_df.sort_values('expected_points', ascending=False).head())
