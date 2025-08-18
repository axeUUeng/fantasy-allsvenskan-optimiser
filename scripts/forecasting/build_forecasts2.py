# scripts/simulate_forecasts.py
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
INPUT_FILE = DATA_DIR / "player_gameweek_stats.parquet"
OUTPUT_FILE = DATA_DIR / "player_simulation_forecasts.parquet"
TOTAL_ROUNDS = 30  # Total number of rounds in the season


def weighted_history(
    points: np.ndarray, decay: float = 0.9, n_samples: int = None
) -> np.ndarray:
    if len(points) == 0:
        return np.array([])
    if n_samples is None:
        n_samples = len(points)
    weights = decay ** np.arange(len(points))[::-1]
    weights /= weights.sum()
    return np.random.choice(points, size=n_samples, p=weights, replace=True)


def simulate_rest_of_season(
    points: np.ndarray, rounds_left: int, n_sims: int = 50_000
) -> float:
    """Simulate remaining rounds using an empirical distribution."""
    if len(points) == 0 or rounds_left <= 0:
        return 0.0

    # Empirical distribution with extra high/low points
    sims = np.array(
        [
            weighted_history(points, decay=0.9, n_samples=rounds_left)
            for _ in range(n_sims)
        ]
    )
    totals = sims.sum(axis=1)
    return totals.mean() / rounds_left


def build_simulation_forecasts(
    df: pd.DataFrame, total_rounds: int = TOTAL_ROUNDS
) -> pd.DataFrame:
    latest_round = df["round"].max()
    rounds_left = max(total_rounds - latest_round, 0)

    grouped = df.groupby("element")["total_points"].apply(list)
    results = []
    for player_id, history in tqdm(
        grouped.items(), desc="Simulating", total=len(grouped), unit="player"
    ):
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
    print(forecast_df.sort_values("expected_points", ascending=False).head())
