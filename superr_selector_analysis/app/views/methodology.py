import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui import components as U
from ui import data as D
from ui.theme import C, style

sys.path.insert(0, str(D.ROOT))
from config import settings as S  # noqa: E402  (the same settings the pipeline used)

meta = D.guard(D.metrics)
kb, kw = D.constants("bat"), D.constants("bowl")

@st.cache_data(show_spinner="Loading worked examples…")
def example_balls() -> pd.DataFrame:
    """One real ball per scenario, from the candidates the pipeline saved."""
    p = D.OUT / "method_examples.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    return df.groupby("example", sort=False).sample(1, random_state=7).reset_index(drop=True)


U.page_header("Methodology", "How the system works — every attribute, every calculation",
              "This page is generated from the same configuration file and outputs the pipeline used, so what you read "
              "here is what was computed. Expand any section for the detail.")

c1, c2 = st.columns([3, 1])
with c2:
    for f, label in (("methodology_report.docx", "Download report (.docx)"), ("methodology_report.md", "Download report (.md)")):
        p = D.REPORTS / f
        if p.exists():
            st.download_button(label, p.read_bytes(), file_name=f, width="stretch")
with c1:
    st.markdown("""
**The pipeline in eight steps**

1. **Clean & merge** the six CSVs into one ball-by-ball master file.
2. **Rebuild the match state** before every ball (score, wickets, balls left, target, required rate, momentum, dots…).
3. **Add each player's history** from earlier matches only (experience, form, head-to-head, phase record).
4. **Fit models** for par scores, win probability and what an *average* player would do on every ball.
5. **Score pressure** on every ball, separately for the batter and the bowler (0–100).
6. **Measure performance** on pressure balls against expectation and against the player's own baseline.
7. **Rate** each player on six components and **rank** them by how reliably they stay good across 360 replicates.
8. **Apply the selection rules** (played in 2026, not a Pakistan player) and validate everything.
""")

tabs = st.tabs(["1 · Data attributes", "2 · Match-state attributes", "3 · Models", "4 · Pressure index",
                "5 · Worked example", "6 · Performance & rating", "7 · Ranking & selection", "8 · Equal opportunity",
                "9 · Limitations & research"])

# ------------------------------------------------------------------ 1
with tabs[0]:
    U.section("Raw fields used", "from the six supplied files")
    st.markdown("""
| File | Field | Used for |
|---|---|---|
| ball_by_ball | `match_id`, `innings`, `overid`, `over_ball_num`, `innings_ball_num` | ordering every ball and rebuilding the match state |
| ball_by_ball | `striker_id`, `non_striker_id`, `bowler_id` (+ names) | who faced / bowled; the non-striker for the partner signal |
| ball_by_ball | `runs`, `is_four`, `is_six` | runs off the bat, boundaries, dot balls |
| ball_by_ball | `extras_type`, `extras_2_runs` | wides & no-balls (not legal balls, +1 run), byes/leg-byes |
| ball_by_ball | `is_wicket`, `dismissal_type`, `dismissed_player_id` | wickets; run-outs / retirements are not credited to the bowler |
| ball_by_ball | `batting_order` | batting position (expected-runs model, tail-end partner, opener check) |
| ball_by_ball | `batting_type`, `bowling_type`, `pace_or_spin` | batter hand and bowler type in the expected-outcome models |
| ball_by_ball | `delivery_style`, `stroke`, `on_or_off`, `over_or_around` | strong zones and dismissal patterns (no line/length in the data) |
| matches | `stage`, `knock_out` | knockout floor, Super 4 stakes |
| matches | `revised_target`, `first/second_inn_revised_overs` | rain-revised targets and innings length (stored in balls) |
| matches | `win_team_id`, `result` | win probability target; result margins to reconcile chase targets |
| matches | `match_date`, `venue_country` | time order for player history; venue splits |
| competitions | `comp_name`, `match_format`, `season` | IPL / T20I / A-team label, season, par totals |
| playing_eleven | `batting_order`, `is_captain`, `team_id` | non-striker position, profile info, nationality for the Pakistan rule |
| teams, mapping | `team_name`, `player_name` | names and the Pakistan rule |
""")
    U.section("Cleaning", "rows before → after, from outputs/data_quality.csv")
    st.dataframe(D.csv("data_quality"), hide_index=True, width="stretch")
    st.markdown("""
**Run accounting.** `team runs = bat runs + 1 per wide/no-ball + 1 per bye/leg-bye (count missing in the data, imputed)
+ extras_2_runs`. **Bowler conceded** = bat runs + wides + no-balls (never byes). **Bowler wicket** = wicket that is not a
run-out, retirement or obstruction. **Chase target** is reconciled with the published result (defending side won by X runs →
2nd-innings total + X + 1; chasing side won → min(1st-innings total + 1, final chase total); rain → `revised_target`).
""")

