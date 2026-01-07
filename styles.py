import streamlit as st
import requests
from streamlit_lottie import st_lottie_spinner

# CSS STYLY
def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #1f2937; }
        #MainMenu, footer, header, .stDeployButton, [data-testid="stToolbar"], [data-testid="stDecoration"] {visibility: hidden; display:none;}

        /* Nadpis a Logo */
        h1 span.gradient-text {
            background: -webkit-linear-gradient(45deg, #166534, #15803d);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-weight: 900; text-transform: uppercase; letter-spacing: -1px;
        }
        h1 { text-align: center !important; display: flex; align-items: center; justify-content: center; gap: 15px; }
        h1 img.header-logo { height: 60px; width: auto; margin-top: -5px; transition: transform 0.3s ease; }
        h1 img.header-logo:hover { transform: scale(1.1) rotate(5deg); }

        /* Popover a UI */
        div[data-testid="stPopoverBody"] { width: 800px !important; max-width: 95vw !important; max-height: 85vh !important; border-radius: 12px !important; }
        .floating-container { position: fixed; bottom: 30px; right: 30px; z-index: 9999; }
        .floating-container button { background: linear-gradient(135deg, #2563EB, #1D4ED8) !important; color: white !important; border-radius: 50px !important; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4) !important; }
        
        /* Kalendář */
        .today-box { background: #DC2626; color: white; padding: 4px 12px; border-radius: 20px; font-weight: 700; }
        .day-number { font-size: 1.1em; font-weight: 700; color: #6B7280; display: block; text-align: center; }
        div[data-testid="column"] { padding: 2px; }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] { border-radius: 8px !important; border: 1px solid #E5E7EB; }
    </style>
    """, unsafe_allow_html=True)

# LOTTIE ANIMACE
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except: return None

lottie_success = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_jbrw3hcz.json")

# DEFINICE BAREV
BARVY_AKCI = {
    "mcr": {"bg": "linear-gradient(90deg, #EF4444, #F59E0B, #10B981, #3B82F6, #8B5CF6)", "color": "white", "border": "none"},
    "za": {"bg": "#DC2626", "color": "white", "border": "none"},
    "zb": {"bg": "#EA580C", "color": "white", "border": "none"},
    "soustredeni": {"bg": "#D97706", "color": "white", "border": "none"},
    "oblastni": {"bg": "#2563EB", "color": "white", "border": "none"},
    "zimni_liga": {"bg": "#4B5563", "color": "white", "border": "none"},
    "stafety": {"bg": "#9333EA", "color": "white", "border": "none"},
    "trenink": {"bg": "#16A34A", "color": "white", "border": "none"},
    "zavod": {"bg": "#0D9488", "color": "white", "border": "none"},
    "default": {"bg": "#FFFFFF", "color": "#374151", "border": "1px solid #E5E7EB"}
}

def badge(text, bg="#f3f4f6", color="#111"):
    return f"<span style='background-color: {bg}; color: {color}; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-right: 6px;'>{text}</span>"
