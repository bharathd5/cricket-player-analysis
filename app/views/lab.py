import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui import components as U
from ui import data as D
from ui.theme import C, style

U.page_header("Performance Lab", "Actual vs expected under pressure",
              "Every pressure ball has an expected outcome from cross-fitted models: what an average player would "
              "produce in exactly that situation against that opponent. The gap is the player's contribution.")

role_lab = st.segmented_control("Role", ["Batting", "Bowling"], default="Batting", key="lab_role") or "Batting"
role = "bat" if role_lab == "Batting" else "bowl"
rank = D.guard(D.rankings, role)
tot = D.guard(D.player_pressure_totals, role)
d = rank.merge(tot.rename(columns={"balls": "p_balls", "runs": "p_runs", "outs": "p_outs"}), on="player_id")
d["act100"] = d.p_runs * 100 / d.p_balls
d["exp100"] = d.x_runs * 100 / d.p_balls
d["label"] = np.where(d.final_rank <= 10, d.player.str.split().str[-1], "")
accent = C["lime"] if role == "bat" else C["teal"]

U.section("Expected vs actual", "per 100 pressure balls · eligible players · bubble size = pressure balls")
c1, c2 = st.columns(2)
with c1:
    lo, hi = float(min(d.exp100.min(), d.act100.min())) - 5, float(max(d.exp100.max(), d.act100.max())) + 5
    fig = go.Figure()
    fig.add_scatter(x=[lo, hi], y=[lo, hi], mode="lines", line=dict(color=C["faint"], dash="dot"), hoverinfo="skip",
                    showlegend=False)
    good = d.act100 >= d.exp100 if role == "bat" else d.act100 <= d.exp100
    fig.add_scatter(x=d.exp100, y=d.act100, mode="markers+text", text=d.label, textposition="top center",
                    textfont=dict(size=10, color=C["text"]), showlegend=False,
                    marker=dict(size=np.clip(d.p_balls / 25, 6, 28), color=np.where(good, C["pos"], C["neg"]), opacity=0.8,
                                line=dict(color=C["bg"], width=1)),
                    customdata=np.c_[d.player, d.p_balls, d.final_rank],
                    hovertemplate="%{customdata[0]} (#%{customdata[2]})<br>expected %{x:.1f} · actual %{y:.1f}"
                                  "<br>%{customdata[1]} pressure balls<extra></extra>")
    fig.update_layout(xaxis=dict(title="Expected runs" + (" scored" if role == "bat" else " conceded"), range=[lo, hi]),
                      yaxis=dict(title="Actual runs" + (" scored" if role == "bat" else " conceded"), range=[lo, hi]))
    st.plotly_chart(style(fig, 420, "Runs"), width="stretch")
    U.note("Above the diagonal = more runs than an average batter in the same spots." if role == "bat" else
           "Below the diagonal = fewer runs conceded than an average bowler in the same spots.")
with c2:
    d["out_act"] = d.p_outs * 100 / d.p_balls
    d["out_exp"] = d.x_outs * 100 / d.p_balls
    lo, hi = 0, float(max(d.out_act.max(), d.out_exp.max())) + 1
    good = d.out_act <= d.out_exp if role == "bat" else d.out_act >= d.out_exp
    fig = go.Figure()
    fig.add_scatter(x=[lo, hi], y=[lo, hi], mode="lines", line=dict(color=C["faint"], dash="dot"), hoverinfo="skip",
                    showlegend=False)
    fig.add_scatter(x=d.out_exp, y=d.out_act, mode="markers+text", text=d.label, textposition="top center",
                    textfont=dict(size=10, color=C["text"]), showlegend=False,
                    marker=dict(size=np.clip(d.p_balls / 25, 6, 28), color=np.where(good, C["pos"], C["neg"]), opacity=0.8,
                                line=dict(color=C["bg"], width=1)),
                    customdata=np.c_[d.player, d.p_outs, d.x_outs],
                    hovertemplate="%{customdata[0]}<br>expected %{customdata[2]:.1f} · actual %{customdata[1]:.0f}"
                                  "<extra></extra>")
    fig.update_layout(xaxis=dict(title="Expected " + ("dismissals" if role == "bat" else "wickets") + " per 100 balls",
                                 range=[lo, hi]),
                      yaxis=dict(title="Actual per 100 balls", range=[lo, hi]))
    st.plotly_chart(style(fig, 420, "Dismissals" if role == "bat" else "Wickets"), width="stretch")
    U.note("Below the diagonal = gets out less often than expected." if role == "bat" else
           "Above the diagonal = takes more wickets than expected.")

