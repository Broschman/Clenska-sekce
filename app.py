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
import auth

print("--- ZAČÁTEK RERUNU ---")

# Načtení CSS a mobilního varování
styles.load_css()
styles.inject_mobile_warning()

# --- 1. NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Kalendář RBK", page_icon="🌲", layout="wide")

# 2. LOGIN BRÁNA 🚪
# Pokud check_password vrátí False, aplikace se tady zastaví a dál nečte.
if not auth.check_password():
    st.stop()
    
# --- HLAVIČKA S LOGEM A PROFILEM ---
# Přidali jsme col_profile pro tvoji osobní kartu
col_dummy, col_title, col_profile, col_help = st.columns([0.5, 7, 2, 1], vertical_alignment="center")

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

# --- TVŮJ OSOBNÍ PROFIL ---
with col_profile:
    prihlaseny = st.session_state.get("prihlaseny_uzivatel", "Závodník")
    role = st.session_state.get("role", "")
    
    # Korunka pro admina rovnou na zavřeném tlačítku
    btn_text = f"👑 {prihlaseny}" if role == "admin" else f"👤 {prihlaseny}"
    
    with st.popover(btn_text, use_container_width=True):
        odznak = "👑 (Admin)" if role == "admin" else ""
        st.markdown(f"### 🏃‍♂️ Ahoj, {prihlaseny} {odznak}")
        
        try:
            df_p = data_manager.load_prihlasky()
            df_akce = data_manager.load_akce() 
            
            if df_p.empty or 'jméno' not in df_p.columns:
                moje_prihlasky = pd.DataFrame()
            else:
                moje_prihlasky = df_p[df_p['jméno'] == prihlaseny]
            
            pocet_akci = len(moje_prihlasky)
            ridic_pocet = 0
            if not moje_prihlasky.empty and 'doprava' in moje_prihlasky.columns:
                ridic_pocet = sum(moje_prihlasky['doprava'].astype(str).str.contains("Řidič", na=False))
            
            c1, c2 = st.columns(2)
            c1.metric("Závodů", pocet_akci)
            c2.metric("Dělám řidiče", ridic_pocet)
            
            st.divider()
            st.markdown("**📅 Moje nejbližší akce**")
            
            if not moje_prihlasky.empty and not df_akce.empty and 'id_akce' in moje_prihlasky.columns:
                moje_akce_id = moje_prihlasky['id_akce'].astype(str).tolist()
                
                df_akce_temp = df_akce.copy()
                df_akce_temp['datum_dt'] = pd.to_datetime(df_akce_temp['datum'], errors='coerce')
                sloupec_id = 'id_akce' if 'id_akce' in df_akce_temp.columns else 'id'
                
                moje_budouci = df_akce_temp[
                    (df_akce_temp[sloupec_id].astype(str).isin(moje_akce_id)) & 
                    (df_akce_temp['datum_dt'] >= pd.Timestamp('today').normalize())
                ].sort_values(by='datum_dt').head(3)
                
                if moje_budouci.empty:
                    st.caption("Zatím nic v plánu. Začni trénovat!")
                else:
                    for _, row in moje_budouci.iterrows():
                        nazev = row['název']
                        if len(nazev) > 22: nazev = nazev[:19] + "..."
                        d_str = row['datum_dt'].strftime('%d.%m.') if pd.notnull(row['datum_dt']) else "??"
                        st.caption(f"📍 {d_str} | {nazev}")
            else:
                st.caption("Zatím nejsi nikde zapsaný.")
                
        except Exception as e:
            st.error(f"Chyba profilu: {e}")
            
        st.divider()
        
        # --- ZMĚNA HESLA ---
        with st.expander("🔑 Změnit heslo"):
            with st.form("form_zmena_pinu"):
                stary_pin = st.text_input("Současné heslo", type="password")
                novy_pin = st.text_input("Nové heslo (min. 4 znaky)", type="password")
                potvrzeni = st.text_input("Potvrď nové heslo", type="password")
                btn_zmenit = st.form_submit_button("Uložit nové heslo", type="primary", use_container_width=True)

                if btn_zmenit:
                    if novy_pin != potvrzeni:
                        st.error("❌ Nová hesla se neshodují!")
                    elif len(novy_pin) < 4:
                        st.error("❌ Heslo musí mít alespoň 4 znaky.")
                    else:
                        try:
                            # Načtení databáze jmen pro ověření a zápis
                            conn_jmena = data_manager.get_connection()
                            df_jmena = conn_jmena.read(worksheet="jmena", ttl=0)
                            col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
                            col_pin = 'PIN' if 'PIN' in df_jmena.columns else 'pin'

                            spravny_radek = df_jmena[df_jmena[col_name] == prihlaseny]
                            if not spravny_radek.empty:
                                real_pin = str(spravny_radek.iloc[0].get(col_pin, '')).strip()
                                if real_pin.endswith('.0'): real_pin = real_pin[:-2]

                                if stary_pin.strip() == real_pin:
                                    # Přepsání hesla v tabulce
                                    idx = spravny_radek.index[0]
                                    df_jmena.at[idx, col_pin] = novy_pin
                                    conn_jmena.update(worksheet="jmena", data=df_jmena)

                                    # Aktualizace cookies
                                    import extra_streamlit_components as stx
                                    cookie_manager = stx.CookieManager(key="update_pin_cookie")
                                    from datetime import datetime, timedelta
                                    expires = datetime.now() + timedelta(days=30)
                                    cookie_manager.set("rbk_login_token", f"{prihlaseny}|{novy_pin}", expires_at=expires)

                                    st.success("✅ Heslo úspěšně změněno!")
                                    import time
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ Špatné současné heslo!")
                            else:
                                st.error("❌ Uživatel nenalezen v databázi.")
                        except Exception as e:
                            st.error(f"❌ Chyba spojení: {e}")

        st.divider()
        # --- FILTR NA MOJE AKCE ---
        filtr_zapnuty = st.session_state.get("filtr_moje_akce", False)
        if filtr_zapnuty:
            if st.button("🌐 Zobrazit všechny akce", use_container_width=True):
                st.session_state["filtr_moje_akce"] = False
                st.rerun()
        else:
            if st.button("🎯 Vyfiltrovat jen moje akce", use_container_width=True):
                st.session_state["filtr_moje_akce"] = True
                st.rerun()
                
        # ODHLÁŠENÍ VŽDY VIDITELNÉ
        if st.button("🚪 Odhlásit se", use_container_width=True, type="primary"):
            st.session_state.clear()
            import extra_streamlit_components as stx
            cookie_manager = stx.CookieManager(key="logout_cookie")
            cookie_manager.delete("rbk_login_token")
            import time
            time.sleep(0.5)
            st.rerun()
            
