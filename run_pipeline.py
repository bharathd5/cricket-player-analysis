"""SupeRR Selector Season 2 - full analytical pipeline.

    python run_pipeline.py            # full run (about 2-3 minutes)
    python run_pipeline.py --fast     # 60 replicates instead of 360 (quick check)
    python run_pipeline.py --csv      # also export the master ball-by-ball file as CSV

Steps: load & clean -> match state -> player history -> models -> pressure index ->
ratings & reliability -> validation -> insights -> report.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config import settings as S  # noqa: E402
from src import data_prep, insights, match_state, models, pressure, ratings, validation  # noqa: E402

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def enrich(table: pd.DataFrame, b: pd.DataFrame, role: str, players: pd.DataFrame) -> pd.DataFrame:
    pid = "striker_id" if role == "bat" else "bowler_id"
    team_col = "batting_team" if role == "bat" else "bowling_team"
    t = table.copy()
    names = players.set_index("player_id").player_name
    t.insert(0, "player", t.index.map(names))
    recent = b.sort_values("match_date").groupby(pid)
    t["team"] = t.index.map(recent[team_col].last())
    t["teams"] = t.index.map(recent[team_col].agg(lambda s: ", ".join(list(dict.fromkeys(s[::-1]))[:3])))
    t["matches"] = t.index.map(b.groupby(pid).match_id.nunique())
    t["last_match"] = t.index.map(recent.match_date.last())
    end = b.match_date.max()
    t["active"] = (end - t.last_match).dt.days <= 365
    if role == "bat":
        t["pressure_sr"] = t.pr * 100 / t.pb
        t["normal_sr"] = t.nr * 100 / t.nb.clip(lower=1)
        t["pressure_avg"] = t.pr / t.po.clip(lower=1)
        t["normal_avg"] = t.nr / t["no"].clip(lower=1)
        t["pressure_boundary_pct"] = t.p4 * 100 / t.pb
        t["impact_share_raw"] = t.impact / t.inn.clip(lower=1)
    else:
        t["pressure_overs"] = t.pb / 6
        t["pressure_econ"] = t.pc * 6 / t.pb
        t["normal_econ"] = t.nc * 6 / t.nb.clip(lower=1)
        t["pressure_dot_pct"] = t["pd"] * 100 / t.pb
        t["pressure_balls_per_wkt"] = t.pb / t.pk.clip(lower=1)
        t["impact_share_raw"] = t.impact / t.inn.clip(lower=1)
    t["evidence"] = np.select(
        [(t.p_top10 >= 0.5) & (t.defs_top10 >= 4), (t.p_top10 >= 0.25) | (t.defs_top10 >= 3)],
        ["Strong", "Moderate"], "Uncertain")
    t.loc[~t.selectable, "evidence"] = "Excluded"
    t["final_rank"] = t.final_rank.astype("Int64")
    t.index.name = "player_id"
    return t.reset_index()


def exclusions(b: pd.DataFrame, tables: dict, role: str) -> pd.Series:
    """player_id -> reason for every player the user's selection rules remove from the ranking."""
    pid = "striker_id" if role == "bat" else "bowler_id"
    xi = tables["playing_xi"].merge(tables["teams"].drop_duplicates("team_id")[["team_id", "team_name"]],
                                    on="team_id", how="left")
    # last season the player appeared in ANY capacity (batted, bowled or named in a playing XI)
    season = b.drop_duplicates("match_id").set_index("match_id").season_year
    appear = pd.concat([b[["striker_id", "match_id"]].rename(columns={"striker_id": "p"}),
                        b[["non_striker_id", "match_id"]].rename(columns={"non_striker_id": "p"}),
                        b[["bowler_id", "match_id"]].rename(columns={"bowler_id": "p"}),
                        xi[xi.match_id.isin(season.index)][["player_id", "match_id"]].rename(columns={"player_id": "p"})])
    appear["yr"] = appear.match_id.map(season)
    last_any = appear.groupby("p").yr.max()
    last = last_any.reindex(b[pid].unique())
    mp = pd.read_csv(S.RAW / S.RAW_FILES["mapping"])
    pak = set(xi.loc[xi.team_name.isin(S.EXCLUDED_TEAMS), "player_id"]) | \
        set(mp.loc[mp.team_name.isin(S.EXCLUDED_TEAMS), "player_id"])
    reasons = {}
    for p_, yr in last.items():
        r = []
        if p_ in pak:
            r.append("Pakistan player")
        if yr < S.REQUIRED_SEASON:
            r.append(f"No match in {S.REQUIRED_SEASON} (last: {int(yr)})")
        if r:
            reasons[p_] = "; ".join(r)
    return pd.Series(reasons, dtype=str)


