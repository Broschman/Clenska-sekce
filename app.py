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

def vykreslit_detail_akce(akce, unique_key):
    """
    Vykreslí detail akce. 
    Verze bez st.form pro maximální interaktivitu tlačítek.
    """
    # --- PŘÍPRAVA DAT ---
    mapa_raw = str(akce['mapa']).strip() if 'mapa' in df_akce.columns and pd.notna(akce['mapa']) else ""
    body_k_vykresleni = utils.parse_map_coordinates(mapa_raw, akce['název']) 
    main_lat, main_lon = None, None
    if body_k_vykresleni: main_lat, main_lon, _ = body_k_vykresleni[0]
    
    if (not main_lat or not main_lon) and akce['místo']:
        found_lat, found_lon = utils.get_coords_from_place(str(akce['místo']))
        if found_lat and found_lon: main_lat, main_lon = found_lat, found_lon

    akce_id_str = str(akce['id']) if 'id' in df_akce.columns else ""
    typ_udalosti = str(akce['typ']).lower().strip() if 'typ' in df_akce.columns else ""
    druh_akce = str(akce['druh']).lower().strip() if 'druh' in df_akce.columns else "ostatní"
    kategorie_txt = str(akce['kategorie']).strip() if 'kategorie' in df_akce.columns else ""
    je_stafeta = "štafety" in typ_udalosti
    je_zavod_obecne = any(s in typ_udalosti for s in ["závod", "mčr", "žebříček", "liga", "mistrovství", "štafety", "ža", "žb"])
    dnes = date.today()
    je_po_deadlinu = dnes > akce['deadline']
    deadline_str = akce['deadline'].strftime('%d.%m.%Y')

    if akce_id_str:
        df_full = data_manager.load_prihlasky()
        lidi = df_full[df_full['id_akce'] == akce_id_str].copy().fillna("")
    else: lidi = pd.DataFrame()

    # --- LAYOUT ---
    col_info, col_form = st.columns([1.2, 1], gap="large")
    
    # === LEVÝ SLOUPEC (INFO) ===
    with col_info:
        c_head, c_cal = st.columns([0.85, 0.15], gap="small", vertical_alignment="center")
        with c_head: st.markdown(f"<h3 style='margin:0; padding:0;'>{akce['název']}</h3>", unsafe_allow_html=True)
        with c_cal:
            ics_data = utils.generate_ics(akce)
            b64 = base64.b64encode(ics_data.encode('utf-8')).decode()
            st.markdown(styles.get_ics_button_html(b64, akce["název"]), unsafe_allow_html=True)
        
        st.markdown(styles.badge(typ_udalosti.upper(), bg="#F3F4F6", color="#333"), unsafe_allow_html=True)
        st.markdown(f"<div style='margin-top:20px; color:#444'>📍 <b>Místo:</b> {akce['místo']}<br>🗓️ <b>Datum:</b> {akce['datum'].strftime('%d.%m.%Y')}</div>", unsafe_allow_html=True)
        if pd.notna(akce['popis']): st.info(akce['popis'], icon="ℹ️")
        
        if je_po_deadlinu: st.error(f"⛔ DEADLINE BYL: {deadline_str}")
        else: st.success(f"📅 Deadline: {deadline_str}")

        if main_lat and main_lon:
            forecast = utils.get_forecast(main_lat, main_lon, akce['datum'])
            if forecast:
                w_icon, w_text = utils.get_weather_emoji(forecast['code'])
                st.markdown(styles.get_weather_card_html(w_icon, w_text, round(forecast['temp_max']), forecast['precip'], forecast['wind']), unsafe_allow_html=True)
        
        if je_zavod_obecne:
            st.markdown(f"""<a href="{str(akce.get('odkaz', 'https://oris.orientacnisporty.cz/'))}" target="_blank"><div style="background-color: #2563EB; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold;">👉 Otevřít ORIS</div></a>""", unsafe_allow_html=True)

    # === PRAVÝ SLOUPEC (PŘIHLÁŠKA) ===
    with col_form:
        delete_key_state = f"confirm_delete_{unique_key}"
        
        # Container místo Formu
        with stylable_container(
            key=f"form_cont_{unique_key}",
            css_styles="{border: 1px solid #E5E7EB; border-radius: 12px; padding: 20px; background-color: #F9FAFB; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);}"
        ):
            if not je_po_deadlinu and delete_key_state not in st.session_state:
                st.markdown("<h4 style='margin-top:0;'>✍️ Přihláška</h4>", unsafe_allow_html=True)
                
                # == 1. WIDGETY (ŽIVÉ) ==
                # Klíč je důležitý, aby si pamatoval hodnotu
                vybrane_jmeno = st.selectbox("Jméno", options=seznam_jmen, index=None, placeholder="Vyber jméno...", key=f"sel_jmeno_{unique_key}")
                nove_jmeno = st.text_input("Nebo nové jméno", key=f"inp_new_{unique_key}")
                poznamka = st.text_input("Poznámka", key=f"inp_note_{unique_key}")
                
                ubyt = False
                if "trénink" not in typ_udalosti:
                     ubyt = st.checkbox("🛏️ Společné ubytko", key=f"chk_ubyt_{unique_key}")

                finalni_jmeno = nove_jmeno.strip() if nove_jmeno else vybrane_jmeno

                st.markdown("<br>", unsafe_allow_html=True)

                # == 2. TLAČÍTKA ==
                c_btn1, c_btn2 = st.columns([1, 1], gap="small")
                
                with c_btn1:
                    # Tlačítko pro přímý zápis (bez dopravy)
                    with stylable_container(key=f"c_save_{unique_key}", css_styles="button {background-color: #16A34A !important; color: white !important; border: none !important; width: 100%;}"):
                        if st.button("💾 Zapsat se", key=f"btn_save_{unique_key}"):
                            if finalni_jmeno:
                                try:
                                    df_full = data_manager.load_prihlasky()
                                    # Zachování dopravy, pokud už existuje
                                    existujici = df_full[(df_full['id_akce'] == akce_id_str) & (df_full['jméno'] == finalni_jmeno)]
                                    old_dopr, old_id_auto = "", ""
                                    if not existujici.empty:
                                        old_dopr = existujici.iloc[0].get('doprava', "")
                                        old_id_auto = existujici.iloc[0].get('id_auto', "")

                                    df_full = df_full[~((df_full['id_akce'] == akce_id_str) & (df_full['jméno'] == finalni_jmeno))]
                                    
                                    novy = pd.DataFrame([{
                                        "id_akce": akce_id_str, "název": akce['název'], "jméno": finalni_jmeno,
                                        "poznámka": poznamka, 
                                        "doprava": old_dopr, 
                                        "ubytování": "Ano 🛏️" if ubyt else "",
                                        "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "id_auto": old_id_auto
                                    }])
                                    conn.update(worksheet="prihlasky", data=pd.concat([df_full, novy], ignore_index=True))
                                    st.toast(f"✅ {finalni_jmeno} uložen!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e: st.error(str(e))
                            else: st.warning("Vyber jméno!")

                with c_btn2:
                    # Tlačítko pro DOPRAVU (Otevře dialog)
                    # Díky absenci st.form můžeme číst 'finalni_jmeno' HNED!
                    if st.button("🚗 Doprava...", key=f"btn_dopr_{unique_key}", use_container_width=True):
                        if finalni_jmeno:
                            # Posíláme i poznámku a ubytko, aby to dialog mohl uložit komplet
                            utils.show_doprava_dialog(
                                akce_id_str, akce['název'], akce['datum'].strftime('%d.%m.'), 
                                finalni_jmeno, poznamka, ubyt
                            )
                        else:
                            st.warning("Nejdřív vyber jméno!")

            elif je_po_deadlinu: 
                st.info("🔒 Přihlášky uzavřeny. Kontaktuj trenéra.")

    # --- SEZNAM (Zebra striping preserved) ---
    st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)
    if body_k_vykresleni:
        start_lat, start_lon, _ = body_k_vykresleni[0]
        m = folium.Map(location=[start_lat, start_lon], tiles="OpenStreetMap")
        folium.Marker([start_lat, start_lon], tooltip="Sraz").add_to(m)
        st_folium(m, height=250, width=700, key=f"m_{unique_key}", returned_objects=[])

    st.markdown(f"#### 👥 Zapsaní ({len(lidi)})")
    if not lidi.empty:
        h1, h2, h3, h4, h5, h6 = st.columns([0.4, 2.0, 1.5, 1.2, 0.6, 0.5]) 
        h1.markdown("<b style='color:#9CA3AF'>#</b>", unsafe_allow_html=True)
        h2.markdown("<b>Jméno</b>", unsafe_allow_html=True)
        h3.markdown("<b>Poznámka</b>", unsafe_allow_html=True)
        h4.markdown("<b>Doprava</b>", unsafe_allow_html=True)
        h5.markdown("<b>Ubyt</b>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 5px 0 10px 0; border-top: 1px solid #E5E7EB;'>", unsafe_allow_html=True)
        
        for i, (_, row) in enumerate(lidi.iterrows()):
             bg = "#F3F4F6" if i % 2 == 0 else "white"
             pad = "10px 5px 25px 5px !important" if i % 2 == 0 else "0px 5px 10px 5px !important"
             
             with stylable_container(key=f"r_{unique_key}_{i}", css_styles=f"{{background-color: {bg}; border-radius: 6px; padding: {pad}; margin-bottom: 2px; display: flex; align-items: center; min-height: 40px;}}"):
                 
                 je_k_smazani = (delete_key_state in st.session_state) and (st.session_state[delete_key_state] == row['jméno'])
                 
                 if je_k_smazani:
                     col_warn, col_yes, col_no = st.columns([3, 1, 1], vertical_alignment="center")
                     col_warn.warning(f"Smazat: **{row['jméno']}**?", icon="⚠️")
                     # ... (Logika mazání stejná jako minule - zkráceno pro přehlednost) ...
                     with stylable_container(key=f"btn_yes_c_{i}", css_styles="button {background-color: #DC2626 !important; color: white !important; border: none;}"):
                         if col_yes.button("ANO", key=f"yes_{unique_key}_{i}"):
                            # 1. POKUS O SMAZÁNÍ AUTA A ÚKLID PASAŽÉRŮ (Nová logika)
                            # Pokud je uživatel řidič, handle_driver_removal to vyřeší.
                            # Pokud ne, nic se nestane.
                            utils.handle_driver_removal(conn, akce_id_str, row['jméno'])
                            
                            # 2. SMAZÁNÍ Z PŘIHLÁŠEK (Standardní)
                            # Musíme znovu načíst (refresh), protože handle_driver_removal mohla sáhnout do DB
                            df_curr = data_manager.load_prihlasky() # Použijeme data_manager pro čerstvost
                            df_curr = df_curr[~((df_curr['id_akce'] == akce_id_str) & (df_curr['jméno'] == row['jméno']))]
                            conn.update(worksheet="prihlasky", data=df_curr)
                            
                            del st.session_state[delete_key_state]
                            st.rerun()
                     if col_no.button("ZPĚT", key=f"no_{unique_key}_{i}"):
                         del st.session_state[delete_key_state]
                         st.rerun()

                 else:
                     c1, c2, c3, c4, c5, c6 = st.columns([0.4, 2.0, 1.5, 1.2, 0.6, 0.5], vertical_alignment="center")
                     c1.write(f"{i+1}.")
                     c2.markdown(f"**{row['jméno']}**")
                     c3.caption(row.get('poznámka', ''))
                     
                     # === ZMĚNA: KLIKACÍ TLAČÍTKO PRO DOPRAVU ===
                     dopr = str(row.get('doprava', ''))
                     btn_label = dopr if dopr else "➕"
                     
                     # Stylování tlačítka podle statusu
                     btn_color = "#374151" # Default šedá
                     btn_bg = "#E5E7EB"
                     if "Řidič" in dopr: 
                         btn_color = "white"; btn_bg = "#16A34A"
                     elif "Spolujízda" in dopr or "Jedu s" in dopr:
                         btn_color = "white"; btn_bg = "#2563EB"
                         # Zkrácení labelu, aby nebyl moc dlouhý
                         btn_label = dopr.replace("Spolujízda: ", "🚙 ").replace("Jedu s: ", "🚙 ")
                     elif "Chci" in dopr:
                         btn_color = "white"; btn_bg = "#DC2626"
                         btn_label = "🙋‍♂️ Chci"

                     with stylable_container(
                         key=f"cont_btn_d_{unique_key}_{i}", 
                         css_styles=f"button {{background-color: {btn_bg} !important; color: {btn_color} !important; border: none; padding: 2px 8px; font-size: 0.8rem; height: auto !important; min-height: 0px !important;}}"
                     ):
                         # Kliknutí otevře dialog s předvyplněným jménem a NULL inputy (načte se z DB)
                         if c4.button(btn_label, key=f"btn_row_d_{unique_key}_{i}"):
                             utils.show_doprava_dialog(akce_id_str, akce['název'], akce['datum'].strftime('%d.%m.'), row['jméno'], None, None)

                     c5.write(row.get('ubytování', ''))
                     
                     if not je_po_deadlinu:
                         with stylable_container(key=f"delc_{unique_key}_{i}", css_styles="button {margin:0 !important; padding:0 !important; height:auto !important; border:none; background:transparent; color: #EF4444;}"):
                             if c6.button("🗑️", key=f"del_{unique_key}_{i}"):
                                 st.session_state[delete_key_state] = row['jméno']
                                 st.rerun()
    utils.export_admin_section(lidi, akce['název'], unique_key)
    
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

