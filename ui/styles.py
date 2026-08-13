THEME = {
    "bg_base": "#0a0a0c",
    "bg_surface": "#14141a",
    "bg_elevated": "#1f1f28",
    "bg_input": "#282833",
    "bg_card": "#18181f",
    "border": "rgba(255, 255, 255, 0.12)",
    "border_strong": "rgba(255, 255, 255, 0.22)",
    "accent": "#a855f7",
    "accent_hover": "#9333ea",
    "accent_soft": "rgba(168, 85, 247, 0.18)",
    "accent_glow": "rgba(168, 85, 247, 0.45)",
    "text_primary": "#fafafa",
    "text_secondary": "#d4d4d8",
    "text_muted": "#a1a1aa",
    "text_on_accent": "#ffffff",
    "success": "#4ade80",
    "success_bg": "rgba(74, 222, 128, 0.12)",
    "danger": "#fca5a5",
    "danger_bg": "rgba(248, 113, 113, 0.12)",
    "warning": "#fcd34d",
    "warning_bg": "rgba(251, 191, 36, 0.12)",
}

APP_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    .stApp {{
        background: {THEME['bg_base']};
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: {THEME['text_primary']};
    }}

    #MainMenu, footer, header {{ visibility: hidden; }}

    .block-container {{
        padding: 2rem 1.5rem 4rem;
        max-width: 960px;
    }}

    .app-hero {{
        text-align: center;
        padding: 2rem 0 2.5rem;
    }}

    .app-hero .badge {{
        display: inline-block;
        background: {THEME['accent_soft']};
        color: #e9d5ff;
        padding: 5px 16px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 1.25rem;
        border: 1px solid rgba(168, 85, 247, 0.4);
    }}

    .app-hero h1 {{
        color: {THEME['text_primary']};
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0 0 0.6rem;
        line-height: 1.15;
        letter-spacing: -0.02em;
    }}

    .app-hero p {{
        color: {THEME['text_secondary']};
        font-size: 1.05rem;
        margin: 0;
    }}

    .app-card {{
        background: {THEME['bg_card']};
        border: 1px solid {THEME['border_strong']};
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    }}

    .app-card h3,
    .app-card .stMarkdown h3 {{
        color: {THEME['text_primary']} !important;
        font-size: 1.15rem !important;
        font-weight: 600 !important;
        margin: 0 0 1.25rem !important;
    }}

    .stat-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin: 1.25rem 0;
    }}

    @media (max-width: 700px) {{
        .stat-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}

    .stat-box {{
        background: {THEME['bg_elevated']};
        border: 1px solid {THEME['border_strong']};
        border-radius: 14px;
        padding: 1.1rem 1rem;
        text-align: center;
    }}

    .stat-box .number {{
        font-size: 1.9rem;
        font-weight: 700;
        color: {THEME['text_primary']};
    }}

    .stat-box .label {{
        font-size: 0.7rem;
        color: {THEME['text_muted']};
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
        margin-top: 0.25rem;
    }}

    .result-pass {{
        background: {THEME['success_bg']};
        border: 1px solid rgba(74, 222, 128, 0.35);
        border-left: 4px solid {THEME['success']};
        padding: 1.25rem 1.5rem;
        border-radius: 14px;
        margin: 1.25rem 0;
        color: #dcfce7;
    }}

    .result-fail {{
        background: {THEME['danger_bg']};
        border: 1px solid rgba(248, 113, 113, 0.35);
        border-left: 4px solid #f87171;
        padding: 1.25rem 1.5rem;
        border-radius: 14px;
        margin: 1.25rem 0;
        color: #fee2e2;
    }}

    .issue-card {{
        background: {THEME['bg_elevated']};
        border: 1px solid {THEME['border_strong']};
        border-radius: 14px;
        padding: 1rem 1.15rem 0.5rem;
        margin-bottom: 0.35rem;
    }}

    .issue-card--grave {{
        border-left: 4px solid #f87171;
    }}

    .issue-card--posible {{
        border-left: 4px solid #fbbf24;
    }}

    .issue-card-header {{
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 0.65rem;
    }}

    .issue-index {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 28px;
        height: 28px;
        background: {THEME['accent_soft']};
        color: #e9d5ff;
        border-radius: 8px;
        font-size: 0.72rem;
        font-weight: 700;
        border: 1px solid rgba(168, 85, 247, 0.45);
    }}

    .issue-severity {{
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        padding: 4px 10px;
        border-radius: 6px;
    }}

    .issue-card--grave .issue-severity {{
        background: {THEME['danger_bg']};
        color: {THEME['danger']};
        border: 1px solid rgba(248, 113, 113, 0.35);
    }}

    .issue-card--posible .issue-severity {{
        background: {THEME['warning_bg']};
        color: {THEME['warning']};
        border: 1px solid rgba(251, 191, 36, 0.35);
    }}

    .issue-cat {{
        background: rgba(255, 255, 255, 0.08);
        color: {THEME['text_secondary']};
        padding: 3px 10px;
        border-radius: 14px;
        font-size: 0.72rem;
        font-weight: 600;
        border: 1px solid {THEME['border']};
    }}

    .issue-msg {{
        color: {THEME['text_primary']};
        font-size: 0.92rem;
        font-weight: 500;
        line-height: 1.45;
        margin-bottom: 0.75rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid {THEME['border']};
    }}

    .issue-meta-label {{
        color: {THEME['text_muted']};
        font-weight: 600;
        font-size: 0.72rem;
        text-transform: uppercase;
    }}

    .issue-meta-value {{
        color: {THEME['text_secondary']};
        font-weight: 500;
    }}

    .issue-meta-row {{
        display: flex;
        gap: 10px;
        align-items: baseline;
        margin-bottom: 0.45rem;
        font-size: 0.84rem;
    }}

    .issue-meta-label {{
        flex: 0 0 72px;
    }}

    .issue-compare-item {{
        background: {THEME['bg_input']};
        border: 1px solid {THEME['border_strong']};
        border-radius: 10px;
        padding: 0.65rem 0.85rem;
        margin-bottom: 0.75rem;
    }}

    .issue-compare-item--actual {{
        border-color: rgba(248, 113, 113, 0.45);
        background: rgba(248, 113, 113, 0.08);
    }}

    .issue-compare-item--actual-posible {{
        border-color: rgba(251, 191, 36, 0.45) !important;
        background: rgba(251, 191, 36, 0.08) !important;
    }}

    .issue-compare-label {{
        display: block;
        color: {THEME['text_muted']};
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 4px;
    }}

    .issue-compare-value {{
        display: block;
        color: {THEME['text_primary']};
        font-size: 0.82rem;
        line-height: 1.4;
        word-break: break-word;
    }}

    .filter-summary {{
        background: {THEME['bg_elevated']};
        border: 1px solid {THEME['border_strong']};
        border-left: 4px solid {THEME['accent']};
        border-radius: 12px;
        padding: 0.8rem 1rem;
        margin: 1rem 0 1.25rem;
        color: {THEME['text_secondary']};
        font-size: 0.9rem;
    }}

    .filter-summary strong {{
        color: {THEME['text_primary']};
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {THEME['bg_elevated']} !important;
        border: 1px solid {THEME['border_strong']} !important;
        border-radius: 16px !important;
        padding: 0.5rem 0.75rem 0.85rem !important;
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] h3 {{
        color: {THEME['text_primary']} !important;
    }}

    div[data-testid="stPills"] > label p {{
        color: {THEME['text_secondary']} !important;
        font-weight: 700 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }}

    div[data-testid="stPills"] button {{
        border-radius: 999px !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        padding: 0.45rem 1rem !important;
    }}

    div[data-testid="stPills"] button[aria-pressed="false"] {{
        background: {THEME['bg_input']} !important;
        color: {THEME['text_muted']} !important;
        border: 1px solid {THEME['border']} !important;
    }}

    div[data-testid="stPills"] button[aria-pressed="false"]:hover {{
        background: #32323d !important;
        color: {THEME['text_secondary']} !important;
        border-color: {THEME['border_strong']} !important;
    }}

    div[data-testid="stPills"] button[aria-pressed="true"] {{
        background: {THEME['accent']} !important;
        color: {THEME['text_on_accent']} !important;
        border: 1px solid #c084fc !important;
        box-shadow: 0 2px 12px {THEME['accent_glow']} !important;
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] .stButton > button {{
        background: {THEME['bg_input']} !important;
        color: {THEME['text_secondary']} !important;
        border: 1px solid {THEME['border_strong']} !important;
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] .stButton > button:hover {{
        background: #32323d !important;
        color: {THEME['text_primary']} !important;
    }}

    .download-section {{
        margin-top: 1.5rem;
        padding-top: 1.25rem;
        border-top: 1px solid {THEME['border_strong']};
    }}

    .download-section p {{
        color: {THEME['text_secondary']};
        font-size: 0.85rem;
        margin: 0 0 0.75rem;
    }}

    div[data-testid="stSidebar"] {{
        background: {THEME['bg_surface']};
        border-right: 1px solid {THEME['border_strong']};
    }}

    div[data-testid="stSidebar"] .stMarkdown,
    div[data-testid="stSidebar"] .stMarkdown p,
    div[data-testid="stSidebar"] .stMarkdown li,
    div[data-testid="stSidebar"] h3 {{
        color: {THEME['text_primary']} !important;
    }}

    div[data-testid="stSidebar"] .stCaption,
    div[data-testid="stSidebar"] small {{
        color: {THEME['text_muted']} !important;
    }}

    div[data-testid="stSidebar"] hr {{
        border-color: {THEME['border_strong']};
    }}

    .stButton > button[kind="primary"] {{
        width: 100%;
        background: {THEME['accent']} !important;
        color: {THEME['text_on_accent']} !important;
        border: 2px solid #c084fc !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        padding: 0.75rem 2rem !important;
        box-shadow: 0 4px 24px {THEME['accent_glow']} !important;
    }}

    .stButton > button[kind="primary"]:hover {{
        background: {THEME['accent_hover']} !important;
        border-color: #d8b4fe !important;
        box-shadow: 0 6px 28px {THEME['accent_glow']} !important;
    }}

    .stDownloadButton > button {{
        width: 100%;
        background: {THEME['bg_elevated']} !important;
        color: {THEME['text_primary']} !important;
        border: 1px solid {THEME['border_strong']} !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }}

    .stDownloadButton > button:hover {{
        background: {THEME['bg_input']} !important;
        border-color: {THEME['accent']} !important;
    }}

    .stButton > button[kind="secondary"] {{
        background: {THEME['bg_elevated']} !important;
        color: {THEME['text_secondary']} !important;
        border: 1px solid {THEME['border_strong']} !important;
    }}

    div[data-testid="stExpander"] {{
        background: {THEME['bg_card']};
        border: 1px solid {THEME['border_strong']};
        border-radius: 14px;
        margin-bottom: 0.75rem;
    }}

    div[data-testid="stExpander"] details[open] > div {{
        padding: 0.5rem 1rem 1.25rem;
        border-top: 1px solid {THEME['border']};
        background: {THEME['bg_surface']};
    }}

    div[data-testid="stExpander"] summary {{
        color: {THEME['text_primary']} !important;
        font-weight: 600 !important;
    }}

    div[data-testid="stExpander"] summary:hover {{
        color: #e9d5ff !important;
    }}

    section[data-testid="stFileUploader"] {{
        background: transparent !important;
    }}

    section[data-testid="stFileUploader"] > div {{
        background: {THEME['bg_input']} !important;
        border: 1px solid {THEME['border_strong']} !important;
        border-radius: 14px !important;
        padding: 0.5rem !important;
    }}

    [data-testid="stFileUploaderDropzone"] {{
        background: {THEME['bg_input']} !important;
        border: 1px dashed rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        padding: 1.5rem 1rem !important;
    }}

    [data-testid="stFileUploaderDropzone"]:hover {{
        border-color: {THEME['accent']} !important;
        background: #2e2e3a !important;
    }}

    [data-testid="stFileUploaderDropzone"] div,
    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzone"] p,
    [data-testid="stFileUploaderDropzone"] small {{
        color: {THEME['text_secondary']} !important;
    }}

    [data-testid="stFileUploaderDropzone"] svg {{
        fill: {THEME['text_muted']} !important;
        stroke: {THEME['text_muted']} !important;
    }}

    section[data-testid="stFileUploader"] button {{
        background: {THEME['accent']} !important;
        color: {THEME['text_on_accent']} !important;
        border: 1px solid #c084fc !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }}

    section[data-testid="stFileUploader"] button:hover {{
        background: {THEME['accent_hover']} !important;
        border-color: #d8b4fe !important;
    }}

    section[data-testid="stFileUploader"] button p,
    section[data-testid="stFileUploader"] button span {{
        color: {THEME['text_on_accent']} !important;
    }}

    [data-testid="stFileUploader"] small {{
        color: {THEME['text_muted']} !important;
    }}

    div[data-testid="stAlert"] {{
        background: {THEME['bg_elevated']} !important;
        border: 1px solid {THEME['border_strong']} !important;
        border-radius: 12px !important;
        color: {THEME['text_primary']} !important;
    }}

    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] span {{
        color: {THEME['text_primary']} !important;
    }}

    [data-testid="stSpinner"] {{
        color: {THEME['accent']} !important;
    }}
</style>
"""

ADG_CSS = APP_CSS
