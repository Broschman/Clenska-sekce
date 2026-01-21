import streamlit as st
import requests

# === 1. BARVY (Paleta Cyber-Forest) ===
# Definujeme je tady, abychom je mohli používat i v Python kódu
NEON_GREEN = "#39ff14"
NEON_BLUE = "#00f3ff"
NEON_RED = "#ff073a"
NEON_ORANGE = "#ff5f1f"
DARK_BG = "#0e1117"
GLASS_BG = "rgba(20, 26, 35, 0.7)"
GLASS_BORDER = "1px solid rgba(255, 255, 255, 0.1)"

# --- DEFINICE BAREV PRO AKCE (Neonová edice) ---
# Tady měníme pastely na neonové barvy na tmavém pozadí
BARVY_AKCI = {
    "mcr": {
        "bg": "linear-gradient(135deg, rgba(255, 7, 58, 0.2), rgba(0, 243, 255, 0.2))", 
        "color": "#fff", "border": "1px solid #ff073a", "shadow": "0 0 15px rgba(255, 7, 58, 0.4)"
    },
    "za": {"bg": "rgba(255, 7, 58, 0.15)", "color": "#ffadb8", "border": "1px solid #ff073a", "shadow": "0 0 10px rgba(255, 7, 58, 0.2)"},
    "zb": {"bg": "rgba(255, 95, 31, 0.15)", "color": "#ffcbb3", "border": "1px solid #ff5f1f", "shadow": "0 0 10px rgba(255, 95, 31, 0.2)"},
    "soustredeni": {"bg": "rgba(255, 215, 0, 0.15)", "color": "#fff5cc", "border": "1px solid #ffd700", "shadow": "0 0 10px rgba(255, 215, 0, 0.2)"},
    "oblastni": {"bg": "rgba(0, 243, 255, 0.15)", "color": "#ccfcff", "border": "1px solid #00f3ff", "shadow": "0 0 10px rgba(0, 243, 255, 0.2)"},
    "zimni_liga": {"bg": "rgba(100, 116, 139, 0.3)", "color": "#e2e8f0", "border": "1px solid #64748b", "shadow": "none"},
    "stafety": {"bg": "rgba(189, 0, 255, 0.15)", "color": "#f2ccff", "border": "1px solid #bd00ff", "shadow": "0 0 10px rgba(189, 0, 255, 0.2)"},
    "trenink": {"bg": "rgba(57, 255, 20, 0.1)", "color": "#ccffc4", "border": "1px solid #39ff14", "shadow": "0 0 8px rgba(57, 255, 20, 0.15)"},
    "zavod": {"bg": "rgba(0, 243, 255, 0.1)", "color": "#ccfcff", "border": "1px solid #00f3ff", "shadow": "none"},
    "default": {
        "bg": "rgba(255, 255, 255, 0.05)", "color": "#e0e0e0", "border": "1px solid rgba(255,255,255,0.1)", "shadow": "none"
    }
}

