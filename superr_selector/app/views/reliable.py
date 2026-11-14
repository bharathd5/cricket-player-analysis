import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui import components as U
from ui import data as D
from ui.theme import C, DEF_LABELS, EVIDENCE_COLORS, style

meta = D.guard(D.metrics)
bat = D.guard(D.rankings, "bat")
bowl = D.guard(D.rankings, "bowl")

U.page_header("Final selection", "Most Reliable Players Under Pressure",
              f"The submission lists. Each player's rating was recomputed {meta['replicates']} times — resampling the "
              "matches and switching between six definitions of pressure — and players are ordered by the 20th "
              "percentile of those ratings. A player only ranks high if he stays good in the bad draws too.")

c1, c2 = st.columns(2)
with c1:
    U.section("Top 10 batters", "Reliability Score")
    U.ranked_list(bat.head(10), "reliability_score", "team")
with c2:
    U.section("Top 10 bowlers", "Reliability Score")
    U.ranked_list(bowl.head(10), "reliability_score", "team")

with st.expander("Copy the ordered lists (for the Unstop dropdowns)"):
    txt = "TOP 10 BATTERS\n" + "\n".join(f"{int(r.final_rank)}. {r.player}" for r in bat.head(10).itertuples())
    txt += "\n\nTOP 10 BOWLERS\n" + "\n".join(f"{int(r.final_rank)}. {r.player}" for r in bowl.head(10).itertuples())
    st.code(txt, language=None)

role = st.segmented_control("Show evidence for", ["Batters", "Bowlers"], default="Batters", key="rel_role") or "Batters"
t = bat if role == "Batters" else bowl
r_key = "bat" if role == "Batters" else "bowl"
top = t.head(10)
reps = D.replicates(r_key)

U.section("Rating across replicates", "box = middle 50%, whiskers = 5th–95th percentile, ◆ = Reliability Score")
fig = go.Figure()
for _, r in top.iloc[::-1].iterrows():
    v = reps[str(r.player_id)]
    q = v.quantile([0.05, 0.25, 0.5, 0.75, 0.95]).to_numpy()
    fig.add_box(y=[r.player], q1=[q[1]], median=[q[2]], q3=[q[3]], lowerfence=[q[0]], upperfence=[q[4]],
                orientation="h", marker_color=C["lime"] if r_key == "bat" else C["teal"], showlegend=False,
                fillcolor="rgba(184,243,107,0.12)" if r_key == "bat" else "rgba(66,216,208,0.12)",
                hoverinfo="skip")
fig.add_scatter(x=top.reliability_score[::-1], y=top.player[::-1], mode="markers", name="Reliability Score",
                marker=dict(symbol="diamond", size=11, color=C["warn"], line=dict(color=C["bg"], width=1)),
                hovertemplate="%{y}: Reliability Score %{x:.1f}<extra></extra>")
fig.add_vline(x=50, line=dict(color=C["faint"], dash="dot"), annotation_text="average eligible player",
              annotation_font_color=C["muted"])
fig.update_layout(xaxis_title="Pressure rating (50 = average eligible, 10 = one sd)", yaxis_title=None)
st.plotly_chart(style(fig, 460), width="stretch")

c1, c2 = st.columns([1.15, 1])
with c1:
    U.section("Rank under each pressure definition", "full data; green = top 10")
    cols = [f"rank_{d}" for d in DEF_LABELS]
    h = top.set_index("player")[cols]
    h.columns = list(DEF_LABELS.values())
    z = np.where(h.values <= 10, 1, np.where(h.values <= 20, 0.5, 0))
    fig = go.Figure(go.Heatmap(z=z, x=h.columns, y=h.index, text=h.values.astype(int), texttemplate="%{text}",
                               colorscale=[[0, "#1A2638"], [0.5, "#2E5A7A"], [1, "#2F6B3A"]], showscale=False,
                               hovertemplate="%{y} · %{x}: rank %{text}<extra></extra>"))
    fig.update_layout(yaxis=dict(autorange="reversed"), xaxis=dict(side="top"))
    st.plotly_chart(style(fig, 420), width="stretch")
with c2:
    U.section("Probability of being top 10", "share of replicates")
    d = top.iloc[::-1]
    fig = go.Figure(go.Bar(x=d.p_top10, y=d.player, orientation="h",
                           marker_color=[EVIDENCE_COLORS[e] for e in d.evidence],
                           text=[f"{p:.0%} · {e}" for p, e in zip(d.p_top10, d.evidence)], textposition="outside",
                           hovertemplate="%{y}: %{x:.0%}<extra></extra>"))
    fig.update_layout(xaxis=dict(tickformat=".0%", range=[0, 1.15], title=None), yaxis_title=None)
    st.plotly_chart(style(fig, 420), width="stretch")

U.section("Consistency: the key ranking signal",
          "impact innings = ≥10 pressure runs at SR ≥156 · impact spell = econ ≤9.5 with a wicket or ≥40% dots")
d = top.iloc[::-1]
fig = go.Figure()
fig.add_bar(x=d.impact, y=d.player, orientation="h", name="Impact " + ("innings" if r_key == "bat" else "spells"),
            marker_color=C["pos"], hovertemplate="%{y}: %{x} impact<extra></extra>")
fig.add_bar(x=d.inn - d.impact, y=d.player, orientation="h", name="Other pressure " + ("innings" if r_key == "bat" else "spells"),
            marker_color="#2A3B52", hovertemplate="%{y}: %{x} other<extra></extra>")
for _, r in d.iterrows():
    fig.add_annotation(x=r.inn, y=r.player, text=f"  {r.impact_share_raw:.0%}", showarrow=False, xanchor="left",
                       font=dict(color=C["text"], size=11))
fig.update_layout(barmode="stack", xaxis_title="Pressure " + ("innings" if r_key == "bat" else "spells"),
                  yaxis_title=None)
st.plotly_chart(style(fig, 400), width="stretch")

with st.expander("How the Reliability Score is computed"):
    st.markdown(f"""
1. **Rating.** Six standardised components — impact rate (0.30), pressure value (0.25), uplift vs own baseline (0.15),
   value consistency (0.10), win probability added (0.10), volume (0.10) — combine into a rating where 50 is the average
   eligible player and 10 points is one standard deviation.
2. **Replicates.** {meta['replicates']} times: give every match a random Poisson(1) weight (some matches count twice,
   some not at all) and use one of the six pressure definitions in turn (consensus, leverage, Paper-1 resource,
   Paper-2 Lemmer, rule-based, equal weights). Recompute every rating.
3. **Reliability Score** = the 20th percentile of the {meta['replicates']} ratings: the level a player clears in four
   draws out of five.
4. **Evidence tag.** Strong: top-10 in ≥ 50% of replicates *and* under ≥ 4 of 6 definitions. Moderate: top-10 in ≥ 25%
   of replicates or under ≥ 3 definitions. Otherwise Uncertain.
""")