# ------------------------------------------------------------------ 2
with tabs[1]:
    U.section("Match state before every ball", "computed from earlier balls of the same innings only")
    st.markdown(f"""
| Attribute | How it is calculated | Why it matters |
|---|---|---|
| `score_before`, `wkts_before` | cumulative team runs / wickets before this ball | the scoreboard |
| `balls_rem` | innings length (120 or revised) − legal balls bowled | resources left |
| `phase` | Powerplay overs 1–{S.POWERPLAY_OVERS}, Middle, Death overs {S.DEATH_OVER}–20 | context for par and fair comparison |
| `runs_req`, `rrr` | target − score; `rrr = runs_req × 6 / balls_rem` (2nd innings) | chasing pressure |
| `crr` | score × 6 / legal balls | first-innings tempo |
| `runs_last12` | team runs in the previous 12 deliveries | batting momentum (bowler pressure) |
| `boundaries_last6` | boundaries in the previous 6 deliveries | bowler just got hit |
| `wkts_last18` | wickets in the previous 18 deliveries | collapse |
| `pp_wkts_before` | wickets lost in the powerplay so far | powerplay recovery |
| `team_dot_streak` | consecutive dot balls (legal, 0 team runs) just before this ball | dot-ball squeeze |
| `striker_dot_streak` | consecutive dots the striker himself has just faced | batter stuck |
| `dots_last12` | dot balls among the previous 12 deliveries | sustained squeeze |
| `balls_since_boundary` | legal balls since the team's last four or six | scoring drought |
| `striker_runs_before / balls_before` | striker's innings so far | new batter vs set batter; "stuck" check |
| `part_runs_before` | runs in the current partnership | set partnership (bowler pressure) |
| `non_striker_order` | non-striker's batting position (playing XI) | tail-end partner |
| `prev_over_conc` | runs conceded in the bowler's previous over in this innings | bowler's spell going wrong |
""")
    U.section("Player history before each match", "only matches played earlier — no look-ahead")
    st.markdown("""
| Attribute | How it is calculated | Used in |
|---|---|---|
| `bat_exp`, `bowl_exp` | number of earlier matches batted / bowled in the data | personal pressure (inexperience) |
| `bat_form_runs` | mean runs in the previous 5 innings | personal pressure (poor form) |
| `bowl_form_econ` | economy over the previous 5 matches | personal pressure (poor form) |
| `h2h_balls`, `h2h_runs`, `h2h_outs` | earlier balls this batter faced from this bowler, runs and dismissals | match-up pressure (both roles) |
| `phase_prior_sr` | batter's earlier strike rate in this phase | own record in this situation |
| `bat_prior_sr`, `bowl_prior_econ` | career-to-date strike rate / economy | **opponent strength** in the expected-outcome models |
""")

