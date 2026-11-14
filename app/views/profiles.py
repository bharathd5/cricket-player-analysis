import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui import components as U
from ui import data as D
from ui.theme import C, COMP_COLORS, EVIDENCE_COLORS, style

U.page_header("Player Profiles", "Complete player profiles",
              "Every match, every ball — batting and bowling careers across IPL and T20Is in the data, by season, "
              "competition, phase and opponent. For performance under pressure open the Player Explorer.")

info = D.guard(D.career, "player_info")
cb = D.guard(D.career, "career_bat")
cw = D.guard(D.career, "career_bowl")
cp = D.guard(D.career, "career_phase")

# players ordered by involvement (runs + 20 x wickets)
vol = (cb.groupby("player_id").runs.sum().reindex(info.player_id).fillna(0)
       + 20 * cw.groupby("player_id").wkts.sum().reindex(info.player_id).fillna(0))
order = vol.sort_values(ascending=False).index.tolist()
names = info.set_index("player_id").player_name.fillna("Unknown")
want = st.session_state.get("explorer_player")
idx = order.index(want) if want in order else 0
pid = st.selectbox("Search player", order, index=idx, format_func=lambda p: names.get(p, str(p)), key="prof_pick")
st.session_state["explorer_player"] = int(pid)

me = info.set_index("player_id").loc[pid]
bat = cb[cb.player_id == pid].sort_values("match_date")
bowl = cw[cw.player_id == pid].sort_values("match_date")
runs, balls = int(bat.runs.sum()), int(bat.balls.sum())
wk, bb = int(bowl.wkts.sum()), int(bowl.balls.sum())
if bb >= 120 and balls >= 200 and wk >= 10 and runs >= 300:
    role_label = "All-rounder"
elif bb > balls:
    role_label = "Bowler"
else:
    role_label = "Batter"

# selection / ranking status
pills = U.pill(role_label, C["teal"])
for rl, lab in (("bat", "Batting"), ("bowl", "Bowling")):
    rk = D.rankings(rl, True)
    r = rk[rk.player_id == pid]
    if not r.empty:
        r = r.iloc[0]
        if r.selectable:
            pills += U.pill(f"{lab} pressure rank {int(r.final_rank)} · {r.evidence}", EVIDENCE_COLORS.get(r.evidence))
        else:
            pills += U.pill(f"{lab}: rated, not ranked ({r.excluded_reason})", C["warn"])
ex = D.exclusions("bat").combine_first(D.exclusions("bowl"))
if pid in ex.index and "not ranked" not in pills and ex[pid] not in pills:
    pills += U.pill(ex[pid], C["warn"])
first = pd.to_datetime(me.first_match)
last = pd.to_datetime(me.last_match)
meta_bits = [b_ for b_ in [
    f"{int(me.matches)} matches" if pd.notna(me.matches) else None,
    f"{first:%b %Y} – {last:%b %Y}" if pd.notna(first) else None,
    me.batting_hand if isinstance(me.batting_hand, str) else None,
    me.bowling_style if isinstance(me.bowling_style, str) else None,
    f"usually bats at {int(me.usual_position)}" if pd.notna(me.usual_position) else None,
    f"captain in {int(me.captain_matches)} matches" if pd.notna(me.captain_matches) and me.captain_matches > 0 else None,
] if b_]
st.markdown(
    f"<div class='si-profile'><div class='nm'>{html.escape(names.get(pid, ''))}</div>"
    f"<div class='meta'>{html.escape(' · '.join(meta_bits))}</div>"
    f"<div class='meta'>{html.escape(str(me.teams) if isinstance(me.teams, str) else '')}"
    f"{' · ' + html.escape(me.competitions) if isinstance(me.competitions, str) else ''}</div>"
    f"<div style='margin-top:10px'>{pills}</div></div>", unsafe_allow_html=True)
c1, c2 = st.columns([1, 5])
if c1.button("Pressure profile →", key="prof_to_exp"):
    st.session_state["explorer_role"] = "bowl" if role_label == "Bowler" else "bat"
    st.switch_page("views/explorer.py")
st.write("")

tabs = st.tabs(["Batting", "Bowling", "Season by season", "Competitions & opponents", "Recent matches"])


def bat_summary(d: pd.DataFrame) -> dict:
    inns, outs = len(d), int(d.out.sum())
    r, bl = int(d.runs.sum()), int(d.balls.sum())
    hs = d.loc[d.runs.idxmax()] if inns else None
    return {"Inns": inns, "Runs": r, "Avg": r / outs if outs else np.nan, "SR": r * 100 / bl if bl else np.nan,
            "HS": f"{int(hs.runs)}{'' if hs.out else '*'}" if hs is not None else "–",
            "50s": int(((d.runs >= 50) & (d.runs < 100)).sum()), "100s": int((d.runs >= 100).sum()),
            "4s": int(d.fours.sum()), "6s": int(d.sixes.sum()), "Not out": inns - outs,
            "Dot %": d.dots.sum() * 100 / bl if bl else np.nan}


