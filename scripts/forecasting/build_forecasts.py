# scripts/build_forecasts.py
from pathlib import Path
import pandas as pd
import numpy as np
from tqdm import tqdm
import pymc as pm
import warnings
from fantasy_optimizer.api_client import fetch_bootstrap_static

warnings.filterwarnings("ignore", category=UserWarning)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
INPUT_FILE = DATA_DIR / "player_gameweek_stats.parquet"
FIXTURES_FILE = DATA_DIR / "fixtures.parquet"  # pre-built fixture file
OUTPUT_FILE = DATA_DIR / "player_forecasts.parquet"

# --- Estimate points with expanded covariates ---
def estimate_expected_points_with_covariates(X: np.ndarray, y: np.ndarray, group_idx: int, num_groups: int) -> float:
    if len(y) < 2 or np.all(np.array(y) == 0):
        return 0.0

    X_std = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-3)

    with pm.Model():
        alpha_group = pm.Normal("alpha_group", mu=1.0, sigma=1.0, shape=num_groups)
        beta = pm.Normal("beta", mu=0.0, sigma=1.0, shape=X.shape[1])
        sigma = pm.Exponential("sigma", 1.0)

        mu = alpha_group[group_idx] + pm.math.dot(X_std, beta)
        pm.Normal("obs", mu=mu, sigma=sigma, observed=y)

        approx = pm.fit(2000, method="advi", progressbar=False)
        trace = approx.sample(500)

    # Predict for average standardized row
    alpha_samples = trace.posterior["alpha_group"].values[:, :, group_idx].flatten()
    beta_samples = trace.posterior["beta"].values.reshape(-1, X.shape[1])

    x_pred_std = (X.mean(axis=0) - X.mean(axis=0)) / (X.std(axis=0) + 1e-3)
    expected_log = alpha_samples + beta_samples @ x_pred_std
    return expected_log.mean().item()

# --- Forecasting logic ---
def build_forecasts(df: pd.DataFrame, fixtures: pd.DataFrame, group_column: str = "position", last_n: int = 5) -> pd.DataFrame:
    df = df[df["minutes"] > 0].copy()
    latest_round = df["round"].max()
    df_recent = df[df["round"] > latest_round - last_n].copy()

    df_recent = df_recent.merge(
        fixtures[["round", "team", "opponent_team", "was_home"]],
        how="left",
        on=["round", "opponent_team", "was_home"]
    )

    bootstrap = fetch_bootstrap_static()
    players = pd.DataFrame(bootstrap["elements"])

    team_strength = df_recent.groupby("team")["goals_scored"].mean().rename("team_strength")
    opponent_strength = df_recent.groupby("opponent_team")["goals_conceded"].mean().rename("opponent_weakness")

    merged = df_recent.merge(
        players[["id", group_column]].rename(columns={"id": "player_id"}),
        left_on="element", right_on="player_id"
    )
    group_map = {name: i for i, name in enumerate(merged[group_column].unique())}
    merged["group_idx"] = merged[group_column].map(group_map)

    merged = merged.merge(team_strength, on="team", how="left")
    merged = merged.merge(opponent_strength, left_on="opponent_team", right_index=True, how="left")
    merged["home"] = merged["was_home"].astype(float)

    grouped = merged.groupby("element").agg({
        "total_points": list,
        "minutes": list,
        "team_strength": list,
        "opponent_weakness": list,
        "home": list,
        "group_idx": "first"
    }).reset_index()

    results = []
    for _, row in tqdm(grouped.iterrows(), total=len(grouped)):
        try:
            X = np.column_stack([
                np.log(np.array(row["minutes"]) + 1e-3),
                row["team_strength"],
                row["opponent_weakness"],
                row["home"]
            ])
            y = np.array(row["total_points"])
            pred = estimate_expected_points_with_covariates(X, y, row["group_idx"], len(group_map))
        except Exception as e:
            print(f"❌ Failed for player {row['element']}: {e}")
            pred = np.mean(row["total_points"])

        results.append({"player_id": row["element"], "expected_points": pred})

    return pd.DataFrame(results)
# --- Main Entrypoint ---
if __name__ == "__main__":
    print("📥 Loading data...")
    df = pd.read_parquet(INPUT_FILE)
    fixtures = pd.read_parquet(FIXTURES_FILE)  # should contain was_home and opponent_team columns

    print("🔍 Running hierarchical forecast with covariates...")
    forecast_df = build_forecasts(df, fixtures, group_column="element_type")

    print(f"💾 Saving forecast to {OUTPUT_FILE}")
    forecast_df.to_parquet(OUTPUT_FILE, index=False)
    print(forecast_df.sort_values("expected_points", ascending=False).head())
