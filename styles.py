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
    "mcr": {"bg": "rgba(255, 7, 58, 0.1)", "glow": "#ff073a"},
    "za": {"bg": "rgba(255, 7, 58, 0.1)", "glow": "#ef4444"},
    "zb": {"bg": "rgba(249, 115, 22, 0.1)", "glow": "#f97316"},
    "soustredeni": {"bg": "rgba(234, 179, 8, 0.1)", "glow": "#eab308"},
    "oblastni": {"bg": "rgba(59, 130, 246, 0.1)", "glow": "#3b82f6"},
    "zimni_liga": {"bg": "rgba(107, 114, 128, 0.1)", "glow": "#9ca3af"},
    "stafety": {"bg": "rgba(168, 85, 247, 0.1)", "glow": "#a855f7"},
    "trenink": {"bg": "rgba(34, 197, 94, 0.1)", "glow": "#22c55e"},
    "zavod": {"bg": "rgba(20, 184, 166, 0.1)", "glow": "#14b8a6"},
    "default": {"bg": "rgba(255, 255, 255, 0.05)", "glow": "#ffffff"}
}

def load_css():
    st.markdown(f"""
    <style>
        /* FONT FIX: Rajdhani pro češtinu */
        @import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@300;400;600;800&family=Rajdhani:wght@500;600;700&display=swap&subset=latin,latin-ext');

        /* === GLOBÁLNÍ RESET === */
        body, p, h1, h2, h3, h4, h5, h6, li, a, label, input, textarea, button {{
            font-family: 'Exo 2', sans-serif !important;
            color: #e0e0e0;
        }}
        
        /* Nadpisy */
        h1, h2, h3 {{
            font-family: 'Rajdhani', 'Exo 2', sans-serif !important;
            letter-spacing: 1px;
            text-transform: uppercase;
            font-weight: 700 !important;
        }}
        h1 {{ font-size: 2.5rem !important; }}

        /* Logo, Pozadí */
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

        .stApp {{
            background-color: {DARK_BG};
            background-image: 
                radial-gradient(circle at 50% 30%, rgba(0, 243, 255, 0.04) 0%, transparent 60%),
                repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.02) 0px, rgba(255, 255, 255, 0.02) 1px, transparent 1px, transparent 40px),
                repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.02) 0px, rgba(255, 255, 255, 0.02) 1px, transparent 1px, transparent 40px);
            background-attachment: fixed;
        }}

        /* === GLOBÁLNÍ DEFAULT PRO TLAČÍTKA === */
        /* Zde nastavíme jen to nejnutnější. ŽÁDNÉ PŘEBÍJENÍ FONT-WEIGHT! */
        .stButton > button {{
            background: rgba(255, 255, 255, 0.05);
            color: {NEON_BLUE};
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            /* Zlatý střed - ani tučné, ani tenké. Specifické styly si to přepíšou. */
            font-weight: 500; 
            transition: all 0.3s ease;
        }}

        /* Primary tlačítko (Zapsat se) - to chceme vždy výrazné */
        button[kind="primary"] {{
            background: rgba(57, 255, 20, 0.1) !important;
            color: {NEON_GREEN} !important;
            border: 1px solid {NEON_GREEN} !important;
            font-weight: 700 !important;
        }}

        /* Kalendář box */
        .today-box {{
            background: rgba(255, 7, 58, 0.2); 
            color: {NEON_RED}; 
            border: 1px solid {NEON_RED};
            display: inline-flex; align-items: center; justify-content: center;    
            width: 30px; height: 30px; border-radius: 8px; font-weight: 800;
            box-shadow: 0 0 15px rgba(255, 7, 58, 0.4);
            margin: 0 auto 8px auto;    
        }}
        .day-number {{ color: #888; font-weight: 600; display: block; text-align: center; margin-bottom: 8px; }}

        div[data-testid="stPopoverBody"] {{
            background-color: rgba(14, 17, 23, 0.95) !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            backdrop-filter: blur(20px);
            border-radius: 12px !important;
            box-shadow: 0 0 40px rgba(0, 0, 0, 0.8) !important;
        }}

        /* Plovoucí tlačítko */
        .floating-container button {{
            background: linear-gradient(135deg, {NEON_BLUE}, #0056b3) !important;
            box-shadow: 0 0 20px {NEON_BLUE} !important;
            border-radius: 8px !important;
            padding: 10px 20px !important;
            height: auto !important; width: auto !important;
        }}

        #MainMenu, footer, header, .stDeployButton {{visibility: hidden;}}
        [data-testid="stToolbar"] {{visibility: hidden;}}
        [data-testid="stDecoration"] {{display:none;}}
    </style>
    """, unsafe_allow_html=True)