# ------------------------------------------------------------------ 3
with tabs[2]:
    rm, wp, em = meta["resource_model"], meta["win_probability"], meta["expected_models"]
    U.section("Resource table (Paper 3 / DLS idea)")
    st.markdown(f"""
Monotone gradient boosting learns **expected runs still to come**, `exp_rem(balls_rem, wkts_before)`, from full first
innings. A full innings is worth **{rm['full_innings_expected_runs']:.0f}** runs on average.

* `wicket_value = exp_rem(b, w) − exp_rem(b, w+1)` — runs a wicket costs at that moment (mean {rm['mean_wicket_value']:.1f}).
* `par_total` — median first-innings total for that competition type and season.
* `projected_total = score_before + exp_rem × par_total / {rm['full_innings_expected_runs']:.0f}`.
* `chase_ratio = runs_req ÷ (exp_rem × par_total / {rm['full_innings_expected_runs']:.0f})` — 1.0 means an average side with these
  balls and wickets would get there exactly; above 1 the chase is behind.
""")
    U.section("Win probability (Paper 4)")
    st.markdown(f"""
One model per innings (monotone gradient boosting, 5 folds grouped by match, so a ball is never scored by a model that saw
its match). Features: 1st innings — score, wickets, balls left, par, IPL flag; 2nd innings — runs needed, balls left,
wickets in hand, required rate, IPL flag. Out-of-fold AUC **{wp['innings_2']['auc']:.3f}** (2nd innings, Brier
{wp['innings_2']['brier']:.3f}) and **{wp['innings_1']['auc']:.3f}** (1st innings).

* `wp` — batting side's chance of winning before the ball.
* `leverage = WP(if this ball goes for four) − WP(if it is a wicket)` — how much one ball can swing the match.
* `closeness = 4·wp·(1−wp)` — 1 when the game is 50/50, 0 when it is decided.
* `wpa = wp_after − wp` — win probability added by the ball (credited to the batter, minus to the bowler).
""")
    U.section("Expected outcomes (Paper 5, ERD idea)")
    st.markdown(f"""
Four cross-fitted models estimate what an **average** player would produce on this exact ball:
`x_bat_runs`, `x_bat_out` (batter view, opponent strength = bowler's prior economy) and `x_conceded`, `x_bowl_wkt`
(bowler view, opponent strength = batter's prior strike rate). Context features: innings, over, balls left, wickets,
required & current rate, competition, pace/spin, bowler type, batter hand, batting position, balls the striker has faced,
knockout. Dismissal-model AUC {em['bat_out_auc']:.3f}; wicket-model AUC {em['bowl_wkt_auc']:.3f}.
""")

