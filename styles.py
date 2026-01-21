import streamlit as st
import requests

# === 1. BARVY (Paleta Cyber-ROG - Stabilní) ===
NEON_GREEN = "#39ff14"
NEON_BLUE = "#00f3ff"
NEON_RED = "#ff073a"
NEON_ORANGE = "#ff5f1f"
DARK_BG = "#0e1117"
CARD_BG = "#1b1e24" # Tmavá šedá pro karty (aby byly čitelné)

# --- DEFINICE BAREV PRO AKCE (Zůstává stejné) ---
BARVY_AKCI = {
    "mcr": {"bg": "linear-gradient(135deg, #7f1d1d, #be123c)", "color": "#fff", "border": "1px solid #ff073a", "shadow": "0 2px 5px rgba(0,0,0,0.5)"},
    "za": {"bg": "#7f1d1d", "color": "#fecaca", "border": "1px solid #ef4444", "shadow": "none"},
    "zb": {"bg": "#7c2d12", "color": "#fed7aa", "border": "1px solid #f97316", "shadow": "none"},
    "soustredeni": {"bg": "#713f12", "color": "#fef08a", "border": "1px solid #eab308", "shadow": "none"},
    "oblastni": {"bg": "#1e3a8a", "color": "#bfdbfe", "border": "1px solid #3b82f6", "shadow": "none"},
    "zimni_liga": {"bg": "#374151", "color": "#e5e7eb", "border": "1px solid #6b7280", "shadow": "none"},
    "stafety": {"bg": "#581c87", "color": "#e9d5ff", "border": "1px solid #a855f7", "shadow": "none"},
    "trenink": {"bg": "#14532d", "color": "#bbf7d0", "border": "1px solid #22c55e", "shadow": "none"},
    "zavod": {"bg": "#134e4a", "color": "#99f6e4", "border": "1px solid #14b8a6", "shadow": "none"},
    "default": {"bg": "#262626", "color": "#e5e5e5", "border": "1px solid #404040", "shadow": "none"}
}

# --- 2. CSS STYLY ---
def load_css():
    st.markdown(f"""
    <style>
        /* === 1. FONTY S ČESKOU PODPOROU === */
        /* Načítáme latin-ext pro správné zobrazení háčků a čárek */
        @import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@300;400;600&family=Orbitron:wght@400;700;900&display=swap&subset=latin,latin-ext');

        /* Aplikace fontů - SPECIFICKY, aby se nerozbily ikony (expand_m) */
        h1, h2, h3, h4 {{
            font-family: 'Orbitron', sans-serif !important;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        
        /* Aplikujeme Exo 2 na textové elementy, ale NE na ikonové kontejnery */
        p, div:not([class*="stIcon"]), span, label, input, textarea, button {{
            font-family: 'Exo 2', sans-serif;
        }}

        /* === 2. ROG POZADÍ A LINKY === */
        .stApp {{
            background-color: {DARK_BG};
            background-image: 
                radial-gradient(circle at 50% 30%, rgba(0, 243, 255, 0.04) 0%, transparent 60%),
                repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.02) 0px, rgba(255, 255, 255, 0.02) 1px, transparent 1px, transparent 40px),
                repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.02) 0px, rgba(255, 255, 255, 0.02) 1px, transparent 1px, transparent 40px);
            background-attachment: fixed;
        }}

        /* Boční svítící linky */
        body::before, body::after {{
            content: "";
            position: fixed;
            top: 0; bottom: 0;
            width: 2px;
            z-index: 9999;
            pointer-events: none;
            opacity: 0.5;
            box-shadow: 0 0 8px {NEON_BLUE};
        }}
        body::before {{
            left: 10px;
            background: linear-gradient(to bottom, transparent, {NEON_BLUE}, {NEON_GREEN}, transparent);
        }}
        body::after {{
            right: 10px;
            background: linear-gradient(to bottom, transparent, {NEON_GREEN}, {NEON_BLUE}, transparent);
        }}

        /* === 3. TLAČÍTKA (PLNÁ A ČITELNÁ) === */
        .stButton > button {{
            background-color: {CARD_BG} !important;
            color: {NEON_BLUE} !important;
            border: 1px solid {NEON_BLUE} !important;
            border-radius: 4px !important;
            font-family: 'Orbitron', sans-serif !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.5) !important;
        }}
        .stButton > button:hover {{
            background-color: {NEON_BLUE} !important;
            color: #000 !important;
            transform: translateY(-2px);
            box-shadow: 0 0 15px {NEON_BLUE} !important;
        }}
        
        /* Primary (Zelená) */
        .stButton > button[kind="primary"] {{
            background-color: rgba(34, 197, 94, 0.15) !important;
            color: {NEON_GREEN} !important;
            border: 1px solid {NEON_GREEN} !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            background-color: {NEON_GREEN} !important;
            color: #000 !important;
            box-shadow: 0 0 15px {NEON_GREEN} !important;
        }}

        /* === 4. INPUTY A KALENDÁŘ === */
        .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextArea textarea {{
            background-color: #111827 !important;
            color: white !important;
            border: 1px solid #374151 !important;
            font-family: 'Exo 2', sans-serif !important;
        }}
        .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within {{
            border-color: {NEON_BLUE} !important;
            box-shadow: 0 0 5px rgba(0, 243, 255, 0.3) !important;
        }}

        /* Oprava mřížky kalendáře */
        hr {{
            margin: 0 0 15px 0;
            border: 0;
            border-top: 1px solid #374151 !important; /* Viditelná šedá čára */
        }}
        
        .today-box {{
            background-color: #ef4444; color: white;
            padding: 4px 12px; border-radius: 20px; font-weight: 700;
            box-shadow: 0 0 10px #ef4444; display: inline-block; margin-bottom: 8px;
        }}
        
        .day-number {{
            color: #9ca3af; font-weight: 600; display: block; text-align: center; margin-bottom: 8px;
        }}

        /* === 5. HEADER A PATIČKA === */
        h1 span.gradient-text {{
            background: linear-gradient(90deg, {NEON_GREEN}, {NEON_BLUE});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        h1 img.header-logo {{
            height: 60px;
            filter: drop-shadow(0 0 5px {NEON_GREEN});
            transition: transform 0.3s;
        }}
        h1 img.header-logo:hover {{ transform: scale(1.1) rotate(5deg); }}

        /* GLOW PRO LOGA (Contour drop-shadow) */
        .footer-glow img {{
            filter: drop-shadow(0 0 3px rgba(255,255,255,0.6));
            transition: transform 0.3s;
        }}
        .footer-glow img:hover {{
            transform: scale(1.05);
            filter: drop-shadow(0 0 8px rgba(255,255,255,0.9));
        }}

        /* Skrytí UI Streamlitu */
        #MainMenu, footer, header, .stDeployButton {{visibility: hidden;}}
        [data-testid="stToolbar"] {{visibility: hidden;}}
        [data-testid="stDecoration"] {{display:none;}}
        
    </style>
    """, unsafe_allow_html=True)