# --- GENERÁTORY STYLŮ (IZOLOVANÉ) ---

def get_cyber_button_css(bg_color, glow_color):
    """
    PRO: Kalendář, Dashboard, Hledání
    VZHLED: Tučné, Svítící, Větší padding
    """
    return f"""
        button {{
            background: {bg_color} !important;
            border: none !important;
            box-shadow: inset 0 0 0 1px {glow_color}, 0 0 8px {glow_color}44 !important;
            color: #e0e0e0 !important;
            
            width: 100% !important;
            border-radius: 8px !important;
            padding: 12px 15px !important;
            text-align: left !important;
            margin-bottom: 8px !important;
            white-space: normal !important;
            height: auto !important;
            min-height: 50px !important;
            
            transition: box-shadow 0.2s ease !important;
        }}
        
        /* Cílíme na obsah tlačítka - VYNUCUJEME TUČNÉ */
        button p, button div {{
            font-family: 'Exo 2', sans-serif !important;
            font-weight: 700 !important;   /* <--- TUČNÉ */
            font-size: 1.05rem !important;
            letter-spacing: 0.5px !important;
            line-height: 1.4 !important;
            color: #ffffff !important;
        }}
        
        button:hover {{
            box-shadow: inset 0 0 0 2px {glow_color}, 0 0 25px {glow_color} !important;
            background-color: {glow_color}22 !important;
            color: #fff !important;
            z-index: 99 !important;
            border-radius: 8px !important;
        }}
    """

def get_transport_css(bg, color, border):
    """
    PRO: Doprava
    VZHLED: Jemné, Tenké, Malé
    """
    return f"""
        button {{
            background-color: {bg} !important;
            color: {color} !important;
            border: {border} !important;
            border-radius: 6px !important;
            padding: 2px 8px !important;
            height: auto !important;
            min-height: 28px !important;
            width: 100% !important;
            transition: all 0.2s ease !important;
        }}
        
        /* Cílíme na obsah tlačítka - VYNUCUJEME TENKÉ */
        button p, button div {{
            font-family: 'Exo 2', sans-serif !important;
            font-weight: 400 !important;  /* <--- TENKÉ */
            font-size: 0.85rem !important;
            line-height: 1.2 !important;
            margin: 0 !important;
            padding: 0 !important;
            letter-spacing: 0px !important;
        }}

        button:hover {{
            filter: brightness(1.2);
            border-radius: 6px !important;
        }}
    """

def get_delete_css():
    """PRO: Koš"""
    return f"""
        button {{
            background-color: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 6px !important;
            color: #ff073a !important;
            padding: 0 !important;
            width: 40px !important;
            height: 40px !important;
            min-height: 40px !important;
            display: block !important;
            margin: 0 auto !important;
        }}
        
        button > div {{
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            width: 100% !important;
            height: 100% !important;
            margin: 0 !important;
        }}
        
        button:hover {{
            color: #ff5f1f !important;
            background-color: rgba(255, 7, 58, 0.2) !important;
            border-color: #ff073a !important;
            transform: scale(1.05);
            margin: 0 auto !important;
        }}
    """

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
