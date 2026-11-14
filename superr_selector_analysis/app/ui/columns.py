"""Column lists shared by the pipeline (to write the dashboard files) and the dashboard."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import settings as S  # noqa: E402

BALL_COLS = [
    "match_id", "match_date", "season_year", "comp_type", "comp_name", "stage", "is_knockout", "innings", "overid",
    "phase", "striker_id", "bowler_id", "striker_name", "bowler_name", "batting_team", "bowling_team",
    "bat_runs", "bowler_conceded", "is_legal", "ball_faced", "striker_out", "bowler_wicket", "is_dot", "is_boundary",
    "wkts_before", "wickets_in_hand", "balls_rem", "rrr", "wp", "wpa", "leverage", "pressure_bat", "pressure_bowl",
    "bat_category", "bowl_category", "bat_pressure_ball", "bowl_pressure_ball", "x_bat_runs", "x_bat_out",
    "x_conceded", "x_bowl_wkt", "bat_value", "bowl_value", "delivery_style", "venue_country",
]

EXAMPLE_COLS = ["match_id", "match_date", "comp_name", "stage", "is_knockout", "is_dls", "innings", "overid", "over_ball_num",
           "striker_name", "bowler_name", "batting_team", "bowling_team", "batting_order", "phase", "score_before",
           "wkts_before", "balls_rem", "target", "runs_req", "rrr", "crr", "par_total", "projected_total", "chase_ratio",
           "exp_rem", "wicket_value", "wp", "wp_if_four", "wp_if_wicket", "leverage", "closeness", "wkts_last18",
           "pp_wkts_before", "team_dot_streak", "striker_dot_streak", "balls_since_boundary", "dots_last12",
           "striker_balls_before", "striker_runs_before", "non_striker_order", "runs_last12", "boundaries_last6",
           "part_runs_before", "prev_over_conc", "bat_exp", "bat_form_runs", "h2h_balls", "h2h_outs", "phase_prior_sr",
           "bowl_exp", "bowl_form_econ", "bat_runs", "striker_out", "x_bat_runs", "x_bat_out", "bat_value",
           "bowler_conceded", "x_conceded", "x_bowl_wkt", "bowl_value", "pressure_bat", "pressure_bowl",
           "bat_category", "ball_faced"] + [f"pc_bat_{k}" for k in S.BAT_WEIGHTS] + [f"pc_bowl_{k}" for k in S.BOWL_WEIGHTS]