# ------------------------------------------------------------------ 4
with tabs[3]:
    U.section("Principles")
    st.markdown("""
1. **Pressure belongs to the ball, not the match** — recomputed before every delivery, so it rises and falls within an
   innings (six tense balls, then ten easy ones).
2. **Context, not template** — death overs and second innings are not pressure by default. A tight powerplay with four dots
   in a row is pressure; a cruise at the death is not.
3. **Batting ≠ bowling pressure** (Paper 2) — two separate indices.
4. **A live contest** — situational parts are scaled by closeness, so a lost cause is not maximum pressure.
5. **Knockouts are always pressure**; rain-revised matches carry a premium; personal context adds to the situation.
""")
    U.section("Batting components (each 0–1)")
    bw = S.BAT_WEIGHTS
    st.markdown(f"""
| Component | Weight | Formula |
|---|---|---|
| Leverage | {bw['leverage']} | percentile rank of `leverage` over all balls |
| Chase / par | {bw['chase']} | 2nd inns: max( σ(4·(chase_ratio−1)), clip((rrr−8)/7) × (1+0.6·wkts/10) ). 1st inns from over 3: max( clip((par−projected)/(0.15·par)), 0.8 if CRR<7 at over 12+ ) |
| Wickets | {bw['wickets']} | max( 0.6·Lemmer-weighted wickets lost (top order heavier) + 0.4·clip((wkts_last18−1)/2), clip((pp_wkts−1)/2) up to over 10 ) |
| Squeeze | {bw['squeeze']} | max( clip((team_dot_streak−1)/5), clip((striker_dot_streak−1)/4), 0.8·clip((balls_since_boundary−9)/15), clip((dots_last12−5)/5), stuck ) where stuck = clip((needed SR − striker SR)/50) after 8+ balls |
| Stage | {bw['stage']} | death overs 0.6 → 1.0; otherwise 0.5 × share of innings used |
| Partner | {bw['partner']} | max( 1 if non-striker bats 8+, 0.5 if 7; 0.6 if striker has faced < 6 balls ) |
| Stakes | {bw['stakes']} | Super 4 0.6, rain-revised 0.5 (knockouts use the floor) |
| Personal | {bw['personal']} | mean of experience (1 − matches/30), form (25 − last-5 avg)/25, match-up (dismissed by this bowler / SR < 110), phase record |
""")
    U.section("Bowling components (each 0–1)")
    ww = S.BOWL_WEIGHTS
    st.markdown(f"""
| Component | Weight | Formula |
|---|---|---|
| Leverage | {ww['leverage']} | same as batting |
| Defend / par | {ww['defend']} | 2nd inns: σ(4·(1−chase_ratio)) — target being run down; 1st inns from over 3: clip((projected−par)/(0.15·par)) |
| Momentum | {ww['momentum']} | max( 0.5·clip((runs_last12−15)/12) + 0.3·clip((partnership−30)/40) + 0.2·clip(boundaries_last6/2), clip((boundaries_last6−1)/2) ) |
| Stage | {ww['stage']} | as batting |
| Spell | {ww['spell']} | clip((previous over runs − 8)/10) |
| Stakes | {ww['stakes']} | as batting |
| Personal | {ww['personal']} | mean of experience, form (economy last 5 − 7.5)/4, match-up (batter has scored at SR 160+ off him) |
""")
    U.section("From components to a 0–100 score")
    st.latex(r"g_i = %.2f + %.2f \cdot 4\,\mathrm{WP}_i(1-\mathrm{WP}_i) \quad\text{(applied to situational components)}"
             % (S.GATE_FLOOR, 1 - S.GATE_FLOOR))
    st.latex(r"\mathrm{raw}_i = \sum_k w_k\, c_{k,i}")
    st.latex(r"P_i = 100\Big[(1-\lambda)\,\mathrm{pct}_{\text{all balls}}(\mathrm{raw}_i) + "
             r"\lambda\,\mathrm{pct}_{\text{same innings, phase, wickets band}}(\mathrm{raw}_i)\Big],\ \lambda = %.1f"
             % S.PHASE_FAIR_SHARE)
    st.latex(r"\text{rain-revised: } P\times %.2f;\qquad \text{knockout: } \max(P,\ %.0f + %.2f\,P)"
             % (S.DLS_MULTIPLIER, S.KNOCKOUT_FLOOR, S.KNOCKOUT_SLOPE))
    st.markdown(f"""
* **Context-fair half.** Half of the score compares the ball with *comparable* match states (same innings, same phase,
  0–1 / 2–4 / 5+ wickets down). This is what gives openers and top-order batters an equal chance to face pressure:
  a dot-heavy powerplay with no wicket down is judged against other powerplays, not against death-over collapses.
* **Pressure ball:** P ≥ **{S.PRESSURE_THRESHOLD:.0f}**. Categories: Low < 40 · Moderate 40–75 · High 75–90 · Extreme ≥ 90.
* **Alternative definitions** used for robustness: leverage only, Paper-1 resource index, Paper-2 Lemmer index,
  rule-based (knockout or 2+ of: death, RRR > 10, collapse, PP collapse, slow first innings, 6+ down, very close game,
  4+ dots in a row), equal weights.
""")

