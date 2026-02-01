import streamlit as st
import requests

# === 1. CSS STYLY & KONFIGURACE ===

def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #1f2937;
            background-color: #F9FAFB; /* Světlé pozadí celé appky */
        }
        
        /* === UI TWEAKS === */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display:none;}
        [data-testid="stToolbar"] {visibility: hidden;}
        [data-testid="stDecoration"] {display:none;}
        
        /* Nadpis */
        h1 span.gradient-text {
            background: -webkit-linear-gradient(45deg, #166534, #15803d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: -1px;
        }
        
        h1 {
            text-align: center !important;
            padding-bottom: 20px;
            display: flex; align-items: center; justify-content: center;
        }

        h1 img.header-logo {
            height: 55px; width: auto;
            margin-right: 15px; margin-top: -8px;
            transition: transform 0.3s ease;
        }
        h1 img.header-logo:hover { transform: scale(1.1) rotate(5deg); }

        h2, h3, h4 { color: #111827; font-weight: 700; }

        /* === POPOVER (MODÁLNÍ OKNO) === */
        div[data-testid="stPopoverBody"] {
            width: 800px !important;      
            max-width: 95vw !important;   
            max-height: 85vh !important;
            border-radius: 12px !important;
            box-shadow: 0 20px 40px rgba(0,0,0,0.15) !important;
            border: 1px solid #e5e7eb !important;
            background-color: #ffffff !important;
            padding: 24px !important; 
        }

        /* Dnešní den v kalendáři */
        .today-box {
            background: #DC2626; color: white;
            padding: 2px 8px; border-radius: 6px;
            font-weight: 700; display: inline-block;
            box-shadow: 0 2px 5px rgba(220, 38, 38, 0.3);
            margin-bottom: 5px; font-size: 0.9em;
        }
        .day-number {
            font-size: 1em; font-weight: 600; color: #6B7280;
            margin-bottom: 5px; display: block; text-align: center;
        }
        
        /* Inputy - Clean style */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #ffffff !important;
            border-radius: 8px !important;
            border: 1px solid #D1D5DB !important;
            color: #111 !important;
        }
        .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within {
            border-color: #2563EB !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
        }
        
        /* Checkbox */
        div[data-testid="stCheckbox"] label span { color: #374151 !important; }

    </style>
    """, unsafe_allow_html=True)

# === 2. CSS GENERÁTORY (ADAPTÉRY PRO NOVÝ DESIGN) ===

def get_nav_button_css():
    """
    Speciální styl JEN pro navigační tlačítka (Další/Předchozí).
    Vynucuje bílé pozadí a TMAVÝ text.
    """
    return """
        button {
            background-color: #ffffff !important;
            border: 1px solid #d1d5db !important;
            color: #111827 !important; /* Tmavě šedá až černá */
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
            transition: all 0.2s !important;
        }
        /* Musíme zacílit i vnitřní <p>, jinak to Streamlit přebije */
        button p {
            color: #111827 !important;
            font-weight: 700 !important;
        }
        button:hover {
            background-color: #f3f4f6 !important;
            border-color: #9ca3af !important;
            color: #000000 !important;
        }
        button:hover p {
            color: #000000 !important;
        }
    """

def get_event_button_css(style_dict):
    """
    Generuje CSS pro tlačítka akcí (Dashboard, Kalendář, Search).
    Používá 'Clean Mode' logiku - žádné neony, jen solidní background nebo border.
    """
    bg = style_dict.get("bg", "#ffffff")
    color = style_dict.get("color", "#1f2937")
    border = style_dict.get("border", "none")
    shadow = style_dict.get("shadow", "none")
    
    return f"""
        button {{
            background: {bg} !important;
            color: {color} !important;
            border: {border} !important;
            box-shadow: {shadow} !important;
            
            width: 100% !important;
            border-radius: 8px !important;
            padding: 8px 4px !important;
            min-height: 50px !important;
            height: auto !important;
            
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
            
            transition: all 0.2s ease !important;
        }}
        
        button p {{
            font-family: 'Inter', sans-serif !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            line-height: 1.3 !important;
            margin: 0 !important;
            color: {color} !important;
            text-align: center !important;
        }}

        button:hover {{
            filter: brightness(1.08);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
            z-index: 10;
        }}
    """

def get_transport_css(bg, color, border):
    """Clean verze tlačítek pro dopravu (v soupisce)."""
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
            font-weight: 600 !important;
            font-size: 0.8rem !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        }}
        button:hover {{ filter: brightness(0.95); }}
    """

def get_delete_css():
    """Clean verze tlačítka koše."""
    return f"""
        button {{
            background-color: white !important;
            border: 1px solid #fee2e2 !important;
            border-radius: 6px !important;
            color: #ef4444 !important;
            width: 35px !important; height: 35px !important;
            padding: 0 !important;
            margin: 0 auto !important;
            display: flex; justify-content: center; align-items: center;
        }}
        button:hover {{
            background-color: #fef2f2 !important;
            border-color: #ef4444 !important;
        }}
    """

def get_floating_chat_css():
    """CSS pro pozici chatbota (pravý dolní roh)."""
    return """
        {
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 9999;
        }
    """

# === 3. HTML KOMPONENTY ===

def inject_mobile_warning():
    st.markdown("""
    <style>
        #rotate-warning {
            display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background-color: #ffffff; z-index: 999999;
            flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px;
        }
        @media only screen and (orientation: portrait) and (max-width: 900px) {
            #rotate-warning { display: flex !important; }
            .stApp { overflow: hidden; }
        }
    </style>
    <div id="rotate-warning">
        <div style="font-size: 60px;">📱➡️🔄</div>
        <h1 style="color: #000; margin-top: 20px;">Otoč telefon</h1>
        <p style="color: #333; font-size: 1.2rem;">Pro správné zobrazení kalendáře otoč zařízení na šířku.</p>
    </div>
    """, unsafe_allow_html=True)

def get_ics_button_html(b64_data, filename):
    return f"""
    <a href="data:text/calendar;base64,{b64_data}" download="{filename}.ics" style="text-decoration:none;">
        <div style="background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px 15px; 
        text-align: center; cursor: pointer; color: #374151; font-weight: 600; font-size: 0.9rem; 
        display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
            📅 Do kalendáře
        </div>
    </a>
    """

def get_weather_card_html(w_icon, w_text, temp, rain, wind, sunset_html=""):
    bg_weather = "#eff6ff" if rain > 1 else "#ffffff"
    border_weather = "#bfdbfe" if rain > 1 else "#e5e7eb"
    
    return f"""
    <div style="margin-top: 15px; margin-bottom: 20px; padding: 15px; background-color: {bg_weather}; 
    border: 1px solid {border_weather}; border-radius: 10px; display: flex; align-items: center; 
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="font-size: 2.2rem; margin-right: 15px;">{w_icon}</div>
        <div style="line-height: 1.3; flex-grow: 1;">
            <div style="font-weight: 700; color: #1f2937; font-size: 1.1rem;">{w_text}, {temp}°C</div>
            <div style="font-size: 0.9rem; color: #4b5563;">💧 {rain} mm • 💨 {wind} km/h</div>
        </div>
        {sunset_html}
    </div>
    """

def get_footer_html():
    return "<div style='text-align: center; color: #9CA3AF; font-size: 0.8em; margin-top: 30px;'><b>Členská sekce RBK</b> • Clean Mode</div>"

def get_base64_image(image_path):
    # (Placeholder pokud ho utils.py potřebuje, nebo importuje z app.py)
    # Zde jen pro kompletnost, pokud by byl v styles.py
    import base64, os
    if not os.path.exists(image_path): return None
    with open(image_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode()

def badge(text, bg="#f3f4f6", color="#111"):
    return f"<span style='background-color: {bg}; color: {color}; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-right: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.05);'>{text}</span>"

# === 4. POMOCNÉ FUNKCE (Lottie atd.) ===

@st.cache_data(ttl=3600*24)
def load_lottieurl(url):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# === 5. BAREVNÁ SCHÉMATA (Clean Palette) ===
BARVY_AKCI = {
    "mcr": {
        "bg": "linear-gradient(135deg, #2563EB, #1D4ED8)", 
        "color": "white", "border": "none", "shadow": "0 4px 10px rgba(37, 99, 235, 0.3)"
    },
    "za": {"bg": "#DC2626", "color": "white", "border": "1px solid #B91C1C", "shadow": "0 2px 4px rgba(220, 38, 38, 0.2)"},
    "zb": {"bg": "#EA580C", "color": "white", "border": "1px solid #C2410C", "shadow": "0 2px 4px rgba(234, 88, 12, 0.2)"},
    "soustredeni": {"bg": "#D97706", "color": "white", "border": "1px solid #B45309", "shadow": "0 2px 4px rgba(217, 119, 6, 0.2)"},
    "oblastni": {"bg": "#3B82F6", "color": "white", "border": "1px solid #2563EB", "shadow": "0 2px 4px rgba(59, 130, 246, 0.2)"},
    "zimni_liga": {"bg": "#4B5563", "color": "white", "border": "1px solid #374151", "shadow": "0 2px 4px rgba(75, 85, 99, 0.2)"},
    "stafety": {"bg": "#9333EA", "color": "white", "border": "1px solid #7E22CE", "shadow": "0 2px 4px rgba(147, 51, 234, 0.2)"},
    "trenink": {"bg": "#16A34A", "color": "white", "border": "1px solid #15803D", "shadow": "0 2px 4px rgba(22, 163, 74, 0.2)"},
    "zavod": {"bg": "#0D9488", "color": "white", "border": "1px solid #0F766E", "shadow": "0 2px 4px rgba(13, 148, 136, 0.2)"},
    
    # Default je bílý s rámečkem
    "default": {
        "bg": "#FFFFFF", "color": "#374151", "border": "1px solid #E5E7EB", "shadow": "0 1px 2px rgba(0,0,0,0.05)"
    }
}

# Lottie (zůstává)
lottie_success = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_jbrw3hcz.json")
