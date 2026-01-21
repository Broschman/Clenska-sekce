import streamlit as st
import requests

# === 1. BARVY (Paleta Cyber-ROG) ===
NEON_GREEN = "#39ff14"
NEON_BLUE = "#00f3ff"
NEON_RED = "#ff073a"
NEON_ORANGE = "#ff5f1f"
DARK_BG = "#0e1117"

# --- DEFINICE BAREV PRO AKCE ---
BARVY_AKCI = {
    "mcr": {"bg": "linear-gradient(135deg, rgba(255, 7, 58, 0.2), rgba(0, 243, 255, 0.2))", "color": "#fff", "border": "1px solid #ff073a", "shadow": "0 0 15px rgba(255, 7, 58, 0.4)"},
    "za": {"bg": "rgba(255, 7, 58, 0.15)", "color": "#ffadb8", "border": "1px solid #ff073a", "shadow": "0 0 10px rgba(255, 7, 58, 0.2)"},
    "zb": {"bg": "rgba(255, 95, 31, 0.15)", "color": "#ffcbb3", "border": "1px solid #ff5f1f", "shadow": "0 0 10px rgba(255, 95, 31, 0.2)"},
    "soustredeni": {"bg": "rgba(255, 215, 0, 0.15)", "color": "#fff5cc", "border": "1px solid #ffd700", "shadow": "0 0 10px rgba(255, 215, 0, 0.2)"},
    "oblastni": {"bg": "rgba(0, 243, 255, 0.15)", "color": "#ccfcff", "border": "1px solid #00f3ff", "shadow": "0 0 10px rgba(0, 243, 255, 0.2)"},
    "zimni_liga": {"bg": "rgba(100, 116, 139, 0.3)", "color": "#e2e8f0", "border": "1px solid #64748b", "shadow": "none"},
    "stafety": {"bg": "rgba(189, 0, 255, 0.15)", "color": "#f2ccff", "border": "1px solid #bd00ff", "shadow": "0 0 10px rgba(189, 0, 255, 0.2)"},
    "trenink": {"bg": "rgba(57, 255, 20, 0.1)", "color": "#ccffc4", "border": "1px solid #39ff14", "shadow": "0 0 8px rgba(57, 255, 20, 0.15)"},
    "zavod": {"bg": "rgba(0, 243, 255, 0.1)", "color": "#ccfcff", "border": "1px solid #00f3ff", "shadow": "none"},
    "default": {"bg": "rgba(255, 255, 255, 0.05)", "color": "#e0e0e0", "border": "1px solid rgba(255,255,255,0.1)", "shadow": "none"}
}

# --- 2. CSS STYLY ---
def load_css():
    st.markdown(f"""
    <style>
        /* === 1. FONTY S ČESKOU PODPOROU (latin-ext) === */
        /* Exo 2 je skvělý sci-fi font, který umí české znaky perfektně */
        @import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@300;400;600;800&family=Orbitron:wght@400;700;900&display=swap&subset=latin,latin-ext');

        /* === 2. APLIKACE FONTŮ (Bezpečně pro ikony) === */
        
        /* Nadpisy (Orbitron pro efekt, Exo 2 fallback) */
        h1, h2, h3, h4 {{
            font-family: 'Orbitron', 'Exo 2', sans-serif !important;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}

        /* Běžný text + Tlačítka + Inputy (Exo 2) */
        /* Cílíme konkrétní elementy, abychom nerozbili ikony ve .stIcon nebo span class="..." */
        html, body, p, a, span, div, label, input, textarea, button {{
            color: #e0e0e0;
        }}
        
        /* Specifické cílení na textový obsah, vynecháváme třídy ikon */
        .stMarkdown p, .stMarkdown li, .stMarkdown div, 
        .stButton button, .stTextInput input, .stTextArea textarea, 
        .stSelectbox div, .stNumberInput input, label {{
            font-family: 'Exo 2', sans-serif !important;
        }}

        /* === 3. ROG POZADÍ A LINKY === */
        .stApp {{
            background-color: {DARK_BG};
            background-image: 
                radial-gradient(circle at 50% 30%, rgba(0, 243, 255, 0.04) 0%, transparent 60%),
                repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.02) 0px, rgba(255, 255, 255, 0.02) 1px, transparent 1px, transparent 40px),
                repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.02) 0px, rgba(255, 255, 255, 0.02) 1px, transparent 1px, transparent 40px);
            background-attachment: fixed;
        }}

        /* Boční svítící linky (ROG Style) */
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

        /* === 4. TLAČÍTKA (GLASSMORPHISM) === */
        /* Průhledná, rozmazaná, neonové okraje */
        .stButton > button {{
            background: rgba(255, 255, 255, 0.03) !important;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            color: {NEON_BLUE} !important;
            border: 1px solid rgba(0, 243, 255, 0.3) !important;
            border-radius: 6px !important;
            text-shadow: 0 0 5px rgba(0, 243, 255, 0.5);
            transition: all 0.3s ease !important;
        }}
        .stButton > button:hover {{
            background: rgba(0, 243, 255, 0.15) !important;
            border-color: {NEON_BLUE} !important;
            box-shadow: 0 0 15px rgba(0, 243, 255, 0.4) !important;
            transform: translateY(-2px);
        }}
        
        /* Primary (Zapsat se - Zelená) */
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, rgba(57, 255, 20, 0.15), rgba(57, 255, 20, 0.05)) !important;
            color: {NEON_GREEN} !important;
            border: 1px solid {NEON_GREEN} !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            box-shadow: 0 0 20px rgba(57, 255, 20, 0.6) !important;
        }}

        /* === 5. INPUTY A KALENDÁŘ === */
        /* Inputy - tmavé, ale průhledné */
        .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextArea textarea {{
            background-color: rgba(255, 255, 255, 0.05) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 6px !important;
        }}
        .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within {{
            border-color: {NEON_BLUE} !important;
            box-shadow: 0 0 10px rgba(0, 243, 255, 0.2) !important;
        }}

        /* Kalendář - Oprava mřížky */
        hr {{
            margin: 0 0 15px 0;
            border: 0;
            border-top: 1px solid rgba(255,255,255,0.15) !important;
        }}
        
        .today-box {{
            background: rgba(255, 7, 58, 0.2); color: {NEON_RED}; border: 1px solid {NEON_RED};
            padding: 4px 12px; border-radius: 20px; font-weight: 700;
            box-shadow: 0 0 15px rgba(255, 7, 58, 0.4); display: inline-block; margin-bottom: 8px;
        }}
        /* Čísla dní - Exo 2 */
        .day-number {{
            font-family: 'Exo 2', sans-serif;
            color: #888; font-weight: 600; display: block; text-align: center; margin-bottom: 8px;
        }}

        /* Popover Glow */
        div[data-testid="stPopoverBody"] {{
            background-color: rgba(14, 17, 23, 0.95) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            backdrop-filter: blur(15px);
            border-radius: 12px !important;
            box-shadow: 0 0 40px rgba(0, 0, 0, 0.8) !important;
        }}

        /* === 6. HEADER A PATIČKA === */
        h1 span.gradient-text {{
            background: linear-gradient(90deg, {NEON_GREEN}, {NEON_BLUE});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        h1 img.header-logo {{
            height: 60px;
            filter: drop-shadow(0 0 8px {NEON_GREEN});
            transition: transform 0.3s;
        }}
        h1 img.header-logo:hover {{ transform: scale(1.1) rotate(5deg); }}

        /* GLOW PRO LOGA (Contour drop-shadow) */
        .footer-glow img {{
            filter: drop-shadow(0 0 5px rgba(255,255,255,0.5));
            transition: transform 0.3s;
        }}
        .footer-glow img:hover {{
            transform: scale(1.05);
            filter: drop-shadow(0 0 10px rgba(255,255,255,0.9));
        }}

        /* Skrytí UI Streamlitu */
        #MainMenu, footer, header, .stDeployButton {{visibility: hidden;}}
        [data-testid="stToolbar"] {{visibility: hidden;}}
        [data-testid="stDecoration"] {{display:none;}}
        
    </style>
    """, unsafe_allow_html=True)

