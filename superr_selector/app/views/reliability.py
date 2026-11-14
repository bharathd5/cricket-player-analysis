import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui import components as U
from ui import data as D
from ui.theme import C, CATEGORY_COLORS, DEF_LABELS, style

meta = D.guard(D.metrics)
U.page_header("Model Reliability", "How much can the rankings be trusted?",
              "Cricket under pressure is noisy. This page shows how big each player's sample is, how wide the "
              "uncertainty is, and how much the rankings move when the assumptions change.")

role_lab = st.segmented_control("Role", ["Batting", "Bowling"], default="Batting", key="rel_role_m") or "Batting"
role = "bat" if role_lab == "Batting" else "bowl"
rank = D.guard(D.rankings, role)
accent = C["lime"] if role == "bat" else C["teal"]
sh = meta["split_half"][role]
th = D.csv(f"threshold_sensitivity_{role}")
ws = D.csv(f"weight_sensitivity_{role}")
wp = meta["win_probability"]

U.kpi_row([
    ("Eligible players", f"{len(rank)}", "meet the sample-size rules", accent),
    ("Replicates", f"{meta['replicates']}", "match bootstrap × 6 definitions", C["teal"]),
    ("Split-half agreement", f"{sh['rating_spearman']:.2f}", "rating from odd vs even matches (Spearman)", C["warn"]),
    ("Weight robustness", f"{ws.overlap.mean():.1f}/10", "top-10 kept under 100 random weightings", C["pos"]),
    ("Win-prob. model AUC", f"{wp['innings_2']['auc']:.3f}", f"2nd innings · Brier {wp['innings_2']['brier']:.3f}", C["teal"]),
])

U.section("Sample size", "pressure innings/spells per player; dashed line = eligibility")
logs = D.match_logs(role)
cnt = logs.groupby("player_id").inn.sum()
cnt = cnt[cnt > 0]
need = 10
c1, c2 = st.columns([1.3, 1])
with c1:
    fig = go.Figure(go.Histogram(x=cnt, xbins=dict(size=2), marker_color=C["faint"],
                                 hovertemplate="%{x} innings: %{y} players<extra></extra>"))
    fig.add_vline(x=need, line=dict(color=C["warn"], dash="dash"), annotation_text="≥ 10 required",
                  annotation_font_color=C["warn"])
    fig.update_layout(xaxis_title="Pressure innings/spells", yaxis_title="Players")
    st.plotly_chart(style(fig, 300), width="stretch")
with c2:
    U.insight(f"<b>{(cnt >= need).sum()}</b> of {len(cnt)} players with any pressure "
              f"{'innings' if role == 'bat' else 'spells'} reach the 10 required; a further ball-count rule leaves "
              f"<b>{len(rank)}</b> eligible.")
    U.insight("Small samples are not thrown away inside the model: every rate is shrunk towards the population average "
              "in proportion to how little evidence there is (empirical Bayes).")
    k = D.constants(role)
    U.insight(f"Value per ball is shrunk with k = <b>{k['k_p']:.0f}</b> balls: a player with {k['k_p']:.0f} balls keeps "
              "half of his observed difference from average.")

U.section("Confidence intervals", "90% interval of the rating across replicates · top 25")
d = rank.head(25).iloc[::-1]
fig = go.Figure()
for _, r in d.iterrows():
    fig.add_shape(type="line", x0=r.ci_low, x1=r.ci_high, y0=r.player, y1=r.player, line=dict(color="#2A3B52", width=6))
fig.add_scatter(x=d.rating, y=d.player, mode="markers", name="Full-data rating", marker=dict(color=C["muted"], size=8),
                hovertemplate="%{y}: full-data rating %{x:.1f}<extra></extra>")
fig.add_scatter(x=d.reliability_score, y=d.player, mode="markers", name="Reliability Score (20th pct)",
                marker=dict(color=accent, size=10, symbol="diamond"),
                customdata=np.c_[d.ci_low, d.ci_high],
                hovertemplate="%{y}: %{x:.1f} (90% interval %{customdata[0]:.1f}–%{customdata[1]:.1f})<extra></extra>")
fig.add_vline(x=50, line=dict(color=C["faint"], dash="dot"))
fig.update_layout(xaxis_title="Rating", yaxis_title=None)
st.plotly_chart(style(fig, 640), width="stretch")
U.note("Read it like a weather forecast: the bar is the range of ratings the player gets across plausible versions of "
       "the data and of the pressure definition. Short bars far to the right are the most trustworthy picks.")

c1, c2 = st.columns(2)
with c1:
    U.section("Reliability-adjusted vs raw", "who the conservative score promotes or demotes")
    fig = go.Figure(go.Scatter(
        x=rank.rating, y=rank.reliability_score, mode="markers",
        marker=dict(color=np.where(rank.final_rank <= 10, accent, C["faint"]), size=8, line=dict(color=C["bg"], width=1)),
        customdata=np.c_[rank.player, rank.final_rank],
        hovertemplate="%{customdata[0]} (#%{customdata[1]})<br>rating %{x:.1f} → reliability %{y:.1f}<extra></extra>"))
    fig.update_layout(xaxis_title="Full-data rating", yaxis_title="Reliability Score")
    st.plotly_chart(style(fig, 360), width="stretch")
