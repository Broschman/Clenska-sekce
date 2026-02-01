import streamlit as st
import requests

# === 1. CSS STYLY (Clean/Light Design) ===
def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #1f2937;
        }
        
        /* === UI FIXY === */
        #MainMenu, footer, header, .stDeployButton {display:none !important;}
        [data-testid="stToolbar"] {visibility: hidden;}
        [data-testid="stDecoration"] {display:none;}
        
        /* Odkazy */
        a { color: #2563EB; text-decoration: none; }
        a:hover { text-decoration: underline; }

        /* Nadpis */
        h1 {
            text-align: center; margin: 0; padding-bottom: 20px;
            display: flex; align-items: center; justify-content: center; gap: 15px;
        }
        h1 img.header-logo { height: 60px; width: auto; transition: transform 0.3s ease; }
        h1 img.header-logo:hover { transform: scale(1.1) rotate(5deg); }
        
        h1 span.gradient-text {
            background: -webkit-linear-gradient(45deg, #166534, #15803d);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-weight: 900; text-transform: uppercase;
        }

        /* Bublina (Popover) */
        div[data-testid="stPopoverBody"] {
            width: 800px !important; max-width: 95vw !important; max-height: 85vh !important;
            border-radius: 12px !important; padding: 20px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1) !important; border: 1px solid #e5e7eb !important;
        }

        /* Plovoucí tlačítko (Chat) */
        .floating-container { position: fixed; bottom: 30px; right: 30px; z-index: 9999; }

        /* Tlačítka v kalendáři */
        .event-btn {
            width: 100%; border-radius: 6px; padding: 4px 8px; margin-bottom: 4px;
            text-align: left; font-size: 0.9rem; font-weight: 600;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            border: none; cursor: pointer; display: block;
            color: white; transition: transform 0.1s;
        }
        .event-btn:hover { transform: scale(1.02); filter: brightness(1.1); }
        
        /* Tlačítka dopravy */
        .transport-btn {
            padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600;
            text-align: center; cursor: pointer; border: 1px solid transparent; width: 100%;
        }

        /* Dnešní den */
        .today-box {
            background: #DC2626; color: white; padding: 2px 8px; border-radius: 12px;
            font-weight: 700; font-size: 0.9em; display: inline-block; margin-bottom: 5px;
        }
    </style>
    """, unsafe_allow_html=True)

# === 2. BAREVNÁ PALETA (Původní + Nové pro dopravu) ===
BARVY_AKCI = {
    "mcr": "#F59E0B",   # Oranžová/Zlatá
    "za": "#DC2626",    # Červená
    "zb": "#EA580C",    # Tmavě oranžová
    "soustredeni": "#D97706", 
    "oblastni": "#2563EB", # Modrá
    "zimni_liga": "#4B5563", # Šedá
    "stafety": "#9333EA", # Fialová
    "trenink": "#16A34A", # Zelená
    "zavod": "#0D9488",   # Tyrkysová
    "default": "#3B82F6"
}

# Barvy pro auta (HTML styly)
COLORS = {
    "driver": "background-color: #dcfce7; color: #166534; border: 1px solid #bbf7d0;",
    "passenger": "background-color: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe;",
    "waiting": "background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca;",
    "default": "background-color: #f3f4f6; color: #374151; border: 1px solid #e5e7eb;"
}

# === 3. POMOCNÉ FUNKCE (HTML) ===
def get_event_button_html(nazev, typ, key):
    """Vykreslí HTML tlačítko akce v kalendáři (místo těžkého Streamlit tlačítka)."""
    color = BARVY_AKCI.get(typ, BARVY_AKCI["default"])
    return f"""
    <button class="event-btn" style="background-color: {color};" onclick="parent.postMessage({{type: 'streamlit:setComponentValue', key: '{key}', value: true}}, '*')">
        {nazev}
    </button>
    """

def inject_mobile_warning(): st.markdown("<style>@media only screen and (orientation: portrait) and (max-width: 900px) {#rotate-warning {display:flex !important;} .stApp {overflow:hidden;}}</style>", unsafe_allow_html=True)
def get_footer_html(): return "<div style='text-align: center; color: #9CA3AF; font-size: 0.8em; margin-top: 20px;'>RBK 2026 • Light Version</div>"
def badge(text, bg="#f3f4f6", color="#111"): return f"<span style='background-color:{bg}; color:{color}; padding:4px 10px; border-radius:12px; font-size:0.75rem; font-weight:700;'>{text}</span>"
