import streamlit as st
import requests

# === 1. DEFINICE BAREV ===

# Proměnné pro app.py (Kompatibilita)
NEON_GREEN = "#16A34A"
NEON_BLUE = "#2563EB"
NEON_RED = "#DC2626"
NEON_ORANGE = "#EA580C"
DARK_BG = "#FFFFFF"

# Barvy pro tlačítka v tabulce (utils.py)
COLORS = {
    # Řidič: Zelené pozadí, Bílý text
    "driver_bg": "#16A34A", "driver_text": "#FFFFFF",
    # Pasažér: Modré pozadí, Bílý text
    "passenger_bg": "#2563EB", "passenger_text": "#FFFFFF",
    # Chci odvoz: Červené pozadí, Bílý text
    "waiting_bg": "#DC2626", "waiting_text": "#FFFFFF",
    # Neutrální: Šedé pozadí, ČERNÝ TEXT (!)
    "gray_bg": "#F3F4F6", "gray_text": "#1F2937"
}

# Definice barev pro akce (Kalendář)
BARVY_AKCI = {
    "mcr": {"bg": "linear-gradient(90deg, #EF4444, #F59E0B, #10B981)", "glow": "#EF4444"},
    "za": {"bg": "#DC2626", "glow": "#DC2626"},
    "zb": {"bg": "#EA580C", "glow": "#EA580C"},
    "soustredeni": {"bg": "#D97706", "glow": "#D97706"},
    "oblastni": {"bg": "#2563EB", "glow": "#2563EB"},
    "zimni_liga": {"bg": "#4B5563", "glow": "#4B5563"},
    "stafety": {"bg": "#9333EA", "glow": "#9333EA"},
    "trenink": {"bg": "#16A34A", "glow": "#16A34A"},
    "zavod": {"bg": "#0D9488", "glow": "#0D9488"},
    "default": {"bg": "#FFFFFF", "glow": "#E5E7EB"}
}

