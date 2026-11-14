import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui import components as U
from ui import data as D
from ui.theme import C, CATEGORY_COLORS, EVIDENCE_COLORS, style

U.page_header("Player Explorer", "Individual pressure profiles",
              "Search any player who batted or bowled in the data. Numbers come straight from the pipeline outputs.")

default_role = st.session_state.get("explorer_role", "bat")
c1, c2 = st.columns([1, 3])
role_lab = c1.segmented_control("Profile", ["Batting", "Bowling"],
                                default="Batting" if default_role == "bat" else "Bowling", key="exp_role") or "Batting"
role = "bat" if role_lab == "Batting" else "bowl"
logs = D.guard(D.match_logs, role)
rank = D.guard(D.rankings, role)
nm = D.names()
tot = logs.groupby("player_id").agg(pb=("pb", "sum"), matches=("match_id", "nunique"))
tot = tot[tot.pb > 0]
order = rank.player_id.tolist() + tot.sort_values("pb", ascending=False).index.difference(rank.player_id).tolist()
order = [p for p in order if p in tot.index]
labels = {p: nm.get(p, str(p)) for p in order}
want = st.session_state.get("explorer_player")
idx = order.index(want) if want in order else 0
pid = c2.selectbox("Search player", order, index=idx, format_func=lambda p: labels[p], key=f"exp_pick_{role}")
st.session_state["explorer_player"] = int(pid)
st.session_state["explorer_role"] = role

pl = logs[logs.player_id == pid].sort_values("match_date")
r = rank[rank.player_id == pid]
eligible = not r.empty
name = labels[pid]
teams = ", ".join(pl.team.dropna().iloc[::-1].unique()[:4])
comps = ", ".join(sorted(pl.comp_type.dropna().unique()))
pills = ""
if eligible:
    rr = r.iloc[0]
    pills = (U.pill(f"Rank {int(rr.final_rank)} of {len(rank)}", C["lime"]) +
             U.pill(f"{rr.evidence} evidence", EVIDENCE_COLORS[rr.evidence]) +
             U.pill("Active" if rr.active else "Inactive >365 days", C["teal"] if rr.active else C["warn"]))
else:
    pills = U.pill("Not eligible for the ranking (sample too small)", C["warn"])
st.markdown(
    f"<div class='si-profile'><div class='nm'>{html.escape(name)}</div>"
    f"<div class='meta'>{html.escape(teams)} · {comps} · {pl.match_id.nunique()} matches "
    f"({pl.match_date.min():%b %Y} – {pl.match_date.max():%b %Y})</div>"
    f"<div style='margin-top:10px'>{pills}</div></div>", unsafe_allow_html=True)
st.write("")

s = pl.sum(numeric_only=True)
if role == "bat":
    p_sr = s.pr * 100 / max(s.pb, 1)
    n_sr = s.nr * 100 / max(s.nb, 1)
    items = [("Pressure innings", f"{int(s.inn)}", f"{int(s.pb)} pressure balls faced", C["teal"]),
             ("Impact innings", f"{int(s.impact)}", f"{s.impact / max(s.inn, 1):.0%} of pressure innings", C["pos"]),
             ("Pressure SR", f"{p_sr:.1f}", f"baseline {n_sr:.1f} ({p_sr - n_sr:+.1f})",
              C["pos"] if p_sr >= n_sr else C["neg"]),
             ("Pressure average", f"{s.pr / max(s.po, 1):.1f}", f"{int(s.po)} dismissals under pressure", C["teal"]),
             ("Runs vs average", f"{s.pv:+.0f}", "on pressure balls, vs an average batter", C["lime"])]
else:
    p_ec = s.pc * 6 / max(s.pb, 1)
    n_ec = s.nc * 6 / max(s.nb, 1)
    items = [("Pressure spells", f"{int(s.inn)}", f"{s.pb / 6:.1f} pressure overs", C["teal"]),
             ("Impact spells", f"{int(s.impact)}", f"{s.impact / max(s.inn, 1):.0%} of pressure spells", C["pos"]),
             ("Pressure economy", f"{p_ec:.2f}", f"baseline {n_ec:.2f} ({p_ec - n_ec:+.2f})",
              C["pos"] if p_ec <= n_ec else C["neg"]),
             ("Pressure wickets", f"{int(s.pk)}", f"{s['pd'] / max(s.pb, 1):.0%} dot balls", C["teal"]),
             ("Runs saved vs average", f"{s.pv:+.0f}", "on pressure balls, vs an average bowler", C["lime"])]
if eligible:
    items.append(("Reliability Score", f"{rr.reliability_score:.1f}", f"rating {rr.rating:.1f} · top-10 in "
                                                                       f"{rr.p_top10:.0%} of replicates", C["lime"]))
U.kpi_row(items)