# ------------------------------------------------------------------ 5
with tabs[4]:
    ex = example_balls()
    if ex.empty:
        U.empty("Examples unavailable.")
    else:
        lab = st.selectbox("Pick a real ball from the data", ex.example.tolist())
        r = ex[ex.example == lab].iloc[0]
        st.markdown(
            f"**{r.striker_name}** (No. {int(r.batting_order) if pd.notna(r.batting_order) else '–'}) facing "
            f"**{r.bowler_name}** · {r.batting_team} v {r.bowling_team} · {r.comp_name}, {r.stage} · "
            f"{pd.to_datetime(r.match_date):%d %b %Y} · innings {int(r.innings)}, over {int(r.overid)}.{int(r.over_ball_num)}")
        state = {
            "Score": f"{int(r.score_before)}/{int(r.wkts_before)}", "Balls left": int(r.balls_rem),
            "Target / needed": f"{int(r.target)} / {int(r.runs_req)}" if pd.notna(r.target) else "1st innings",
            "Required rate": f"{r.rrr:.2f}" if pd.notna(r.rrr) else "–",
            "Par / projected": f"{r.par_total:.0f} / {r.projected_total:.0f}",
            "Win probability": f"{r.wp:.0%}", "WP if four / wicket": f"{r.wp_if_four:.0%} / {r.wp_if_wicket:.0%}",
            "Closeness": f"{r.closeness:.2f}", "Dots in a row (team / striker)": f"{int(r.team_dot_streak)} / {int(r.striker_dot_streak)}",
            "Balls since boundary": int(r.balls_since_boundary), "Wkts in last 18 balls": int(r.wkts_last18),
            "Striker so far": f"{int(r.striker_runs_before)} ({int(r.striker_balls_before)})",
        }
        st.dataframe(pd.DataFrame([(k, str(v)) for k, v in state.items()], columns=["Match state", "Value"]), hide_index=True, width="stretch")
        c1, c2 = st.columns(2)
        for col, role, w, score in ((c1, "bat", S.BAT_WEIGHTS, r.pressure_bat), (c2, "bowl", S.BOWL_WEIGHTS, r.pressure_bowl)):
            comp = pd.DataFrame({"component": list(w), "value": [r[f"pc_{role}_{k}"] for k in w],
                                 "weight": list(w.values())})
            comp["contribution"] = comp.value * comp.weight
            fig = go.Figure(go.Bar(x=comp.contribution, y=comp.component, orientation="h",
                                   marker_color=C["lime"] if role == "bat" else C["teal"],
                                   customdata=np.c_[comp.value, comp.weight],
                                   text=[f"{v:.2f} × {wt:.2f}" for v, wt in zip(comp.value, comp.weight)],
                                   textposition="outside",
                                   hovertemplate="%{y}: component %{customdata[0]:.2f} × weight %{customdata[1]:.2f}"
                                                 "<extra></extra>"))
            fig.update_layout(yaxis=dict(autorange="reversed"), xaxis=dict(title="value × weight",
                                                                           range=[0, max(0.3, comp.contribution.max() * 1.6)]))
            col.plotly_chart(style(fig, 330, f"{'Batting' if role == 'bat' else 'Bowling'} pressure = {score:.1f}"),
                             width="stretch")
        st.markdown(
            f"Raw batting sum {sum(r[f'pc_bat_{k}'] * v for k, v in S.BAT_WEIGHTS.items()):.3f} → percentile (all balls "
            f"and comparable states) → **{r.pressure_bat:.1f}** ({r.bat_category}). "
            f"Outcome: {int(r.bat_runs)} run(s){' and out' if r.striker_out else ''}; an average batter was expected "
            f"{r.x_bat_runs:.2f} runs and a {r.x_bat_out:.1%} dismissal chance, wicket worth {r.wicket_value:.1f} runs → "
            f"ball value **{r.bat_value:+.2f}** runs for the batter and **{r.bowl_value:+.2f}** for the bowler.")

