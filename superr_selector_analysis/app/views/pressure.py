import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ui import components as U
from ui import data as D
from ui.theme import C, CATEGORY_COLORS, style

b = D.guard(D.balls)
U.page_header("Pressure Analysis", "How the Pressure Index behaves",
              "Pressure is recalculated before every ball from the live match state. Filter the deliveries and see "
              "how the batting and bowling indices respond to the required rate, wickets, balls left and stage.")

with st.container(border=True):
    c = st.columns([1, 1, 1, 1.3, 1.3])
    comp = c[0].selectbox("Competition", ["All", "IPL", "T20I", "A-team T20"])
    season = c[1].selectbox("Season", ["All"] + sorted(b.season_year.unique().astype(int).astype(str)))
    inn = c[2].selectbox("Innings", ["Both", "1st", "2nd"])
    cats = c[3].multiselect("Pressure category (batting)", ["Low", "Moderate", "High", "Extreme"],
                            default=["Low", "Moderate", "High", "Extreme"])
    sit = c[4].selectbox("Match situation", ["All", "Powerplay", "Middle overs", "Death overs", "Knockout matches",
                                             "Chasing (RRR > 10)"])
f = b
if comp != "All":
    f = f[f.comp_type == comp]
if season != "All":
    f = f[f.season_year == int(season)]
if inn != "Both":
    f = f[f.innings == (1 if inn == "1st" else 2)]
f = f[f.bat_category.isin(cats)]
sit_map = {"Powerplay": f.phase == "Powerplay", "Middle overs": f.phase == "Middle", "Death overs": f.phase == "Death",
           "Knockout matches": f.is_knockout, "Chasing (RRR > 10)": (f.innings == 2) & (f.rrr > 10)}
if sit != "All":
    f = f[sit_map[sit]]
if len(f) < 50:
    U.empty("Fewer than 50 deliveries match these filters. Widen the selection.")
    st.stop()

U.kpi_row([
    ("Deliveries", f"{len(f):,}", "matching the filters", C["teal"]),
    ("Mean batting pressure", f"{f.pressure_bat.mean():.1f}", "0–100 scale", C["lime"]),
    ("Mean bowling pressure", f"{f.pressure_bowl.mean():.1f}", "0–100 scale", C["teal"]),
    ("Pressure balls (bat)", f"{f.bat_pressure_ball.mean():.0%}", "score ≥ 75", C["warn"]),
    ("Mean |WP swing| / ball", f"{f.wpa.abs().mean() * 100:.2f}%", "how much each ball moves the result", C["neg"]),
])

U.section("Distribution", "the index is a percentile scale; knockout balls are floored at 70")
c1, c2 = st.columns([1.3, 1])
with c1:
    fig = go.Figure()
    fig.add_histogram(x=f.pressure_bat, name="Batting", nbinsx=50, marker_color=C["lime"], opacity=0.75)
    fig.add_histogram(x=f.pressure_bowl, name="Bowling", nbinsx=50, marker_color=C["teal"], opacity=0.55)
    fig.add_vline(x=75, line=dict(color=C["warn"], dash="dot"), annotation_text="pressure ball ≥ 75",
                  annotation_font_color=C["warn"])
    fig.update_layout(barmode="overlay", xaxis_title="Pressure score", yaxis_title="Deliveries")
    st.plotly_chart(style(fig, 320, "Pressure score distribution"), width="stretch")
with c2:
    g = (f.groupby("bat_category", observed=True).agg(n=("wpa", "size"), swing=("wpa", lambda s: s.abs().mean() * 100))
         .reindex(["Low", "Moderate", "High", "Extreme"]).dropna())
    fig = go.Figure(go.Bar(x=g.index, y=g.swing, marker_color=[CATEGORY_COLORS[k] for k in g.index],
                           text=g.swing.map("{:.2f}%".format), textposition="outside",
                           customdata=g.n, hovertemplate="%{x}: %{y:.2f}% mean swing · %{customdata:,} balls<extra></extra>"))
    fig.update_layout(yaxis_title="Mean |win-probability swing| per ball (%)", xaxis_title=None)
    st.plotly_chart(style(fig, 320, "Categories separate decisive balls"), width="stretch")