U.section("Normal vs pressure", "same player, ordinary balls vs pressure balls")
sp = D.splits()
mine = sp[(sp.player_id == pid) & (sp.role == role)]
c1, c2 = st.columns(2)
with c1:
    if role == "bat":
        mets = {"Strike rate": (p_sr, n_sr), "Average": (s.pr / max(s.po, 1), s.nr / max(s["no"], 1)),
                "Balls per dismissal": (s.pb / max(s.po, 1), s.nb / max(s["no"], 1))}
    else:
        mets = {"Economy": (p_ec, n_ec), "Balls per wicket": (s.pb / max(s.pk, 1), s.nb / max(s.nk, 1)),
                "Runs per spell": (s.pc / max((pl.pb > 0).sum(), 1), s.nc / max((pl.nb > 0).sum(), 1))}
    fig = go.Figure()
    fig.add_bar(x=list(mets), y=[v[1] for v in mets.values()], name="Normal", marker_color=C["faint"],
                hovertemplate="%{x} normal: %{y:.2f}<extra></extra>")
    fig.add_bar(x=list(mets), y=[v[0] for v in mets.values()], name="Pressure",
                marker_color=C["lime"] if role == "bat" else C["teal"], hovertemplate="%{x} pressure: %{y:.2f}<extra></extra>")
    fig.update_layout(barmode="group", yaxis_title=None)
    st.plotly_chart(style(fig, 320), width="stretch")
with c2:
    cat = mine[(mine.split == "Pressure category") & (mine.scope == "All")].set_index("split_value").reindex(
        ["Low", "Moderate", "High", "Extreme"]).dropna(subset=["balls"])
    if cat.empty:
        U.empty("No category breakdown available.")
    else:
        y = cat.strike_rate if role == "bat" else cat.economy
        fig = go.Figure(go.Bar(x=cat.index, y=y, marker_color=[CATEGORY_COLORS[k] for k in cat.index],
                               text=[f"{v:.1f}<br>{int(n)} balls" for v, n in zip(y, cat.balls)], textposition="outside",
                               hovertemplate="%{x}: %{y:.2f}<extra></extra>"))
        fig.update_layout(yaxis=dict(title="Strike rate" if role == "bat" else "Economy",
                                     range=[0, float(y.max()) * 1.25]))
        st.plotly_chart(style(fig, 320, "By pressure category"), width="stretch")

U.section("Match by match", "value on pressure balls in each match (runs vs an average player); ● = impact performance")
pm = pl[pl.pb > 0].copy()
if pm.empty:
    U.empty("No pressure balls recorded for this player.")
else:
    pm["roll"] = pm.pv.rolling(5, min_periods=1).mean()
    pm["label"] = pm.opponent.fillna("") + " · " + pm.comp_name.fillna("")
    fig = go.Figure()
    fig.add_bar(x=pm.match_date, y=pm.pv, marker_color=np.where(pm.pv >= 0, C["pos"], C["neg"]), opacity=0.55,
                name="Match value", customdata=np.c_[pm.label, pm.pb],
                hovertemplate="%{x|%d %b %Y} vs %{customdata[0]}<br>%{y:+.1f} runs vs average · "
                              "%{customdata[1]} pressure balls<extra></extra>")
    imp = pm[pm.impact > 0]
    fig.add_scatter(x=imp.match_date, y=imp.pv, mode="markers", name="Impact", marker=dict(color=C["lime"], size=8),
                    hoverinfo="skip")
    fig.add_scatter(x=pm.match_date, y=pm.roll, mode="lines", name="5-match average",
                    line=dict(color=C["warn"], width=2), hovertemplate="5-match avg %{y:+.1f}<extra></extra>")
    fig.update_layout(yaxis_title="Runs vs average", xaxis_title=None, bargap=0.3)
    st.plotly_chart(style(fig, 330), width="stretch")
    inn = pm[pm.inn > 0].copy()
    if len(inn) >= 3:
        inn["cum_rate"] = inn.impact.cumsum() / np.arange(1, len(inn) + 1)
        inn["cum_pos"] = (inn.pv > 0).cumsum() / np.arange(1, len(inn) + 1)
        fig = go.Figure()
        fig.add_scatter(x=inn.match_date, y=inn.cum_rate, name="Impact rate (cumulative)", line=dict(color=C["lime"], width=2))
        fig.add_scatter(x=inn.match_date, y=inn.cum_pos, name="Positive-value rate (cumulative)",
                        line=dict(color=C["teal"], width=2, dash="dot"))
        fig.update_layout(yaxis=dict(tickformat=".0%", range=[0, 1], title=None))
        st.plotly_chart(style(fig, 260, "Consistency trend"), width="stretch")

U.section("Strong zones and situations", "pressure balls vs all balls")
splits_avail = [x for x in ["Delivery style", "Stroke", "Shot side", "Bowling type", "Pace/spin", "Phase", "Innings",
                            "Situation", "Match type", "Venue country", "Competition"] if x in set(mine.split)]
