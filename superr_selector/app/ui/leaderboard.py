"""Shared leaderboard page used by Batter Rankings and Bowler Rankings."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui import components as U
from ui import data as D
from ui.theme import C, CATEGORY_COLORS, EVIDENCE_COLORS, style

COMPONENTS = {"impact_rate": "Impact rate", "pressure_value": "Pressure value", "uplift": "Uplift vs baseline",
              "value_consistency": "Value consistency", "wpa": "Win prob. added", "volume": "Volume"}


def _scoped_view(role: str, comp: str, season: str, main: pd.DataFrame) -> pd.DataFrame:
    sc = D.scoped(role)
    scope = comp if season == "All" else season
    if comp != "All" and season != "All":
        st.info("Scoped ratings are precomputed per competition or per season. Showing the season filter.")
    d = sc[sc.scope == scope].copy()
    nm = D.names()
    d["player"] = d.player_id.map(nm)
    d = d.merge(main[["player_id", "team", "final_rank", "evidence", "active", "matches"]], on="player_id", how="left")
    d["team"] = d.team.fillna("–")
    d["evidence"] = d.evidence.fillna("Not eligible overall")
    d["active"] = d.active.fillna(False)
    if role == "bat":
        d["pressure_sr"] = d.pr * 100 / d.pb.clip(lower=1)
        d["normal_sr"] = d.nr * 100 / d.nb.clip(lower=1)
    else:
        d["pressure_econ"] = d.pc * 6 / d.pb.clip(lower=1)
        d["normal_econ"] = d.nc * 6 / d.nb.clip(lower=1)
        d["pressure_overs"] = d.pb / 6
        d["pressure_dot_pct"] = d["pd"] * 100 / d.pb.clip(lower=1)
    d["view_rank"] = d.scope_rank
    return d.sort_values("view_rank")


def render(role: str) -> None:
    is_bat = role == "bat"
    noun = "Batters" if is_bat else "Bowlers"
    main = D.guard(D.rankings, role)
    U.page_header(f"{noun[:-1]} Rankings", f"{noun} under pressure",
                  "Ranked by Reliability Score: the 20th percentile of each player's rating across 360 replicates "
                  "(match bootstrap × six pressure definitions). A high rank means the player stays good when the "
                  "sample and the definition of pressure change.")

    seasons = sorted(D.scoped(role).scope.loc[lambda s: s.str.isnumeric()].unique().tolist())
    with st.container(border=True):
        c = st.columns([1.2, 1, 1.4, 1.3, 0.9])
        comp = c[0].segmented_control("Competition", ["All", "IPL", "T20I"], default="All", key=f"{role}_comp") or "All"
        season = c[1].selectbox("Season", ["All"] + seasons, key=f"{role}_season")
        search = c[2].text_input("Search player or team", key=f"{role}_search", placeholder="e.g. Yadav")
        ev = c[3].multiselect("Evidence", ["Strong", "Moderate", "Uncertain"], key=f"{role}_ev")
        active = c[4].toggle("Active only", key=f"{role}_active", help="Played within the last 365 days of the data")

    scoped = comp != "All" or season != "All"
    if scoped:
        d = _scoped_view(role, comp, season, main)
        U.note(f"Scoped rating on the same scale as the overall rating, for {season if season != 'All' else comp} "
               "matches only (players with ≥ 4 pressure innings/spells). The official ranking is the overall one.")
        score_col, score_label = "rating", "Scoped rating"
    else:
        d = main.copy()
        d["view_rank"] = d.final_rank
        score_col, score_label = "reliability_score", "Reliability Score"
    if search:
        d = d[d.player.str.contains(search, case=False, na=False) | d.team.str.contains(search, case=False, na=False)]
    if ev:
        d = d[d.evidence.isin(ev)]
    if active:
        d = d[d.active.astype(bool)]
    if d.empty:
        U.empty("No players match these filters.")
        return

    if not scoped and not (search or ev or active):
        meta = (lambda r: f"{int(r.impact)}/{int(r.inn)} impact innings · SR {r.pressure_sr:.0f}") if is_bat else \
               (lambda r: f"{int(r.impact)}/{int(r.inn)} impact spells · econ {r.pressure_econ:.2f}")
        U.podium(d, score_col, score_label, meta)
        st.write("")

    U.section("Leaderboard", f"{len(d)} players")
    if is_bat:
        cols = {"view_rank": "Rank", "player": "Player", "team": "Team", "matches": "Matches", "inn": "Pressure inns",
                score_col: score_label, "rating": "Pressure rating",
                "normal_sr": "Baseline SR", "pressure_sr": "Pressure SR", "impact_rate": "Consistency",
                "evidence": "Reliability"}
    else:
        cols = {"view_rank": "Rank", "player": "Player", "team": "Team",
                "pressure_overs": "Pressure overs", "pressure_econ": "Pressure econ", "pk": "Pressure wkts",
                "normal_econ": "Baseline econ", score_col: score_label, "rating": "Pressure rating",
                "impact_rate": "Consistency", "evidence": "Reliability"}
    cols = {k: v for k, v in cols.items() if k in d.columns}
    show = d[list(dict.fromkeys(cols))].rename(columns=cols)
    show = show.loc[:, ~show.columns.duplicated()]
    cfg = {
        "Rank": st.column_config.NumberColumn(width=50, format="%d"),
        "Player": st.column_config.TextColumn(width=140), "Team": st.column_config.TextColumn(width=120),
        score_label: st.column_config.ProgressColumn(format="%.1f", min_value=30, max_value=float(max(90, d[score_col].max())),
                                                     help="Reliability Score = 20th percentile of 360 replicate ratings"
                                                     if not scoped else "Rating within the selected scope"),
        "Pressure rating": st.column_config.NumberColumn(format="%.1f", help="Full-data rating, 50 = average eligible player"),
        "Consistency": st.column_config.NumberColumn(format="%.2f", help="Shrunk share of pressure innings/spells "
                                                     "that were impact performances"),
        "Baseline SR": st.column_config.NumberColumn(format="%.1f"), "Pressure SR": st.column_config.NumberColumn(format="%.1f"),
        "Pressure econ": st.column_config.NumberColumn(format="%.2f"), "Baseline econ": st.column_config.NumberColumn(format="%.2f"),
        "Pressure overs": st.column_config.NumberColumn(format="%.1f"),
        "Pressure inns": st.column_config.NumberColumn(format="%d"), "Pressure balls": st.column_config.NumberColumn(format="%d"),
        "Pressure wkts": st.column_config.NumberColumn(format="%d"), "Matches": st.column_config.NumberColumn(format="%d"),
    }
    st.dataframe(show, hide_index=True, width="stretch", height=min(38 * len(show) + 40, 520), column_config=cfg)

    top = d.head(15)
    U.section("Normal vs high-pressure performance", "each player against his own baseline")
    c1, c2 = st.columns([1.25, 1])
    with c1:
        x0, x1, lab = ("normal_sr", "pressure_sr", "Strike rate") if is_bat else ("normal_econ", "pressure_econ", "Economy")
        tt = top.iloc[::-1]
        better = (tt[x1] >= tt[x0]) if is_bat else (tt[x1] <= tt[x0])
        fig = go.Figure()
        for _, r in tt.iterrows():
            fig.add_shape(type="line", x0=r[x0], x1=r[x1], y0=r.player, y1=r.player,
                          line=dict(color=C["border"], width=3))
        fig.add_scatter(x=tt[x0], y=tt.player, mode="markers", name="Baseline (non-pressure)",
                        marker=dict(color=C["muted"], size=9), hovertemplate="%{y}: baseline %{x:.2f}<extra></extra>")
        fig.add_scatter(x=tt[x1], y=tt.player, mode="markers", name="Under pressure",
                        marker=dict(color=np.where(better, C["pos"], C["neg"]), size=11, line=dict(color=C["bg"], width=1)),
                        hovertemplate="%{y}: under pressure %{x:.2f}<extra></extra>")
        fig.update_layout(xaxis_title=lab, yaxis_title=None)
        st.plotly_chart(style(fig, 470, f"{lab}: baseline → under pressure (green = better than own baseline)"),
                        width="stretch")
    with c2:
        logs = D.match_logs(role)
        ids = top.player_id.head(10).tolist()
        lg = logs[logs.player_id.isin(ids) & (logs.inn > 0)].copy()
        if lg.empty:
            U.empty("No pressure innings for these players.")
        else:
            lg["player"] = lg.player_id.map(D.names())
            lg["value"] = lg.pv
            order = top.player.head(10).tolist()
            fig = go.Figure()
            for p in order[::-1]:
                v = lg[lg.player == p]
                fig.add_box(x=v.value, name=p, orientation="h", marker_color=C["lime"] if is_bat else C["teal"],
                            boxpoints="all", jitter=0.4, pointpos=0, marker=dict(size=3, opacity=0.5),
                            line=dict(width=1.2), fillcolor="rgba(184,243,107,0.10)" if is_bat else "rgba(66,216,208,0.10)",
                            hovertemplate=f"{p}: %{{x:.1f}} runs vs average<extra></extra>")
            fig.add_vline(x=0, line=dict(color=C["faint"], dash="dot"))
            fig.update_layout(showlegend=False, xaxis_title="Runs above average in each pressure " +
                              ("innings" if is_bat else "spell"))
            st.plotly_chart(style(fig, 470, "Consistency across matches (top 10)"), width="stretch")

    if not is_bat:
        U.section("Wicket-taking and choking", "how bowlers create value under pressure")
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Scatter(
                x=d.pressure_dot_pct, y=d.pressure_balls_per_wkt if "pressure_balls_per_wkt" in d else d.pb / d.pk.clip(lower=1),
                mode="markers+text", text=np.where(d.view_rank <= 10, d.player.str.split().str[-1], ""),
                textposition="top center", textfont=dict(size=10, color=C["muted"]),
                marker=dict(size=np.clip(d.pb / 25, 6, 26), color=d[score_col], colorscale=[[0, "#2E5A7A"], [1, C["teal"]]],
                            line=dict(color=C["bg"], width=1), colorbar=dict(title=score_label[:11], thickness=10)),
                customdata=np.c_[d.player, d.pk, d.pressure_econ],
                hovertemplate="%{customdata[0]}<br>Dot %{x:.1f}% · %{y:.1f} balls/wkt<br>%{customdata[1]} wkts · "
                              "econ %{customdata[2]:.2f}<extra></extra>"))
            fig.update_layout(xaxis_title="Dot-ball % under pressure", yaxis=dict(title="Balls per wicket under pressure",
                                                                                  autorange="reversed"))
            st.plotly_chart(style(fig, 400, "Top-right = strikes often and chokes the scoring"), width="stretch")
        with c2:
            sp = D.splits()
            ids = d.player_id.head(8).tolist()
            s = sp[(sp.role == "bowl") & (sp.split == "Pressure category") & (sp.scope == "All") & sp.player_id.isin(ids)].copy()
            s["player"] = s.player_id.map(D.names())
            if s.empty:
                U.empty("No category data.")
            else:
                h = s.pivot_table(index="player", columns="split_value", values="economy").reindex(
                    columns=["Low", "Moderate", "High", "Extreme"]).reindex(d.player.head(8)).dropna(how="all")
                fig = go.Figure(go.Heatmap(z=h.values, x=h.columns, y=h.index, colorscale=[[0, C["pos"]], [0.5, "#1C2A3F"],
                                                                                           [1, C["neg"]]],
                                           zmid=8.5, text=np.round(h.values, 2), texttemplate="%{text}",
                                           hovertemplate="%{y} · %{x}: econ %{z:.2f}<extra></extra>",
                                           colorbar=dict(thickness=10)))
                fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(style(fig, 400, "Economy by pressure category"), width="stretch")
    else:
        U.section("Performance by pressure category", "strike rate as pressure rises")
        sp = D.splits()
        ids = d.player_id.head(8).tolist()
        s = sp[(sp.role == "bat") & (sp.split == "Pressure category") & (sp.scope == "All") & sp.player_id.isin(ids)].copy()
        s["player"] = s.player_id.map(D.names())
        if not s.empty:
            h = s.pivot_table(index="player", columns="split_value", values="strike_rate").reindex(
                columns=["Low", "Moderate", "High", "Extreme"]).reindex(d.player.head(8)).dropna(how="all")
            fig = go.Figure(go.Heatmap(z=h.values, x=h.columns, y=h.index,
                                       colorscale=[[0, C["neg"]], [0.5, "#1C2A3F"], [1, C["pos"]]], zmid=140,
                                       text=np.round(h.values, 0), texttemplate="%{text}",
                                       hovertemplate="%{y} · %{x}: SR %{z:.1f}<extra></extra>", colorbar=dict(thickness=10)))
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(style(fig, 360, "Strike rate by pressure category"), width="stretch")

    U.section("Compare players", "standardised rating components (0 = average eligible player)")
    pool = main[main.player_id.isin(d.player_id)] if not scoped else main[main.player_id.isin(d.player_id)]
    pool = pool if len(pool) else main
    default = pool.player.head(3).tolist()
    sel = st.multiselect("Choose up to 4 players", pool.player.tolist(), default=default, max_selections=4,
                         key=f"{role}_cmp")
    if sel:
        cmp_ = main[main.player.isin(sel)].set_index("player").reindex(sel)
        fig = go.Figure()
        palette = [C["lime"], C["teal"], C["warn"], "#A78BFA"]
        for i, p in enumerate(sel):
            fig.add_bar(y=list(COMPONENTS.values()), x=[cmp_.loc[p, f"z_{k}"] for k in COMPONENTS], name=p,
                        orientation="h", marker_color=palette[i],
                        hovertemplate=f"{p} · %{{y}}: %{{x:+.2f}} sd<extra></extra>")
        fig.add_vline(x=0, line=dict(color=C["faint"]))
        fig.update_layout(barmode="group", xaxis_title="Standardised (true-talent sd)", yaxis=dict(autorange="reversed"))
        c1, c2 = st.columns([1.3, 1])
        c1.plotly_chart(style(fig, 380), width="stretch")
        keep = (["final_rank", "reliability_score", "rating", "p_top10", "defs_top10", "inn", "impact", "pressure_sr",
                 "normal_sr", "pressure_value"] if is_bat else
                ["final_rank", "reliability_score", "rating", "p_top10", "defs_top10", "inn", "impact", "pk",
                 "pressure_econ", "normal_econ", "pressure_value"])
        lab = {"final_rank": "Rank", "reliability_score": "Reliability", "rating": "Rating", "p_top10": "P(top10)",
               "defs_top10": "Defs top-10", "inn": "Pressure inns", "impact": "Impact", "pressure_sr": "Pressure SR",
               "normal_sr": "Baseline SR", "pressure_value": "Value / 100 balls", "pk": "Wkts",
               "pressure_econ": "Pressure econ", "normal_econ": "Baseline econ"}
        c2.dataframe(cmp_[keep].rename(columns=lab).T.round(2), width="stretch")

    U.section("Player profile", "open any player in the Player Explorer")
    c1, c2 = st.columns([3, 1])
    pick = c1.selectbox("Player", d.player.tolist(), key=f"{role}_profile", label_visibility="collapsed")
    if c2.button("Open profile", type="primary", width="stretch", key=f"{role}_open"):
        U.open_profile(int(d.loc[d.player == pick, "player_id"].iloc[0]), role)
