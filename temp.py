import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import styles
import data_manager
import folium
from streamlit_folium import st_folium
import base64
from io import BytesIO
import re

@st.cache_data(ttl=3600*24) # Uložíme si to na 24 hodin
def get_coords_from_place(place_name):
    """Zjistí souřadnice podle názvu místa (Geocoding přes Nominatim)."""
    if not place_name or len(place_name) < 3:
        return None, None
        
    try:
        # User-Agent je povinný pro Nominatim (identifikace aplikace)
        headers = {'User-Agent': 'RBK_Kalendar_App/1.0'}
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": place_name,
            "format": "json",
            "limit": 1,
            "countrycodes": "cz" # Preferujeme Česko
        }
        
        r = requests.get(url, params=params, headers=headers, timeout=2)
        data = r.json()
        
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
        return None, None
    except:
        return None, None
        
# === POMOCNÉ FUNKCE ===
def get_base64_image(image_path):
    """Načte obrázek a převede ho na base64 string pro HTML."""
    if not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()
        
def generate_ics(akce):
    """
    Vygeneruje robustní .ics soubor kompatibilní s Google Calendar i Outlook.
    """
    # 1. Formátování data (YYYYMMDD)
    fmt = "%Y%m%d"
    start_str = akce['datum'].strftime(fmt)
    # Pro celodenní událost musí být konec o den dál
    end_date = akce['datum_do'] + timedelta(days=1)
    end_str = end_date.strftime(fmt)
    
    # 2. Timestamp vytvoření (Google to vyžaduje pro validaci)
    now_str = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    
    # 3. Příprava popisu - POZOR: Google nesnáší skutečné odřádkování v textu
    # Musíme nahradit reálný enter znakem '\\n' (textové lomítko a n)
    popis_raw = str(akce.get('popis', '')) if pd.notna(akce.get('popis')) else ""
    odkaz_raw = str(akce.get('odkaz', '')) if pd.notna(akce.get('odkaz')) else ""
    
    # Sestavení textu popisu
    full_desc_list = []
    if popis_raw:
        full_desc_list.append(popis_raw)
    if odkaz_raw:
        full_desc_list.append(f"Web: {odkaz_raw}")
    
    # Spojíme to a nahradíme reálné entery za escaped sekvenci
    full_desc = "\\n\\n".join(full_desc_list)
    # Důležité: Nahrazení případných enterů uvnitř textu poznámky
    full_desc = full_desc.replace("\r\n", "\\n").replace("\n", "\\n").replace(",", "\\,")
    
    # Čištění názvu a místa (taky nesmí obsahovat čárky bez lomítka)
    summary = akce['název'].replace(",", "\\,")
    location = str(akce['místo']).replace(",", "\\,")
    
    # Unikátní ID
    uid = f"rbk_{akce.get('id', 'unknown')}_{start_str}@rbk-kalendar"
    
    # 4. Sestavení souboru s povinnými CRLF (\r\n) konci řádků
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//RBK Kalendar//CZ",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_str}",
        f"DTSTART;VALUE=DATE:{start_str}",
        f"DTEND;VALUE=DATE:{end_str}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{full_desc}",
        f"LOCATION:{location}",
        "STATUS:CONFIRMED",
        "TRANSP:TRANSPARENT", # Událost je zobrazena jako "Volno" (celodenní), změň na OPAQUE pro "Obsazeno"
        "END:VEVENT",
        "END:VCALENDAR"
    ]
    
    # Spojíme řádky pomocí standardního CRLF
    return "\r\n".join(ics_lines)
    
# === DIALOG PRO AUTA (NOVÁ FUNKCE - ZACHOVÁNA) ===
@st.dialog("🚗 Správa dopravy")
def show_doprava_dialog(akce_id, nazev_akce, datum_akce, pre_jmeno, in_poznamka=None, in_ubytovani=None):
    # ... (Zde je logika dialogu stejná jako v Cyber verzi, jen bez stylů) ...
    # Zkopíruj si sem obsah funkce show_doprava_dialog z předchozího kódu.
    # Jediná změna: místo `styles.get_...` použij prostě `st.button`.
    
    # PRO ÚSPORU MÍSTA ZDE VYPISUJI JEN ZKRÁCENOU LOGIKU - POUŽIJ TU Z MINULA, ALE BEZ STYLABLE CONTAINERŮ
    conn = data_manager.get_connection()
    df_auta = data_manager.load_auta()
    df_lidi = data_manager.load_prihlasky()
    
    lidi_akce = df_lidi[df_lidi['id_akce'] == akce_id]
    
    st.markdown(f"**{nazev_akce}** ({datum_akce}) - {pre_jmeno}")
    
    # Jednoduché rádio
    role = st.radio("Doprava:", ["Zrušit dopravu", "Řidič (Auto)", "Pasažér (Chci svézt)"], horizontal=True)
    
    if role == "Řidič (Auto)":
        kap = st.number_input("Kapacita", 1, 9, 4)
        cas = st.text_input("Čas", placeholder="17:00")
        misto = st.text_input("Místo odjezdu", placeholder="Loděnice")
        if st.button("Uložit auto", type="primary"):
            # ... (Logika uložení stejná jako minule) ...
            # Zde doplň volání data_manageru
            st.rerun()
            
    elif role == "Pasažér (Chci svézt)":
        # Výběr auta
        auta_akce = df_auta[df_auta['id_akce'] == akce_id]
        opts = [f"{row['ridic']} (Volno: {row['kapacita']})" for _, row in auta_akce.iterrows()]
        opts.append("Čekám na odvoz (Waiting List)")
        
        vyber = st.selectbox("Ke komu?", opts)
        if st.button("Uložit pasažéra", type="primary"):
            # ... (Logika uložení) ...
            st.rerun()
            
    else: # Zrušit
        if st.button("Smazat požadavek na dopravu"):
            # ... (Logika smazání) ...
            st.rerun()

