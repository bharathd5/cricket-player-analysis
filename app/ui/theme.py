"""Design system: colours, CSS and the Plotly chart template."""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

C = {
    "bg": "#0B1220", "bg2": "#101B2D", "card": "#111F32", "lime": "#B8F36B", "teal": "#42D8D0",
    "pos": "#35D6A1", "warn": "#F5B942", "neg": "#F16C75", "text": "#F1F5F9", "muted": "#94A3B8",
    "border": "#26364B", "grid": "#1C2A3F", "faint": "#475569",
}
CATEGORY_COLORS = {"Low": "#2E5A7A", "Moderate": "#42D8D0", "High": "#F5B942", "Extreme": "#F16C75"}
COMP_COLORS = {"IPL": "#B8F36B", "T20I": "#42D8D0", "A-team T20": "#94A3B8"}
EVIDENCE_COLORS = {"Strong": "#35D6A1", "Moderate": "#F5B942", "Uncertain": "#94A3B8"}
DEF_LABELS = {"consensus": "Consensus", "leverage": "Leverage", "resource_p1": "Resource (P1)",
              "lemmer_p2": "Lemmer (P2)", "rule_based": "Rule-based", "equal_weights": "Equal weights"}
FONT = "Inter, Manrope, -apple-system, Segoe UI, sans-serif"

_template = go.layout.Template(
    layout=dict(
        font=dict(family=FONT, color=C["text"], size=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=[C["lime"], C["teal"], C["warn"], C["neg"], "#A78BFA", "#60A5FA", C["muted"]],
        xaxis=dict(gridcolor=C["grid"], zerolinecolor=C["border"], linecolor=C["border"],
                   tickfont=dict(color=C["muted"], size=11), title=dict(font=dict(color=C["muted"], size=12))),
        yaxis=dict(gridcolor=C["grid"], zerolinecolor=C["border"], linecolor=C["border"],
                   tickfont=dict(color=C["muted"], size=11), title=dict(font=dict(color=C["muted"], size=12))),
        legend=dict(font=dict(color=C["muted"], size=11), bgcolor="rgba(0,0,0,0)", orientation="h",
                    yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor=C["bg2"], bordercolor=C["border"], font=dict(family=FONT, color=C["text"], size=12)),
        margin=dict(l=10, r=10, t=36, b=10),
        title=dict(font=dict(size=14, color=C["text"]), x=0, xanchor="left"),
        coloraxis=dict(colorbar=dict(tickfont=dict(color=C["muted"]), outlinewidth=0)),
    )
)
pio.templates["superr"] = _template
pio.templates.default = "superr"


def style(fig: go.Figure, height: int = 360, title: str | None = None) -> go.Figure:
    """Apply the house template. With a title, the legend sits on its own line under it."""
    fig.update_layout(height=height, template="superr")
    has_legend = any(getattr(t, "showlegend", None) is not False for t in fig.data) and len(fig.data) > 1
    if title:
        fig.update_layout(title=dict(text=title, y=0.99, yref="container", yanchor="top", x=0, xref="container",
                                     pad=dict(l=8, t=4)),
                          margin=dict(t=70 if has_legend else 44))
        if has_legend:
            fig.update_layout(legend=dict(y=1.0, yref="paper", yanchor="bottom"))
    return fig


def inject_css() -> None:
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, button, input, textarea, select {{ font-family: {FONT}; }}
.stApp {{ background: {C['bg']}; }}
.block-container {{ padding-top: 2.6rem; padding-bottom: 3rem; max-width: 1480px; }}
section[data-testid="stSidebar"] {{ background: {C['bg2']}; border-right: 1px solid {C['border']}; }}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"] {{ border-radius: 8px; margin: 1px 0; }}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"] {{
  background: rgba(184,243,107,0.10); box-shadow: inset 3px 0 0 {C['lime']}; }}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"] span {{ color: {C['lime']} !important; }}
