import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_extras.stylable_container import stylable_container
from streamlit_lottie import st_lottie, st_lottie_spinner # <--- NOVÉ: Animace
import requests # <--- NOVÉ: Pro stažení animace
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import time
import base64
import os

# --- 1. NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Kalendář RBK", page_icon="🌲", layout="wide")

# --- NOVÉ: NAČTENÍ LOTTIE ANIMACE ---
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# Načtení animace "Success" (zelená fajfka)
lottie_success = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_jbrw3hcz.json")

# --- CSS VZHLED (DESIGN 4.2 - LOGO IN HEADER) ---
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

    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- DEFINICE BAREV ---
BARVY_AKCI = {
    "mcr": {
        "bg": "linear-gradient(90deg, #EF4444, #F59E0B, #10B981, #3B82F6, #8B5CF6)", 
        "color": "white",
        "border": "none",
        "shadow": "0 4px 6px rgba(0,0,0,0.15)"
    },
    "za": {
        "bg": "#DC2626", 
        "color": "white",
        "border": "none",
        "shadow": "0 2px 4px rgba(220, 38, 38, 0.3)"
    },
    "zb": {
        "bg": "#EA580C", 
        "color": "white",
        "border": "none",
        "shadow": "0 2px 4px rgba(234, 88, 12, 0.3)"
    },
    "soustredeni": {
        "bg": "#D97706", 
        "color": "white",
        "border": "none",
        "shadow": "0 2px 4px rgba(217, 119, 6, 0.3)"
    },
    "oblastni": {
        "bg": "#2563EB", 
        "color": "white",
        "border": "none",
        "shadow": "0 2px 4px rgba(37, 99, 235, 0.3)"
    },
    "zimni_liga": {
        "bg": "#4B5563", 
        "color": "white",
        "border": "none",
        "shadow": "0 2px 4px rgba(75, 85, 99, 0.3)"
    },
    "stafety": {
        "bg": "#9333EA", 
        "color": "white",
        "border": "none",
        "shadow": "0 2px 4px rgba(147, 51, 234, 0.3)"
    },
    "trenink": {
        "bg": "#16A34A", 
        "color": "white",
        "border": "none",
        "shadow": "0 2px 4px rgba(22, 163, 74, 0.3)"
    },
    "default": {
        "bg": "#FFFFFF",
        "color": "#374151",
        "border": "1px solid #E5E7EB",
        "shadow": "0 1px 2px rgba(0,0,0,0.05)"
    }
}

# --- POMOCNÉ FUNKCE ---
def badge(text, bg="#f3f4f6", color="#111"):
    return f"<span style='background-color: {bg}; color: {color}; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-right: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>{text}</span>"

def get_base64_image(image_path):
    """Načte obrázek a převede ho na base64 string pro HTML."""
    if not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# --- HLAVIČKA S LOGEM ---
col_dummy, col_title, col_help = st.columns([1, 10, 1], vertical_alignment="center")

with col_title:
    # Cesta k tvému logu
    logo_path = "logo_rbk.jpg" 
    
    # Zkusíme načíst lokální logo, jinak placeholder
    logo_b64 = get_base64_image(logo_path)
    
    if logo_b64:
        img_src = f"data:image/png;base64,{logo_b64}"
    else:
        # Placeholder (pokud soubor neexistuje)
        img_src = "https://cdn-icons-png.flaticon.com/512/2051/2051939.png"

    # HTML Nadpis s vloženým obrázkem
    st.markdown(f"""
        <h1>
            <span class="gradient-text">🌲 Kalendář</span>
            <img src="{img_src}" class="header-logo" alt="RBK Logo">
        </h1>
    """, unsafe_allow_html=True)