# ------------------------------------------------------------------ 6
with tabs[5]:
    U.section("Value of each ball (actual − expected)")
    st.latex(r"v^{bat} = (r - \hat r) - W\,(o - \hat o) \qquad v^{bowl} = (\hat c - c) + W\,(w - \hat w)")
    st.markdown("`r` runs off the bat, `o` 1 if the striker is out, `c` runs conceded, `w` 1 for a bowler's wicket; hats = "
                "expected for an average player; `W` = wicket value at that moment. Summed over pressure balls this is "
                "the player's contribution; summed over his other balls it is his **personal baseline**.")
    U.section("Pressure innings / spells and impact performances", "the consistency signal")
    st.markdown(f"""
* **Pressure innings**: a match in which the batter faced ≥ {S.BAT_INNINGS_MIN_BALLS} pressure balls.
  **Pressure spell**: a match in which the bowler bowled ≥ {S.BOWL_SPELL_MIN_BALLS} pressure balls.
* **Impact innings** = ≥ {S.BAT_IMPACT_RUNS} pressure runs at SR ≥ {S.BAT_IMPACT_SR:.0f}, **or** ≥ {S.BAT_IMPACT_ALT_RUNS}
  pressure runs that beat the situation by ≥ +{S.BAT_IMPACT_ALT_VALUE:.0f} runs (credits rebuilding innings and batters who
  survive a squeeze, whatever their position).
* **Impact spell** = economy ≤ {S.BOWL_IMPACT_MAX_ECON} on pressure balls with ≥ 1 wicket or ≥ {S.BOWL_IMPACT_DOT_SHARE:.0%} dots.
""")
    U.section("Rating components")
    rows = [
        ("impact_rate", "(impact + a) / (pressure innings + a + b)", "beta-binomial prior, fitted by maximum likelihood",
         f"a+b = {kb['a_i'] + kb['b_i']:.1f} bat · {kw['a_i'] + kw['b_i']:.1f} bowl"),
        ("pressure_value", "100 × Σ v_pressure / (pressure balls + k)", "empirical-Bayes shrinkage towards average",
         f"k = {kb['k_p']:.0f} balls bat · {kw['k_p']:.0f} bowl"),
        ("uplift", "(v_pressure/ball − v_normal/ball) × τ²/(τ² + noise)", "own-baseline difference, shrunk by its reliability",
         f"τ = {kb['tau']['uplift']:.2f} bat · {kw['tau']['uplift']:.2f} bowl (per 100 balls)"),
        ("value_consistency", "(innings with v > 0 + a) / (innings + a + b)", "beta-binomial prior",
         f"a+b = {kb['a_v'] + kb['b_v']:.1f} bat · {kw['a_v'] + kw['b_v']:.1f} bowl"),
        ("wpa", "100 × Σ WPA in pressure innings / (innings + k)", "shrunk towards 0",
         f"k = {kb['k_w']:.0f} bat · {kw['k_w']:.0f} bowl"),
        ("volume", "log(1 + pressure innings)", "proven over many occasions", "—"),
    ]
    t = pd.DataFrame(rows, columns=["component", "formula", "adjustment", "fitted constant"])
    t.insert(1, "weight", t.component.map(S.RATING_WEIGHTS))
    st.dataframe(t, hide_index=True, width="stretch")
    st.latex(r"z_m = \frac{x_m - \bar x_m}{\tau_m},\qquad \mathrm{Rating} = 50 + 10\cdot\frac{\sum_m \omega_m z_m - \mu}{\sigma}")
    st.markdown("Each component is standardised by its **true-talent spread τ** (estimated from the data), not its observed "
                "spread — a component that is mostly noise therefore moves the rating very little. 50 = average eligible "
                "player, 10 points = one standard deviation.")
    U.section("Worked example: how a rating is built", "standardised components × weights")
    role_lab = st.segmented_control("Role", ["Batting", "Bowling"], default="Batting", key="meth_role") or "Batting"
    role = "bat" if role_lab == "Batting" else "bowl"
    rk = D.rankings(role)
    who = st.selectbox("Player", rk.player.head(30).tolist(), key=f"meth_who_{role}")
    r = rk[rk.player == who].iloc[0]
    comps = list(S.RATING_WEIGHTS)
    dfc = pd.DataFrame({"component": comps, "raw value": [r[m] for m in comps], "z": [r[f"z_{m}"] for m in comps],
                        "weight": [S.RATING_WEIGHTS[m] for m in comps]})
    dfc["weight × z"] = dfc.z * dfc.weight
    c1, c2 = st.columns([1, 1.1])
    c1.dataframe(dfc.round(3), hide_index=True, width="stretch")
    fig = go.Figure(go.Bar(x=dfc["weight × z"], y=dfc.component, orientation="h",
                           marker_color=np.where(dfc["weight × z"] >= 0, C["pos"], C["neg"])))
    fig.add_vline(x=0, line=dict(color=C["faint"]))
    fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="contribution (weight × z)")
    c2.plotly_chart(style(fig, 300, f"{who}: rating {r.rating:.1f} · Reliability Score {r.reliability_score:.1f}"),
                    width="stretch")

