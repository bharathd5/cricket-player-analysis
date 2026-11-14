import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ui import components as U
from ui import data as D
from ui.theme import C, CATEGORY_COLORS, COMP_COLORS, style

meta = D.guard(D.metrics)
b = D.guard(D.balls)
bat = D.guard(D.rankings, "bat")
bowl = D.guard(D.rankings, "bowl")

U.page_header("Overview", "Pressure Performance Analytics",
              f"Who delivers when the game is on the line? Every one of {meta['deliveries']:,} IPL and T20I deliveries "
              f"({meta['date_min']} → {meta['date_max']}) is scored for batting and bowling pressure, and every player "
              "is measured against what an average player would do in the same situation.")

seasons = sorted(b.season_year.unique().astype(int).astype(str).tolist())
comp, season = U.scope_filters("ov", seasons)
f = b
if comp != "All":
    f = f[f.comp_type == comp]
if season != "All":
    f = f[f.season_year == int(season)]
if f.empty:
    U.empty("No deliveries for this competition and season.")
    st.stop()

bf = f[f.ball_faced]
U.kpi_row([
    ("Matches analysed", f"{f.match_id.nunique():,}", f"{meta['competitions']} competitions in full data", C["lime"]),
    ("Players", f"{pd.concat([f.striker_id, f.bowler_id]).nunique():,}", "batted or bowled", C["teal"]),
    ("Deliveries", f"{len(f):,}", "super overs and no-results removed", C["teal"]),
    ("High-pressure balls", f"{int(bf.bat_pressure_ball.sum()):,}",
     f"{bf.bat_pressure_ball.mean():.0%} of balls faced (batting index ≥ 75)", C["warn"]),
    ("Eligible batters", f"{meta['eligible_batters']}", "≥100 pressure balls, ≥10 pressure innings", C["lime"]),
    ("Eligible bowlers", f"{meta['eligible_bowlers']}", "≥120 pressure balls, ≥10 pressure spells", C["lime"]),
])

U.section("Pressure landscape", "how pressure is distributed in the selected data")
c1, c2 = st.columns([1.15, 1])
with c1:
    cat = (pd.concat([bf.bat_category.value_counts(normalize=True).rename("Batting"),
                      f.bowl_category.value_counts(normalize=True).rename("Bowling")], axis=1)
           .reindex(["Low", "Moderate", "High", "Extreme"]).reset_index(names="category")
           .melt("category", var_name="role", value_name="share"))
    fig = px.bar(cat, x="share", y="role", color="category", orientation="h", color_discrete_map=CATEGORY_COLORS,
                 text=cat.share.map("{:.0%}".format))
    fig.update_traces(textposition="inside", insidetextfont=dict(color="#0B1220", size=11),
                      hovertemplate="%{y} · %{fullData.name}: %{x:.1%}<extra></extra>")
    fig.update_traces(selector=dict(name="Low"), insidetextfont=dict(color="#F1F5F9"))
    fig.update_layout(xaxis=dict(tickformat=".0%", title=None), yaxis_title=None, legend_title=None, barmode="stack")
    st.plotly_chart(style(fig, 230, "Pressure situation distribution"), width="stretch")
    ph = (f.groupby(["innings", "phase"], observed=True).pressure_bat.mean().unstack()
          .reindex(columns=["Powerplay", "Middle", "Death"]))
    fig = go.Figure(go.Heatmap(z=ph.values, x=ph.columns, y=[f"Innings {i}" for i in ph.index],
                               colorscale=[[0, "#13263B"], [0.5, C["teal"]], [1, C["lime"]]],
                               text=np.round(ph.values, 1), texttemplate="%{text}",
                               hovertemplate="%{y} · %{x}: mean batting pressure %{z:.1f}<extra></extra>",
                               colorbar=dict(title="", thickness=10)))
    st.plotly_chart(style(fig, 210, "Mean batting pressure by innings stage"), width="stretch")
with c2:
    cov = (f.drop_duplicates("match_id").groupby(["season_year", "comp_type"], observed=True).size()
           .rename("matches").reset_index())
    cov["season_year"] = cov.season_year.astype(str)
    fig = px.bar(cov, x="season_year", y="matches", color="comp_type", color_discrete_map=COMP_COLORS)
    fig.update_traces(hovertemplate="%{x} · %{fullData.name}: %{y} matches<extra></extra>")
    fig.update_layout(xaxis_title=None, yaxis_title="Matches", legend_title=None)
    st.plotly_chart(style(fig, 260, "IPL vs T20I coverage"), width="stretch")
    perf = (bf.groupby("bat_category", observed=True)
            .agg(sr=("bat_runs", "mean"), out=("striker_out", "mean")).reindex(["Low", "Moderate", "High", "Extreme"]))
    fig = go.Figure()
    fig.add_bar(x=perf.index, y=perf.sr * 100, name="Strike rate", marker_color=[CATEGORY_COLORS[c] for c in perf.index],
                hovertemplate="%{x}: SR %{y:.1f}<extra></extra>")
    fig.add_scatter(x=perf.index, y=perf.out * 100, name="Dismissal % per ball", yaxis="y2", mode="lines+markers",
                    line=dict(color=C["neg"], width=2), hovertemplate="%{x}: %{y:.2f}% dismissed<extra></extra>")
    fig.update_layout(yaxis=dict(title="Strike rate"), yaxis2=dict(title="Dismissal %", overlaying="y", side="right",
                                                                     showgrid=False, tickformat=".1f"))
    st.plotly_chart(style(fig, 230, "Batting performance falls as pressure rises"), width="stretch")