def bowl_summary(d: pd.DataFrame) -> dict:
    b_, r, w = int(d.balls.sum()), int(d.runs.sum()), int(d.wkts.sum())
    best = d.sort_values(["wkts", "runs"], ascending=[False, True]).iloc[0] if len(d) else None
    return {"Inns": len(d), "Overs": f"{b_ // 6}.{b_ % 6}", "Wkts": w, "Econ": r * 6 / b_ if b_ else np.nan,
            "Avg": r / w if w else np.nan, "SR": b_ / w if w else np.nan,
            "Best": f"{int(best.wkts)}/{int(best.runs)}" if best is not None else "–",
            "3w+": int((d.wkts >= 3).sum()), "Maidens": int(d.maidens.sum()),
            "Dot %": d.dots.sum() * 100 / b_ if b_ else np.nan}


def fmt(v, nd=2):
    if isinstance(v, str):
        return v
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    return f"{v:,.{nd}f}" if isinstance(v, float) else f"{v:,}"


with tabs[0]:
    if bat.empty:
        U.empty("No batting innings recorded.")
    else:
        s = bat_summary(bat)
        U.kpi_row([("Innings", fmt(s["Inns"]), f"{s['Not out']} not out", C["teal"]),
                   ("Runs", fmt(s["Runs"]), f"HS {s['HS']}", C["lime"]),
                   ("Average", fmt(s["Avg"]), "runs per dismissal", C["teal"]),
                   ("Strike rate", fmt(s["SR"], 1), f"dot balls {fmt(s['Dot %'], 1)}%", C["lime"]),
                   ("50s / 100s", f"{s['50s']} / {s['100s']}", f"{s['4s']} fours · {s['6s']} sixes", C["warn"])])
        st.write("")
        c1, c2 = st.columns([1.4, 1])
        with c1:
            fig = go.Figure(go.Scatter(
                x=bat.match_date, y=bat.runs, mode="markers",
                marker=dict(size=np.clip(bat.balls / 2.5, 5, 22), color=[COMP_COLORS.get(c, C["muted"]) for c in bat.comp_type],
                            line=dict(color=C["bg"], width=1),
                            symbol=np.where(bat.out, "circle", "circle-open")),
                customdata=np.c_[bat.opponent, bat.balls, bat.comp_name, np.where(bat.out, "", "*")],
                hovertemplate="%{x|%d %b %Y} vs %{customdata[0]}<br>%{y}%{customdata[3]} (%{customdata[1]} balls)"
                              "<br>%{customdata[2]}<extra></extra>"))
            fig.add_scatter(x=bat.match_date, y=bat.runs.rolling(10, min_periods=3).mean(), mode="lines",
                            line=dict(color=C["warn"], width=2), name="10-innings average", hoverinfo="skip")
            fig.update_layout(showlegend=False, yaxis_title="Runs", xaxis_title=None)
            st.plotly_chart(style(fig, 330, "Every innings (size = balls faced, open = not out; line = 10-innings avg)"),
                            width="stretch")
        with c2:
            ph = cp[(cp.player_id == pid) & (cp.role == "bat")].set_index("phase").reindex(["Powerplay", "Middle", "Death"])
            ph = ph.dropna(subset=["balls"])
            if not ph.empty:
                sr = ph.runs * 100 / ph.balls
                fig = go.Figure(go.Bar(x=ph.index, y=sr, marker_color=[C["teal"], C["lime"], C["warn"]][:len(ph)],
                                       text=[f"SR {v:.0f}<br>{int(b_)} balls<br>avg {r_ / max(o, 1):.1f}"
                                             for v, b_, r_, o in zip(sr, ph.balls, ph.runs, ph.outs)],
                                       textposition="outside"))
                fig.update_layout(yaxis=dict(title="Strike rate", range=[0, sr.max() * 1.45]))
                st.plotly_chart(style(fig, 330, "By phase of the innings"), width="stretch")
        c1, c2 = st.columns(2)
        with c1:
            pos = bat.position.dropna().astype(int).value_counts().sort_index()
            fig = go.Figure(go.Bar(x=pos.index.astype(str), y=pos.values, marker_color=C["teal"],
                                   hovertemplate="No. %{x}: %{y} innings<extra></extra>"))
            fig.update_layout(xaxis_title="Batting position", yaxis_title="Innings")
            st.plotly_chart(style(fig, 280, "Where he bats"), width="stretch")
        with c2:
            dis = bat.dismissal.value_counts()
            if dis.empty:
                U.empty("Never dismissed.")
            else:
                fig = go.Figure(go.Bar(x=dis.values, y=dis.index, orientation="h", marker_color=C["neg"]))
                fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Dismissals")
                st.plotly_chart(style(fig, 280, "How he gets out"), width="stretch")