# ------------------------------------------------------------------ 7
with tabs[6]:
    U.section("Eligibility")
    st.markdown(f"""
| | Pressure balls | Pressure innings / spells | Eligible | Ranked after selection rules |
|---|---|---|---|---|
| Batters | ≥ {S.BAT_MIN_PRESSURE_BALLS} | ≥ {S.BAT_MIN_PRESSURE_INNINGS} | {meta['eligible_batters']} | {meta['selectable_batters']} |
| Bowlers | ≥ {S.BOWL_MIN_PRESSURE_BALLS} | ≥ {S.BOWL_MIN_PRESSURE_SPELLS} | {meta['eligible_bowlers']} | {meta['selectable_bowlers']} |
""")
    U.section("Reliability Score → final rank")
    st.markdown(f"""
{meta['replicates']} replicates. Each one gives every match a random Poisson(1) weight (a bootstrap of matches) and uses one
of the six pressure definitions in turn; every rating is recomputed. **Reliability Score = 20th percentile** of a player's
{meta['replicates']} ratings — the level he clears in four draws out of five. The final rank orders selectable players by it.

**Evidence tag:** *Strong* = top-10 in ≥ 50% of replicates and under ≥ 4/6 definitions; *Moderate* = ≥ 25% or ≥ 3/6;
otherwise *Uncertain*.
""")
    U.section("Selection rules (applied after rating)")
    st.markdown(f"""
* **Must have played in {S.REQUIRED_SEASON}** — players whose last match in the data is before {S.REQUIRED_SEASON} are treated
  as retired / unavailable.
* **Not a Pakistan player** — anyone who has played for {', '.join(S.EXCLUDED_TEAMS)} (not available for the IPL).

Excluded players are still **rated on the same scale** (they remain part of the population that defines "average"), but they are
not ranked and do not take top-10 places in any replicate. Use **Show excluded** on the ranking pages to see them and the reason.
""")
    for role, lab in (("bat", "Batters"), ("bowl", "Bowlers")):
        allr = D.rankings(role, True)
        exd = allr[~allr.selectable][["player", "reliability_score", "excluded_reason"]].head(12)
        with st.expander(f"{lab} removed by the selection rules ({int((~allr.selectable).sum())} eligible players)"):
            st.dataframe(exd.rename(columns={"player": "Player", "reliability_score": "Reliability Score",
                                             "excluded_reason": "Reason"}).round(1), hide_index=True, width="stretch")

