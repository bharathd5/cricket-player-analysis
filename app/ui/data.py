"""Cached access to the pipeline outputs. The dashboard never re-runs the analysis."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
PROC = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"



class MissingOutput(Exception):
    pass


def _need(path: Path) -> Path:
    if not path.exists():
        raise MissingOutput(path)
    return path


REQUIRED = ["model_metrics.json", "batter_rankings.csv", "bowler_rankings.csv", "app_balls.parquet",
            "players.parquet", "player_splits.parquet", "match_logs_bat.parquet", "match_logs_bowl.parquet",
            "scoped_ratings_bat.parquet", "scoped_ratings_bowl.parquet", "replicates_bat.parquet",
            "replicates_bowl.parquet", "career_bat.parquet", "career_bowl.parquet", "career_phase.parquet",
            "player_info.parquet", "exclusions_bat.csv", "exclusions_bowl.csv", "method_examples.parquet",
            "shrinkage_constants_bat.json", "shrinkage_constants_bowl.json"]


def guard(fn, *a, **k):
    """Run a loader; on a missing output show exactly what is missing and where the app is looking."""
    try:
        return fn(*a, **k)
    except MissingOutput as e:
        missing = [f for f in REQUIRED if not (OUT / f).exists()]
        found = sorted(p.name for p in OUT.glob("*")) if OUT.exists() else []
        st.markdown(
            f"<div class='si-empty'><b>Analytical output not found</b><br>{Path(str(e)).name} is missing.</div>",
            unsafe_allow_html=True)
        st.markdown(f"""
**The dashboard is looking in:** `{OUT}`
({'the folder exists' if OUT.exists() else 'this folder does not exist'}, {len(found)} files found;
{len(missing)} of {len(REQUIRED)} required files missing)

**Running locally (PyCharm):** run `python run_pipeline.py` in the project folder, then refresh.

**Deployed (Streamlit Community Cloud):** the cloud app only sees what is in your GitHub repository. Running the pipeline
in PyCharm does not upload anything. Commit and push the whole `outputs/` folder (every file is under 25 MB), then reboot
the app from its menu (⋮ → Reboot app).
""")
        if missing:
            with st.expander(f"Missing files ({len(missing)})"):
                st.code("\n".join(f"outputs/{f}" for f in missing), language=None)
        st.stop()


@st.cache_data(show_spinner="Loading deliveries…")
def balls() -> pd.DataFrame:
    df = pd.read_parquet(_need(OUT / "app_balls.parquet"))
    for c in ["comp_type", "phase", "bat_category", "bowl_category", "delivery_style", "venue_country", "stage"]:
        df[c] = df[c].astype("category")
    return df


@st.cache_data
def rankings(role: str, include_excluded: bool = False) -> pd.DataFrame:
    """Eligible players. By default only those selectable under the selection rules (played in 2026,
    not a Pakistan player); `include_excluded=True` adds the excluded ones (unranked) with their reason."""
    f = "batter_rankings.csv" if role == "bat" else "bowler_rankings.csv"
    df = pd.read_csv(_need(OUT / f), parse_dates=["last_match"])
    df["excluded_reason"] = df.excluded_reason.fillna("")
    if not include_excluded:
        df = df[df.selectable].copy()
        df["final_rank"] = df.final_rank.astype(int)
    return df.reset_index(drop=True)


@st.cache_data
def career(kind: str) -> pd.DataFrame:
    """kind: career_bat, career_bowl, career_phase or player_info."""
    return pd.read_parquet(_need(OUT / f"{kind}.parquet"))


@st.cache_data
def scoped(role: str) -> pd.DataFrame:
    return pd.read_parquet(_need(OUT / f"scoped_ratings_{role}.parquet"))


@st.cache_data
def replicates(role: str) -> pd.DataFrame:
    return pd.read_parquet(_need(OUT / f"replicates_{role}.parquet"))


@st.cache_data
def match_logs(role: str) -> pd.DataFrame:
    return pd.read_parquet(_need(OUT / f"match_logs_{role}.parquet"))


@st.cache_data
def splits() -> pd.DataFrame:
    return pd.read_parquet(_need(OUT / "player_splits.parquet"))


@st.cache_data
def dismissals() -> pd.DataFrame:
    return pd.read_parquet(_need(OUT / "dismissal_profile.parquet"))


@st.cache_data
def matchups() -> pd.DataFrame:
    return pd.read_parquet(_need(OUT / "matchups.parquet"))


@st.cache_data
def players() -> pd.DataFrame:
    return pd.read_parquet(_need(OUT / "players.parquet"))


@st.cache_data
def csv(name: str) -> pd.DataFrame:
    return pd.read_csv(_need(OUT / f"{name}.csv"))


@st.cache_data
def metrics() -> dict:
    return json.loads(_need(OUT / "model_metrics.json").read_text())


@st.cache_data
def constants(role: str) -> dict:
    return json.loads(_need(OUT / f"shrinkage_constants_{role}.json").read_text())


def names() -> pd.Series:
    return players().set_index("player_id").player_name


@st.cache_data(show_spinner=False)
def player_pressure_totals(role: str) -> pd.DataFrame:
    """Actual vs expected totals on pressure balls per player (from the master file's model columns)."""
    b = balls()
    if role == "bat":
        d = b[b.ball_faced & b.bat_pressure_ball]
        g = d.groupby("striker_id").agg(balls=("ball_faced", "sum"), runs=("bat_runs", "sum"),
                                        x_runs=("x_bat_runs", "sum"), outs=("striker_out", "sum"),
                                        x_outs=("x_bat_out", "sum"), value=("bat_value", "sum"))
    else:
        d = b[b.bowl_pressure_ball]
        g = d.groupby("bowler_id").agg(balls=("is_legal", "sum"), runs=("bowler_conceded", "sum"),
                                       x_runs=("x_conceded", "sum"), outs=("bowler_wicket", "sum"),
                                       x_outs=("x_bowl_wkt", "sum"), value=("bowl_value", "sum"))
    g.index.name = "player_id"
    return g.reset_index()


@st.cache_data
def exclusions(role: str) -> pd.Series:
    """player_id -> reason for players removed from the rankings by the selection rules."""
    df = pd.read_csv(_need(OUT / f"exclusions_{role}.csv"))
    return df.set_index("player_id").reason