U.section("Pressure performance deviations", "how good under pressure vs how much better than his own baseline")
c1, c2 = st.columns(2)
with c1:
    fig = go.Figure(go.Scatter(
        x=d.pressure_value, y=d.uplift, mode="markers+text", text=d.label, textposition="top center",
        textfont=dict(size=10, color=C["text"]),
        marker=dict(size=9, color=d.reliability_score, colorscale=[[0, "#2E5A7A"], [1, accent]],
                    colorbar=dict(title="Reliability", thickness=10), line=dict(color=C["bg"], width=1)),
        customdata=d.player, hovertemplate="%{customdata}<br>value %{x:+.1f} / 100 balls · uplift %{y:+.2f}<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=C["faint"], dash="dot"))
    fig.add_vline(x=0, line=dict(color=C["faint"], dash="dot"))
    fig.update_layout(xaxis_title="Pressure value (runs vs average per 100 pressure balls, shrunk)",
                      yaxis_title="Uplift vs own baseline (shrunk)")
    st.plotly_chart(style(fig, 400), width="stretch")
    U.note("Uplift is shrunk by its own reliability. Its true spread is small, so most players sit near zero: "
           "players who are good under pressure are mostly good players who keep delivering.")
with c2:
    fig = go.Figure(go.Scatter(
        x=d.impact_rate, y=d.value_consistency, mode="markers+text", text=d.label, textposition="top center",
        textfont=dict(size=10, color=C["text"]),
        marker=dict(size=np.clip(d.inn, 6, 30), color=accent, opacity=0.7, line=dict(color=C["bg"], width=1)),
        customdata=np.c_[d.player, d.inn, d.impact],
        hovertemplate="%{customdata[0]}<br>impact rate %{x:.2f} (%{customdata[2]}/%{customdata[1]})"
                      "<br>value consistency %{y:.2f}<extra></extra>"))
    fig.update_layout(xaxis_title="Impact rate (shrunk)", yaxis_title="Share of pressure innings with positive value (shrunk)")
    st.plotly_chart(style(fig, 400), width="stretch")
    U.note("Consistency view: right = more impact performances, top = more often above average. Bubble size = "
           "pressure innings/spells.")

U.section("Situational performance", "on pressure balls · top 12 by reliability")
sp = D.splits()
ids = rank.player_id.head(12).tolist()
s = sp[(sp.role == role) & (sp.scope == "Pressure") & sp.player_id.isin(ids) &
       sp.split.isin(["Phase", "Innings", "Situation", "Match type", "Pace/spin"])].copy()
s["col"] = s.split_value.replace({"After collapse (2+ wkts in 18 balls)": "After collapse",
                                  "League/bilateral": "Non-knockout"})
s = s[s.col != "Normal"]
metric = "strike_rate" if role == "bat" else "economy"
s.loc[s.balls < 12, metric] = np.nan
h = s.pivot_table(index="player_id", columns="col", values=metric)
order = [c for c in ["Powerplay", "Middle", "Death", "1st innings", "2nd innings", "After collapse", "Knockout",
                     "Pace", "Spin"] if c in h.columns]
h = h.reindex(index=ids, columns=order)
h.index = h.index.map(D.names())
fig = go.Figure(go.Heatmap(
    z=h.values, x=h.columns, y=h.index, text=np.where(np.isnan(h.values), "–", np.round(h.values, 1).astype(str)),
    texttemplate="%{text}",
    colorscale=([[0, C["neg"]], [0.5, "#1C2A3F"], [1, C["pos"]]] if role == "bat" else
                [[0, C["pos"]], [0.5, "#1C2A3F"], [1, C["neg"]]]),
    zmid=140 if role == "bat" else 8.5, colorbar=dict(thickness=10),
    hovertemplate="%{y} · %{x}: %{z:.1f}<extra></extra>"))
fig.update_layout(yaxis=dict(autorange="reversed"), xaxis=dict(side="top"))
st.plotly_chart(style(fig, 470), width="stretch")
U.note(("Strike rate" if role == "bat" else "Economy") + " on pressure balls in each situation; cells with fewer "
       "than 12 balls are left blank.")

U.section("Form under pressure over time", "rolling 8-match value on pressure balls")
logs = D.match_logs(role)
pick = st.multiselect("Players", rank.player.tolist(), default=rank.player.head(3).tolist(), max_selections=5,
                      key=f"lab_trend_{role}")
if pick:
    fig = go.Figure()
    palette = [C["lime"], C["teal"], C["warn"], "#A78BFA", "#60A5FA"]
    for i, p in enumerate(pick):
        pid = rank.loc[rank.player == p, "player_id"].iloc[0]
        g = logs[(logs.player_id == pid) & (logs.pb > 0)].sort_values("match_date")
        fig.add_scatter(x=g.match_date, y=g.pv.rolling(8, min_periods=3).mean(), name=p,
                        line=dict(color=palette[i], width=2), hovertemplate=f"{p}: %{{y:+.1f}}<extra></extra>")
    fig.add_hline(y=0, line=dict(color=C["faint"], dash="dot"))
    fig.update_layout(yaxis_title="Runs vs average per match (8-match rolling)", xaxis_title=None)
    st.plotly_chart(style(fig, 360), width="stretch")
