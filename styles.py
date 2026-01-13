import streamlit as st
import requests

# --- 1. CSS STYLY ---
def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #1f2937;
        }
        /* === STEALTH MODE (SKRYTÍ UI STREAMLITU) === */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display:none;}
        [data-testid="stToolbar"] {visibility: hidden;}
        [data-testid="stDecoration"] {display:none;}

        /* Nadpis - Textová část s gradientem */
        h1 span.gradient-text {
            background: -webkit-linear-gradient(45deg, #166534, #15803d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: -1px;
        }
        
        /* Nadpis - Kontejner */
        h1 {
            text-align: center !important;
            margin: 0;
            padding-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px; /* Mezera mezi textem a logem */
        }

        /* Logo v nadpisu */
        h1 img.header-logo {
            height: 60px; /* Výška loga v nadpisu */
            width: auto;
            vertical-align: middle;
            margin-top: -5px; /* Jemné doladění pozice */
            transition: transform 0.3s ease;
        }
        
        h1 img.header-logo:hover {
            transform: scale(1.1) rotate(5deg);
        }

        h3 {
            font-weight: 700;
            color: #111;
            margin-bottom: 0.5rem;
        }

        /* === ŠIROKÁ BUBLINA (POPOVER) === */
        div[data-testid="stPopoverBody"] {
            width: 800px !important;      
            max-width: 95vw !important;   
            max-height: 85vh !important;
            border-radius: 12px !important;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2) !important;
            padding: 20px !important; 
            overflow-y: auto !important;
        }

        /* Plovoucí tlačítko */
        .floating-container {
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 9999;
        }
        .floating-container button {
            background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
            color: white !important;
            border: none !important;
            border-radius: 50px !important;
            box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4) !important;
            font-weight: 600 !important;
            padding: 12px 24px !important;
            transition: all 0.3s ease !important;
        }
        .floating-container button:hover {
            transform: translateY(-5px) scale(1.05) !important;
            box-shadow: 0 8px 25px rgba(37, 99, 235, 0.6) !important;
        }

        /* Dnešní den */
        .today-box {
            background: #DC2626;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 700;
            box-shadow: 0 4px 10px rgba(220, 38, 38, 0.4);
            display: inline-block;
            margin-bottom: 8px;
        }

        .day-number {
            font-size: 1.1em;
            font-weight: 700;
            color: #6B7280;
            margin-bottom: 8px;
            display: block;
            text-align: center;
        }
        
        div[data-testid="column"] {
            padding: 2px;
        }
        
        /* Inputy */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            border-radius: 8px !important;
            border: 1px solid #E5E7EB;
        }
        .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within {
            border-color: #2563EB !important;
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2) !important;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOTTIE ANIMACE ---
@st.cache_data(ttl=3600*24)
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# Načtení animace "Success" (zelená fajfka) - toto se provede při importu
lottie_success = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_jbrw3hcz.json")

# --- 3. DEFINICE BAREV ---
BARVY_AKCI = {
    "mcr": {
        "bg": "linear-gradient(90deg, #EF4444, #F59E0B, #10B981, #3B82F6, #8B5CF6)", 
        "color": "white", "border": "none", "shadow": "0 4px 6px rgba(0,0,0,0.15)"
    },
    "za": {"bg": "#DC2626", "color": "white", "border": "none", "shadow": "0 2px 4px rgba(220, 38, 38, 0.3)"},
    "zb": {"bg": "#EA580C", "color": "white", "border": "none", "shadow": "0 2px 4px rgba(234, 88, 12, 0.3)"},
    "soustredeni": {"bg": "#D97706", "color": "white", "border": "none", "shadow": "0 2px 4px rgba(217, 119, 6, 0.3)"},
    "oblastni": {"bg": "#2563EB", "color": "white", "border": "none", "shadow": "0 2px 4px rgba(37, 99, 235, 0.3)"},
    "zimni_liga": {"bg": "#4B5563", "color": "white", "border": "none", "shadow": "0 2px 4px rgba(75, 85, 99, 0.3)"},
    "stafety": {"bg": "#9333EA", "color": "white", "border": "none", "shadow": "0 2px 4px rgba(147, 51, 234, 0.3)"},
    "trenink": {"bg": "#16A34A", "color": "white", "border": "none", "shadow": "0 2px 4px rgba(22, 163, 74, 0.3)"},
    "zavod": {"bg": "#0D9488", "color": "white", "border": "none", "shadow": "0 2px 4px rgba(13, 148, 136, 0.3)"},
    "default": {
        "bg": "#FFFFFF", "color": "#374151", "border": "1px solid #E5E7EB", "shadow": "0 1px 2px rgba(0,0,0,0.05)"
    }
}

# ... (tady nahoře máš BARVY_AKCI = { ... }) ...

# === GLOBÁLNÍ STYLY A ANIMACE ===
GLOBAL_CSS = """
<style>
    
    /* 2. ODSTRANĚNÍ OKRAJŮ NA MOBILU */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    @media (max-width: 600px) {
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
    }

    /* 3. ANIMACE PRO BLIKAJÍCÍ RÁMEČEK (Deadline) */
    @keyframes pulse-red {
        0% {
            border-color: #ef4444;
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
        }
        70% {
            border-color: #b91c1c;
            box-shadow: 0 0 0 6px rgba(239, 68, 68, 0);
        }
        100% {
            border-color: #ef4444;
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
        }
    }

    /* 4. VAROVÁNÍ "OTOČ TELEFON" (Opona) */
    #rotate-warning {
        display: none; 
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        background-color: #ffffff;
        z-index: 999999;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        padding: 20px;
    }
    @media only screen and (orientation: portrait) and (max-width: 900px) {
        #rotate-warning { display: flex !important; }
        .stApp { overflow: hidden; }
    }
</style>

<div id="rotate-warning">
    <div style="font-size: 60px;">📱➡️🔄</div>
    <h1 style="color: #000000; margin-top: 20px; font-family: sans-serif;">Otoč telefon</h1>
    <p style="color: #333333; font-size: 1.2rem; margin-top: 10px; font-family: sans-serif;">
        Pro správné zobrazení kalendáře<br>
        prosím otoč zařízení na šířku.
    </p>
</div>
"""

def badge(text, bg="#f3f4f6", color="#111"):
    return f"<span style='background-color: {bg}; color: {color}; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-right: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>{text}</span>"