# === 2. CSS STYLY ===
def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #1f2937; /* Defaultní černá */
        }
        
        a { color: #2563EB !important; text-decoration: none; }
        a:hover { text-decoration: underline; }

        h1, h2, h3, h4 { color: #111827 !important; font-weight: 700 !important; }
        
        .stButton > button { font-weight: 600 !important; border-radius: 8px !important; }
        
        #MainMenu, footer, header, .stDeployButton, [data-testid="stToolbar"], [data-testid="stDecoration"] {
            display: none !important; visibility: hidden !important;
        }

        h1 span.gradient-text {
            background: -webkit-linear-gradient(45deg, #166534, #15803d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        h1 { display: flex; align-items: center; justify-content: center; gap: 15px; padding-bottom: 20px; }
        h1 img.header-logo { height: 60px; width: auto; transition: transform 0.3s; }
        h1 img.header-logo:hover { transform: scale(1.1) rotate(5deg); }

        div[data-testid="stPopoverBody"] {
            width: 800px !important; max-width: 95vw !important; max-height: 85vh !important;
            border-radius: 12px !important; padding: 25px !important;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1) !important;
            border: 1px solid #e5e7eb !important;
        }

        .floating-container { position: fixed; bottom: 30px; right: 30px; z-index: 9999; }

        .today-box {
            background: #DC2626; color: white; padding: 4px 12px; border-radius: 20px;
            font-weight: 700; box-shadow: 0 4px 10px rgba(220, 38, 38, 0.4); display: inline-block;
        }
        .day-number { font-size: 1.1em; font-weight: 700; color: #6B7280; display: block; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# === 3. CSS GENERÁTORY ===

def get_cyber_button_css(bg_color, glow_color):
    """
    CSS pro tlačítka v kalendáři a dashboardu.
    """
    bg_lower = str(bg_color).lower()
    
    # Seznam barev, které jsou tmavé/syté a vyžadují BÍLÝ text
    dark_bg_triggers = [
        "gradient", # MČR
        "#dc2626", "#ef4444", # Červená
        "#ea580c", "#d97706", # Oranžová
        "#2563eb", "#3b82f6", # Modrá
        "#16a34a", "#22c55e", # Zelená
        "#4b5563",            # Tmavě šedá
        "#9333ea",            # Fialová
        "#0d9488"             # Tyrkysová
    ]
    
    # Zjištění, zda máme použít bílý text
    use_white_text = any(trigger in bg_lower for trigger in dark_bg_triggers)

    # Nastavení barev
    text_col = "#FFFFFF" if use_white_text else "#1F2937" # Bílá vs Tmavě šedá
    border = "none" if use_white_text else "1px solid #E5E7EB"
    
    # Stín: Standardní pro bílá tlačítka, žádný pro barevná (mají plochý design)
    shadow = "0 1px 2px rgba(0,0,0,0.05)" if not use_white_text else "none"

    return f"""
        button {{
            background: {bg_color} !important;
            color: {text_col} !important;
            border: {border} !important;
            box-shadow: {shadow} !important;
            border-radius: 8px !important;
            padding: 8px 10px !important;
            min-height: 50px !important;
            width: 100% !important;
            transition: all 0.2s !important;
        }}
        button p {{ 
            color: {text_col} !important; 
            font-weight: 600 !important; 
            font-size: 15px !important; 
        }}
        button:hover {{ 
            transform: translateY(-1px); 
            opacity: 0.9;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        }}
    """

def get_transport_css(bg, color, border):
    """
    CSS pro malá tlačítka dopravy. Zde barvu textu řídí přímo utils.py.
    """
    return f"""
        button {{
            background-color: {bg} !important;
            color: {color} !important;
            border: {border} !important;
            border-radius: 6px !important;
            padding: 4px 12px !important;
            min-height: 32px !important;
            font-size: 0.85rem !important;
            width: 100% !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        }}
        button p {{ margin: 0 !important; font-weight: 600 !important; color: {color} !important; }}
        button:hover {{ filter: brightness(1.05); }}
    """

def get_delete_css():
    return """
        button {
            background: transparent !important; border: 1px solid #fee2e2 !important; color: #ef4444 !important;
            width: 38px !important; height: 38px !important; border-radius: 6px !important;
        }
        button:hover { background: #fee2e2 !important; }
    """

def get_floating_chat_css():
    return "{position: fixed; bottom: 90px; right: 30px; z-index: 99999;}"

# === 4. HTML KOMPONENTY ===
def inject_mobile_warning(): st.markdown("<style>@media only screen and (orientation: portrait) and (max-width: 900px) {#rotate-warning {display:flex !important;} .stApp {overflow:hidden;}}</style>", unsafe_allow_html=True)
def get_ics_button_html(b64, name): return f"""<a href="data:text/calendar;base64,{b64}" download="{name}.ics" style="text-decoration:none;"><div style="background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:6px; text-align:center; color:#374151; font-size:1.2rem; transition:0.2s;" onmouseover="this.style.background='#f9fafb'" onmouseout="this.style.background='#fff'">📅</div></a>"""
def get_weather_card_html(icon, text, temp, rain, wind, sunset=""):
    bg = "#eff6ff" if rain > 1 else "#f9fafb"
    return f"""<div style="padding:10px; background:{bg}; border:1px solid #e5e7eb; border-radius:10px; display:flex; align-items:center; box-shadow:0 1px 2px rgba(0,0,0,0.05); color:#1f2937;"><div style="font-size:2rem; margin-right:15px;">{icon}</div><div><div style="font-weight:700;">{text}, {temp}°C</div><div style="font-size:0.85rem; color:#6b7280;">💧 {rain} mm • 💨 {wind} km/h</div></div>{sunset}</div>"""
def get_footer_html(): return "<div style='text-align: center; color: #9CA3AF; font-size: 0.8em; margin-top:20px;'>RBK 2026 • Light Mode</div>"
def badge(text, bg="#f3f4f6", color="#111"): return f"<span style='background-color:{bg}; color:{color}; padding:4px 10px; border-radius:12px; font-size:0.75rem; font-weight:700;'>{text}</span>"
@st.cache_data(ttl=3600*24)
def load_lottieurl(url): 
    try: return requests.get(url).json() 
    except: return None
lottie_success = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_jbrw3hcz.json")