with c2:
    U.section("Pressure threshold", "rank agreement when the pressure-ball cut-off moves")
    fig = go.Figure()
    fig.add_bar(x=th.threshold.astype(str), y=th.top10_overlap, name="Top-10 overlap (of 10)", marker_color=accent,
                text=th.top10_overlap, textposition="outside")
    fig.add_scatter(x=th.threshold.astype(str), y=th.rank_corr * 10, name="Rank correlation ×10", mode="lines+markers",
                    line=dict(color=C["warn"], width=2), customdata=th.rank_corr,
                    hovertemplate="threshold %{x}: ρ = %{customdata:.2f}<extra></extra>")
    fig.update_layout(xaxis_title="Pressure-ball threshold (default 75)", yaxis=dict(range=[0, 11.5], title=None))
    st.plotly_chart(style(fig, 360), width="stretch")

U.section("Ranking stability", "rank of the final top 10 under each pressure definition and how often it is top-10")
reps = D.replicates(role)
top = rank.head(10)
rows = []
for dname in DEF_LABELS:
    sub = reps[reps.definition == dname].drop(columns="definition")
    rk = sub.rank(axis=1, ascending=False)
    for pid in top.player_id:
        rows.append({"definition": DEF_LABELS[dname], "player": top.set_index("player_id").player[pid],
                     "p_top10": float((rk[str(pid)] <= 10).mean())})
pr = pd.DataFrame(rows).pivot(index="player", columns="definition", values="p_top10").reindex(top.player)
pr = pr[list(DEF_LABELS.values())]
fig = go.Figure(go.Heatmap(z=pr.values, x=pr.columns, y=pr.index, text=np.round(pr.values * 100).astype(int),
                           texttemplate="%{text}%", colorscale=[[0, "#13263B"], [1, accent]], zmin=0, zmax=1,
                           colorbar=dict(thickness=10, tickformat=".0%"),
                           hovertemplate="%{y} · %{x}: top-10 in %{z:.0%} of bootstrap replicates<extra></extra>"))
fig.update_layout(yaxis=dict(autorange="reversed"), xaxis=dict(side="top"))
st.plotly_chart(style(fig, 420), width="stretch")

U.section("Model validation", "does the pressure index measure pressure?")
c1, c2, c3 = st.columns(3)
tiers = D.csv("pressure_tiers")
with c1:
    t = tiers[tiers.role.eq("Batting" if role == "bat" else "Bowling")]
    fig = go.Figure(go.Bar(x=t.category, y=t.mean_abs_wpa * 100, marker_color=[CATEGORY_COLORS[c] for c in t.category],
                           text=(t.mean_abs_wpa * 100).map("{:.2f}".format), textposition="outside"))
    fig.update_layout(yaxis=dict(title="Mean |WP swing| %", range=[0, t.mean_abs_wpa.max() * 130]))
    st.plotly_chart(style(fig, 300, f"Extreme balls swing {meta['extreme_low_wpa_swing'][role]:.1f}× more"), width="stretch")
with c2:
    p4 = D.csv("p4_outcome_test")
    fig = go.Figure()
    fig.add_bar(x=p4.chase_snapshot_over.astype(str), y=p4.auc_rrr_only, name="RRR only", marker_color=C["faint"])
    fig.add_bar(x=p4.chase_snapshot_over.astype(str), y=p4.auc_rrr_plus_pressure, name="RRR + pressure", marker_color=accent)
    fig.update_layout(barmode="group", yaxis=dict(range=[0.75, 1], title="AUC (cross-validated)"),
                      xaxis_title="Chase snapshot at over")
    st.plotly_chart(style(fig, 300, "Paper 4 test: predicting the chase"), width="stretch")
with c3:
    dc = D.csv("definition_comparison")
    dc = dc[dc.role == role].assign(lbl=lambda x: x.definition.map(DEF_LABELS)).sort_values("wpa_ratio_top_vs_bottom_quartile")
    fig = go.Figure(go.Bar(x=dc.wpa_ratio_top_vs_bottom_quartile, y=dc.lbl, orientation="h",
                           marker_color=[accent if x == "consensus" else C["faint"] for x in dc.definition],
                           text=dc.wpa_ratio_top_vs_bottom_quartile.map("{:.1f}×".format), textposition="outside"))
    fig.update_layout(xaxis=dict(title="Top vs bottom quartile |WP swing|", range=[0, dc.wpa_ratio_top_vs_bottom_quartile.max() * 1.25]))
    st.plotly_chart(style(fig, 300, "Six definitions compared"), width="stretch")

with st.expander("Split-half reliability of each rating component"):
    comp = {k.replace("_spearman", ""): v for k, v in sh.items()}
    st.dataframe(pd.Series(comp, name="Spearman ρ (odd vs even matches)").round(3), width="stretch")
    st.caption("Values near zero mean the component is mostly noise over this many matches; the rating weights each "
               "component by its estimated true-talent spread, so noisy components contribute less.")
with st.expander("Win-probability and expected-outcome models"):
    st.json({"win_probability": meta["win_probability"], "expected_models": meta["expected_models"],
             "resource_model": {k: v for k, v in meta["resource_model"].items() if k != "par_totals"}})
