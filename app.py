import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_extras.stylable_container import stylable_container
from streamlit_lottie import st_lottie, st_lottie_spinner
import streamlit.components.v1 as components
import folium
from streamlit_folium import st_folium
import requests
import re
from urllib.parse import urlparse, parse_qs
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import time
import base64
import os
from io import BytesIO
import textwrap
import styles
import utils
import data_manager

print("--- ZAČÁTEK RERUNU ---")

# Načtení CSS a mobilního varování
styles.load_css()
styles.inject_mobile_warning()

# --- 1. NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Kalendář RBK", page_icon="🌲", layout="wide")
    
# --- HLAVIČKA S LOGEM ---
col_dummy, col_title, col_help = st.columns([1, 10, 1], vertical_alignment="center")

with col_title:
    logo_path = "logo_rbk.jpg" 
    logo_b64 = utils.get_base64_image(logo_path)
    if logo_b64:
        img_src = f"data:image/png;base64,{logo_b64}"
    else:
        img_src = "https://cdn-icons-png.flaticon.com/512/2051/2051939.png"

    st.markdown(f"""
        <h1>
            <span class="gradient-text">🌲 Kalendář</span>
            <img src="{img_src}" class="header-logo" alt="RBK Logo">
        </h1>
    """, unsafe_allow_html=True)

