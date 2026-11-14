"""Every weight, threshold and rule used by the SupeRR Selector pipeline lives here.

Changing a value here and re-running `python run_pipeline.py` reproduces the whole analysis
with the new setting. The dashboard only reads the outputs; it never recomputes them.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"

RAW_FILES = {
    "balls": "ball_by_ball.csv",
    "matches": "matches.csv",
    "playing_xi": "playing_eleven.csv",
    "teams": "teams.csv",
    "mapping": "competition_team_player_mapping.csv",
    "competitions": "competitions.csv",
}

SEED = 42
N_FOLDS = 5                 # cross-fitting folds (grouped by match) for every model
N_REPLICATES = 360          # reliability replicates = match bootstrap x pressure definitions
RELIABILITY_QUANTILE = 0.20  # final rank uses the 20th percentile of a player's replicate ratings

# ---------------------------------------------------------------- pressure index
# Component weights of the Consensus Pressure Index (each component is scaled 0-1).
# Batting and bowling use different components (Bhattacharjee & Lemmer 2016: the same
# situation is a different problem for the two sides).
BAT_WEIGHTS = {
    "leverage": 0.20,      # how much one ball can swing win probability (closeness, P4)
    "chase": 0.18,         # resource-adjusted required rate (P1, P3) / below par (1st innings, from over 3)
    "wickets": 0.12,       # Lemmer-weighted wickets lost + recent collapse + powerplay collapse (P2)
    "squeeze": 0.17,       # dot-ball build-up and a stuck batter: consecutive dots, dots in last 12,
                           # balls since a boundary, striker scoring well below the rate the game needs
    "stage": 0.05,         # death overs / balls remaining (kept small: pressure is context, not template)
    "partner": 0.07,       # tail-end non-striker, new batter at the crease
    "stakes": 0.07,        # Super 4 / rain-revised match (knockouts handled by the floor)
    "personal": 0.14,      # experience, current form, record vs this bowler, own record in this phase
}
BOWL_WEIGHTS = {
    "leverage": 0.22,
    "defend": 0.20,        # defending a target the batting side is on course for / above-par 1st innings
    "momentum": 0.16,      # boundaries in last 6 balls, batting side scoring fast in last 12, set partnership
    "stage": 0.08,
    "spell": 0.08,         # bowler's previous over in this match was expensive
    "stakes": 0.12,
    "personal": 0.14,      # experience, current form, record vs this batter
}
# Context-fair scoring: the final score averages the percentile over all balls with the percentile among
# comparable match states (same innings x phase x wickets-lost band). A tense, dot-heavy powerplay with no
# wicket down is pressure even though collapses and death overs are, on average, tenser - so openers and
# top-order batters get an equal chance to face pressure. Absolute extremes still dominate via the first half.
PHASE_FAIR_SHARE = 0.5
WICKET_BANDS = [-1, 1, 4, 10]   # 0-1 down, 2-4 down, 5+ down
# Situation components (all except leverage/stakes/personal) are multiplied by
# (GATE_FLOOR + (1 - GATE_FLOOR) * closeness) so a hopeless chase is not "maximum pressure".
GATE_FLOOR = 0.35
KNOCKOUT_FLOOR = 70.0       # every knockout ball scores at least 70 ...
KNOCKOUT_SLOPE = 0.30       # ... as 70 + 0.30 * situational score
DLS_MULTIPLIER = 1.10       # rain-revised matches
PRESSURE_THRESHOLD = 75.0   # a "pressure ball" scores >= 75 (top quarter + every knockout ball)
CATEGORY_BINS = [0, 40, 75, 90, 100.0001]
CATEGORY_LABELS = ["Low", "Moderate", "High", "Extreme"]
DEATH_OVER = 16
POWERPLAY_OVERS = 6

# ---------------------------------------------------------------- eligibility
BAT_MIN_PRESSURE_BALLS = 100
BAT_MIN_PRESSURE_INNINGS = 10   # innings with >= BAT_INNINGS_MIN_BALLS pressure balls
BAT_INNINGS_MIN_BALLS = 5
BOWL_MIN_PRESSURE_BALLS = 120
BOWL_MIN_PRESSURE_SPELLS = 10   # matches with >= BOWL_SPELL_MIN_BALLS pressure balls
BOWL_SPELL_MIN_BALLS = 6

# ---------------------------------------------------------------- impact (consistency) rules
# The user's key rule: a batter is valuable under pressure when he scores important runs fast
# in most of his pressure innings; a bowler when he takes crucial wickets or chokes the scoring.
BAT_IMPACT_SR = 156.0
BAT_IMPACT_RUNS = 10
# ... or the innings beat the situation: >= 15 pressure runs and >= +5 runs above an average batter
# (credits innings that rebuild after a collapse or survive a squeeze, which are not always at SR 156)
BAT_IMPACT_ALT_RUNS = 15
BAT_IMPACT_ALT_VALUE = 5.0
BOWL_IMPACT_DOT_SHARE = 0.40
BOWL_IMPACT_MAX_ECON = 9.5

# ---------------------------------------------------------------- rating weights
RATING_WEIGHTS = {
    "impact_rate": 0.30,       # share of pressure innings/spells that were impact performances
    "pressure_value": 0.25,    # runs above expected per 100 pressure balls (P5 ERD idea)
    "uplift": 0.15,            # pressure value minus own non-pressure value (vs personal baseline)
    "value_consistency": 0.10, # share of pressure innings/spells with positive value
    "wpa": 0.10,               # win-probability added per pressure innings/spell
    "volume": 0.10,            # log of pressure innings/spells (proven over many occasions)
}

# Alternative pressure definitions used for robustness / reliability replicates.
DEFINITIONS = ["consensus", "leverage", "resource_p1", "lemmer_p2", "rule_based", "equal_weights"]

# ---------------------------------------------------------------- selection exclusions (user rules)
# Excluded players are still rated on the same scale (they shape the baselines) but are not ranked.
REQUIRED_SEASON = 2026                       # must have played at least one match in this season
EXCLUDED_TEAMS = ["Pakistan", "Pakistan A"]  # players who have represented these sides (not available for IPL)
