
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
import google.generativeai as genai
import styles
import utils
import data_manager
import chatbot

print("--- ZAČÁTEK RERUNU ---")

styles.load_css()
styles.inject_mobile_warning()

st.set_page_config(page_title="Kalendář RBK", page_icon="🌲", layout="wide")

# --- HLAVIČKA ---
col_dummy, col_title, col_help = st.columns([1, 10, 1], vertical_alignment="center")

with col_title:
    logo_path = "logo_rbk.jpg" 
    logo_b64 = utils.get_base64_image(logo_path)
    img_src = f"data:image/png;base64,{logo_b64}" if logo_b64 else "https://cdn-icons-png.flaticon.com/512/2051/2051939.png"

    st.markdown(f"""
        <h1>
            <span class="gradient-text">🌲 Kalendář</span>
            <img src="{img_src}" class="header-logo" alt="RBK Logo">
        </h1>
    """, unsafe_allow_html=True)

with col_help:
    with st.popover("❔", help="Nápověda"):
        st.markdown("### 🌲 Průvodce")
        st.write("Vítej v Cyber-Sekci RBK.")

conn = data_manager.get_connection()
df_akce = data_manager.load_akce()
seznam_jmen = data_manager.load_jmena()

if 'vybrany_datum' not in st.session_state:
    st.session_state.vybrany_datum = date.today()

# --- DASHBOARD (HOŘÍCÍ TERMÍNY) ---
dnes = date.today()
future_deadlines = df_akce[df_akce['deadline'] >= dnes].sort_values('deadline').head(3)

if not future_deadlines.empty:
    st.markdown("### 🔥 Pozor, hoří termíny!")
    cols_d = st.columns(len(future_deadlines))
    
    for i, (_, row) in enumerate(future_deadlines.iterrows()):
        days_left = (row['deadline'] - dnes).days
        
        if days_left == 0:
            glow_c, bg_c, icon, time_msg = styles.NEON_RED, "rgba(255, 7, 58, 0.1)", "🚨", "DNES!"
        elif days_left <= 3:
            glow_c, bg_c, icon, time_msg = styles.NEON_ORANGE, "rgba(255, 95, 31, 0.1)", "⚠️", f"Za {days_left} dny"
        else:
            glow_c, bg_c, icon, time_msg = styles.NEON_GREEN, "rgba(57, 255, 20, 0.1)", "📅", row['deadline'].strftime('%d.%m.')

        unique_key_dash = f"dash_{row['id']}"
        
        # ZDE POUŽIJEME FUNKCI ZE STYLES
        dash_css = styles.get_cyber_button_css(bg_c, glow_c)

        with cols_d[i]:
            with stylable_container(key=f"dash_card_{i}", css_styles=dash_css):
                label_text = f"{icon} {row['název']}\n{time_msg}"
                
                with st.popover(label_text, use_container_width=True):
                    utils.vykreslit_detail_akce(row, unique_key_dash)
                    
    st.markdown("<div style='margin-bottom: 25px'></div>", unsafe_allow_html=True)

