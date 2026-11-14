import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from ui import components as U
from ui import data as D

sys.path.insert(0, str(D.ROOT))
from config import settings as S  # noqa: E402  (the same settings the pipeline used)

meta = D.guard(D.metrics)
kb, kw = D.constants("bat"), D.constants("bowl")

U.page_header("Methodology", "How the system works",
              "Everything shown here is read from the pipeline's own configuration and outputs, so it always matches "
              "the implementation.")

c1, c2 = st.columns([3, 1])
with c2:
    for f, label in (("methodology_report.docx", "Download report (.docx)"), ("methodology_report.md", "Download report (.md)")):
        p = D.REPORTS / f
        if p.exists():
            st.download_button(label, p.read_bytes(), file_name=f, width="stretch")
with c1:
    U.section("1 · Pressure definition", "dynamic, ball-by-ball, separate for batting and bowling")
    st.markdown("""
Pressure is recomputed **before every delivery** from the live match state, so it rises and falls within an innings.
Batting and bowling get **separate indices** (Bhattacharjee & Lemmer): a slipping chase is pressure on the batter, a
target being run down is pressure on the bowler. Situational components are gated by how **live the contest** is,
so a hopeless chase is not "maximum pressure". **Knockout** balls are always pressure balls, rain-revised matches carry
a premium, and **personal context** (experience, form, match-up, own record in this phase) is added — all from
matches before the current one.
""")

U.section("2 · Pressure score calculation")
st.latex(r"g_i = %.2f + %.2f\cdot 4\,\mathrm{WP}_i(1-\mathrm{WP}_i)" % (S.GATE_FLOOR, 1 - S.GATE_FLOOR))
st.latex(r"\mathrm{raw}_{r,i} = \sum_k w_{r,k}\, c_{r,k,i}\;(\times g_i \text{ for situational } k)")
st.latex(r"P_{r,i} = 100\cdot \mathrm{pct}(\mathrm{raw}_{r,i});\quad \text{DLS: } \times %.2f;\quad "
         r"\text{knockout: } \max(P, %.0f + %.2f P)" % (S.DLS_MULTIPLIER, S.KNOCKOUT_FLOOR, S.KNOCKOUT_SLOPE))
c1, c2 = st.columns(2)
c1.dataframe(pd.Series(S.BAT_WEIGHTS, name="weight").rename_axis("batting component"), width="stretch")
c2.dataframe(pd.Series(S.BOWL_WEIGHTS, name="weight").rename_axis("bowling component"), width="stretch")
with st.expander("Component definitions"):
    st.markdown("""
| Component | Batting | Bowling |
|---|---|---|
| Leverage | percentile of WP(after a four) − WP(after a wicket) | same |
| Chase / defend | 2nd inns: logistic in runs needed ÷ runs an average side scores from these balls & wickets; RRR ramp 8→15 × wickets multiplier. 1st inns (from over 7): projected total below par, or CRR < 7 at over 12 | 2nd inns: target being run down; 1st inns: projected total above par |
| Wickets | Lemmer-weighted wickets lost, 2+ wickets in 18 balls, 2+ powerplay wickets | — |
| Stage | death overs 0.6→1.0, otherwise share of innings used | same |
| Partner | tail-end non-striker (No. 8+), new batter (< 6 balls) | — |
| Momentum | — | runs in last 12 balls, set partnership |
| Spell | — | his previous over in this match went for 8+ |
| Stakes | Super 4 0.6, rain-revised 0.5 | same |
| Personal | experience, last-5 form, head-to-head vs this bowler, own record in this phase | experience, last-5 economy, batter has dominated him |
""")
st.markdown(f"A **pressure ball** scores ≥ **{S.PRESSURE_THRESHOLD:.0f}**. Categories: Low < 40 · Moderate 40–75 · "
            "High 75–90 · Extreme ≥ 90.")

U.section("3 · Batting and bowling ratings")
st.latex(r"v^{bat}_i = (r_i - \hat r_i) - W_i\,(o_i - \hat o_i) \qquad v^{bowl}_i = (\hat c_i - c_i) + W_i\,(w_i - \hat w_i)")
st.markdown("""
`r̂, ô, ĉ, ŵ` are expected runs / dismissal / runs conceded / wicket for an **average player in the same situation
against the same opponent**, from cross-fitted gradient-boosting models. `W` is the run value of a wicket at that
moment (drop in expected remaining runs).
""")
w = pd.DataFrame({"weight": S.RATING_WEIGHTS}).rename_axis("component")
w["meaning"] = ["share of pressure innings/spells that were impact performances",
                "runs above average per 100 pressure balls", "pressure value minus own non-pressure value",
                "share of pressure innings/spells with positive value", "win probability added per pressure innings/spell",
                "log(1 + pressure innings/spells)"]