U.section("What drives pressure", "mean index by match-state variable")
tab1, tab2, tab3, tab4 = st.tabs(["Required run rate", "Wickets × balls remaining", "Balls remaining", "Innings stage"])
with tab1:
    ch = f[(f.innings == 2) & f.rrr.notna()].copy()
    if ch.empty:
        U.empty("Required run rate exists only in second innings; select the 2nd innings or Both.")
    else:
        ch["rrr_bin"] = pd.cut(ch.rrr.clip(0, 24), bins=np.arange(0, 25, 2))
        g = ch.groupby(["rrr_bin", "wickets_in_hand"], observed=True).pressure_bat.mean().reset_index()
        g["rrr"] = g.rrr_bin.apply(lambda x: x.mid)
        g = g[g.wickets_in_hand.isin([10, 8, 6, 4, 2])]
        fig = px.line(g, x="rrr", y="pressure_bat", color=g.wickets_in_hand.astype(str) + " in hand", markers=True,
                      color_discrete_sequence=[C["lime"], C["teal"], C["warn"], "#FB923C", C["neg"]])
        fig.update_layout(xaxis_title="Required run rate", yaxis_title="Mean batting pressure", legend_title=None)
        fig.update_traces(hovertemplate="RRR %{x}: %{y:.1f}<extra></extra>")
        st.plotly_chart(style(fig, 360, "Same required rate, more pressure with fewer wickets in hand"), width="stretch")
        U.note("A hopeless chase is not maximum pressure: situational components are gated by contest closeness, "
               "so lines flatten or dip at very high required rates.")
with tab2:
    f2 = f.assign(br=pd.cut(f.balls_rem, [0, 12, 24, 36, 60, 90, 120], labels=["1–12", "13–24", "25–36", "37–60",
                                                                               "61–90", "91–120"]))
    h = f2.groupby(["wickets_in_hand", "br"], observed=True).pressure_bat.mean().unstack().sort_index(ascending=False)
    fig = go.Figure(go.Heatmap(z=h.values, x=h.columns.astype(str), y=h.index.astype(str),
                               colorscale=[[0, "#13263B"], [0.5, C["teal"]], [1, C["lime"]]],
                               hovertemplate="%{y} wickets in hand, %{x} balls left: %{z:.1f}<extra></extra>",
                               colorbar=dict(thickness=10)))
    fig.update_layout(xaxis_title="Balls remaining", yaxis_title="Wickets in hand")
    st.plotly_chart(style(fig, 380, "Batting pressure heatmap"), width="stretch")
with tab3:
    g = f.groupby(pd.cut(f.balls_rem, np.arange(0, 121, 6)), observed=True)[["pressure_bat", "pressure_bowl"]].mean()
    g.index = [int(i.right) for i in g.index]
    fig = go.Figure()
    fig.add_scatter(x=g.index, y=g.pressure_bat, name="Batting", line=dict(color=C["lime"], width=2.5))
    fig.add_scatter(x=g.index, y=g.pressure_bowl, name="Bowling", line=dict(color=C["teal"], width=2.5))
    fig.update_layout(xaxis=dict(title="Balls remaining", autorange="reversed"), yaxis_title="Mean pressure")
    st.plotly_chart(style(fig, 340, "Pressure as the innings runs out"), width="stretch")
with tab4:
    d = f.sample(min(len(f), 40000), random_state=1)
    fig = go.Figure()
    for role, col, colr in (("Batting", "pressure_bat", C["lime"]), ("Bowling", "pressure_bowl", C["teal"])):
        fig.add_box(x=d.phase.astype(str) + " · inns " + d.innings.astype(str), y=d[col], name=role,
                    marker_color=colr, boxpoints=False)
    fig.update_layout(boxmode="group", yaxis_title="Pressure score", xaxis_title=None)
    st.plotly_chart(style(fig, 360, "Pressure by innings stage"), width="stretch")

U.section("Batting vs bowling pressure", "the two indices measure different things (Bhattacharjee & Lemmer)")
c1, c2 = st.columns([1.2, 1])
with c1:
    fig = go.Figure(go.Histogram2d(x=f.pressure_bat, y=f.pressure_bowl, nbinsx=40, nbinsy=40,
                                   colorscale=[[0, "rgba(0,0,0,0)"], [0.02, "#13263B"], [0.4, C["teal"]], [1, C["lime"]]],
                                   hovertemplate="bat %{x:.0f} · bowl %{y:.0f}: %{z} balls<extra></extra>",
                                   colorbar=dict(thickness=10)))
    fig.update_layout(xaxis_title="Batting pressure", yaxis_title="Bowling pressure")
    st.plotly_chart(style(fig, 360, "Joint distribution"), width="stretch")
with c2:
    comp_tbl = D.csv("pressure_components")
    comp_tbl = comp_tbl.assign(label=comp_tbl.role.map({"bat": "Bat", "bowl": "Bowl"}) + " · " + comp_tbl.component)
    comp_tbl = comp_tbl.sort_values("corr_with_abs_wpa")
    fig = go.Figure(go.Bar(x=comp_tbl.corr_with_abs_wpa, y=comp_tbl.label, orientation="h",
                           marker_color=[C["lime"] if r == "bat" else C["teal"] for r in comp_tbl.role],
                           hovertemplate="%{y}: r = %{x:.3f} with |WP swing|<extra></extra>"))
    fig.update_layout(xaxis_title="Correlation with |win-probability swing|", yaxis_title=None)
    st.plotly_chart(style(fig, 360, "Which components track decisive balls"), width="stretch")
st.caption(f"Correlation between batting and bowling pressure in this selection: "
           f"{np.corrcoef(f.pressure_bat, f.pressure_bowl)[0, 1]:.2f}.")