with tabs[1]:
    if bowl.empty:
        U.empty("Has not bowled in the data.")
    else:
        s = bowl_summary(bowl)
        U.kpi_row([("Innings", fmt(s["Inns"]), f"{s['Overs']} overs", C["teal"]),
                   ("Wickets", fmt(s["Wkts"]), f"best {s['Best']} · {s['3w+']} three-fors", C["lime"]),
                   ("Economy", fmt(s["Econ"]), f"dot balls {fmt(s['Dot %'], 1)}%", C["teal"]),
                   ("Average", fmt(s["Avg"]), "runs per wicket", C["lime"]),
                   ("Strike rate", fmt(s["SR"], 1), f"balls per wicket · {s['Maidens']} maidens", C["warn"])])
        st.write("")
        c1, c2 = st.columns([1.4, 1])
        with c1:
            econ = bowl.runs * 6 / bowl.balls.clip(lower=1)
            fig = go.Figure(go.Scatter(
                x=bowl.match_date, y=econ, mode="markers",
                marker=dict(size=6 + bowl.wkts * 4, color=[COMP_COLORS.get(c, C["muted"]) for c in bowl.comp_type],
                            line=dict(color=C["bg"], width=1)),
                customdata=np.c_[bowl.opponent, bowl.wkts, bowl.runs, bowl.balls // 6, bowl.balls % 6],
                hovertemplate="%{x|%d %b %Y} vs %{customdata[0]}<br>%{customdata[1]}/%{customdata[2]} in "
                              "%{customdata[3]}.%{customdata[4]} overs<extra></extra>"))
            fig.add_scatter(x=bowl.match_date, y=econ.rolling(10, min_periods=3).mean(), mode="lines",
                            line=dict(color=C["warn"], width=2), hoverinfo="skip")
            fig.update_layout(showlegend=False, yaxis_title="Economy", xaxis_title=None)
            st.plotly_chart(style(fig, 330, "Every spell (size = wickets; line = 10-spell avg economy)"), width="stretch")
        with c2:
            ph = cp[(cp.player_id == pid) & (cp.role == "bowl")].set_index("phase").reindex(["Powerplay", "Middle", "Death"])
            ph = ph.dropna(subset=["balls"])
            if not ph.empty:
                ec = ph.runs * 6 / ph.balls
                fig = go.Figure(go.Bar(x=ph.index, y=ec, marker_color=[C["teal"], C["lime"], C["warn"]][:len(ph)],
                                       text=[f"econ {v:.2f}<br>{b_ / 6:.0f} overs<br>{int(w)} wkts"
                                             for v, b_, w in zip(ec, ph.balls, ph.outs)], textposition="outside"))
                fig.update_layout(yaxis=dict(title="Economy", range=[0, ec.max() * 1.45]))
                st.plotly_chart(style(fig, 330, "By phase of the innings"), width="stretch")
        dis = D.dismissals()
        dd = dis[(dis.player_id == pid) & (dis.role == "bowl")].groupby("dismissal_type").n.sum().sort_values()
        if len(dd):
            fig = go.Figure(go.Bar(x=dd.values, y=dd.index, orientation="h", marker_color=C["pos"]))
            fig.update_layout(xaxis_title="Wickets")
            st.plotly_chart(style(fig, 240, "How he takes wickets"), width="stretch")

with tabs[2]:
    rows = []
    for yr in sorted(set(bat.season_year) | set(bowl.season_year)):
        sb, sw = bat[bat.season_year == yr], bowl[bowl.season_year == yr]
        r = {"Season": str(yr), "Matches": len(set(sb.match_id) | set(sw.match_id))}
        if len(sb):
            x = bat_summary(sb)
            r.update({"Runs": x["Runs"], "Bat avg": x["Avg"], "Bat SR": x["SR"], "50s": x["50s"] + x["100s"]})
        if len(sw):
            y = bowl_summary(sw)
            r.update({"Wkts": y["Wkts"], "Econ": y["Econ"], "Bowl avg": y["Avg"]})
        rows.append(r)
    ss = pd.DataFrame(rows)
    if ss.empty:
        U.empty("No seasons.")
    else:
        fig = go.Figure()
        if "Runs" in ss:
            fig.add_bar(x=ss.Season, y=ss.Runs, name="Runs", marker_color=C["lime"])
        if "Wkts" in ss:
            fig.add_scatter(x=ss.Season, y=ss.Wkts, name="Wickets", yaxis="y2", mode="lines+markers",
                            line=dict(color=C["teal"], width=2.5))
        fig.update_layout(yaxis=dict(title="Runs"), yaxis2=dict(title="Wickets", overlaying="y", side="right",
                                                                 showgrid=False), xaxis=dict(type="category"))
        st.plotly_chart(style(fig, 320, "Season by season"), width="stretch")
        st.dataframe(ss, hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="%.2f") for c in
                                    ["Bat avg", "Bat SR", "Econ", "Bowl avg"]})