@st.fragment
def show_calendar_section():
    if 'vybrany_datum' not in st.session_state: st.session_state.vybrany_datum = date.today()

    col_nav1, col_nav2, col_nav3 = st.columns([2, 5, 2], vertical_alignment="center")
    with col_nav1:
        if st.button("⬅️ Předchozí", use_container_width=True):
            st.session_state.vybrany_datum = (st.session_state.vybrany_datum.replace(day=1) - timedelta(days=1)).replace(day=1)
    with col_nav3:
        if st.button("Další ➡️", use_container_width=True):
            st.session_state.vybrany_datum = (st.session_state.vybrany_datum.replace(day=28) + timedelta(days=4)).replace(day=1)

    year, month = st.session_state.vybrany_datum.year, st.session_state.vybrany_datum.month
    ceske_mesice = ["", "Leden", "Únor", "Březen", "Duben", "Květen", "Červen", "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"]
    
    with col_nav2:
        st.markdown(f"<h2 style='text-align: center; margin:0; padding:0;'>{ceske_mesice[month]} <span style='color:#666'>{year}</span></h2>", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)
    
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)
    dnes = date.today()

    events_map = {}
    start_view = date(year, month, 1) - timedelta(days=7)
    end_view = date(year, month, 28) + timedelta(days=14)
    relevant_events = df_akce[(df_akce['datum'] <= end_view) & (df_akce['datum_do'] >= start_view)]

    for _, akce in relevant_events.iterrows():
        curr = akce['datum']
        while curr <= akce['datum_do']:
            if curr not in events_map: events_map[curr] = []
            events_map[curr].append(akce)
            curr += timedelta(days=1)

    cols_header = st.columns(7)
    for i, d in enumerate(["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]):
        cols_header[i].markdown(f"<div style='text-align: center; color: #6B7280; font-weight: 700; font-size: 0.8rem; margin-bottom: 10px;'>{d}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='margin: 0 0 15px 0;'>", unsafe_allow_html=True)

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
                    
                    # ... předchozí logika (typ, styly, ikony) ...
                    
                    styly = styles.BARVY_AKCI.get(style_key, styles.BARVY_AKCI["default"])
                    glow_color = styly.get("glow", "#39ff14")
                    bg_color = styly.get("bg", "rgba(255,255,255,0.05)")

                    ikony = { "les": "🌲", "sprint": "🏙️", "nočák": "🌗" }
                    emoji = ikony.get(druh, "🏃")
                    label = f"{emoji} {akce['název'].split('-')[0].strip()}"
                    if je_po_deadlinu: label = "🔒 " + label
                    
                    # ZDE POUŽIJEME FUNKCI ZE STYLES (TUČNÉ PÍSMO)
                    calendar_css = styles.get_cyber_button_css(bg_color, glow_color)

                    with stylable_container(key=f"btn_c_{unique_key}", css_styles=calendar_css):
                        with st.popover(label, use_container_width=True):
                            utils.vykreslit_detail_akce(akce, unique_key)

# ==============================================================================
# 2. HLEDÁNÍ
# ==============================================================================
st.markdown("### 📅 Kalendář akcí")

if "search_query" not in st.session_state: st.session_state.search_query = ""
if "search_date" not in st.session_state: st.session_state.search_date = []

def clear_search():
    st.session_state.search_query = ""
    st.session_state.search_date = []

col_text, col_date, col_close, _ = st.columns([1.5, 1.5, 0.5, 4], vertical_alignment="bottom")
with col_text:
    search_text = st.text_input("Hledat text", placeholder="🔍 Název nebo místo...", label_visibility="collapsed", key="search_query")
with col_date:
    search_date_value = st.date_input("Vyber datum", min_value=date.today(), max_value=date(2030, 12, 31), key="search_date", label_visibility="collapsed")
with col_close:
    if search_text or len(st.session_state.search_date) > 0:
        st.button("❌", on_click=clear_search)
        
components.html("""<script>const doc = window.parent.document; doc.addEventListener('keydown', function(e) { if (e.key === 'Escape') { const buttons = Array.from(doc.querySelectorAll('button')); const closeBtn = buttons.find(btn => btn.innerText.includes('❌')); if (closeBtn) closeBtn.click(); } });</script>""", height=0, width=0)

if search_text or len(search_date_value) > 0:
    dnes = date.today()
    mask = pd.Series([True] * len(df_akce))
    if search_text:
        mask = mask & (df_akce['název'].str.contains(search_text, case=False, na=False) | df_akce['místo'].str.contains(search_text, case=False, na=False))
        if len(search_date_value) == 0: mask = mask & (df_akce['datum'] >= dnes)
    if len(search_date_value) > 0:
        if len(search_date_value) == 1: mask = mask & (df_akce['datum'] == search_date_value[0])
        elif len(search_date_value) == 2: mask = mask & (df_akce['datum'] >= search_date_value[0]) & (df_akce['datum'] <= search_date_value[1])

    results = df_akce[mask].sort_values(by='datum')
    st.markdown(f"<div style='color: #4B5563; margin-bottom: 10px; font-size: 0.9rem;'>Nalezeno {len(results)} akcí</div>", unsafe_allow_html=True)
    
    if results.empty: st.warning("Nic nenalezeno.")
    else:
        for _, akce in results.iterrows():
            akce_id_str = str(akce['id'])
            unique_key = f"search_{akce_id_str}"
            je_po_deadlinu = dnes > akce['deadline']
            
            typ_udalosti = str(akce.get('typ', '')).lower()
            style_key = "default"
            if "mčr" in typ_udalosti: style_key = "mcr"
            elif "ža" in typ_udalosti: style_key = "za"
            elif "žb" in typ_udalosti: style_key = "zb"
            elif "soustředění" in typ_udalosti: style_key = "soustredeni"
            elif "oblastní" in typ_udalosti: style_key = "oblastni"
            elif "zimní" in typ_udalosti: style_key = "zimni_liga"
            elif "štafety" in typ_udalosti: style_key = "stafety"
            elif "trénink" in typ_udalosti: style_key = "trenink"
            elif any(s in typ_udalosti for s in ["závod", "liga"]): style_key = "zavod"

            styly = styles.BARVY_AKCI.get(style_key, styles.BARVY_AKCI["default"])
            # ... logika stylů ...
            glow_color = styly.get("glow", "#39ff14")
            bg_color = styly.get("bg", "rgba(255,255,255,0.05)")
            
            # ZDE POUŽIJEME FUNKCI ZE STYLES
            search_css = styles.get_cyber_button_css(bg_color, glow_color)

            with stylable_container(key=f"btn_search_{unique_key}", css_styles=search_css):
                with st.popover(label, use_container_width=True):
                    utils.vykreslit_detail_akce(akce, unique_key)
else:
    show_calendar_section()
st.markdown("<div style='margin-bottom: 50px'></div>", unsafe_allow_html=True)
        
# --- 5. PLOVOUCÍ TLAČÍTKO ---
st.markdown('<div class="floating-container">', unsafe_allow_html=True)
with st.popover("💡 Nápad?"):
    st.markdown("### 🛠️ Máš návrh?")
    with st.form("form_navrhy", clear_on_submit=True):
        text_navrhu = st.text_area("Tvůj text:", height=100)
        if st.form_submit_button("🚀 Odeslat", type="primary") and text_navrhu:
            try:
                aktualni = conn.read(worksheet="navrhy", ttl=0)
                nove = pd.DataFrame([{"datum": datetime.now().strftime("%Y-%m-%d"), "text": text_navrhu}])
                conn.update(worksheet="navrhy", data=pd.concat([aktualni, nove], ignore_index=True))
                st.toast("✅ Díky!")
            except: 
                try: 
                    conn.update(worksheet="navrhy", data=pd.DataFrame([{"datum": datetime.now().strftime("%Y-%m-%d"), "text": text_navrhu}]))
                    st.toast("✅ Díky!")
                except Exception as e: st.error(f"Chyba: {e}")
st.markdown('</div>', unsafe_allow_html=True)

# --- PATIČKA ---
st.markdown("---")
st.markdown('<div class="footer-glow">', unsafe_allow_html=True)
with stylable_container(key="footer_logos", css_styles="img {height: 50px !important; width: auto !important; object-fit: contain;} div[data-testid=\"column\"] {display: flex; align-items: center; justify-content: center;}"):
    col_left, col_center, col_right = st.columns([1.5, 2, 1.5], gap="medium", vertical_alignment="center")
    with col_left:
        l1, l2 = st.columns(2)
        l1.image("logo1.jpg", width="stretch"); l2.image("logo2.jpg", width="stretch")
    with col_center:
        st.markdown(styles.get_footer_html(), unsafe_allow_html=True)
    with col_right:
        r1, r2 = st.columns(2)
        r1.image("logo3.jpg", width="stretch"); r2.image("logo4.jpg", width="stretch")
st.markdown('</div>', unsafe_allow_html=True)
st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)

# ... (Patička a konec předchozího kódu) ...
st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)

# ==============================================================================
# 6. FLOATING CYBER-COACH (Pravý dolní roh) - DOČASNĚ VYPNUTO
# ==============================================================================
"""
# TENTO KÓD JE ZAKOMENTOVANÝ A NEBUDE SE SPOUŠTĚT
# AŽ HO BUDEŠ CHTÍT ZAPNOUT, SMAŽ TY TŘI UVOZOVKY NA ZAČÁTKU A NA KONCI

chat_css = styles.get_floating_chat_css()

with stylable_container(key="floating_bot_container", css_styles=chat_css):
    with st.popover("🤖", help="Otevřít Cyber-Coache"):
        try:
            import data_manager
            # Načteme data (pro jistotu znovu, ať vidí změny)
            df_akce_pro_bota = data_manager.load_akce()
            
            # Spustíme logiku chatbota
            chatbot.main(df_akce_pro_bota)
            
        except Exception as e:
            st.error(f"Bot Error: {e}")
"""