with col_help:
    with st.popover("❔", help="Nápověda a Legenda"):
        # --- NADPIS ---
        st.markdown("### 🌲 Průvodce aplikací")
        
        # --- 1. FUNKCIONALITY ---
        st.markdown("""
        **1. 📅 Dva pohledy na akce**
        * **Kalendář:** Klasický měsíční pohled. Kliknutím na den/akci otevřeš detaily.
        * **Vyhledávání (nahoře):** Zadej text (např. "MČR") nebo vyber datum. Kalendář zmizí a uvidíš seznam vyfiltrovaných akcí.
        
        **2. ✍️ Přihlašování & Odhlašování**
        * **Zápis:** V detailu akce vyber své jméno (nebo napiš nové), zvol dopravu/ubytko a potvrď.
        * **Odhlášení:** V seznamu přihlášených najdi své jméno a klikni na **koš 🗑️**.
        * ⚠️ **Pozor:** U závodů (ŽA, ŽB, MČR) je tato tabulka **pouze interní** (doprava/spaní). Na závod se musíš přihlásit přes **ORIS** (odkaz je vždy v detailu akce).
        
        **3. 🗺️ Mapy a Počasí**
        * U každé akce se automaticky načítá **předpověď počasí** a čas **západu slunce 🌑** (hodí se na nočáky).
        * Dole v detailu najdeš mapu s bodem srazu a tlačítka pro navigaci (**Waze, Google, Mapy.cz**).
        
        **4. 🗓️ Export do mobilu**
        * V záhlaví každé akce je malé tlačítko 📅. Kliknutím si stáhneš soubor `.ics`, který ti akci přidá do tvého Outlooku nebo Google Kalendáře.
        
        **5. 🔐 Pro trenéry**
        * Pod seznamem přihlášených je tlačítko **Export**. Po zadání hesla se stáhne Excel soupiska (např. pro nahlášení ubytování).
        """)
        
        st.divider()

        # --- 2. LEGENDA BAREV ---
        st.markdown("### 🎨 Legenda barev (Typ akce)")
        st.markdown("""
        <div style="display: grid; gap: 8px; font-size: 0.85rem;">
            <div style="display: flex; align-items: center;"><span style="width: 18px; height: 18px; border-radius: 4px; background: linear-gradient(90deg, #EF4444, #F59E0B, #10B981); margin-right: 10px;"></span><b>MČR / Mistrovství</b></div>
            <div style="display: flex; align-items: center;"><span style="width: 18px; height: 18px; border-radius: 4px; background: #DC2626; margin-right: 10px;"></span><b>Závod ŽA</b>  (Licence A)</div>
            <div style="display: flex; align-items: center;"><span style="width: 18px; height: 18px; border-radius: 4px; background: #EA580C; margin-right: 10px;"></span><b>Závod ŽB</b>  (Licence B)</div>
            <div style="display: flex; align-items: center;"><span style="width: 18px; height: 18px; border-radius: 4px; background: #D97706; margin-right: 10px;"></span><b>Soustředění</b></div>
            <div style="display: flex; align-items: center;"><span style="width: 18px; height: 18px; border-radius: 4px; background: #2563EB; margin-right: 10px;"></span><b>Oblastní žebříček</b></div>
            <div style="display: flex; align-items: center;"><span style="width: 18px; height: 18px; border-radius: 4px; background: #4B5563; margin-right: 10px;"></span><b>Zimní liga</b></div>
            <div style="display: flex; align-items: center;"><span style="width: 18px; height: 18px; border-radius: 4px; background: #9333EA; margin-right: 10px;"></span><b>Štafety</b></div>
            <div style="display: flex; align-items: center;"><span style="width: 18px; height: 18px; border-radius: 4px; background: #16A34A; margin-right: 10px;"></span><b>Trénink</b></div>
             <div style="display: flex; align-items: center;"><span style="width: 18px; height: 18px; border-radius: 4px; background: #0D9488; margin-right: 10px;"></span><b>Ostatní závody</b></div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
# --- 2. PŘIPOJENÍ A NAČTENÍ DAT ---
conn = data_manager.get_connection()
df_akce = data_manager.load_akce()
seznam_jmen = data_manager.load_jmena()

# --- 3. LOGIKA KALENDÁŘE ---
if 'vybrany_datum' not in st.session_state:
    st.session_state.vybrany_datum = date.today()

# --- DASHBOARD NEJBLIŽŠÍCH DEADLINŮ (CYBER-ROG EDITION) ---
dnes = date.today()
future_deadlines = df_akce[df_akce['deadline'] >= dnes].sort_values('deadline').head(3)

if not future_deadlines.empty:
    st.markdown("### 🔥 Pozor, hoří termíny!")
    cols_d = st.columns(len(future_deadlines))
    
    for i, (_, row) in enumerate(future_deadlines.iterrows()):
        days_left = (row['deadline'] - dnes).days
        
        # Logika NEONOVÝCH barev a záře
        if days_left == 0:
            border_color = styles.NEON_RED
            bg_color = "rgba(255, 7, 58, 0.1)"
            shadow = f"0 0 20px {styles.NEON_RED}"
            icon, time_msg = "🚨", "DNES!"
        elif days_left <= 3:
            border_color = styles.NEON_ORANGE
            bg_color = "rgba(255, 95, 31, 0.1)"
            shadow = f"0 0 15px {styles.NEON_ORANGE}"
            icon, time_msg = "⚠️", f"Za {days_left} dny"
        else:
            border_color = styles.NEON_GREEN
            bg_color = "rgba(57, 255, 20, 0.1)"
            shadow = f"0 0 10px {styles.NEON_GREEN}"
            icon, time_msg = "📅", row['deadline'].strftime('%d.%m.')

        unique_key_dash = f"dash_{row['id']}"

        with cols_d[i]:
            with stylable_container(
                key=f"dash_card_{i}",
                css_styles=f"""
                button {{
                    background-color: {bg_color} !important;
                    border: 1px solid {border_color} !important;
                    box-shadow: {shadow} !important;
                    border-radius: 12px !important;
                    color: #fff !important;
                    width: 100% !important;
                    height: auto !important;
                    min-height: 110px !important;
                    white-space: pre-wrap !important;
                    display: flex !important;
                    flex-direction: column !important;
                    justify-content: center !important;
                    align-items: center !important;
                    padding: 10px !important;
                    transition: all 0.3s !important;
                    /* === ZDE JE ZMĚNA === */
                    font-family: 'Exo 2', sans-serif !important;
                }}
                button:hover {{
                    transform: scale(1.05) !important;
                    box-shadow: 0 0 30px {border_color} !important;
                    background-color: {border_color}22 !important;
                }}
                button p {{
                    /* === I ZDE PRO JISTOTU === */
                    font-family: 'Exo 2', sans-serif !important;
                    letter-spacing: 1px;
                    font-weight: 700;
                }}
                """
            ):
                label_text = f"{icon}\n{row['název']}\n{time_msg}"
                with st.popover(label_text, use_container_width=True):
                    utils.vykreslit_detail_akce(row, unique_key_dash)
                    
@st.fragment  # ✅ Fragment je zpět!
def show_calendar_section():
    # --- 1. NAVIGACE MĚSÍCŮ ---
    if 'vybrany_datum' not in st.session_state:
        st.session_state.vybrany_datum = date.today()

    col_nav1, col_nav2, col_nav3 = st.columns([2, 5, 2], vertical_alignment="center")
    
    with col_nav1:
        # BEZ st.rerun()! Fragment se obnoví sám.
        if st.button("⬅️ Předchozí", use_container_width=True):
            curr = st.session_state.vybrany_datum
            prev_month = curr.replace(day=1) - timedelta(days=1)
            st.session_state.vybrany_datum = prev_month.replace(day=1)
            # st.rerun() <--- TADY NIC NEPIŠ

    with col_nav3:
        # BEZ st.rerun()! Fragment se obnoví sám.
        if st.button("Další ➡️", use_container_width=True):
            curr = st.session_state.vybrany_datum
            next_month = (curr.replace(day=28) + timedelta(days=4)).replace(day=1)
            st.session_state.vybrany_datum = next_month
            # st.rerun() <--- TADY NIC NEPIŠ

    year = st.session_state.vybrany_datum.year
    month = st.session_state.vybrany_datum.month
    ceske_mesice = ["", "Leden", "Únor", "Březen", "Duben", "Květen", "Červen", "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"]
    
    with col_nav2:
        st.markdown(f"<h2 style='text-align: center; margin:0; padding:0;'>{ceske_mesice[month]} <span style='color:#666'>{year}</span></h2>", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)
    
    # --- 2. PŘÍPRAVA DAT ---
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)
    dnes = date.today()

    events_map = {}
    start_view = date(year, month, 1) - timedelta(days=7)
    end_view = date(year, month, 28) + timedelta(days=14)
    relevant_events = df_akce[(df_akce['datum'] <= end_view) & (df_akce['datum_do'] >= start_view)]

    for _, akce in relevant_events.iterrows():
        curr = akce['datum']
        konec = akce['datum_do']
        while curr <= konec:
            if curr not in events_map: events_map[curr] = []
            events_map[curr].append(akce)
            curr += timedelta(days=1)

    # --- 3. VYKRESLENÍ MŘÍŽKY ---
    dny_v_tydnu = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
    cols_header = st.columns(7)
    for i, d in enumerate(dny_v_tydnu):
        cols_header[i].markdown(f"<div style='text-align: center; color: #6B7280; font-weight: 700; text-transform: uppercase; font-size: 0.8rem; margin-bottom: 10px;'>{d}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='margin: 0 0 15px 0; border: 0; border-top: 1px solid #E5E7EB;'>", unsafe_allow_html=True)

    for tyden in month_days:
        cols = st.columns(7, gap="small")
        for i, den_cislo in enumerate(tyden):
            with cols[i]:
                if den_cislo == 0:
                    st.write("")
                    continue
                
                aktualni_den = date(year, month, den_cislo)
                
                if aktualni_den == dnes:
                    st.markdown(f"<div style='text-align: center;'><span class='today-box'>{den_cislo}</span></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span class='day-number'>{den_cislo}</span>", unsafe_allow_html=True)

                akce_dne = events_map.get(aktualni_den, [])
                for akce in akce_dne:
                    je_po_deadlinu = dnes > akce['deadline']
                    akce_id_str = str(akce['id'])
                    unique_key = f"{akce_id_str}_{aktualni_den.strftime('%Y%m%d')}"

                    typ = str(akce.get('typ', '')).lower()
                    druh = str(akce.get('druh', '')).lower()
                    
                    zavodni_slova = ["závod", "mčr", "žebříček", "liga", "mistrovství", "štafety", "ža", "žb"]
                    je_zavod_obecne = any(s in typ for s in zavodni_slova)
                    style_key = "default"
                    if "mčr" in typ: style_key = "mcr"
                    elif "ža" in typ: style_key = "za"
                    elif "žb" in typ: style_key = "zb"
                    elif "soustředění" in typ: style_key = "soustredeni"
                    elif "oblastní" in typ: style_key = "oblastni"
                    elif "zimní" in typ: style_key = "zimni_liga"
                    elif "štafety" in typ: style_key = "stafety"
                    elif "trénink" in typ: style_key = "trenink"
                    elif je_zavod_obecne: style_key = "zavod"
                    
                    styly = styles.BARVY_AKCI.get(style_key, styles.BARVY_AKCI["default"])
                    ikony = { "les": "🌲", "sprint": "🏙️", "nočák": "🌗" }
                    emoji = ikony.get(druh, "🏃")
                    
                    label = f"{emoji} {akce['název'].split('-')[0].strip()}"
                    if je_po_deadlinu: label = "🔒 " + label

                    with stylable_container(
                        key=f"btn_c_{unique_key}",
                        # Přidal jsem font-family na konec stringu
                        css_styles=f"""button {{background: {styly['bg']} !important; color: {styly['color']} !important; border: {styly['border']} !important; width: 100%; border-radius: 8px; padding: 8px 10px !important; text-align: left; font-size: 0.85rem; font-weight: 600; box-shadow: {styly.get('shadow', 'none')}; margin-bottom: 6px; white-space: normal !important; height: auto !important; min-height: 40px; font-family: 'Exo 2', sans-serif !important;}} button:hover {{filter: brightness(1.2); transform: translateY(-2px); z-index: 5;}}"""
                    ):
                        with st.popover(label, use_container_width=True):
                            utils.vykreslit_detail_akce(akce, unique_key)

# ==============================================================================
# 2. VYKRESLOVÁNÍ UI - HLEDÁNÍ A KALENDÁŘ
# ==============================================================================

st.markdown("### 📅 Kalendář akcí")

if "search_query" not in st.session_state:
    st.session_state.search_query = ""

if "search_date" not in st.session_state:
    st.session_state.search_date = []

def clear_search():
    st.session_state.search_query = ""
    st.session_state.search_date = []

col_text, col_date, col_close, _ = st.columns([1.5, 1.5, 0.5, 4], vertical_alignment="bottom")

with col_text:
    search_text = st.text_input(
        "Hledat text", 
        placeholder="🔍 Název nebo místo...", 
        label_visibility="collapsed",
        key="search_query"
    )

with col_date:
    search_date_value = st.date_input(
        "Vyber datum",
        min_value=date.today(),
        max_value=date(2030, 12, 31),
        key="search_date",
        label_visibility="collapsed",
        help="Vyber termín (minulost nelze vybrat)"
    )

with col_close:
    if search_text or len(st.session_state.search_date) > 0:
        st.button("❌", on_click=clear_search, help="Zrušit filtry")
        
# === JAVASCRIPT PRO ESCAPE KLÁVESU ===
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const buttons = Array.from(doc.querySelectorAll('button'));
            const closeBtn = buttons.find(btn => btn.innerText.includes('❌'));
            if (closeBtn) closeBtn.click();
        }
    });
    </script>
    """,
    height=0, width=0
)