with tabs[3]:
    c1, c2 = st.columns(2)
    with c1:
        U.section("By competition")
        rows = []
        for comp in sorted(set(bat.comp_type) | set(bowl.comp_type)):
            sb, sw = bat[bat.comp_type == comp], bowl[bowl.comp_type == comp]
            r = {"Competition": comp, "Matches": len(set(sb.match_id) | set(sw.match_id))}
            if len(sb):
                x = bat_summary(sb)
                r.update({"Runs": x["Runs"], "Bat avg": x["Avg"], "Bat SR": x["SR"]})
            if len(sw):
                y = bowl_summary(sw)
                r.update({"Wkts": y["Wkts"], "Econ": y["Econ"]})
            rows.append(r)
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="%.2f") for c in ["Bat avg", "Bat SR", "Econ"]})
        U.section("By match type")
        rows = []
        for lab, mb, mw in (("Knockout", bat.is_knockout, bowl.is_knockout), ("Other", ~bat.is_knockout, ~bowl.is_knockout),
                            ("Team won", bat.won.astype(bool), bowl.won.astype(bool)),
                            ("Team lost", ~bat.won.astype(bool), ~bowl.won.astype(bool))):
            sb, sw = bat[mb], bowl[mw]
            r = {"Matches": lab}
            if len(sb):
                x = bat_summary(sb)
                r.update({"Bat inns": x["Inns"], "Runs": x["Runs"], "Bat SR": x["SR"]})
            if len(sw):
                y = bowl_summary(sw)
                r.update({"Wkts": y["Wkts"], "Econ": y["Econ"]})
            rows.append(r)
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="%.2f") for c in ["Bat SR", "Econ"]})
    with c2:
        U.section("By opponent", "most-played opponents")
        ob = bat.groupby("opponent").agg(inns=("runs", "size"), runs=("runs", "sum"), balls=("balls", "sum"),
                                         outs=("out", "sum"))
        ow = bowl.groupby("opponent").agg(spells=("wkts", "size"), wkts=("wkts", "sum"), conc=("runs", "sum"),
                                          bb=("balls", "sum"))
        op = ob.join(ow, how="outer")
        op["matches"] = op.inns.fillna(0) + op.spells.fillna(0)
        op = op.sort_values("matches", ascending=False).head(12)
        out = pd.DataFrame({"Opponent": op.index, "Runs": op.runs, "Bat SR": op.runs * 100 / op.balls,
                            "Bat avg": op.runs / op.outs.replace(0, np.nan), "Wkts": op.wkts,
                            "Econ": op.conc * 6 / op.bb})
        st.dataframe(out, hide_index=True, width="stretch", height=460,
                     column_config={c: st.column_config.NumberColumn(format="%.2f") for c in ["Bat SR", "Bat avg", "Econ"]})

with tabs[4]:
    m = pd.concat([
        bat.assign(Batting=[f"{int(r)}{'' if o else '*'} ({int(b_)})" for r, o, b_ in zip(bat.runs, bat.out, bat.balls)])
        [["match_id", "match_date", "opponent", "comp_name", "stage", "Batting", "won"]],
        bowl.assign(Bowling=[f"{int(w)}/{int(r)} ({b_ // 6}.{b_ % 6})" for w, r, b_ in zip(bowl.wkts, bowl.runs, bowl.balls)])
        [["match_id", "match_date", "opponent", "comp_name", "stage", "Bowling", "won"]]])
    if m.empty:
        U.empty("No matches.")
    else:
        m = (m.groupby("match_id").agg(Date=("match_date", "first"), Opponent=("opponent", "first"),
                                       Competition=("comp_name", "first"), Stage=("stage", "first"),
                                       Batting=("Batting", "first"), Bowling=("Bowling", "first"),
                                       Result=("won", lambda s: "Won" if bool(s.iloc[0]) else "Lost"))
             .sort_values("Date", ascending=False).head(15))
        m["Date"] = pd.to_datetime(m.Date).dt.strftime("%d %b %Y")
        st.dataframe(m.fillna("–"), hide_index=True, width="stretch", height=560)
        U.note("Batting shown as runs (balls), * = not out; bowling as wickets/runs (overs).")