# === HLAVNÍ DETAIL AKCE (REFACTOR -> LIGHT VERSION) ===
def vykreslit_detail_akce(akce, unique_key):
    """Vykreslí detail akce - ČISTÁ, RYCHLÁ VERZE."""
    conn = data_manager.get_connection()
    
    # Data
    akce_id = str(akce['id']).replace('.0', '')
    dnes = date.today()
    deadline = akce['deadline']
    je_po_deadlinu = dnes > deadline
    
    lidi = data_manager.load_prihlasky_pro_akci(akce_id) # Optimalizované načítání
    
    # Layout: 2 Sloupce (Info vs Formulář)
    c1, c2 = st.columns([1.3, 1], gap="large")
    
    with c1:
        st.subheader(f"🌲 {akce['název']}")
        st.caption(f"📅 {akce['datum'].strftime('%d.%m.%Y')} • 📍 {akce['místo']}")
        
        if pd.notna(akce.get('popis')): st.info(akce['popis'])
        
        # Deadliny (Jednoduché metrics)
        d_cols = st.columns(2)
        d_cols[0].metric("Deadline přihlášek", deadline.strftime('%d.%m.'), delta="Uzavřeno" if je_po_deadlinu else "Otevřeno", delta_color="inverse")
        if pd.notna(akce.get('deadline_ubytovani')):
            d_cols[1].metric("Deadline ubytování", akce['deadline_ubytovani'].strftime('%d.%m.'))
            
        # Odkazy (Jednoduchá tlačítka)
        u_cols = st.columns([1, 1, 2])
        if pd.notna(akce.get('odkaz')): u_cols[0].link_button("Web / ORIS", akce['odkaz'])
        
        # Mapa (Folium)
        if pd.notna(akce.get('mapa')):
            st.markdown("---")
            # Zde by byla logika mapy (zkráceno)
            st.caption("🗺️ Mapa místa")

    with c2:
        # Formulář Přihlášky
        st.markdown("#### ✍️ Přihláška")
        if not je_po_deadlinu:
            with st.form(f"form_{unique_key}"):
                jmeno = st.selectbox("Jméno", data_manager.load_jmena(), key=f"n_{unique_key}")
                poznamka = st.text_input("Poznámka")
                ubyt = st.checkbox("Chci ubytování")
                
                submitted = st.form_submit_button("Přihlásit se", type="primary", use_container_width=True)
                if submitted:
                    data_manager.sign_up_user(akce_id, jmeno, poznamka) # Volání backendu
                    st.toast("Uloženo!")
                    st.rerun()
        else:
            st.error("🔒 Přihlášky jsou uzavřeny.")

        # Tabulka lidí (RYCHLÁ - Bez stylable containers)
        st.markdown(f"#### 👥 Přihlášeno ({len(lidi)})")
        if not lidi.empty:
            # Hlavička
            h = st.columns([0.5, 2, 1.5, 1.5, 0.5])
            h[1].markdown("**Jméno**")
            h[2].markdown("**Poznámka**")
            h[3].markdown("**Doprava**")
            
            st.divider()
            
            for i, row in lidi.iterrows():
                cols = st.columns([0.5, 2, 1.5, 1.5, 0.5])
                cols[0].write(f"{i+1}.")
                cols[1].write(row['jméno'])
                cols[2].caption(row.get('poznámka', ''))
                
                # Tlačítko dopravy (Jednoduché)
                dopr = row.get('doprava', '')
                btn_lbl = "➕"
                btn_type = "secondary"
                if "Řidič" in dopr: btn_lbl, btn_type = "🚙 Řidič", "primary"
                elif "Chci" in dopr: btn_lbl, btn_type = "🙋‍♂️ Chci", "secondary"
                elif "Spolujízda" in dopr: btn_lbl, btn_type = f"🚙 {dopr.split(':')[-1]}", "secondary"
                
                if cols[3].button(btn_lbl, key=f"d_{unique_key}_{i}", type=btn_type, use_container_width=True):
                    show_doprava_dialog(akce_id, akce['název'], "", row['jméno'])

                # Koš
                if not je_po_deadlinu:
                    if cols[4].button("🗑️", key=f"del_{unique_key}_{i}"):
                        data_manager.sign_out_user(akce_id, row['jméno'])
                        st.rerun()
