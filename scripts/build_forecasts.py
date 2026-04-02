import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from tqdm import tqdm

TOTAL_ROUNDS = 30


def _empirical_decay_pmf(points: np.ndarray, decay: float = 0.9):
    if len(points) == 0:
        return np.array([0]), np.array([1.0])

    w = decay ** np.arange(len(points))[::-1]
    w = w / w.sum()

    counts: dict = {}
    for x, wi in zip(points, w):
        counts[x] = counts.get(x, 0.0) + wi

    support = np.array(sorted(counts.keys()))
    probs = np.array([counts[x] for x in support], dtype=float)
    probs = probs / probs.sum()
    return support, probs


def _pmf_from_pool(pool_points: np.ndarray | None):
    if pool_points is None or len(pool_points) == 0:
        support = np.arange(0, 21)
        lam = 0.20
        probs = (1 - lam) * (lam**support)
        probs = probs / probs.sum()
        return support, probs

    return _empirical_decay_pmf(np.asarray(pool_points), decay=0.995)


def _align_and_mix_pmfs(s1, p1, s2, p2, mix=0.2):
    smin = min(s1.min(), s2.min())
    smax = max(s1.max(), s2.max())
    grid = np.arange(smin, smax + 1)

    def on_grid(s, p):
        out = np.zeros_like(grid, dtype=float)
        out[s - smin] = p
        return out

    mixed = (1 - mix) * on_grid(s1, p1) + mix * on_grid(s2, p2)
    mixed = mixed / mixed.sum()
    return grid, mixed


def _apply_zero_inflation(grid, probs, zero_boost: float = 0.0):
    if zero_boost <= 0.0:
        return grid, probs
    out = probs.copy()
    if 0 in grid:
        zero_idx = np.where(grid == 0)[0][0]
    else:
        grid = np.arange(min(0, grid.min()), grid.max() + 1)
        out_ext = np.zeros_like(grid, dtype=float)
        shift = (
            np.where(grid == 0)[0][0]
            - np.where(np.arange(out.size) + grid.min() == grid.min())[0][0]
        )
        out_ext[shift : shift + out.size] = out
        out = out_ext
        zero_idx = np.where(grid == 0)[0][0]

    non_zero = np.ones_like(out, dtype=bool)
    non_zero[zero_idx] = False
    taken = zero_boost * out[non_zero] / out[non_zero].sum()
    out[non_zero] -= taken
    out[zero_idx] += zero_boost
    out = out / out.sum()
    return grid, out


def _smooth_discrete_pmf(grid, probs, sigma: float = 0.4):
    if sigma <= 0:
        return grid, probs
    sm = gaussian_filter1d(probs, sigma=sigma, mode="nearest")
    sm = np.clip(sm, 0, None)
    sm = sm / sm.sum()
    return grid, sm


def build_points_pmf(
    player_points: np.ndarray,
    decay: float = 0.9,
    pool_points: np.ndarray | None = None,
    mix_with_pool: float = 0.20,
    zero_boost: float = 0.0,
    smooth_sigma: float = 0.4,
):
    s_emp, p_emp = _empirical_decay_pmf(np.asarray(player_points), decay=decay)
    s_pool, p_pool = _pmf_from_pool(pool_points)

    grid, pmf = _align_and_mix_pmfs(s_emp, p_emp, s_pool, p_pool, mix=mix_with_pool)
    grid, pmf = _apply_zero_inflation(grid, pmf, zero_boost=zero_boost)
    grid, pmf = _smooth_discrete_pmf(grid, pmf, sigma=smooth_sigma)
    return grid, pmf


def build_simulation_forecasts(df: pd.DataFrame) -> pd.DataFrame:
    latest_round = int(df["round"].max())  # type: ignore[arg-type]

    position_col = next(
        (c for c in ["position", "element_type"] if c in df.columns), None
    )

    pool_points_by_pos: dict = {}
    if position_col is not None:
        for pos_val, sub in df.groupby(position_col):
            pool_points_by_pos[pos_val] = sub["total_points"].astype(int).to_numpy()

    def get_player_pool_points(player_id: int) -> np.ndarray | None:
        if position_col is None:
            return None
        sub = df.loc[df["element"] == player_id, position_col]
        if sub.empty:
            return None
        pos_val = sub.mode(dropna=True).iloc[0]
        return pool_points_by_pos.get(pos_val)

    grouped = df.groupby("element")["total_points"].apply(list)

    results = []
    for player_id, history in tqdm(
        grouped.items(),
        desc=f"Building pmf (GW {latest_round})",
        total=len(grouped),
        unit="player",
    ):
        pts = np.asarray(history, dtype=int)

        if pts.size:
            w = 0.8 ** np.arange(min(6, pts.size))[::-1]
            recent = pts[-len(w) :]
            zero_rate = (w * (recent == 0)).sum() / w.sum()
            zero_boost = float(np.clip(0.5 * zero_rate, 0.0, 0.06))
        else:
            zero_boost = 0.0

        grid, pmf = build_points_pmf(
            player_points=pts,
            decay=0.9,
            pool_points=get_player_pool_points(int(player_id)),  # type: ignore[arg-type]
            mix_with_pool=0.20,
            zero_boost=zero_boost,
            smooth_sigma=0.4,
        )

        results.append(
            {"player_id": player_id, "expected_points": float((grid * pmf).sum())}
        )

    return pd.DataFrame(results)


if __name__ == "__main__":
    from sqlalchemy import text

    from fantasy_optimizer.db.database import engine
    from fantasy_optimizer.db.upsert import upsert_forecasts

    print("Loading player gameweek stats from DB...")
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT * FROM player_gameweek_stats"), conn)

    print("Building forecasts...")
    forecast_df = build_simulation_forecasts(df)

    upsert_forecasts(forecast_df.to_dict(orient="records"))
    print(f"Saved {len(forecast_df)} forecasts to DB")
    print(forecast_df.sort_values("expected_points", ascending=False).head())