# === VÝHYBKA: FILTROVÁNÍ vs. KALENDÁŘ ===

if search_text or len(search_date_value) > 0:
    
    # 🅰️ FILTROVÁNÍ
    dnes = date.today()
    mask = pd.Series([True] * len(df_akce))

    # 1. Filtr podle TEXTU
    if search_text:
        mask = mask & (
            df_akce['název'].str.contains(search_text, case=False, na=False) | 
            df_akce['místo'].str.contains(search_text, case=False, na=False)
        )
        if len(search_date_value) == 0:
            mask = mask & (df_akce['datum'] >= dnes)

    # 2. Filtr podle DATA
    if len(search_date_value) > 0:
        if len(search_date_value) == 1:
            vybrane_datum = search_date_value[0]
            mask = mask & (df_akce['datum'] == vybrane_datum)
        elif len(search_date_value) == 2:
            start, end = search_date_value
            mask = mask & (df_akce['datum'] >= start) & (df_akce['datum'] <= end)

    results = df_akce[mask].sort_values(by='datum')
    
    info_text = f"Nalezeno {len(results)} akcí"
    if search_text: info_text += f" pro '{search_text}'"
    if len(search_date_value) > 0: 
        d_str = search_date_value[0].strftime('%d.%m.')
        if len(search_date_value) == 2: d_str += f" – {search_date_value[1].strftime('%d.%m.')}"
        info_text += f" v termínu {d_str}"
        
    st.markdown(f"<div style='color: #4B5563; margin-bottom: 10px; font-size: 0.9rem;'>{info_text}</div>", unsafe_allow_html=True)
    
    if results.empty:
        st.warning("Žádné budoucí akce neodpovídají zadání.")
    else:
        for _, akce in results.iterrows():
            # --- VYKRESLENÍ VÝSLEDKŮ ---
            akce_id_str = str(akce['id'])
            unique_key = f"search_{akce_id_str}"
            je_po_deadlinu = dnes > akce['deadline']
            
            typ_udalosti = str(akce.get('typ', '')).lower()
            druh_akce = str(akce.get('druh', '')).lower()
            zavodni_slova = ["závod", "mčr", "žebříček", "liga", "mistrovství", "štafety", "ža", "žb"]
            je_zavod_obecne = any(s in typ_udalosti for s in zavodni_slova)

            style_key = "default"
            if "mčr" in typ_udalosti: style_key = "mcr"
            elif "ža" in typ_udalosti: style_key = "za"
            elif "žb" in typ_udalosti: style_key = "zb"
            elif "soustředění" in typ_udalosti: style_key = "soustredeni"
            elif "oblastní" in typ_udalosti: style_key = "oblastni"
            elif "zimní" in typ_udalosti: style_key = "zimni_liga"
            elif "štafety" in typ_udalosti: style_key = "stafety"
            elif "trénink" in typ_udalosti: style_key = "trenink"
            elif je_zavod_obecne: style_key = "zavod"

            styly = styles.BARVY_AKCI.get(style_key, styles.BARVY_AKCI["default"])
            ikony_mapa = { "les": "🌲", "krátká trať": "🌲", "sprint": "🏙️", "nočák": "🌗" }
            emoji = ikony_mapa.get(druh_akce, "🏃")
            
            datum_str = akce['datum'].strftime('%d.%m.')
            nazev_full = f"{datum_str} | {akce['název']} ({akce['místo']})"
            label = f"{emoji} {nazev_full}"
            if je_po_deadlinu: label = "🔒 " + label

            with stylable_container(
                key=f"btn_search_{unique_key}",
                css_styles=f"""
                    button {{
                        background: {styly['bg']} !important;
                        color: {styly['color']} !important;
                        border: {styly['border']} !important;
                        width: 100%;
                        border-radius: 8px;
                        padding: 12px 15px !important;
                        text-align: left;
                        font-weight: 600;
                        box-shadow: {styly.get('shadow', 'none')};
                        margin-bottom: 8px;
                        /* === PŘIDÁNO === */
                        font-family: 'Exo 2', sans-serif !important;
                    }}
                    button:hover {{
                        filter: brightness(1.2);
                        transform: translateY(-2px);
                    }}
                """
            ):
                with st.popover(label, use_container_width=True):
                    utils.vykreslit_detail_akce(akce, unique_key)

else:
    # 🅱️ REŽIM KALENDÁŘE
    show_calendar_section()
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
# Zabalíme loga do divu s třídou footer-glow pro bílou záři
st.markdown('<div class="footer-glow">', unsafe_allow_html=True)
with stylable_container(key="footer_logos", css_styles="img {height: 50px !important; width: auto !important; object-fit: contain;} div[data-testid=\"column\"] {display: flex; align-items: center; justify-content: center;}"):
    col_left, col_center, col_right = st.columns([1.5, 2, 1.5], gap="medium", vertical_alignment="center")
    
    with col_left:
        l1, l2 = st.columns(2)
        l1.image("logo1.jpg", width="stretch") 
        l2.image("logo2.jpg", width="stretch")
        
    with col_center:
        st.markdown(styles.get_footer_html(), unsafe_allow_html=True)
        
    with col_right:
        r1, r2 = st.columns(2)
        r1.image("logo3.jpg", width="stretch")
        r2.image("logo4.jpg", width="stretch")
st.markdown('</div>', unsafe_allow_html=True) # Ukončení divu footer-glow

st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)