st.dataframe(w, width="stretch")
st.latex(r"\mathrm{Rating} = 50 + 10\cdot\frac{\sum_m \omega_m z_m - \mu}{\sigma},\qquad z_m = \frac{x_m - \bar x_m}{\tau_m}")
st.markdown(f"""
**Impact innings**: ≥ {S.BAT_INNINGS_MIN_BALLS} pressure balls, ≥ {S.BAT_IMPACT_RUNS} pressure runs at SR ≥
{S.BAT_IMPACT_SR:.0f}. **Impact spell**: ≥ {S.BOWL_SPELL_MIN_BALLS} pressure balls at economy ≤ {S.BOWL_IMPACT_MAX_ECON}
with a wicket or ≥ {S.BOWL_IMPACT_DOT_SHARE:.0%} dots. Each component is standardised by its **true-talent spread τ**,
so mostly-noise components carry little weight.
""")

U.section("4 · Baselines and statistical adjustments")
st.markdown(f"""
* **Personal baseline**: the player's own non-pressure balls, measured against expectation (so death specialists are not
  penalised for death overs being expensive).
* **Empirical-Bayes shrinkage** of value per ball: k = {kb['k_p']:.0f} balls (batting), {kw['k_p']:.0f} (bowling),
  estimated from the data.
* **Beta-binomial** priors (maximum likelihood) for impact rate and value consistency.
* **Uplift** shrunk by its own reliability (true spread is small).
* **Cross-fitting**: every model is trained in 5 folds grouped by match.
""")

U.section("5 · Eligibility and sample size")
st.markdown(f"""
| | Pressure balls | Pressure innings/spells | Eligible |
|---|---|---|---|
| Batters | ≥ {S.BAT_MIN_PRESSURE_BALLS} | ≥ {S.BAT_MIN_PRESSURE_INNINGS} | {meta['eligible_batters']} |
| Bowlers | ≥ {S.BOWL_MIN_PRESSURE_BALLS} | ≥ {S.BOWL_MIN_PRESSURE_SPELLS} | {meta['eligible_bowlers']} |

IPL and T20I are analysed together; competition type, season par and opponent strength are inside the models.
""")

U.section("6 · Ranking methodology")
st.markdown(f"""
{meta['replicates']} replicates: Poisson(1) match bootstrap, cycling through six pressure definitions (consensus,
leverage, Paper-1 resource, Paper-2 Lemmer, rule-based, equal weights). **Reliability Score** = 20th percentile of the
replicate ratings → final rank. Evidence tag: *Strong* (top-10 in ≥ 50% of replicates and ≥ 4/6 definitions),
*Moderate* (≥ 25% or ≥ 3/6), else *Uncertain*.
""")

U.section("7 · Model limitations")
st.markdown(f"""
* Pressure performance is noisy: split-half rating agreement ρ = {meta['split_half']['bat']['rating_spearman']:.2f}
  (batting) and {meta['split_half']['bowl']['rating_spearman']:.2f} (bowling).
* Clutch uplift has a small true spread; ratings lean on consistency and volume of impact.
* No line/length coordinates — delivery style, stroke and shot side are used instead.
* Bye/leg-bye run counts are missing; chase targets are reconciled with published results.
* Experience counts from 2022, the start of the data.
""")

with st.expander("Research foundations"):
    st.markdown("""
1. Mallawa Arachchi et al. (2024) — dynamic logistic pressure index for chases → chase component, 0–100 scale.
2. Bhattacharjee & Lemmer (2016) — separate batting and bowling pressure, weighted wickets → two indices.
3. Thomson, Perera & Swartz (2021) — contextual (clutch) batting/bowling with resources → resource table, value vs context.
4. Bhattacharjee & Talukdar (2020) — pressure index validated against outcomes → AUC test.
5. Davis, Perera & Swartz (2015) — expected run differential → actual − expected value.
6. Irvine & Kennedy (2017) — dots, wickets, run rate → impact rules and effect sizes.
7. Jamil et al. (2023) — death-phase factors (Cramér's V) → replicated for T20 death overs.
8. Chathurangi et al. (2025) — composite, Bayesian rankings → multi-component, shrunk rating.
9. Bhattacharjee et al. (2025) — careful composite batting measures → SR not over-rewarded; standardised by τ.
10. Ramanan et al. (2026) — context matters across studies → context-aware design.
""")