with col_help:
    with st.popover("❔", help="Nápověda a Legenda"):
        # --- NADPIS ---
        st.markdown("### 🌲 Průvodce aplikací")
        
        # --- 1. FUNKCIONALITY ---
        st.markdown("""
        **1. 📅 Dva pohledy na akce**
        * **Kalendář:** Klasický měsíční pohled. Kliknutím na den otevřeš detaily.
        * **Seznam (Filtrování):** Použij lištu nahoře.
            * 🆕 **Rychlý filtr měsíce:** Vyber např. "Srpen 2025" a uvidíš jen relevantní akce.
            * **Hledání:** Piš název nebo místo (např. "MČR").
        
        **2. ✍️ Přihlašování**
        * **Zápis:** V detailu akce vyber jméno.
            * 🆕 **Hromadná přihláška:** Vyber v roletce **více lidí najednou** (např. celou rodinu) a přihlas je jedním kliknutím.
        * **Odhlášení:** V seznamu přihlášených najdi své jméno a klikni na **koš 🗑️**.
        * ⚠️ **Závody (ŽA, ŽB, MČR):** Tabulka zde slouží jen pro dopravu/ubytování! Na závod se musíš přihlásit v **IS ORIS**.
        
        **3. 🚗 Doprava a Ubytování**
        * **Dashboard:** Barevný pruh nad seznamem ti hned řekne, jestli je dost aut (🟢) nebo chybí místa (🔴).
        * **Nastavení:** Klikni na **🚗 Doprava** nebo **🔧 Změnit**.
            * 🆕 **Čekací listina:** Pokud hledáš odvoz, můžeš dopsat místo (např. *"Brno-Lesná"*), aby řidič věděl, kde tě nabrat.
            * 🆕 **Rodinná doprava:** V hromadné přihlášce snadno nastavíš auto pro celou skupinu.
        
        **4. 🗺️ Mapy a Počasí**
        * U akce se automaticky načítá **předpověď** a čas **západu slunce 🌑** (pro noční závody).
        * Dole najdeš mapu s bodem srazu a tlačítka pro navigaci (Waze, Mapy.cz).
        
        **5. 🗓️ Export**
        * **Do mobilu:** Tlačítko 📅 v záhlaví akce ti uloží termín do kalendáře.
        * **Pro trenéry:** Tlačítko **Export** pod seznamem stáhne soupisku do Excelu.
        """)
        
        st.divider()

        # --- 2. LEGENDA BAREV ---
        st.markdown("### 🎨 Legenda barev")
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