# --- OSTATNÍ FUNKCE (Beze změny) ---
def inject_mobile_warning():
    st.markdown("""<style>@media only screen and (orientation: portrait) and (max-width: 900px) {#rotate-warning {display:flex !important;} .stApp {overflow:hidden;}}</style>""", unsafe_allow_html=True)

def get_ics_button_html(b64_data, filename):
    # Futuristické tlačítko
    return f"""<a href="data:text/calendar;base64,{b64_data}" download="{filename}.ics" style="text-decoration:none;"><div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 6px 0px; text-align: center; cursor: pointer; color: #fff; font-size: 1.2rem; transition: all 0.3s;" onmouseover="this.style.borderColor='#00f3ff'; this.style.color='#00f3ff'; this.style.boxShadow='0 0 10px #00f3ff';" onmouseout="this.style.borderColor='rgba(255, 255, 255, 0.2)'; this.style.color='#fff'; this.style.boxShadow='none';">📅</div></a>"""

def get_weather_card_html(w_icon, w_text, temp, rain, wind, sunset_html=""):
    border = NEON_BLUE if rain < 2 else NEON_RED
    # Kartička počasí - Exo 2 font
    return f"""<div style="margin-top:10px; margin-bottom:20px; padding:15px; background:linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); border:1px solid {border}; border-left:4px solid {border}; border-radius:10px; display:flex; align-items:center; color:white; box-shadow: 0 4px 15px rgba(0,0,0,0.2);"><div style="font-size:2rem; margin-right:15px; filter: drop-shadow(0 0 5px rgba(255,255,255,0.3));">{w_icon}</div><div style="flex-grow:1;"><div style="font-weight:bold; font-family:'Exo 2', sans-serif; color:{border}">{w_text}, {temp}°C</div><div style="font-size:0.85rem; color:#aaa; font-family:'Exo 2', sans-serif;">💧 {rain} mm • 💨 {wind} km/h</div></div>{sunset_html}</div>"""

def get_footer_html():
    return f"<div style='text-align: center; color: #6b7280; font-size: 0.8em; margin-top: 20px; font-family: \"Orbitron\", sans-serif;'>SYSTEM: <span style='color:{NEON_GREEN}'>ONLINE</span> • RBK 2026</div>"

def badge(text, bg="#333", color="#fff"):
    # Badge - Orbitron font
    return f"<span style='background-color: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #e5e7eb; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-right: 6px; font-family: \"Orbitron\", sans-serif;'>{text}</span>"

@st.cache_data(ttl=3600*24)
def load_lottieurl(url):
    try: return requests.get(url).json()
    except: return None
lottie_success = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_jbrw3hcz.json")