# --- OSTATNÍ FUNKCE (Zůstávají) ---
def inject_mobile_warning():
    st.markdown("""<style>@media only screen and (orientation: portrait) and (max-width: 900px) {#rotate-warning {display:flex !important;} .stApp {overflow:hidden;}}</style>""", unsafe_allow_html=True)

def get_ics_button_html(b64_data, filename):
    return f"""<a href="data:text/calendar;base64,{b64_data}" download="{filename}.ics" style="text-decoration:none;"><div style="background: #1f2937; border: 1px solid #374151; border-radius: 8px; padding: 6px 0; text-align: center; cursor: pointer; color: white; transition: 0.3s;" onmouseover="this.style.borderColor='#00f3ff'; this.style.color='#00f3ff';" onmouseout="this.style.borderColor='#374151'; this.style.color='white';">📅</div></a>"""

def get_weather_card_html(w_icon, w_text, temp, rain, wind, sunset_html=""):
    border = NEON_BLUE if rain < 2 else NEON_RED
    return f"""<div style="margin-top:10px; margin-bottom:20px; padding:10px; background:#111827; border:1px solid {border}; border-left:4px solid {border}; border-radius:8px; display:flex; align-items:center; color:white;"><div style="font-size:2rem; margin-right:15px;">{w_icon}</div><div style="flex-grow:1;"><div style="font-weight:bold; color:{border}">{w_text}, {temp}°C</div><div style="font-size:0.85rem; color:#9ca3af;">💧 {rain} mm • 💨 {wind} km/h</div></div>{sunset_html}</div>"""

def get_footer_html():
    return f"<div style='text-align: center; color: #6b7280; font-size: 0.8em; margin-top: 20px; font-family: \"Orbitron\", sans-serif;'>SYSTEM: <span style='color:{NEON_GREEN}'>ONLINE</span> • RBK 2026</div>"

def badge(text, bg="#333", color="#fff"):
    return f"<span style='background-color: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #e5e7eb; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-right: 6px; font-family: \"Orbitron\", sans-serif;'>{text}</span>"

# Lottie
@st.cache_data(ttl=3600*24)
def load_lottieurl(url):
    try: return requests.get(url).json()
    except: return None
lottie_success = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_jbrw3hcz.json")