# ==========================================
# --- APLIKACE FILTRU "MOJE AKCE" ---
# ==========================================
if st.session_state.get("filtr_moje_akce", False):
    aktualni_uzivatel = st.session_state.get("prihlaseny_uzivatel", "")
    st.info(f"🎯 Zobrazuji pouze akce, na které je přihlášený: **{aktualni_uzivatel}**")
    
    df_p = data_manager.load_prihlasky()
    if not df_p.empty and 'jméno' in df_p.columns and 'id_akce' in df_p.columns:
        moje_prihlasky = df_p[df_p['jméno'] == aktualni_uzivatel]
        moje_akce_id = moje_prihlasky['id_akce'].astype(str).tolist()
        
        sloupec_id = 'id_akce' if 'id_akce' in df_akce.columns else 'id'
        df_akce = df_akce[df_akce[sloupec_id].astype(str).isin(moje_akce_id)]
    else:
        df_akce = pd.DataFrame() # Žádné přihlášky = prázdný kalendář
        
# --- 3. LOGIKA KALENDÁŘE ---
if 'vybrany_datum' not in st.session_state:
    st.session_state.vybrany_datum = date.today()

# --- DASHBOARD NEJBLIŽŠÍCH DEADLINŮ (FINAL - UNIKÁTNÍ AKCE) ---
dnes = date.today()
vsechny_terminy = []

# 1. Sbírání všech možných deadlinů
if not df_akce.empty:
    for _, row in df_akce.iterrows():
        # A) Hlavní deadline
        if row['deadline'] >= dnes:
            vsechny_terminy.append({
                "datum": row['deadline'],
                "typ": "main",
                "nazev": row['název'],
                "row_data": row,
                "id_akce": row['id'] # Důležité pro identifikaci
            })
            
        # B) Deadline ubytování
        raw_ubyt = row.get('deadline_ubytovani')
        if pd.notnull(raw_ubyt):
            try:
                dt_ubyt = pd.to_datetime(raw_ubyt, dayfirst=True, errors='coerce')
                if pd.notnull(dt_ubyt):
                    d_ubyt = dt_ubyt.date()
                    if d_ubyt >= dnes:
                        vsechny_terminy.append({
                            "datum": d_ubyt,
                            "typ": "ubyt",
                            "nazev": row['název'],
                            "row_data": row,
                            "id_akce": row['id']
                        })
            except:
                pass

# 2. Seřadíme podle data (nejbližší nahoře)
vsechny_terminy.sort(key=lambda x: x["datum"])

# 3. FILTRACE DUPLICIT (Chceme jen jednu kartu pro jednu akci - tu nejurgentnější)
unikatni_akce = []
videne_id = set()

for termin in vsechny_terminy:
    if termin['id_akce'] not in videne_id:
        unikatni_akce.append(termin)
        videne_id.add(termin['id_akce'])
    
    # Stačí nám TOP 3
    if len(unikatni_akce) >= 3:
        break

