import streamlit as st
import requests

# === 1. BARVY (Paleta Cyber-ROG) ===
NEON_GREEN = "#39ff14"
NEON_BLUE = "#00f3ff"
NEON_RED = "#ff073a"
NEON_ORANGE = "#ff5f1f"
DARK_BG = "#0e1117"

# --- DEFINICE BAREV PRO AKCE (Používáme 'glow' pro hover) ---
BARVY_AKCI = {
    "mcr": {"bg": "rgba(255, 7, 58, 0.1)", "glow": "#ff073a"},      # Červená
    "za": {"bg": "rgba(255, 7, 58, 0.1)", "glow": "#ef4444"},       # Světlejší červená
    "zb": {"bg": "rgba(249, 115, 22, 0.1)", "glow": "#f97316"},     # Oranžová
    "soustredeni": {"bg": "rgba(234, 179, 8, 0.1)", "glow": "#eab308"}, # Zlatá
    "oblastni": {"bg": "rgba(59, 130, 246, 0.1)", "glow": "#3b82f6"},   # Modrá
    "zimni_liga": {"bg": "rgba(107, 114, 128, 0.1)", "glow": "#9ca3af"}, # Šedá
    "stafety": {"bg": "rgba(168, 85, 247, 0.1)", "glow": "#a855f7"},    # Fialová
    "trenink": {"bg": "rgba(34, 197, 94, 0.1)", "glow": "#22c55e"},     # Zelená
    "zavod": {"bg": "rgba(20, 184, 166, 0.1)", "glow": "#14b8a6"},      # Tyrkysová
    "default": {"bg": "rgba(255, 255, 255, 0.05)", "glow": "#ffffff"}   # Bílá
}

def load_css():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@300;400;600;800&family=Orbitron:wght@400;700;900&display=swap&subset=latin,latin-ext');

        /* === GLOBÁLNÍ RESET === */
        body, p, h1, h2, h3, h4, h5, h6, span, div, label, input, button, textarea {{
            font-family: 'Exo 2', sans-serif !important;
            color: #e0e0e0;
        }}
        
        h1, h2, h3 {{
            font-family: 'Orbitron', 'Exo 2', sans-serif !important;
            letter-spacing: 1px;
            text-transform: uppercase;
            font-weight: 800 !important;
        }}

        /* === LOGO FIX === */
        img.header-logo {{
            height: 60px !important;
            width: auto !important;
            object-fit: contain !important;
            margin-top: 5px;
            filter: drop-shadow(0 0 8px {NEON_BLUE});
            transition: transform 0.3s;
        }}
        img.header-logo:hover {{ transform: scale(1.1) rotate(5deg); }}

        h1 span.gradient-text {{
            background: linear-gradient(90deg, {NEON_GREEN}, {NEON_BLUE});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }}

        /* === POZADÍ === */
        .stApp {{
            background-color: {DARK_BG};
            background-image: 
                radial-gradient(circle at 50% 30%, rgba(0, 243, 255, 0.04) 0%, transparent 60%),
                repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.02) 0px, rgba(255, 255, 255, 0.02) 1px, transparent 1px, transparent 40px),
                repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.02) 0px, rgba(255, 255, 255, 0.02) 1px, transparent 1px, transparent 40px);
            background-attachment: fixed;
        }}

        /* === DEFAULTNÍ TLAČÍTKA (GLASS) === */
        .stButton > button {{
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(5px);
            color: {NEON_BLUE} !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }}
        
        /* Default hover (neutrální modrá z configu) */
        .stButton > button:hover {{
            border-color: {NEON_BLUE} !important;
            box-shadow: 0 0 10px {NEON_BLUE} !important;
            background-color: rgba(0, 243, 255, 0.1) !important;
        }}

        /* Primary tlačítko (Zapsat se) - ZELENÉ */
        .stButton > button[kind="primary"] {{
            background: rgba(57, 255, 20, 0.1) !important;
            color: {NEON_GREEN} !important;
            border: 1px solid {NEON_GREEN} !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            box-shadow: 0 0 20px {NEON_GREEN} !important;
            background-color: rgba(57, 255, 20, 0.2) !important;
        }}

        /* Inputy */
        .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextArea textarea {{
            background-color: rgba(255, 255, 255, 0.05) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
        }}
        .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within {{
            border-color: {NEON_BLUE} !important;
            box-shadow: 0 0 10px rgba(0, 243, 255, 0.2) !important;
        }}

        /* Patička */
        .footer-glow img {{
            filter: drop-shadow(0 0 5px rgba(255,255,255,0.5));
            transition: transform 0.3s;
        }}
        .footer-glow img:hover {{
            transform: scale(1.05);
            filter: drop-shadow(0 0 10px rgba(255,255,255,0.9));
        }}

        #MainMenu, footer, header, .stDeployButton {{visibility: hidden;}}
        [data-testid="stToolbar"] {{visibility: hidden;}}
        [data-testid="stDecoration"] {{display:none;}}
    </style>
    """, unsafe_allow_html=True)

# --- OSTATNÍ FUNKCE ---
def inject_mobile_warning(): st.markdown("""<style>@media only screen and (orientation: portrait) and (max-width: 900px) {#rotate-warning {display:flex !important;} .stApp {overflow:hidden;}}</style>""", unsafe_allow_html=True)
def get_ics_button_html(b64_data, filename): return f"""<a href="data:text/calendar;base64,{b64_data}" download="{filename}.ics" style="text-decoration:none;"><div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 6px 0; text-align: center; cursor: pointer; color: #fff; transition: 0.3s;" onmouseover="this.style.borderColor='#00f3ff'; this.style.color='#00f3ff'; this.style.boxShadow='0 0 10px #00f3ff';" onmouseout="this.style.borderColor='rgba(255, 255, 255, 0.2)'; this.style.color='#fff'; this.style.boxShadow='none';">📅</div></a>"""
def get_weather_card_html(w_icon, w_text, temp, rain, wind, sunset_html=""):
    border = NEON_BLUE if rain < 2 else NEON_RED
    return f"""<div style="margin-top:10px; margin-bottom:20px; padding:15px; background:linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); border:1px solid {border}; border-left:4px solid {border}; border-radius:10px; display:flex; align-items:center; color:white; box-shadow: 0 4px 15px rgba(0,0,0,0.2);"><div style="font-size:2rem; margin-right:15px; filter: drop-shadow(0 0 5px rgba(255,255,255,0.3));">{w_icon}</div><div style="flex-grow:1;"><div style="font-weight:bold; font-family:'Exo 2', sans-serif; color:{border}">{w_text}, {temp}°C</div><div style="font-size:0.85rem; color:#aaa; font-family:'Exo 2', sans-serif;">💧 {rain} mm • 💨 {wind} km/h</div></div>{sunset_html}</div>"""
def get_footer_html(): return f"<div style='text-align: center; color: #6b7280; font-size: 0.8em; margin-top: 20px; font-family: \"Exo 2\", sans-serif;'>SYSTEM: <span style='color:{NEON_GREEN}'>ONLINE</span> • RBK 2026</div>"
def badge(text, bg="#333", color="#fff"): return f"<span style='background-color: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #e5e7eb; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-right: 6px; font-family: \"Exo 2\", sans-serif;'>{text}</span>"
@st.cache_data(ttl=3600*24)
def load_lottieurl(url):
    try: return requests.get(url).json()
    except: return None
lottie_success = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_jbrw3hcz.json")