# --- DASHBOARD NEJBLIŽŠÍCH DEADLINŮ ---
dnes = date.today()
future_deadlines = df_akce[df_akce['deadline'] >= dnes].sort_values('deadline').head(3)

if not future_deadlines.empty:
    st.markdown("### 🔥 Pozor, hoří termíny!")
    
    cols_d = st.columns(len(future_deadlines))
    
    for i, (_, row) in enumerate(future_deadlines.iterrows()):
        days_left = (row['deadline'] - dnes).days
        
        # Logika barev
        if days_left == 0:
            bg_color, border_color, text_color, icon, time_msg = "#FEF2F2", "#EF4444", "#B91C1C", "🚨", "DNES!"
        elif days_left <= 3:
            bg_color, border_color, text_color, icon, time_msg = "#FFFBEB", "#F59E0B", "#B45309", "⚠️", f"Za {days_left} dny"
        else:
            bg_color, border_color, text_color, icon, time_msg = "#ECFDF5", "#10B981", "#047857", "📅", row['deadline'].strftime('%d.%m.')

        unique_key_dash = f"dash_{row['id']}"

        with cols_d[i]:
            with stylable_container(
                key=f"dash_card_{i}",
                css_styles=f"""
                button {{
                    background-color: {bg_color} !important;
                    border: 2px solid {border_color} !important;
                    border-radius: 12px !important;
                    color: #1f2937 !important;
                    width: 100% !important;
                    height: auto !important;
                    min-height: 110px !important;
                    white-space: pre-wrap !important;
                    display: flex !important;
                    flex-direction: column !important;
                    justify-content: center !important;
                    align-items: center !important;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
                    padding: 10px !important;
                    transition: transform 0.2s !important;
                }}
                button:hover {{
                    transform: scale(1.02) !important;
                    border-color: {text_color} !important;
                }}
                button p {{
                    font-family: 'Inter', sans-serif !important;
                }}
                """
            ):
                label_text = f"{icon}\n{row['název']}\n{time_msg}"
                with st.popover(label_text, use_container_width=True):
                    vykreslit_detail_akce(row, unique_key_dash)

    st.markdown("<div style='margin-bottom: 25px'></div>", unsafe_allow_html=True)

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
                        css_styles=f"""button {{background: {styly['bg']} !important; color: {styly['color']} !important; border: {styly['border']} !important; width: 100%; border-radius: 8px; padding: 8px 10px !important; text-align: left; font-size: 0.85rem; font-weight: 600; box-shadow: {styly.get('shadow', 'none')}; margin-bottom: 6px; white-space: normal !important; height: auto !important; min-height: 40px;}} button:hover {{filter: brightness(1.1); transform: translateY(-2px); z-index: 5;}}"""
                    ):
                        with st.popover(label, use_container_width=True):
                            vykreslit_detail_akce(akce, unique_key)

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
                    }}
                    button:hover {{
                        filter: brightness(1.1);
                        transform: translateY(-2px);
                    }}
                """
            ):
                with st.popover(label, use_container_width=True):
                    vykreslit_detail_akce(akce, unique_key)

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

st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)
