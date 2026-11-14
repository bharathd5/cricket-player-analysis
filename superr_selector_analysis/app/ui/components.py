"""Reusable UI components: branding, headers, KPI cards, insights, podium, lists, filters."""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from ui.theme import C, EVIDENCE_COLORS


def brand() -> None:
    st.sidebar.markdown(
        "<div class='si-brand'><div class='t'>SUPERR <b>INTELLIGENCE</b></div>"
        "<div class='s'>CRICKET PERFORMANCE ANALYTICS</div></div>", unsafe_allow_html=True)


def page_header(eyebrow: str, title: str, sub: str = "") -> None:
    st.markdown(f"<div class='si-head'><div class='si-eyebrow'>{eyebrow}</div><div class='si-title'>{title}</div>"
                f"<div class='si-sub'>{sub}</div></div>", unsafe_allow_html=True)


def section(title: str, desc: str = "") -> None:
    st.markdown(f"<div class='si-section'><span class='h'>{title}</span><span class='d'>{desc}</span></div>",
                unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f"<div class='si-note'>{text}</div>", unsafe_allow_html=True)


def kpi(label: str, value: str, desc: str = "", color: str | None = None) -> str:
    color = color or C["lime"]
    return (f"<div class='si-kpi'><div class='bar' style='background:{color}'></div><div class='l'>{label}</div>"
            f"<div class='v'>{value}</div><div class='d'>{desc}</div></div>")


def kpi_row(items: list[tuple], cols: int | None = None) -> None:
    cs = st.columns(cols or len(items))
    for c, it in zip(cs, items):
        c.markdown(kpi(*it), unsafe_allow_html=True)


def insight(text: str) -> None:
    st.markdown(f"<div class='si-insight'>{text}</div>", unsafe_allow_html=True)


def empty(msg: str) -> None:
    st.markdown(f"<div class='si-empty'>{msg}</div>", unsafe_allow_html=True)


def pill(text: str, color: str | None = None) -> str:
    c = color or C["muted"]
    return f"<span class='si-pill' style='color:{c};border-color:{c}55'>{html.escape(str(text))}</span>"


def podium(df: pd.DataFrame, score_col: str, score_label: str, meta_fn) -> None:
    accents = [C["lime"], C["teal"], "#CBD5E1"]
    cols = st.columns(3)
    for i, (c, (_, r)) in enumerate(zip(cols, df.head(3).iterrows())):
        c.markdown(
            f"<div class='si-podium' style='border-top:2px solid {accents[i]}'>"
            f"<div class='rk'>RANK {i + 1}</div><div class='nm'>{html.escape(r.player)}</div>"
            f"<div class='tm'>{html.escape(str(r.team))}</div>"
            f"<div class='sc' style='color:{accents[i]}'>{r[score_col]:.1f}</div>"
            f"<div class='mt'>{score_label} · {meta_fn(r)}</div>"
            f"<div style='margin-top:8px'>{pill(r.evidence + ' evidence', EVIDENCE_COLORS.get(r.evidence))}</div>"
            f"</div>", unsafe_allow_html=True)


def ranked_list(df: pd.DataFrame, score_col: str, sub_col: str | None = None, fmt: str = "{:.1f}") -> None:
    rows = "".join(
        f"<div class='si-row'><div class='r'>{int(r.final_rank)}</div>"
        f"<div class='n'>{html.escape(r.player)}<span>{html.escape(str(r[sub_col])) if sub_col else ''}</span></div>"
        f"<div class='s'>{fmt.format(r[score_col])}</div></div>" for _, r in df.iterrows())
    st.markdown(f"<div class='si-list'>{rows}</div>", unsafe_allow_html=True)


def scope_filters(key: str, seasons: list[str], show_season: bool = True) -> tuple[str, str]:
    c1, c2 = st.columns([1, 1])
    comp = c1.segmented_control("Competition", ["All", "IPL", "T20I"], default="All", key=f"{key}_comp")
    season = "All"
    if show_season:
        season = c2.selectbox("Season", ["All"] + seasons, key=f"{key}_season")
    return comp or "All", season


def open_profile(player_id: int, role: str) -> None:
    st.session_state["explorer_player"] = int(player_id)
    st.session_state["explorer_role"] = role
    st.switch_page("views/explorer.py")