with col_help:
    with st.popover("❔", help="Legenda"):
        st.markdown("<h3 style='margin-bottom:10px;'>🎨 Legenda barev</h3>", unsafe_allow_html=True)
        st.markdown("""
        <div style="display: grid; gap: 10px; font-size: 0.9rem;">
            <div style="display: flex; align-items: center;">
                <span style="width: 20px; height: 20px; border-radius: 6px; background: linear-gradient(90deg, #EF4444, #F59E0B, #10B981); margin-right: 10px;"></span>
                <b>MČR / Mistrovství</b>
            </div>
            <div style="display: flex; align-items: center;">
                <span style="width: 20px; height: 20px; border-radius: 6px; background: #DC2626; margin-right: 10px;"></span>
                <b>Závod ŽA</b> (Licence A)
            </div>
            <div style="display: flex; align-items: center;">
                <span style="width: 20px; height: 20px; border-radius: 6px; background: #EA580C; margin-right: 10px;"></span>
                <b>Závod ŽB</b> (Licence B)
            </div>
            <div style="display: flex; align-items: center;">
                <span style="width: 20px; height: 20px; border-radius: 6px; background: #D97706; margin-right: 10px;"></span>
                <b>Soustředění</b> (Přednostní)
            </div>
            <div style="display: flex; align-items: center;">
                <span style="width: 20px; height: 20px; border-radius: 6px; background: #2563EB; margin-right: 10px;"></span>
                <b>Oblastní žebříček</b>
            </div>
             <div style="display: flex; align-items: center;">
                <span style="width: 20px; height: 20px; border-radius: 6px; background: #9333EA; margin-right: 10px;"></span>
                <b>Štafety</b>
            </div>
            <div style="display: flex; align-items: center;">
                <span style="width: 20px; height: 20px; border-radius: 6px; background: #16A34A; margin-right: 10px;"></span>
                <b>Trénink</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        st.info("💡 **Tip:** Kliknutím na akci se otevře detail.")


# --- 2. PŘIPOJENÍ A NAČTENÍ DAT ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_ID = "1lW6DpUQBSm5heSO_HH9lDzm0x7t1eo8dn6FpJHh2y6U"

url_akce = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=akce"
url_prihlasky = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=prihlasky"
url_jmena = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=jmena"
url_navrhy = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=navrhy"

try:
    df_akce = pd.read_csv(url_akce)
    df_akce['datum'] = pd.to_datetime(df_akce['datum'], dayfirst=True, errors='coerce').dt.date
    if 'datum_do' in df_akce.columns:
        df_akce['datum_do'] = pd.to_datetime(df_akce['datum_do'], dayfirst=True, errors='coerce').dt.date
        df_akce['datum_do'] = df_akce['datum_do'].fillna(df_akce['datum'])
    else:
        df_akce['datum_do'] = df_akce['datum']
    df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], dayfirst=True, errors='coerce').dt.date
    df_akce = df_akce.dropna(subset=['datum'])
    def get_deadline(row):
        if pd.isna(row['deadline']):
            return row['datum'] - timedelta(days=14)
        return row['deadline']
    df_akce['deadline'] = df_akce.apply(get_deadline, axis=1)
    if 'id' in df_akce.columns:
        df_akce['id'] = df_akce['id'].astype(str).str.replace(r'\.0$', '', regex=True)
    
    try:
        df_prihlasky = pd.read_csv(url_prihlasky)
        if 'doprava' not in df_prihlasky.columns: df_prihlasky['doprava'] = ""
        if 'id_akce' not in df_prihlasky.columns: df_prihlasky['id_akce'] = ""
        df_prihlasky['id_akce'] = df_prihlasky['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
    except:
        df_prihlasky = pd.DataFrame(columns=["id_akce", "název", "jméno", "poznámka", "doprava", "čas zápisu"])
        
    try:
        df_jmena = pd.read_csv(url_jmena)
        seznam_jmen = sorted(df_jmena['jméno'].dropna().unique().tolist())
    except:
        seznam_jmen = []
        
except Exception as e:
    st.error(f"⚠️ Chyba načítání dat: {e}")
    st.stop()

# --- 3. LOGIKA KALENDÁŘE ---
if 'vybrany_datum' not in st.session_state:
    st.session_state.vybrany_datum = date.today()

col_nav1, col_nav2, col_nav3 = st.columns([2, 5, 2])
with col_nav1:
    if st.button("⬅️ Předchozí", use_container_width=True):
        curr = st.session_state.vybrany_datum
        prev_month = curr.replace(day=1) - timedelta(days=1)
        st.session_state.vybrany_datum = prev_month.replace(day=1)

with col_nav3:
    if st.button("Další ➡️", use_container_width=True):
        curr = st.session_state.vybrany_datum
        next_month = (curr.replace(day=28) + timedelta(days=4)).replace(day=1)
        st.session_state.vybrany_datum = next_month

rok = st.session_state.vybrany_datum.year
mesic = st.session_state.vybrany_datum.month
ceske_mesice = ["", "Leden", "Únor", "Březen", "Duben", "Květen", "Červen", "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"]

with col_nav2:
    st.markdown(f"<h2 style='text-align: center; color: #111; margin-top: -5px; font-weight: 800; letter-spacing: -0.5px;'>{ceske_mesice[mesic]} <span style='color:#666'>{rok}</span></h2>", unsafe_allow_html=True)

# --- 4. VYKRESLENÍ MŘÍŽKY ---
cal = calendar.Calendar(firstweekday=0)
month_days = cal.monthdayscalendar(rok, mesic)

dny_v_tydnu = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
cols_header = st.columns(7)
for i, d in enumerate(dny_v_tydnu):
    cols_header[i].markdown(f"<div style='text-align: center; color: #6B7280; font-weight: 700; text-transform: uppercase; font-size: 0.8rem; margin-bottom: 10px;'>{d}</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 0 0 15px 0; border: 0; border-top: 1px solid #E5E7EB;'>", unsafe_allow_html=True)

dnes = date.today()

for tyden in month_days:
    cols = st.columns(7, gap="small")
    
    for i, den_cislo in enumerate(tyden):
        with cols[i]:
            if den_cislo == 0:
                st.write("")
                continue
            
            aktualni_den = date(rok, mesic, den_cislo)
            
            if aktualni_den == dnes:
                st.markdown(f"<div style='text-align: center;'><span class='today-box'>{den_cislo}</span></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='day-number'>{den_cislo}</span>", unsafe_allow_html=True)

            maska_dne = (df_akce['datum'] <= aktualni_den) & (df_akce['datum_do'] >= aktualni_den)
            akce_dne = df_akce[maska_dne]
            
            for _, akce in akce_dne.iterrows():
                je_po_deadlinu = dnes > akce['deadline']
                je_dnes_deadline = dnes == akce['deadline']
                
                akce_id_str = str(akce['id']) if 'id' in df_akce.columns else ""
                unique_key = f"{akce_id_str}_{aktualni_den.strftime('%Y%m%d')}"

                typ_udalosti = str(akce['typ']).lower().strip() if 'typ' in df_akce.columns and pd.notna(akce['typ']) else ""
                druh_akce = str(akce['druh']).lower().strip() if 'druh' in df_akce.columns and pd.notna(akce['druh']) else "ostatní"
                
                je_stafeta = "štafety" in typ_udalosti
                je_soustredeni = "soustředění" in typ_udalosti
                
                zavodni_slova = ["závod", "mčr", "žebříček", "liga", "mistrovství", "štafety", "ža", "žb"]
                je_zavod_obecne = any(s in typ_udalosti for s in zavodni_slova)

                style_key = "default"
                typ_label_short = "AKCE"

                if "mčr" in typ_udalosti or "mistrovství" in typ_udalosti:
                    style_key = "mcr"
                    typ_label_short = "MČR"
                elif "ža" in typ_udalosti or "žebříček a" in typ_udalosti:
                    style_key = "za"
                    typ_label_short = "ŽA"
                elif "žb" in typ_udalosti or "žebříček b" in typ_udalosti:
                    style_key = "zb"
                    typ_label_short = "ŽB"
                elif "soustředění" in typ_udalosti:
                    style_key = "soustredeni"
                    typ_label_short = "SOUSTŘEDĚNÍ"
                elif "oblastní" in typ_udalosti or "žebříček" in typ_udalosti:
                    style_key = "oblastni"
                    typ_label_short = "OBLASTNÍ"
                elif "zimní liga" in typ_udalosti or "bzl" in typ_udalosti:
                    style_key = "zimni_liga"
                    typ_label_short = "ZIMNÍ LIGA"
                elif "štafety" in typ_udalosti:
                    style_key = "stafety"
                    typ_label_short = "ŠTAFETY"
                elif "trénink" in typ_udalosti:
                    style_key = "trenink"
                    typ_label_short = "TRÉNINK"
                elif je_zavod_obecne:
                    style_key = "oblastni"
                    typ_label_short = "ZÁVOD"

                vybrany_styl = BARVY_AKCI.get(style_key, BARVY_AKCI["default"])

                ikony_mapa = {
                    "les": "🌲", 
                    "krátká trať": "🌲", 
                    "klasická trať": "🌲",
                    "sprint": "🏙️", 
                    "nočák": "🌗"
                }
                emoji_druh = ikony_mapa.get(druh_akce, "🏃")

                nazev_full = akce['název']
                display_text = nazev_full.split('-')[0].strip() if '-' in nazev_full else nazev_full
                final_text = f"{emoji_druh} {display_text}".strip()
                
                if je_po_deadlinu:
                    final_text = "🔒 " + final_text

                with stylable_container(
                    key=f"btn_container_{unique_key}",
                    css_styles=f"""
                        button {{
                            background: {vybrany_styl['bg']} !important;
                            color: {vybrany_styl['color']} !important;
                            border: {vybrany_styl['border']} !important;
                            width: 100%;
                            border-radius: 8px;
                            padding: 8px 10px !important;
                            transition: all 0.2s ease;
                            text-align: left;
                            font-size: 0.85rem;
                            font-weight: 600;
                            box-shadow: {vybrany_styl.get('shadow', 'none')};
                            margin-bottom: 6px;
                            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
                        }}
                        button:hover {{
                            filter: brightness(1.1);
                            transform: translateY(-2px);
                            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
                            z-index: 5;
                        }}
                    """
                ):
                    with st.popover(final_text, use_container_width=True):
                        
                        col_info, col_form = st.columns([1.2, 1], gap="large")
                        
                        with col_info:
                            st.markdown(f"### {nazev_full}")
                            
                            st.markdown(
                                badge(typ_label_short, bg="#F3F4F6", color="#333") + 
                                badge(druh_akce.upper(), bg="#E5E7EB", color="#555"), 
                                unsafe_allow_html=True
                            )
                            
                            st.markdown("<div style='margin-top: 20px; font-size: 0.95rem; color: #444;'>", unsafe_allow_html=True)
                            st.write(f"📍 **Místo:** {akce['místo']}")
                            
                            if akce['datum'] != akce['datum_do']:
                                d_start = akce['datum'].strftime('%d.%m.')
                                d_end = akce['datum_do'].strftime('%d.%m.%Y')
                                st.write(f"🗓️ **Termín:** {d_start} – {d_end}")
                            
                            kategorie_txt = str(akce['kategorie']).strip() if 'kategorie' in df_akce.columns and pd.notna(akce['kategorie']) else ""
                            if kategorie_txt:
                                st.write(f"🎯 **Kategorie:** {kategorie_txt}")
                            st.markdown("</div>", unsafe_allow_html=True)

                            if pd.notna(akce['popis']): 
                                st.info(f"{akce['popis']}", icon="ℹ️")
                            
                            deadline_str = akce['deadline'].strftime('%d.%m.%Y')
                            
                            st.markdown("---")
                            
                            if je_po_deadlinu:
                                st.error(f"⛔ **DEADLINE BYL:** {deadline_str}")
                            elif je_dnes_deadline:
                                st.warning(f"⚠️ **DNES JE DEADLINE!** ({deadline_str})")
                            else:
                                st.success(f"📅 **Deadline:** {deadline_str}")

                            if je_zavod_obecne:
                                st.caption("Přihlášky probíhají v systému ORIS.")
                                odkaz_zavodu = str(akce['odkaz']).strip() if 'odkaz' in df_akce.columns and pd.notna(akce['odkaz']) else ""
                                link_target = odkaz_zavodu if odkaz_zavodu else "https://oris.orientacnisporty.cz/"
                                
                                if je_stafeta:
                                    st.warning("⚠️ **ŠTAFETY:** Přihlaš se i ZDE (vpravo) kvůli soupiskám!")
                                
                                st.markdown(f"""
                                <a href="{link_target}" target="_blank" style="text-decoration:none;">
                                    <div style="background-color: #2563EB; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold;">
                                        👉 Otevřít ORIS
                                    </div>
                                </a>
                                """, unsafe_allow_html=True)

                        with col_form:
                            delete_key_state = f"confirm_delete_{unique_key}"
                            
                            if (not je_zavod_obecne or je_stafeta or je_soustredeni):
                                with stylable_container(
                                    key=f"form_cont_{unique_key}",
                                    css_styles="""
                                    {
                                        border: 1px solid #E5E7EB;
                                        border-radius: 12px;
                                        padding: 20px;
                                        background-color: #F9FAFB;
                                        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
                                    }
                                    """
                                ):
                                    if not je_po_deadlinu and delete_key_state not in st.session_state:
                                        st.markdown("<h4 style='margin-top:0;'>✍️ Přihláška</h4>", unsafe_allow_html=True)
                                        form_key = f"form_{unique_key}"
                                        
                                        with st.form(key=form_key, clear_on_submit=True):
                                            if kategorie_txt and kategorie_txt.lower() != "všichni":
                                                st.warning(f"Podmínka: **{kategorie_txt}**")
                                            
                                            vybrane_jmeno = st.selectbox("Jméno", options=seznam_jmen, index=None, placeholder="Vyber ze seznamu...")
                                            nove_jmeno = st.text_input("Nebo nové jméno")
                                            poznamka_input = st.text_input("Poznámka")
                                            doprava_input = st.checkbox("🚗 Sháním odvoz")
                                            
                                            st.markdown("<br>", unsafe_allow_html=True)
                                            
                                            with stylable_container(
                                                key=f"submit_btn_{unique_key}",
                                                css_styles="""
                                                    button {
                                                        background-color: #16A34A !important;
                                                        color: white !important;
                                                        border: none !important;
                                                        transform: translateY(-10px) !important;
                                                        margin-top: 0px !important;
                                                    }
                                                    button:hover {
                                                        background-color: #15803d !important;
                                                        color: white !important;
                                                    }
                                                """
                                            ):
                                                odeslat_btn = st.form_submit_button("Přihlásit")
                                            
                                            if odeslat_btn:
                                                finalni_jmeno = nove_jmeno.strip() if nove_jmeno else vybrane_jmeno
                                                if finalni_jmeno:
                                                    # --- KONTROLA DUPLICITY ZAČÁTEK ---
                                                    try:
                                                        aktualni = conn.read(worksheet="prihlasky", ttl=0)
                                                        aktualni['id_akce'] = aktualni['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
                                                        
                                                        duplicita = not aktualni[
                                                            (aktualni['id_akce'] == akce_id_str) & 
                                                            (aktualni['jméno'] == finalni_jmeno)
                                                        ].empty
                                                        
                                                        if duplicita:
                                                            st.warning(f"⚠️ {finalni_jmeno}, na této akci už jsi!")
                                                        else:
                                                            uspesne_zapsano = False
                                                            hodnota_dopravy = "Ano 🚗" if doprava_input else ""
                                                            novy_zaznam = pd.DataFrame([{
                                                                "id_akce": akce_id_str,
                                                                "název": akce['název'],
                                                                "jméno": finalni_jmeno,
                                                                "poznámka": poznamka_input,
                                                                "doprava": hodnota_dopravy,
                                                                "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                            }])
                                                            
                                                            updated = pd.concat([aktualni, novy_zaznam], ignore_index=True)
                                                            conn.update(worksheet="prihlasky", data=updated)
                                                            if finalni_jmeno not in seznam_jmen:
                                                                try:
                                                                    aktualni_jmena = conn.read(worksheet="jmena", ttl=0)
                                                                    novy_clen = pd.DataFrame([{"jméno": finalni_jmeno}])
                                                                    updated_jmena = pd.concat([aktualni_jmena, novy_clen], ignore_index=True)
                                                                    conn.update(worksheet="jmena", data=updated_jmena)
                                                                except: pass
                                                            uspesne_zapsano = True
                                                            
                                                            if uspesne_zapsano:
                                                                # --- LOTTIE ANIMACE START ---
                                                                with st_lottie_spinner(lottie_success, key=f"anim_{unique_key}"):
                                                                    time.sleep(2) 
                                                                # --- LOTTIE ANIMACE END ---
                                                                st.toast(f"✅ {finalni_jmeno} přihlášen(a)!")
                                                                st.rerun()
                                                    except Exception as e:
                                                        st.error(f"Chyba: {e}")
                                                    # --- KONEC LOGIKY ---
                                                else: st.warning("Vyplň jméno!")
                                    elif je_po_deadlinu:
                                        st.info("🔒 Přihlášky uzavřeny.")
                            elif je_zavod_obecne:
                                st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)

                        # --- SPODNÍ ČÁST: SEZNAM PŘIHLÁŠENÝCH (ASYMETRICKÉ ZEBRA STRIPES) ---
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.divider()

                        if not je_zavod_obecne or je_stafeta or je_soustredeni:
                            if akce_id_str:
                                lidi = df_prihlasky[df_prihlasky['id_akce'] == akce_id_str].copy()
                            else:
                                lidi = pd.DataFrame()

                            nadpis_seznam = f"👥 Zájemci ({len(lidi)})" if je_stafeta else f"👥 Přihlášeno ({len(lidi)})"
                            st.markdown(f"#### {nadpis_seznam}")

                            if delete_key_state in st.session_state:
                                clovek_ke_smazani = st.session_state[delete_key_state]
                                with st.container():
                                    st.warning(f"⚠️ Opravdu odhlásit: **{clovek_ke_smazani}**?")
                                    c_yes, c_no = st.columns(2)
                                    if c_yes.button("✅ ANO", key=f"yes_{unique_key}"):
                                        smazano_ok = False
                                        try:
                                            df_curr = conn.read(worksheet="prihlasky", ttl=0)
                                            df_curr['id_akce'] = df_curr['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
                                            mask = (df_curr['id_akce'] == akce_id_str) & (df_curr['jméno'] == clovek_ke_smazani)
                                            df_clean = df_curr[~mask]
                                            conn.update(worksheet="prihlasky", data=df_clean)
                                            smazano_ok = True
                                        except Exception as e: st.error(f"Chyba: {e}")
                                        if smazano_ok:
                                            del st.session_state[delete_key_state]
                                            st.toast("🗑️ Odhlášeno.")
                                            time.sleep(1)
                                            st.rerun()
                                    if c_no.button("❌ ZPĚT", key=f"no_{unique_key}"):
                                        del st.session_state[delete_key_state]
                                        st.rerun()

                            if not lidi.empty:
                                h1, h2, h3, h4, h5 = st.columns([0.4, 2.0, 2.0, 0.8, 0.5]) 
                                h1.markdown("<b style='color:#9CA3AF'>#</b>", unsafe_allow_html=True)
                                h2.markdown("<b>Jméno</b>", unsafe_allow_html=True)
                                h3.markdown("<b>Poznámka</b>", unsafe_allow_html=True)
                                h4.markdown("🚗", unsafe_allow_html=True)
                                h5.markdown("") 
                                st.markdown("<hr style='margin: 5px 0 10px 0; border-top: 1px solid #E5E7EB;'>", unsafe_allow_html=True)
                                
                                for i, (idx, row) in enumerate(lidi.iterrows()):
                                    is_gray = (i % 2 == 0)
                                    bg_color = "#F3F4F6" if is_gray else "white"
                                    
                                    # POKUD JE ŠEDÝ (is_gray), DÁME MU VELKÝ SPODNÍ PADDING
                                    # POKUD JE BÍLÝ, DÁME MU O 10px MENŠÍ HORNÍ PADDING (0px)
                                    padding_style = "10px 5px 25px 5px !important" if is_gray else "0px 5px 10px 5px !important"
                                    
                                    with stylable_container(
                                        key=f"row_{unique_key}_{idx}",
                                        css_styles=f"""
                                        {{
                                            background-color: {bg_color};
                                            border-radius: 6px;
                                            padding: {padding_style}; /* ZDE SE TO LIŠÍ */
                                            margin-bottom: 2px;
                                            display: flex;
                                            align-items: center;
                                            min-height: 40px;
                                        }}
                                        """
                                    ):
                                        c1, c2, c3, c4, c5 = st.columns([0.4, 2.0, 2.0, 0.8, 0.5], vertical_alignment="center")
                                        c1.write(f"{i+1}.")
                                        c2.markdown(f"**{row['jméno']}**")
                                        poznamka_txt = row['poznámka'] if pd.notna(row['poznámka']) else ""
                                        c3.caption(poznamka_txt)
                                        doprava_val = str(row['doprava']) if pd.notna(row.get('doprava')) else ""
                                        c4.write(doprava_val)
                                        
                                        if not je_po_deadlinu:
                                            # KOŠ BEZ MARGINŮ
                                            with stylable_container(
                                                key=f"del_btn_cont_{unique_key}_{idx}",
                                                css_styles="""
                                                    button {
                                                        margin: 0px !important;
                                                        padding-top: 0px !important;
                                                        padding-bottom: 0px !important;
                                                        height: auto !important;
                                                        min-height: 0px !important;
                                                    }
                                                """
                                            ):
                                                if c5.button("🗑️", key=f"del_{unique_key}_{idx}"):
                                                    st.session_state[delete_key_state] = row['jméno']
                                                    st.rerun()
                            else:
                                st.caption("Zatím nikdo. Buď první!")

st.markdown("<div style='margin-bottom: 50px'></div>", unsafe_allow_html=True)


# --- 5. PLOVOUCÍ TLAČÍTKO "NÁVRH" ---
st.markdown('<div class="floating-container">', unsafe_allow_html=True)

with st.popover("💡 Nápad?"):
    st.markdown("### 🛠️ Máš návrh na zlepšení?")
    st.write("Cokoliv tě napadne - k aplikaci, tréninkům nebo soustředění.")
    
    with st.form("form_navrhy", clear_on_submit=True):
        text_navrhu = st.text_area("Tvůj text:", height=100)
        odeslat_navrh = st.form_submit_button("🚀 Odeslat návrh", type="primary")
        
        if odeslat_navrh and text_navrhu:
            uspesne_odeslano = False
            novy_navrh = pd.DataFrame([{
                "datum": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "text": text_navrhu
            }])
            try:
                try:
                    aktualni_navrhy = conn.read(worksheet="navrhy", ttl=0)
                    updated_navrhy = pd.concat([aktualni_navrhy, novy_navrh], ignore_index=True)
                except:
                    updated_navrhy = novy_navrh
                conn.update(worksheet="navrhy", data=updated_navrhy)
                uspesne_odeslano = True
            except Exception as e:
                st.error(f"Chyba při ukládání: {e}")
            
            if uspesne_odeslano:
                st.toast("✅ Díky! Tvůj návrh byl uložen.")

st.markdown('</div>', unsafe_allow_html=True)

# --- PATIČKA ---
st.markdown("---")
with stylable_container(key="footer_logos", css_styles="img {height: 50px !important; width: auto !important; object-fit: contain;} div[data-testid=\"column\"] {display: flex; align-items: center; justify-content: center;}"):
    col_left, col_center, col_right = st.columns([1.5, 2, 1.5], gap="medium", vertical_alignment="center")
    with col_left:
        l1, l2 = st.columns(2)
        # Změna: use_column_width -> use_container_width
        l1.image("logo1.jpg", use_container_width=True)
        l2.image("logo2.jpg", use_container_width=True)
    with col_center:
        st.markdown("<div style='text-align: center; color: #9CA3AF; font-size: 0.8em; font-family: sans-serif;'><b>Členská sekce RBK</b> • Designed by Broschman • v1.9<br>&copy; 2026 All rights reserved</div>", unsafe_allow_html=True)
    with col_right:
        r1, r2 = st.columns(2)
        # Změna: use_column_width -> use_container_width
        r1.image("logo3.jpg", use_container_width=True)
        r2.image("logo4.jpg", use_container_width=True)
st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)
