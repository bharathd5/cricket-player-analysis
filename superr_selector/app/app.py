"""SUPERR INTELLIGENCE - Pressure Performance Analytics Platform.

Run from the project folder:   streamlit run app/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

st.set_page_config(page_title="SupeRR Intelligence", page_icon=":material/sports_cricket:", layout="wide",
                   initial_sidebar_state="expanded")

from ui.theme import inject_css  # noqa: E402

inject_css()
st.logo(str(APP_DIR / "assets" / "logo.svg"), size="large")

V = APP_DIR / "views"
pages = {
    "Analytics": [
        st.Page(V / "overview.py", title="Overview", icon=":material/space_dashboard:", default=True),
        st.Page(V / "pressure.py", title="Pressure Analysis", icon=":material/speed:"),
    ],
    "Rankings": [
        st.Page(V / "reliable.py", title="Most Reliable Players", icon=":material/workspace_premium:"),
        st.Page(V / "batters.py", title="Batter Rankings", icon=":material/sports_cricket:"),
        st.Page(V / "bowlers.py", title="Bowler Rankings", icon=":material/sports_baseball:"),
    ],
    "Explore": [
        st.Page(V / "explorer.py", title="Player Explorer", icon=":material/person_search:"),
        st.Page(V / "lab.py", title="Performance Lab", icon=":material/science:"),
    ],
    "Evidence": [
        st.Page(V / "reliability.py", title="Model Reliability", icon=":material/verified:"),
        st.Page(V / "methodology.py", title="Methodology", icon=":material/menu_book:"),
    ],
}
nav = st.navigation(pages, position="sidebar")
st.sidebar.markdown(
    "<div style='margin-top:18px;font-size:0.72rem;color:#64748B;line-height:1.5'>"
    "IPL &amp; T20I · 2022–2026<br>Consensus pressure index · seed 42</div>", unsafe_allow_html=True)
nav.run()
