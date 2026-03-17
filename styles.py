import streamlit as st

NAVY = "#0d2137"
ACCENT = "#2563eb"
ACCENT_LIGHT = "#dbeafe"
BG = "#f1f5f9"


def apply_styles():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800&display=swap');

    /* ── Global ── */
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }}
    .stApp {{ background-color: {BG} !important; }}

    /* ── Hide Streamlit chrome ── */
    #MainMenu, footer, [data-testid="stDecoration"],
    [data-testid="stAppDeployButton"],
    [data-testid="stToolbarActions"] {{
        display: none !important;
    }}
    /* Make header transparent but keep it in the DOM so the toolbar works */
    [data-testid="stHeader"] {{
        background: transparent !important;
        box-shadow: none !important;
    }}
    /* Keep the toolbar visible but transparent — it holds the expand button */
    [data-testid="stToolbar"] {{
        background: transparent !important;
    }}
    /* Style the expand-sidebar button so it's visible on the light bg */
    [data-testid="stExpandSidebarButton"] {{
        background: {NAVY} !important;
        border-radius: 8px !important;
        padding: 4px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25) !important;
    }}
    [data-testid="stExpandSidebarButton"] svg {{
        fill: white !important;
        color: white !important;
    }}

    /* ── Sidebar shell ── */
    [data-testid="stSidebar"] {{
        background-color: {NAVY} !important;
        min-width: 220px !important;
        max-width: 220px !important;
    }}
    [data-testid="stSidebar"] > div:first-child {{
        background-color: {NAVY} !important;
    }}
    [data-testid="stSidebarContent"] {{
        background-color: {NAVY} !important;
        padding: 0 !important;
    }}

    /* ── Sidebar text colours ── */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown {{
        color: rgba(255,255,255,0.55) !important;
    }}

    /* ── Sidebar nav radio: hide label title ── */
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {{
        display: none !important;
    }}

    /* ── Sidebar radio: style options as nav items ── */
    [data-testid="stSidebar"] div[role="radiogroup"] {{
        gap: 2px !important;
        padding: 0 10px !important;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label {{
        padding: 10px 14px !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        color: rgba(255,255,255,0.62) !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        transition: background 0.15s, color 0.15s !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background: rgba(255,255,255,0.07) !important;
        color: white !important;
    }}
    /* Active nav item via :has */
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
        background: rgba(37,99,235,0.22) !important;
        color: #93c5fd !important;
        font-weight: 600 !important;
    }}
    /* Hide the actual radio circle */
    [data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"] {{
        display: none !important;
    }}
    /* Streamlit adds a styled div for the radio visual; hide it */
    [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {{
        display: none !important;
    }}

    /* ── Content area ── */
    .main .block-container {{
        padding: 28px 36px 40px !important;
        max-width: 1380px !important;
    }}

    /* ── Page header ── */
    .page-title {{
        font-size: 22px;
        font-weight: 800;
        color: #0f172a;
        margin: 0 0 4px;
        letter-spacing: -0.02em;
    }}
    .page-subtitle {{
        font-size: 13px;
        color: #6b7280;
        margin: 0 0 24px;
    }}

    /* ── Stat card ── */
    .stat-card {{
        background: white;
        border-radius: 12px;
        padding: 18px 20px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        height: 100%;
    }}
    .stat-icon {{ font-size: 18px; margin-bottom: 6px; }}
    .stat-label {{
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: .06em;
        color: #6b7280;
        margin-bottom: 4px;
    }}
    .stat-value {{
        font-size: 22px;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.02em;
        line-height: 1.1;
    }}
    .stat-value.green {{ color: #16a34a; }}
    .stat-value.red   {{ color: #dc2626; }}

    /* ── Content card ── */
    .card {{
        background: white;
        border-radius: 12px;
        padding: 20px 22px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 18px;
    }}
    .card-title {{
        font-size: 15px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 14px;
        letter-spacing: -0.01em;
    }}

    /* ── Section header ── */
    .section-hdr {{
        font-size: 15px;
        font-weight: 700;
        color: #111827;
        padding-bottom: 10px;
        border-bottom: 2px solid #e5e7eb;
        margin: 26px 0 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}

    /* ── Scout detail header card ── */
    .scout-hdr {{
        background: white;
        border-radius: 12px;
        padding: 22px 26px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        display: flex;
        gap: 18px;
        align-items: flex-start;
        margin-bottom: 20px;
    }}
    .scout-avatar {{
        width: 52px; height: 52px;
        border-radius: 50%;
        background: {ACCENT_LIGHT};
        color: {ACCENT};
        display: flex; align-items: center; justify-content: center;
        font-size: 18px; font-weight: 800;
        flex-shrink: 0;
    }}
    .scout-name {{
        font-size: 19px; font-weight: 700; color: #0f172a;
        letter-spacing: -0.02em; margin-bottom: 3px;
    }}
    .scout-meta {{ font-size: 13px; color: #6b7280; line-height: 1.6; }}

    /* ── Global buttons ── */
    .stButton > button {{
        background-color: {ACCENT} !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        padding: 8px 18px !important;
        transition: background 0.15s, transform 0.1s !important;
        cursor: pointer !important;
    }}
    .stButton > button:hover {{
        background-color: #1d4ed8 !important;
        transform: translateY(-1px) !important;
    }}
    .stButton > button:active {{ transform: translateY(0) !important; }}

    /* ── Back button: secondary look ── */
    [data-testid="back-btn"] .stButton > button {{
        background: white !important;
        color: {ACCENT} !important;
        border: 1px solid {ACCENT} !important;
        font-weight: 500 !important;
    }}
    [data-testid="back-btn"] .stButton > button:hover {{
        background: {ACCENT_LIGHT} !important;
        transform: none !important;
    }}

    /* ── Form inputs ── */
    .stTextInput input, .stNumberInput input,
    .stDateInput input, .stTextArea textarea {{
        border-radius: 8px !important;
        border: 1px solid #d1d5db !important;
        font-size: 14px !important;
        color: #111827 !important;
    }}
    .stTextInput input:focus, .stNumberInput input:focus,
    .stTextArea textarea:focus {{
        border-color: {ACCENT} !important;
        box-shadow: 0 0 0 3px {ACCENT_LIGHT} !important;
    }}
    .stSelectbox > div > div {{
        border-radius: 8px !important;
        border-color: #d1d5db !important;
        font-size: 14px !important;
    }}
    .stMultiSelect > div {{
        border-radius: 8px !important;
    }}

    /* ── Expander ── */
    .streamlit-expanderHeader {{
        font-weight: 600 !important;
        font-size: 14px !important;
        border-radius: 8px !important;
        background: white !important;
        border: 1px solid #e5e7eb !important;
    }}

    /* ── Download button ── */
    [data-testid="stDownloadButton"] button {{
        background: white !important;
        color: {ACCENT} !important;
        border: 1px solid {ACCENT} !important;
        font-size: 13px !important;
    }}
    [data-testid="stDownloadButton"] button:hover {{
        background: {ACCENT_LIGHT} !important;
        transform: none !important;
    }}

    /* ── Empty state ── */
    .empty {{
        text-align: center;
        padding: 52px 24px;
    }}
    .empty-icon  {{ font-size: 38px; margin-bottom: 10px; }}
    .empty-title {{ font-size: 15px; font-weight: 600; color: #4b5563; margin-bottom: 4px; }}
    .empty-sub   {{ font-size: 13px; color: #9ca3af; }}

    /* ── Horizontal rule ── */
    hr {{
        border: none !important;
        border-top: 1px solid #e5e7eb !important;
        margin: 18px 0 !important;
    }}
    </style>
    """, unsafe_allow_html=True)