def main(fast: bool = False, csv: bool = False) -> None:
    for p in (S.PROCESSED, S.OUTPUTS, S.REPORTS, S.FIGURES):
        p.mkdir(parents=True, exist_ok=True)
    if fast:
        S.N_REPLICATES = 60
    rng = np.random.default_rng(S.SEED)

    log("1/8 loading and cleaning the six input files")
    raw = data_prep.load_raw()
    b, tables, dq = data_prep.clean(raw)
    log(f"     {len(b):,} deliveries, {b.match_id.nunique()} matches")

    log("2/8 reconstructing match state before every ball")
    b, targets = match_state.add_targets(b)
    b = match_state.add_match_state(b)
    log("3/8 player history before each match (experience, form, match-ups)")
    b = match_state.add_player_context(b)

    log("4/8 fitting resource, win-probability and expected-outcome models (cross-fitted)")
    b, res_info = models.resource_model(b)
    b, wp_metrics = models.win_probability(b)
    b, exp_metrics = models.expected_outcomes(b)

    log("5/8 building the batting and bowling pressure indices")
    b, comps = pressure.build(b)

    master = S.PROCESSED / "master_ball_by_ball.parquet"
    b.to_parquet(master, index=False)
    if csv:
        b.to_csv(S.PROCESSED / "master_ball_by_ball.csv", index=False)
    for name, t in tables.items():
        t.to_parquet(S.PROCESSED / f"{name}.parquet", index=False)
    targets.to_csv(S.OUTPUTS / "target_reconciliation.csv", index=False)
    log(f"     master file written: {master.name} ({b.shape[0]:,} rows x {b.shape[1]} columns)")

    log(f"6/8 ratings and reliability ({S.N_REPLICATES} replicates per role)")
    players = tables["players"]
    results, boards = {}, {}
    for role in ("bat", "bowl"):
        excl = exclusions(b, tables, role)
        excl.rename_axis("player_id").rename("reason").reset_index().to_csv(S.OUTPUTS / f"exclusions_{role}.csv",
                                                                           index=False)
        r = ratings.run_role(b, role, rng, players, log=log, excluded=excl)
        results[role] = r
        board = enrich(r["table"], b, role, players)
        boards[role] = board
        board.to_csv(S.OUTPUTS / f"{'batter' if role == 'bat' else 'bowler'}_rankings.csv", index=False)
        board[board.selectable].head(10).to_csv(
            S.OUTPUTS / f"top10_{'batters' if role == 'bat' else 'bowlers'}.csv", index=False)
        reps = r["replicates"].copy()
        reps["definition"] = [S.DEFINITIONS[i % len(S.DEFINITIONS)] for i in range(len(reps))]
        reps.columns = [str(c) for c in reps.columns]
        reps.to_parquet(S.OUTPUTS / f"replicates_{role}.parquet", index=False)
        ratings.scoped_ratings(r, b, role).to_parquet(S.OUTPUTS / f"scoped_ratings_{role}.parquet", index=False)
        ws, keep = ratings.weight_sensitivity(r, rng)
        ws.to_csv(S.OUTPUTS / f"weight_sensitivity_{role}.csv", index=False)
        keep.rename_axis("player_id").reset_index().to_csv(S.OUTPUTS / f"weight_keep_{role}.csv", index=False)
        th = ratings.threshold_sensitivity(b, r, role)
        th["top10_ids"] = th.top10_ids.apply(lambda x: ",".join(map(str, x)))
        th.to_csv(S.OUTPUTS / f"threshold_sensitivity_{role}.csv", index=False)
        sh = ratings.split_half(r)
        json.dump(sh, open(S.OUTPUTS / f"split_half_{role}.json", "w"), indent=2)
        consts = {k: (v if not isinstance(v, dict) else {a: float(c) for a, c in v.items()})
                  for k, v in r["consts"]["consensus"].items()}
        json.dump({k: (float(v) if not isinstance(v, dict) else v) for k, v in consts.items()},
                  open(S.OUTPUTS / f"shrinkage_constants_{role}.json", "w"), indent=2)
        top = board[board.selectable].head(10)
        log(f"     top-10 {role}: " + ", ".join(top.player))

    log("7/8 validation and research-paper replications")
    validation.tier_table(b).to_csv(S.OUTPUTS / "pressure_tiers.csv", index=False)
    validation.definition_table(b).to_csv(S.OUTPUTS / "definition_comparison.csv", index=False)
    validation.p4_outcome_test(b).to_csv(S.OUTPUTS / "p4_outcome_test.csv", index=False)
    validation.p6_effect_sizes(b).to_csv(S.OUTPUTS / "p6_effect_sizes.csv", index=False)
    cv, yk = validation.p7_cramers_v(b)
    cv.to_csv(S.OUTPUTS / "p7_cramers_v.csv", index=False)
    yk.to_csv(S.OUTPUTS / "p7_death_delivery_styles.csv", index=False)
    validation.component_summary(b).to_csv(S.OUTPUTS / "pressure_components.csv", index=False)
    pf, pfp = validation.position_fairness(b)
    pf.to_csv(S.OUTPUTS / "position_fairness.csv", index=False)
    pfp.to_csv(S.OUTPUTS / "position_phase_pressure.csv", index=False)
    swing = validation.extreme_low_swing(b)
    dq.to_csv(S.OUTPUTS / "data_quality.csv", index=False)
    meta = {
        "generated": pd.Timestamp.now().isoformat(timespec="seconds"),
        "seed": S.SEED, "replicates": S.N_REPLICATES,
        "deliveries": int(len(b)), "matches": int(b.match_id.nunique()),
        "players": int(pd.concat([b.striker_id, b.bowler_id]).nunique()),
        "date_min": str(b.match_date.min().date()), "date_max": str(b.match_date.max().date()),
        "competitions": int(b.comp_id.nunique()),
        "bat_pressure_balls": int(b[b.ball_faced].bat_pressure_ball.sum()),
        "bowl_pressure_balls": int(b.bowl_pressure_ball.sum()),
        "eligible_batters": int(len(results["bat"]["pool"])), "eligible_bowlers": int(len(results["bowl"]["pool"])),
        "selectable_batters": int(len(results["bat"]["sel"])), "selectable_bowlers": int(len(results["bowl"]["sel"])),
        "selection_rules": {"required_season": S.REQUIRED_SEASON, "excluded_teams": S.EXCLUDED_TEAMS},
        "resource_model": res_info, "win_probability": wp_metrics, "expected_models": exp_metrics,
        "extreme_low_wpa_swing": swing,
        "split_half": {r: json.load(open(S.OUTPUTS / f"split_half_{r}.json")) for r in ("bat", "bowl")},
    }
    json.dump(meta, open(S.OUTPUTS / "model_metrics.json", "w"), indent=2, default=str)

    log("8/8 player insights, match logs and report")
    bat_ids = set(results["bat"]["players"])
    bowl_ids = set(results["bowl"]["players"])
    insights.player_splits(b, bat_ids, bowl_ids).to_parquet(S.OUTPUTS / "player_splits.parquet", index=False)
    insights.dismissal_profile(b).to_parquet(S.OUTPUTS / "dismissal_profile.parquet", index=False)
    insights.matchups(b).to_parquet(S.OUTPUTS / "matchups.parquet", index=False)
    for name, t in insights.career_tables(b, tables).items():
        t.to_parquet(S.OUTPUTS / f"{name}.parquet", index=False)
    # slim copies for the dashboard, so it needs nothing outside outputs/ (every file < 25 MB, deployable)
    sys.path.insert(0, str(ROOT / "app"))
    from ui.columns import BALL_COLS, EXAMPLE_COLS
    b[BALL_COLS].to_parquet(S.OUTPUTS / "app_balls.parquet", index=False, compression="zstd")
    insights.method_examples(b, EXAMPLE_COLS).to_parquet(S.OUTPUTS / "method_examples.parquet", index=False)
    tables["players"].to_parquet(S.OUTPUTS / "players.parquet", index=False)
    for role in ("bat", "bowl"):
        insights.match_logs(results[role]["player_match"], b, role).to_parquet(
            S.OUTPUTS / f"match_logs_{role}.parquet", index=False)
    try:
        from src import report
        report.build()
        log("     reports/methodology_report.md and .docx written")
    except Exception:  # the report is optional; never hide the error
        log("     report generation failed:\n" + traceback.format_exc())
    log("done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fast", action="store_true", help="60 replicates instead of 360")
    ap.add_argument("--csv", action="store_true", help="also write the master file as CSV")
    a = ap.parse_args()
    try:
        main(fast=a.fast, csv=a.csv)
    except data_prep.DataError as e:
        print(f"\nDATA ERROR: {e}")
        sys.exit(1)
