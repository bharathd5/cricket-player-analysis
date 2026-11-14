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

BALL_COLS = [
    "match_id", "match_date", "season_year", "comp_type", "comp_name", "stage", "is_knockout", "innings", "overid",
    "phase", "striker_id", "bowler_id", "striker_name", "bowler_name", "batting_team", "bowling_team",
    "bat_runs", "bowler_conceded", "is_legal", "ball_faced", "striker_out", "bowler_wicket", "is_dot", "is_boundary",
    "wkts_before", "wickets_in_hand", "balls_rem", "rrr", "wp", "wpa", "leverage", "pressure_bat", "pressure_bowl",
    "bat_category", "bowl_category", "bat_pressure_ball", "bowl_pressure_ball", "x_bat_runs", "x_bat_out",
    "x_conceded", "x_bowl_wkt", "bat_value", "bowl_value", "delivery_style", "venue_country",
]


class MissingOutput(Exception):
    pass


def _need(path: Path) -> Path:
    if not path.exists():
        raise MissingOutput(path)
    return path


def guard(fn, *a, **k):
    """Run a loader; on a missing output show a clear message and stop the page."""
    try:
        return fn(*a, **k)
    except MissingOutput as e:
        st.markdown(
            f"<div class='si-empty'><b>Analytical output not found</b><br>{Path(str(e)).name} is missing.<br>"
            "Run <code>python run_pipeline.py</code> from the project folder, then refresh this page.</div>",
            unsafe_allow_html=True)
        st.stop()


@st.cache_data(show_spinner="Loading deliveries…")
def balls() -> pd.DataFrame:
    df = pd.read_parquet(_need(PROC / "master_ball_by_ball.parquet"), columns=BALL_COLS)
    for c in ["comp_type", "phase", "bat_category", "bowl_category", "delivery_style", "venue_country", "stage"]:
        df[c] = df[c].astype("category")
    return df


@st.cache_data
def rankings(role: str) -> pd.DataFrame:
    f = "batter_rankings.csv" if role == "bat" else "bowler_rankings.csv"
    df = pd.read_csv(_need(OUT / f), parse_dates=["last_match"])
    return df


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
    return pd.read_parquet(_need(PROC / "players.parquet"))


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