# --- 2. CSS STYLY (Inject CSS) ---
def load_css():
    st.markdown(f"""
    <style>
        /* Import futuristického fontu */
        @import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@300;400;600&family=Orbitron:wght@400;700;900&display=swap');

        /* === GLOBÁLNÍ RESET === */
        html, body, [class*="css"] {{
            font-family: 'Exo 2', sans-serif;
            background-color: {DARK_BG};
            color: #e0e0e0;
        }}
        
        /* Nadpisy - Orbitron Font */
        h1, h2, h3, h4 {{
            font-family: 'Orbitron', sans-serif !important;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}

        /* === HEADER === */
        /* Gradientní text pro nadpis "Kalendář" */
        h1 span.gradient-text {{
            background: linear-gradient(90deg, {NEON_GREEN}, {NEON_BLUE});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 900;
            text-shadow: 0 0 20px rgba(57, 255, 20, 0.5);
        }}
        
        h1 img.header-logo {{
            height: 60px;
            filter: drop-shadow(0 0 10px {NEON_GREEN}); /* Záře kolem loga */
            transition: transform 0.3s;
        }}
        h1 img.header-logo:hover {{ transform: scale(1.1) rotate(5deg); }}

        /* === UI KOMPONENTY === */
        
        /* Tlačítka (Buttons) - Glassmorphism + Neon Border */
        .stButton > button {{
            background: rgba(255, 255, 255, 0.05) !important;
            color: {NEON_BLUE} !important;
            border: 1px solid rgba(0, 243, 255, 0.3) !important;
            border-radius: 8px !important;
            font-family: 'Orbitron', sans-serif !important;
            transition: all 0.3s ease !important;
            text-shadow: 0 0 5px rgba(0, 243, 255, 0.5);
        }}
        .stButton > button:hover {{
            background: rgba(0, 243, 255, 0.15) !important;
            border-color: {NEON_BLUE} !important;
            box-shadow: 0 0 15px rgba(0, 243, 255, 0.4) !important;
            transform: translateY(-2px);
        }}
        /* Primary button (Zapsat se) */
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, rgba(57, 255, 20, 0.2), rgba(57, 255, 20, 0.1)) !important;
            color: {NEON_GREEN} !important;
            border: 1px solid {NEON_GREEN} !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            box-shadow: 0 0 20px rgba(57, 255, 20, 0.6) !important;
        }}

        /* Inputy (Textová pole) */
        .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {{
            background-color: rgba(255, 255, 255, 0.03) !important;
            color: #fff !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 6px !important;
        }}
        .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within {{
            border-color: {NEON_BLUE} !important;
            box-shadow: 0 0 10px rgba(0, 243, 255, 0.2) !important;
        }}

        /* Checkbox & Radio */
        .stCheckbox span, .stRadio label {{ color: #ccc !important; }}

        /* === KALENDÁŘ A KARTY === */
        
        /* Dnešní den - Červená záře */
        .today-box {{
            background: rgba(255, 7, 58, 0.2);
            color: {NEON_RED};
            border: 1px solid {NEON_RED};
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 700;
            box-shadow: 0 0 15px rgba(255, 7, 58, 0.4);
            display: inline-block;
            margin-bottom: 8px;
        }}

        .day-number {{
            font-family: 'Orbitron', sans-serif;
            color: #666;
            font-size: 1.1em;
            display: block; text-align: center; margin-bottom: 8px;
        }}

        /* POPOVER (Bublina detailu) - High-Tech Glass */
        div[data-testid="stPopoverBody"] {{
            background-color: rgba(14, 17, 23, 0.95) !important; /* Tmavé sklo */
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            backdrop-filter: blur(20px);
            width: 800px !important;
            max-width: 95vw !important;
            max-height: 85vh !important;
            border-radius: 16px !important;
            box-shadow: 0 0 50px rgba(0, 0, 0, 0.8) !important;
        }}

        /* Floating Button */
        .floating-container button {{
            background: linear-gradient(135deg, {NEON_BLUE}, #0056b3) !important;
            box-shadow: 0 0 20px {NEON_BLUE} !important;
            border-radius: 50% !important;
        }}

        /* Skrytí default Streamlit prvků */
        #MainMenu, footer, header, .stDeployButton {{visibility: hidden;}}
        [data-testid="stToolbar"] {{visibility: hidden;}}
        [data-testid="stDecoration"] {{display:none;}}
        
    </style>
    """, unsafe_allow_html=True)

# === NOVÉ FUNKCE PRO HTML KOMPONENTY (Tmavý režim) ===

def inject_mobile_warning():
    """Vloží CSS/HTML pro varování 'Otoč telefon'."""
    st.markdown("""
    <style>
        #rotate-warning {
            display: none; 
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background-color: #000000; z-index: 999999;
            color: #00f3ff;
            flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px;
        }
        @media only screen and (orientation: portrait) and (max-width: 900px) {
            #rotate-warning { display: flex !important; }
            .stApp { overflow: hidden; }
        }
    </style>
    <div id="rotate-warning">
        <div style="font-size: 60px; text-shadow: 0 0 20px #00f3ff;">📱➡️🔄</div>
        <h1 style="color: #fff; margin-top: 20px; font-family: 'Orbitron';">SYSTEM LOCKED</h1>
        <p style="color: #ccc; font-size: 1.2rem;">Otoč zařízení pro přístup k datům.</p>
    </div>
    """, unsafe_allow_html=True)

