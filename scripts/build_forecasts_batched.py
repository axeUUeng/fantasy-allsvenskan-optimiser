# scripts/build_forecasts_batched.py
from pathlib import Path
import numpy as np
import pandas as pd
import pymc as pm
import pytensor.tensor as pt
from tqdm import tqdm
import warnings
from fantasy_optimizer.api_client import fetch_bootstrap_static

warnings.filterwarnings("ignore", category=UserWarning)

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_FILE = DATA_DIR / "player_gameweek_stats.parquet"
FIXTURES_FILE = DATA_DIR / "fixtures.parquet"
OUTPUT_FILE = DATA_DIR / "player_forecasts.parquet"

# --- Main Forecast Function ---
def build_forecasts_batched(df: pd.DataFrame, fixtures: pd.DataFrame, last_n: int = 5) -> pd.DataFrame:
    df = df[df["minutes"] > 0].copy()
    latest_round = df["round"].max()
    df_recent = df[df["round"] > latest_round - last_n].copy()
    df = df.merge(
        fixtures[["round", "team", "opponent_team", "was_home"]],
        how="left",
        on=["round", "opponent_team", "was_home"]
    )

    df_recent = df_recent.merge(
        fixtures[["round", "team", "opponent_team", "was_home"]],
        how="left",
        on=["round", "opponent_team", "was_home"]
    )

    bootstrap = fetch_bootstrap_static()
    players = pd.DataFrame(bootstrap["elements"])
    teams = pd.DataFrame(bootstrap["teams"])

    # Add position
    players["position"] = players["element_type"].map({1: "GK", 2: "DEF", 3: "MID", 4: "FWD"})
    position_map = {pos: i for i, pos in enumerate(players["position"].unique())}
    players["group_idx"] = players["position"].map(position_map)

    df_recent = df_recent.merge(players[["id", "group_idx"]], left_on="element", right_on="id")

    # Team strength: average goals scored
    df_recent["team_strength"] = df_recent.groupby("team")["goals_scored"].transform("mean")
    # Opponent weakness: average goals conceded
    df_recent["opponent_weakness"] = df_recent.groupby("opponent_team")["goals_conceded"].transform("mean")

    # Assemble design matrix
    df_recent["log_minutes"] = np.log(df_recent["minutes"] + 1e-3)
    df_recent["home"] = df_recent["was_home"].astype(float)
    covariates = ["log_minutes", "team_strength", "opponent_weakness", "home"]
    X = df_recent[covariates].values
    y = df_recent["total_points"].values
    group_idx = df_recent["group_idx"].values

    # Normalize X
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0) + 1e-3
    X_norm = (X - X_mean) / X_std
    
    # PyMC model
    with pm.Model() as model:
        alpha_group = pm.Normal("alpha_group", mu=1.0, sigma=1.0, shape=len(position_map))
        beta = pm.Normal("beta", mu=0.0, sigma=1.0, shape=X.shape[1])
        sigma = pm.Exponential("sigma", 1.0)

        mu = alpha_group[group_idx] + pt.dot(X_norm, beta)
        pm.Normal("obs", mu=mu, sigma=sigma, observed=y)

        approx = pm.fit(2000, method="advi", progressbar=True)
        trace = approx.sample(500)

    # --- Forecast next match ---
    latest_fixture = fixtures[fixtures["round"] == latest_round + 1].copy()
    upcoming = players.merge(latest_fixture, left_on="team", right_on="team", how="inner")
    upcoming = upcoming.rename(columns={"opponent_team": "opponent", "was_home": "home"})
    upcoming = upcoming.merge(df.groupby("element")["minutes"].mean().rename("mean_minutes"), left_on="id", right_index=True, how="left")

    upcoming["team_strength"] = df.groupby("team")["goals_scored"].mean().reindex(upcoming["team"]).values
    upcoming["opponent_weakness"] = df.groupby("opponent_team")["goals_conceded"].mean().reindex(upcoming["opponent"]).values

    upcoming["log_minutes"] = np.log(upcoming["mean_minutes"] + 1e-3)
    upcoming["home"] = upcoming["home"].astype(float)

    X_pred = upcoming[["log_minutes", "team_strength", "opponent_weakness", "home"]].fillna(0).values
    X_pred_std = (X_pred - X_mean) / X_std

    alpha = trace.posterior["alpha_group"].mean(dim=("chain", "draw")).values
    beta = trace.posterior["beta"].mean(dim=("chain", "draw")).values

    mu_pred = alpha[upcoming["group_idx"].values] + X_pred_std @ beta
    upcoming["expected_points"] = mu_pred

    return upcoming[["id", "expected_points"]].rename(columns={"id": "player_id"})


if __name__ == "__main__":
    print("📥 Loading data...")
    df = pd.read_parquet(INPUT_FILE)
    fixtures = pd.read_parquet(FIXTURES_FILE)

    print("🔍 Running batched Bayesian forecast with upcoming fixture covariates...")
    forecast_df = build_forecasts_batched(df, fixtures)

    print(f"💾 Saving to {OUTPUT_FILE}")
    forecast_df.to_parquet(OUTPUT_FILE, index=False)
    print(forecast_df.sort_values("expected_points", ascending=False).head())