tabs = st.tabs(splits_avail) if splits_avail else []
for tab, sname in zip(tabs, splits_avail):
    with tab:
        x = mine[mine.split == sname].pivot_table(index="split_value", columns="scope",
                                                  values=["balls", "runs", "outs", "strike_rate", "economy", "dot_pct"])
        if x.empty:
            U.empty("No data.")
            continue
        metric = "strike_rate" if role == "bat" else "economy"
        bal = x["balls"].fillna(0)
        keep = bal.get("All", pd.Series(0, index=bal.index)) >= 6
        x = x[keep]
        if x.empty:
            U.empty("Too few balls in every group.")
            continue
        x = x.sort_values(("balls", "All"), ascending=False).head(12)
        fig = go.Figure()
        for scope, colr in (("All", C["faint"]), ("Pressure", C["lime"] if role == "bat" else C["teal"])):
            if (metric, scope) in x:
                fig.add_bar(y=x.index, x=x[(metric, scope)], name=f"{scope} balls", orientation="h", marker_color=colr,
                            customdata=np.c_[x[("balls", scope)].fillna(0), x[("outs", scope)].fillna(0)],
                            hovertemplate="%{y}: %{x:.1f} · %{customdata[0]:.0f} balls · %{customdata[1]:.0f} "
                                          + ("dismissals" if role == "bat" else "wickets") + "<extra></extra>")
        fig.update_layout(barmode="group", yaxis=dict(autorange="reversed"),
                          xaxis_title="Strike rate" if role == "bat" else "Economy")
        st.plotly_chart(style(fig, max(260, 34 * len(x) + 80)), width="stretch")
        U.note("Line and length are not recorded in the data; delivery style, stroke and shot side are the closest "
               "description of where a player scores and gets out.")

c1, c2 = st.columns(2)
with c1:
    U.section("Dismissals", "how he gets out" if role == "bat" else "how he takes wickets")
    dis = D.dismissals()
    dd = dis[(dis.player_id == pid) & (dis.role == role)]
    if dd.empty:
        U.empty("No dismissals recorded.")
    else:
        g = dd.groupby(["dismissal_type", "scope"]).n.sum().unstack(fill_value=0)
        fig = go.Figure()
        for scope, colr in (("Normal", C["faint"]), ("Pressure", C["neg"] if role == "bat" else C["pos"])):
            if scope in g:
                fig.add_bar(x=g.index, y=g[scope], name=scope, marker_color=colr)
        fig.update_layout(barmode="group")
        st.plotly_chart(style(fig, 300), width="stretch")
        ds = dd[dd.scope == "Pressure"].groupby("delivery_style").n.sum().sort_values(ascending=False).head(5)
        if len(ds):
            U.note("Most " + ("dismissals" if role == "bat" else "wickets") + " under pressure came from: " +
                   ", ".join(f"{k} ({v})" for k, v in ds.items()))
with c2:
    U.section("Match-ups", "head-to-head, ≥ 12 balls")
    mu = D.matchups()
    key, other = ("striker_id", "bowler_id") if role == "bat" else ("bowler_id", "striker_id")
    m = mu[mu[key] == pid].copy()
    if m.empty:
        U.empty("No match-ups with 12+ balls.")
    else:
        m["Opponent"] = m[other].map(nm)
        m = m.sort_values("balls", ascending=False).head(12)
        st.dataframe(m[["Opponent", "balls", "runs", "outs", "strike_rate", "pressure_balls"]]
                     .rename(columns={"balls": "Balls", "runs": "Runs", "outs": "Outs", "strike_rate": "SR",
                                      "pressure_balls": "P-balls"}),
                     hide_index=True, width="stretch", height=330,
                     column_config={"SR": st.column_config.NumberColumn(format="%.1f")})

U.section("Ratings by competition and season", "same scale as the overall rating; ≥ 4 pressure innings/spells")
sc = D.scoped(role)
ms = sc[sc.player_id == pid]
if ms.empty:
    U.empty("Not enough pressure innings in any single competition or season.")
else:
    ms = ms.assign(order=ms.scope.map(lambda x: (0 if x == "All" else 1 if not x.isnumeric() else 2, x))).sort_values("order")
    fig = go.Figure(go.Bar(x=ms.scope, y=ms.rating, marker_color=[C["lime"] if s_ == "All" else C["teal"] for s_ in ms.scope],
                           text=[f"{v:.1f}<br>#{int(k)}" for v, k in zip(ms.rating, ms.scope_rank)], textposition="outside",
                           customdata=ms.inn, hovertemplate="%{x}: rating %{y:.1f} · %{customdata} pressure innings<extra></extra>"))
    fig.add_hline(y=50, line=dict(color=C["faint"], dash="dot"))
    fig.update_layout(yaxis=dict(title="Rating", range=[min(30, ms.rating.min() - 5), ms.rating.max() + 12]),
                      xaxis=dict(type="category"))
    st.plotly_chart(style(fig, 300), width="stretch")