U.section("Most reliable under pressure", "final ranking = Reliability Score (see Most Reliable Players)")
c1, c2 = st.columns(2)
for col, t, lab, color in ((c1, bat, "Batters", C["lime"]), (c2, bowl, "Bowlers", C["teal"])):
    d = t.head(10).iloc[::-1]
    fig = go.Figure(go.Bar(x=d.reliability_score, y=d.player, orientation="h", marker_color=color,
                           customdata=np.c_[d.final_rank, d.p_top10, d.team],
                           hovertemplate="#%{customdata[0]} %{y} (%{customdata[2]})<br>Reliability %{x:.1f}"
                                         "<br>Top-10 in %{customdata[1]:.0%} of replicates<extra></extra>",
                           text=d.reliability_score.map("{:.1f}".format), textposition="outside"))
    fig.update_layout(xaxis=dict(range=[45, d.reliability_score.max() + 4], title="Reliability Score"))
    col.plotly_chart(style(fig, 380, f"Top 10 {lab}"), width="stretch")

U.section("Key analytical insights", "computed from the pipeline outputs")
tiers = D.csv("pressure_tiers")
p4 = D.csv("p4_outcome_test")
bt = tiers[tiers.role.eq("Batting")].set_index("category")
bw = tiers[tiers.role.eq("Bowling")].set_index("category")
sw = meta["extreme_low_wpa_swing"]
top_b, top_w = bat.iloc[0], bowl.iloc[0]
strong_b = bat.head(10).evidence.eq("Strong").sum()
strong_w = bowl.head(10).evidence.eq("Strong").sum()
death_share = b[b.bat_pressure_ball & b.ball_faced].phase.value_counts(normalize=True).get("Death", np.nan)
ins = [
    f"An <b>Extreme</b>-pressure ball moves the result <b>{sw['bat']:.1f}×</b> (batting) and <b>{sw['bowl']:.1f}×</b> "
    "(bowling) as much as a Low-pressure ball: the index singles out the balls that decide matches.",
    f"Strike rate falls from <b>{bt.loc['Low', 'strike_rate']:.0f}</b> on Low-pressure balls to "
    f"<b>{bt.loc['Extreme', 'strike_rate']:.0f}</b> on Extreme ones, and dismissal risk rises from "
    f"{bt.loc['Low', 'dismissal_pct']:.1f}% to {bt.loc['Extreme', 'dismissal_pct']:.1f}% per ball. "
    f"Bowling economy rises from {bw.loc['Low', 'economy']:.2f} to {bw.loc['Extreme', 'economy']:.2f}.",
    f"Adding the pressure index to the required rate lifts chase-outcome AUC at over 12 from "
    f"<b>{p4.loc[p4.chase_snapshot_over.eq(12), 'auc_rrr_only'].iloc[0]:.3f}</b> to "
    f"<b>{p4.loc[p4.chase_snapshot_over.eq(12), 'auc_rrr_plus_pressure'].iloc[0]:.3f}</b> (paper 4 test).",
    f"<b>{top_b.player}</b> is the most reliable batter: top-10 in {top_b.p_top10:.0%} of 360 replicates and under "
    f"{int(top_b.defs_top10)}/6 pressure definitions, with {int(top_b.impact)} impact innings from {int(top_b.inn)}.",
    f"<b>{top_w.player}</b> leads the bowlers: {int(top_w.pk)} pressure wickets at economy {top_w.pressure_econ:.2f}, "
    f"top-10 in {top_w.p_top10:.0%} of replicates and under {int(top_w.defs_top10)}/6 definitions.",
    f"Only {strong_b} batters and {strong_w} bowlers in the top 10 have <b>Strong</b> evidence; the rest are close "
    "calls, which the reliability ranking makes explicit rather than hiding.",
    f"Death overs supply {death_share:.0%} of batting pressure balls; the rest come from chases going wrong, "
    "collapses, tight first innings and knockouts.",
]
c1, c2 = st.columns(2)
for i, t in enumerate(ins):
    with (c1 if i % 2 == 0 else c2):
        U.insight(t)