[data-testid="stSidebarNavSeparator"] {{ border-color: {C['border']}; }}
h1, h2, h3, h4 {{ color: {C['text']}; letter-spacing: -0.01em; }}
p, li {{ color: #CBD5E1; }}
hr {{ border-color: {C['border']}; }}
.si-brand {{ padding: 4px 4px 14px 4px; border-bottom: 1px solid {C['border']}; margin-bottom: 8px; }}
.si-brand .t {{ font-weight: 800; font-size: 1.02rem; letter-spacing: 0.08em; color: {C['text']}; }}
.si-brand .t b {{ color: {C['lime']}; }}
.si-brand .s {{ font-size: 0.66rem; letter-spacing: 0.16em; color: {C['muted']}; margin-top: 2px; }}
.si-head {{ margin-bottom: 1.1rem; }}
.si-eyebrow {{ font-size: 0.72rem; letter-spacing: 0.16em; text-transform: uppercase; color: {C['lime']}; font-weight: 600; }}
.si-title {{ font-size: 1.85rem; font-weight: 750; color: {C['text']}; margin: 2px 0 4px 0; line-height: 1.2; }}
.si-sub {{ color: {C['muted']}; font-size: 0.95rem; max-width: 900px; }}
.si-section {{ display: flex; align-items: baseline; gap: 10px; margin: 1.6rem 0 0.6rem 0;
  padding-bottom: 6px; border-bottom: 1px solid {C['border']}; }}
.si-section .h {{ font-size: 0.8rem; letter-spacing: 0.14em; text-transform: uppercase; font-weight: 700; color: {C['text']}; }}
.si-section .d {{ font-size: 0.82rem; color: {C['muted']}; }}
.si-kpi {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 14px; padding: 14px 16px 12px 16px;
  height: 100%; transition: border-color .15s ease, transform .15s ease; }}
.si-kpi:hover {{ border-color: #3A4F6B; transform: translateY(-1px); }}
.si-kpi .l {{ font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase; color: {C['muted']}; font-weight: 600;
  display: flex; align-items: center; gap: 6px; }}
.si-kpi .v {{ font-size: 1.75rem; font-weight: 750; color: {C['text']}; margin-top: 4px; line-height: 1.1; font-variant-numeric: tabular-nums; }}
.si-kpi .d {{ font-size: 0.78rem; color: {C['muted']}; margin-top: 4px; }}
.si-kpi .bar {{ width: 26px; height: 3px; border-radius: 2px; margin-bottom: 8px; }}
.si-card {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 14px; padding: 16px 18px; }}
.si-insight {{ background: {C['card']}; border: 1px solid {C['border']}; border-left: 3px solid {C['lime']};
  border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; color: #CBD5E1; font-size: 0.9rem; }}
.si-insight b {{ color: {C['text']}; }}
.si-podium {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 14px; padding: 14px 16px; height: 100%; }}
.si-podium .rk {{ font-size: 0.72rem; letter-spacing: 0.14em; color: {C['muted']}; font-weight: 700; }}
.si-podium .nm {{ font-size: 1.15rem; font-weight: 700; color: {C['text']}; margin-top: 2px; }}
.si-podium .tm {{ font-size: 0.8rem; color: {C['muted']}; }}
.si-podium .sc {{ font-size: 1.6rem; font-weight: 750; margin-top: 8px; font-variant-numeric: tabular-nums; }}
.si-podium .mt {{ font-size: 0.78rem; color: {C['muted']}; margin-top: 2px; }}
.si-pill {{ display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 0.72rem; font-weight: 600;
  border: 1px solid {C['border']}; color: {C['muted']}; margin-right: 6px; }}
.si-profile {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 16px; padding: 18px 20px; }}
.si-profile .nm {{ font-size: 1.6rem; font-weight: 750; color: {C['text']}; }}
.si-profile .meta {{ color: {C['muted']}; font-size: 0.88rem; margin-top: 4px; }}
.si-empty {{ border: 1px dashed {C['border']}; border-radius: 12px; padding: 26px; text-align: center; color: {C['muted']}; }}
.si-note {{ color: {C['muted']}; font-size: 0.8rem; margin-top: -4px; margin-bottom: 8px; }}
.si-list {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 14px; padding: 6px 4px; }}
.si-row {{ display: grid; grid-template-columns: 34px 1fr auto; align-items: center; padding: 8px 12px;
  border-bottom: 1px solid {C['grid']}; }}
.si-row:last-child {{ border-bottom: none; }}
.si-row .r {{ color: {C['muted']}; font-weight: 700; font-variant-numeric: tabular-nums; }}
.si-row .n {{ color: {C['text']}; font-weight: 600; }}
.si-row .n span {{ color: {C['muted']}; font-weight: 400; font-size: 0.8rem; margin-left: 6px; }}
.si-row .s {{ color: {C['lime']}; font-weight: 700; font-variant-numeric: tabular-nums; }}
div[data-testid="stMetric"] {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 12px; padding: 10px 14px; }}
div[data-testid="stExpander"] details {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 12px; }}
div[data-testid="stDataFrame"] {{ border: 1px solid {C['border']}; border-radius: 12px; overflow: hidden; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {C['border']}; }}
.stTabs [data-baseweb="tab"] {{ height: 40px; padding: 0 14px; color: {C['muted']}; }}
.stTabs [aria-selected="true"] {{ color: {C['lime']} !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {C['lime']}; }}
[data-baseweb="tag"], span[data-tag] {{ background-color: #1B3020 !important; border: 1px solid rgba(184,243,107,0.45) !important; }}
[data-baseweb="tag"] *, span[data-tag] * {{ color: {C['lime']} !important; fill: {C['lime']} !important; }}
button[kind="primary"], button[kind="primary"] * {{ color: #0B1220 !important; font-weight: 700; }}
.katex {{ color: {C['text']}; }}
#MainMenu, footer {{ visibility: hidden; }}
[data-testid="stSidebarHeader"] img {{ height: 44px !important; max-width: 100%; }}
[data-testid="stSidebarHeader"] {{ padding-bottom: 10px; margin-bottom: 6px; border-bottom: 1px solid {C['border']}; }}
</style>""", unsafe_allow_html=True)