# 4. Vykreslení
if unikatni_akce:
    st.markdown("### 🔥 Pozor, hoří termíny!")
    
    cols_d = st.columns(len(unikatni_akce))
    
    for i, item in enumerate(unikatni_akce):
        row = item['row_data']
        datum_deadline = item['datum']
        typ = item['typ']
        
        days_left = (datum_deadline - dnes).days
        
        # Logika barev
        if days_left == 0:
            bg_color, border_color, text_color, icon_state, time_msg = "#FEF2F2", "#EF4444", "#B91C1C", "🚨", "DNES!"
        elif days_left <= 3:
            bg_color, border_color, text_color, icon_state, time_msg = "#FFFBEB", "#F59E0B", "#B45309", "⚠️", f"Za {days_left} dny"
        else:
            bg_color, border_color, text_color, icon_state, time_msg = "#ECFDF5", "#10B981", "#047857", "📅", datum_deadline.strftime('%d.%m.')

        # Rozlišení textu
        if typ == "ubyt":
            icon_main = "🛏️"
            # Zkrátíme název, aby se tam vešlo "Ubytování:"
            nazev_short = row['název']
            if len(nazev_short) > 20: nazev_short = nazev_short[:18] + ".."
            display_name = f"Ubytování: {nazev_short}"
        else:
            icon_main = icon_state
            display_name = row['název']

        # Unikátní klíč
        unique_key_dash = f"dash_{row['id']}_{typ}"

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
                    text-align: center !important;
                    margin: 0 !important;
                }}
                """
            ):
                label_text = f"{icon_main}\n{display_name}\n{time_msg}"
                with st.popover(label_text, use_container_width=True):
                    utils.vykreslit_detail_akce(row, unique_key_dash, conn, seznam_jmen)

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
                            utils.vykreslit_detail_akce(akce, unique_key, conn, seznam_jmen)

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
    # Resetujeme i filtr měsíce, pokud je nastaven (pomocí klíče widgetu)
    if "month_filter_key" in st.session_state:
        st.session_state.month_filter_key = "📅 Zobrazit vše"

# --- PŘÍPRAVA DAT PRO FILTR MĚSÍCŮ ---
# Tohle musíme udělat před vykreslením sloupců, abychom měli možnosti pro selectbox
mesice_options = ["📅 Zobrazit vše"]
mapa_mesicu = {"📅 Zobrazit vše": "All"}

if not df_akce.empty:
    df_temp = df_akce.copy()
    df_temp['datum_dt'] = pd.to_datetime(df_temp['datum'], errors='coerce')
    df_temp['mesic_sort'] = df_temp['datum_dt'].dt.to_period('M')
    
    dostupne = sorted(df_temp['mesic_sort'].dropna().unique())
    ceske_m = {1: "Leden", 2: "Únor", 3: "Březen", 4: "Duben", 5: "Květen", 6: "Červen", 
               7: "Červenec", 8: "Srpen", 9: "Září", 10: "Říjen", 11: "Listopad", 12: "Prosinec"}
    
    for m in dostupne:
        nazev = f"{ceske_m[m.month]} {m.year}"
        mesice_options.append(nazev)
        mapa_mesicu[nazev] = m

# --- LAYOUT OVLÁDACÍ LIŠTY ---
# Přidali jsme sloupec col_month [1.5, 1.5, 1.5, 0.5]
col_text, col_month, col_date, col_close = st.columns([1.5, 1.5, 1.2, 0.5], gap="small", vertical_alignment="bottom")

with col_text:
    search_text = st.text_input(
        "Hledat text", 
        placeholder="🔍 Název nebo místo...", 
        label_visibility="collapsed",
        key="search_query"
    )

with col_month:
    # NOVÝ FILTR MĚSÍCŮ VE SLOUPCI
    vybrany_mesic_nazev = st.selectbox(
        "Měsíc",
        options=mesice_options,
        index=0,
        key="month_filter_key", # Důležité pro resetování
        label_visibility="collapsed"
    )

with col_date:
    search_date_value = st.date_input(
        "Vyber datum",
        min_value=date.today(),
        max_value=date(2030, 12, 31),
        key="search_date",
        label_visibility="collapsed",
        help="Vyber konkrétní termín"
    )

with col_close:
    # Tlačítko smazat se zobrazí, pokud je cokoliv aktivní
    if search_text or len(st.session_state.search_date) > 0 or vybrany_mesic_nazev != "📅 Zobrazit vše":
        st.button("❌", on_click=clear_search, help="Zrušit všechny filtry")

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

# Aktivní filtr poznáme tak, že je zadán text, datum NEBO vybrán měsíc
je_aktivni_filtr = search_text or len(search_date_value) > 0 or vybrany_mesic_nazev != "📅 Zobrazit vše"

if je_aktivni_filtr:
    
    # 🅰️ REŽIM SEZNAMU (FILTROVÁNÍ)
    dnes = date.today()
    
    # ZMĚNA: Defaultně hledáme jen v BUDOUCNOSTI (včetně dneška)
    # Tím pádem "MČR" najde jen ta budoucí, ne ta loňská.
    mask = (df_akce['datum'] >= dnes)

    # 1. Filtr podle TEXTU
    if search_text:
        mask = mask & (
            df_akce['název'].str.contains(search_text, case=False, na=False) | 
            df_akce['místo'].str.contains(search_text, case=False, na=False)
        )
    
    # 2. Filtr podle MĚSÍCE (Selectbox)
    if vybrany_mesic_nazev != "📅 Zobrazit vše":
        # Pokud uživatel vybere měsíc, pravděpodobně chce vidět ten konkrétní měsíc, 
        # i kdyby byl už z části v minulosti (např. v půlce srpna chce vidět celý srpen).
        # Takže tady tu podmínku "budoucnosti" trochu uvolníme, aby viděl celý vybraný měsíc.
        temp_dates = pd.to_datetime(df_akce['datum'], errors='coerce').dt.to_period('M')
        target_period = mapa_mesicu[vybrany_mesic_nazev]
        
        # Přepíšeme masku: Chceme akce z TOHOTO měsíce (bez ohledu na to, jestli už proběhly, 
        # protože když si někdo vybere "Srpen", asi chce vidět, co všechno v srpnu je/bylo).
        mask = (temp_dates == target_period)
        
        if isinstance(target_period, pd.Period):
             st.session_state.vybrany_datum = target_period.start_time.date()

    # 3. Filtr podle DATA (Date Input)
    if len(search_date_value) > 0:
        # Pokud vybere konkrétní datum, respektujeme ho (i kdyby bylo v minulosti)
        if len(search_date_value) == 1:
            vybrane_datum = search_date_value[0]
            mask = (df_akce['datum'] == vybrane_datum)
        elif len(search_date_value) == 2:
            start, end = search_date_value
            mask = (df_akce['datum'] >= start) & (df_akce['datum'] <= end)
    
    # Aplikace masky
    results = df_akce[mask].sort_values(by='datum')
    
    # Informativní text
    info_parts = []
    if search_text: info_parts.append(f"text '{search_text}'")
    if vybrany_mesic_nazev != "📅 Zobrazit vše": info_parts.append(f"měsíc {vybrany_mesic_nazev}")
    if len(search_date_value) > 0: info_parts.append("vybrané datum")
    
    info_text = f"Nalezeno {len(results)} akcí"
    if info_parts: info_text += " (" + ", ".join(info_parts) + ")"
        
    st.markdown(f"<div style='color: #4B5563; margin-bottom: 10px; font-size: 0.9rem;'>{info_text}</div>", unsafe_allow_html=True)
    
    if results.empty:
        st.warning("Žádné akce neodpovídají zadání.")
    else:
        for _, akce in results.iterrows():
            # ... (Zde voláme vykreslení stejně jako předtím) ...
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
                    utils.vykreslit_detail_akce(akce, unique_key, conn, seznam_jmen)

else:
    # 🅱️ REŽIM KALENDÁŘE (Pokud není nic vybráno)
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