# ------------------------------------------------------------------ 8
with tabs[7]:
    U.section("Do openers get an equal chance to face pressure?", "share of balls faced that are pressure balls")
    pf = D.csv("position_fairness")
    names = {"consensus": "Consensus (context-fair)", "equal_weights": "Equal weights", "leverage": "Leverage only",
             "resource_p1": "Resource (P1)", "lemmer_p2": "Lemmer (P2)", "rule_based": "Rule-based (template)"}
    pf["definition"] = pf.definition.map(names)
    order = ["Openers (1-2)", "Top order (3-4)", "Middle order (5-7)", "Lower order (8-11)"]
    fig = go.Figure()
    palette = [C["lime"], C["teal"], C["warn"], "#A78BFA", "#60A5FA", C["muted"]]
    for i, d in enumerate(names.values()):
        x = pf[pf.definition == d].set_index("position").reindex(order)
        fig.add_bar(x=order, y=x.pressure_ball_rate, name=d, marker_color=palette[i],
                    hovertemplate=f"{d} · %{{x}}: %{{y:.0%}}<extra></extra>")
    fig.update_layout(barmode="group", yaxis=dict(tickformat=".0%", title="Pressure-ball rate"))
    st.plotly_chart(style(fig, 380), width="stretch")
    st.markdown("""
Template-style definitions (death overs, wickets down, rule lists) push almost all pressure onto the middle and lower
order, so openers are barely measured. The consensus index narrows that gap by:

* the **squeeze** component — dot balls in a row, dots in the last 12, a long wait for a boundary, a batter stuck well
  below the rate the game needs — which happens in any phase;
* checking **par from over 3** (not only from over 7), so a slow powerplay registers;
* the **context-fair half** of the score, which compares a ball with comparable states (same innings, phase and
  wickets band);
* a smaller weight on **stage** (death overs).

Some gap remains on purpose: collapses, tail-end partners and new-batter situations are real pressure and mostly happen
lower down. Ratings themselves are **rates** compared with an average player *in the same batting position and
situation*, so an opener is judged on how consistently he performs in the pressure he faces, not on how often he faces it.
""")
    ph = D.csv("position_phase_pressure")
    h = ph.pivot(index="position", columns="phase", values="rate").reindex(order)[["Powerplay", "Middle", "Death"]]
    st.dataframe(h.style.format("{:.0%}"), width="stretch")

# ------------------------------------------------------------------ 9
with tabs[8]:
    U.section("Limitations")
    st.markdown(f"""
* **Pressure performance is noisy.** Ratings from odd vs even matches agree with ρ = {meta['split_half']['bat']['rating_spearman']:.2f}
  (batting) and {meta['split_half']['bowl']['rating_spearman']:.2f} (bowling); hence the conservative Reliability Score and
  evidence tags.
* **Clutch uplift is small.** The true spread of "better under pressure than his own normal" is small, so ratings lean on
  consistency of impact and value against expectation.
* **No line/length coordinates** — delivery style, stroke and shot side stand in for zones.
* **Bye/leg-bye run counts are missing** — chase targets are reconciled with published results.
* **History starts in 2022** — experience and form are counted from then.
""")
    with st.expander("Research foundations"):
        st.markdown("""
1. Mallawa Arachchi et al. (2024) — dynamic logistic pressure index for chases → chase component, 0–100 scale.
2. Bhattacharjee & Lemmer (2016) — separate batting and bowling pressure, weighted wickets → two indices.
3. Thomson, Perera & Swartz (2021) — contextual (clutch) batting/bowling with resources → resource table, value vs context.
4. Bhattacharjee & Talukdar (2020) — pressure index validated against outcomes → AUC test.
5. Davis, Perera & Swartz (2015) — expected run differential, position cohorts → actual − expected value.
6. Irvine & Kennedy (2017) — dots, wickets, run rate → impact rules, squeeze component, effect sizes.
7. Jamil et al. (2023) — death-phase factors (Cramér's V) → replicated for T20 death overs.
8. Chathurangi et al. (2025) — composite, Bayesian rankings → multi-component, shrunk rating.
9. Bhattacharjee et al. (2025) — careful composite batting measures → SR not over-rewarded; standardised by τ.
10. Ramanan et al. (2026) — context matters across studies → context-aware design.
""")