def get_ics_button_html(b64_data, filename):
    """Futuristické tlačítko pro stažení kalendáře."""
    return f"""
    <a href="data:text/calendar;base64,{b64_data}" download="{filename}.ics" style="text-decoration:none;">
        <div style="
            background: rgba(255, 255, 255, 0.05); 
            border: 1px solid rgba(255, 255, 255, 0.2); 
            border-radius: 8px; padding: 6px 0px; text-align: center; 
            cursor: pointer; color: #fff; font-size: 1.2rem; 
            transition: all 0.3s;" 
        onmouseover="this.style.borderColor='#00f3ff'; this.style.boxShadow='0 0 10px #00f3ff';" 
        onmouseout="this.style.borderColor='rgba(255, 255, 255, 0.2)'; this.style.boxShadow='none';">
            📅
        </div>
    </a>
    """

def get_weather_card_html(w_icon, w_text, temp, rain, wind, sunset_html=""):
    """Vrátí HTML pro kartičku počasí (Dark Mode)."""
    # Barva borderu podle deště (Modrá = OK, Červená = Hodně prší)
    border_color = NEON_BLUE if rain < 2 else NEON_RED
    
    html = f"""
    <div style="
        margin-top: 10px; margin-bottom: 20px; padding: 15px; 
        background: linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); 
        border: 1px solid {border_color}; 
        border-left: 4px solid {border_color};
        border-radius: 10px; display: flex; align-items: center; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        color: white;">
        <div style="font-size: 2rem; margin-right: 15px; filter: drop-shadow(0 0 5px rgba(255,255,255,0.5));">{w_icon}</div>
        <div style="line-height: 1.3; flex-grow: 1;">
            <div style="font-weight: 700; font-family: 'Exo 2'; font-size: 1.1em; color: {border_color};">{w_text}, {temp}°C</div>
            <div style="font-size: 0.85rem; color: #aaa;">💧 {rain} mm • 💨 {wind} km/h</div>
        </div>
        {sunset_html}
    </div>
    """
    return html.replace("\n", "")

def get_map_buttons_html(link_mapy_cz, link_google, link_waze):
    """Tlačítka map v Cyber stylu."""
    style_base = "background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; padding: 12px; text-align: center; font-weight: 700; transition: 0.3s;"
    
    return f"""
    <div style="display: flex; gap: 10px; margin-top: -10px; margin-bottom: 20px; justify-content: space-between;">
        <a href="{link_mapy_cz}" target="_blank" style="text-decoration:none; flex: 1;">
            <div style="{style_base} color: #ff073a;" onmouseover="this.style.background='rgba(255, 7, 58, 0.1)'; this.style.borderColor='#ff073a';">🌲 Mapy.cz</div>
        </a>
        <a href="{link_google}" target="_blank" style="text-decoration:none; flex: 1;">
            <div style="{style_base} color: #4285F4;" onmouseover="this.style.background='rgba(66, 133, 244, 0.1)'; this.style.borderColor='#4285F4';">🚗 Google</div>
        </a>
        <a href="{link_waze}" target="_blank" style="text-decoration:none; flex: 1;">
            <div style="{style_base} color: #00f3ff;" onmouseover="this.style.background='rgba(0, 243, 255, 0.1)'; this.style.borderColor='#00f3ff';">🚙 Waze</div>
        </a>
    </div>
    """

def get_footer_html():
    return f"<div style='text-align: center; color: #555; font-size: 0.8em; font-family: \"Orbitron\", sans-serif; margin-top: 20px;'>SYSTEM: <span style='color:{NEON_GREEN}'>ONLINE</span> • RBK_NET v2.0 • 2026</div>"

# --- LOTTIE A OSTATNÍ ---
@st.cache_data(ttl=3600*24)
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except: return None

# Tady by to chtělo nějakou tech animaci, ale necháme fajfku, ta je univerzální
lottie_success = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_jbrw3hcz.json")

def badge(text, bg="#333", color="#fff"):
    # Ignorujeme bg/color parametry a používáme vlastní cyber styl
    return f"<span style='background-color: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.3); color: #fff; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-family: \"Orbitron\"; letter-spacing: 1px; text-transform: uppercase; margin-right: 6px;'>{text}</span>"
