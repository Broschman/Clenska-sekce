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
import styles
import utils
import data_manager

# Načtení CSS
styles.load_css()

# --- 1. NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Kalendář RBK", page_icon="🌲", layout="wide")
    
def vykreslit_detail_akce(akce, unique_key):
    """
    Vykreslí kompletní obsah popoveru.
    Úprava: Počasí je pod Deadlinem, čára odstraněna.
    """
    # --- 1. PŘÍPRAVA DAT (SOUŘADNICE PRO POČASÍ) ---
    mapa_raw = str(akce['mapa']).strip() if 'mapa' in df_akce.columns and pd.notna(akce['mapa']) else ""
    body_k_vykresleni = [] 
    main_lat, main_lon = None, None
    
    if body_k_vykresleni:
        main_lat, main_lon, _ = body_k_vykresleni[0]

    # === NOVÝ FALLBACK: Zkusíme zjistit polohu podle názvu místa ===
    if (not main_lat or not main_lon) and akce['místo']:
        # Pokud nemáme souřadnice z mapy, zkusíme geocoding
        found_lat, found_lon = utils.get_coords_from_place(str(akce['místo']))
        if found_lat and found_lon:
            main_lat, main_lon = found_lat, found_lon
            # Poznámka: Mapu dole vykreslovat nebudeme (nemáme přesný bod srazu),
            # ale použijeme to aspoň pro počasí.

    # Pomocná funkce DMS -> Decimal
    def dms_to_decimal(dms_str):
        try:
            dms_str = dms_str.upper().strip()
            match = re.match(r"(\d+)[°](\d+)['′](\d+(\.\d+)?)[^NSEW]*([NSEW])?", dms_str)
            if match:
                deg, minutes, seconds, _, direction = match.groups()
                val = float(deg) + float(minutes)/60 + float(seconds)/3600
                if direction in ['S', 'W']: val = -val
                return val
            return float(dms_str)
        except: return None

    # Logika parsování (pro počasí i mapu)
    if mapa_raw:
        try:
            if "http" in mapa_raw:
                parsed = urlparse(mapa_raw)
                params = parse_qs(parsed.query)
                if 'ud' in params:
                    uds = params['ud']
                    uts = params.get('ut', [])
                    for i, ud_val in enumerate(uds):
                        parts = ud_val.split(',')
                        if len(parts) >= 2:
                            lat, lon = dms_to_decimal(parts[0]), dms_to_decimal(parts[1])
                            if lat and lon:
                                nazev = uts[i] if i < len(uts) else f"Bod {i+1}"
                                body_k_vykresleni.append((lat, lon, nazev))
                if not body_k_vykresleni:
                    lat, lon = None, None
                    if 'x' in params and 'y' in params:
                        lon, lat = float(params['x'][0]), float(params['y'][0])
                    elif 'q' in params:
                        q_parts = params['q'][0].replace(' ', '').split(',')
                        if len(q_parts) >= 2: lat, lon = float(q_parts[0]), float(q_parts[1])
                    if lat and lon: body_k_vykresleni.append((lat, lon, akce['název']))
            else:
                raw_parts = mapa_raw.split(';')
                for part in raw_parts:
                    part = part.strip()
                    if not part: continue
                    clean_text = re.sub(r'[^\d.,]', ' ', part)
                    num_parts = clean_text.replace(',', ' ').split()
                    num_parts = [p for p in num_parts if len(p) > 0]
                    if len(num_parts) >= 2:
                        v1, v2 = float(num_parts[0]), float(num_parts[1])
                        if 12 <= v1 <= 19 and 48 <= v2 <= 52: lat, lon = v2, v1
                        else: lat, lon = v1, v2
                        body_k_vykresleni.append((lat, lon, f"Bod {len(body_k_vykresleni)+1}"))
        except: pass
    
    if body_k_vykresleni:
        main_lat, main_lon, _ = body_k_vykresleni[0]

    # --- ZBYTEK PROMĚNNÝCH ---
    akce_id_str = str(akce['id']) if 'id' in df_akce.columns else ""
    typ_udalosti = str(akce['typ']).lower().strip() if 'typ' in df_akce.columns and pd.notna(akce['typ']) else ""
    druh_akce = str(akce['druh']).lower().strip() if 'druh' in df_akce.columns and pd.notna(akce['druh']) else "ostatní"
    kategorie_txt = str(akce['kategorie']).strip() if 'kategorie' in df_akce.columns and pd.notna(akce['kategorie']) else ""
    je_stafeta = "štafety" in typ_udalosti
    je_zavod_obecne = any(s in typ_udalosti for s in ["závod", "mčr", "žebříček", "liga", "mistrovství", "štafety", "ža", "žb"])
    dnes = date.today()
    je_po_deadlinu = dnes > akce['deadline']
    je_dnes_deadline = dnes == akce['deadline']
    deadline_str = akce['deadline'].strftime('%d.%m.%Y')
    nazev_full = akce['název']

    style_key = "default"
    typ_label_short = "AKCE"
    if "mčr" in typ_udalosti: typ_label_short = "MČR"
    elif "ža" in typ_udalosti: typ_label_short = "ŽA"
    elif "žb" in typ_udalosti: typ_label_short = "ŽB"
    elif "soustředění" in typ_udalosti: typ_label_short = "SOUSTŘEDĚNÍ"
    elif "stafety" in typ_udalosti: typ_label_short = "ŠTAFETY"
    elif "trénink" in typ_udalosti: typ_label_short = "TRÉNINK"
    elif je_zavod_obecne: typ_label_short = "ZÁVOD"
    elif "zimní" in typ_udalosti: typ_label_short = "ZIMNÍ LIGA"

    # --- LAYOUT START ---
    col_info, col_form = st.columns([1.2, 1], gap="large")
    
    with col_info:
        # Nadpis + Export
        c_head, c_cal = st.columns([0.85, 0.15], gap="small", vertical_alignment="center")
        with c_head:
            st.markdown(f"<h3 style='margin:0; padding:0;'>{nazev_full}</h3>", unsafe_allow_html=True)
        with c_cal:
            ics_data = utils.generate_ics(akce)
            
            # --- ŘEŠENÍ PRO ČISTÝ LOG (Base64 odkaz) ---
            # Zakódujeme data přímo do tlačítka. Server Streamlitu to ignoruje = žádná chyba v logu.
            b64 = base64.b64encode(ics_data.encode('utf-8')).decode()
            
            # Stylování, aby to vypadalo jako hezké tlačítko
            href = f'<a href="data:text/calendar;base64,{b64}" download="{akce["název"]}.ics" style="text-decoration:none;">'
            href += '''
            <div style="
                background-color: #ffffff;
                border: 1px solid rgba(49, 51, 63, 0.2);
                border-radius: 8px;
                padding: 6px 0px;
                text-align: center;
                cursor: pointer;
                color: #31333F;
                font-size: 1.2rem;
                line-height: 1.5;
                transition: background-color 0.2s;
            " onmouseover="this.style.backgroundColor='#f0f2f6'; this.style.borderColor='#f0f2f6';" onmouseout="this.style.backgroundColor='#ffffff'; this.style.borderColor='rgba(49, 51, 63, 0.2)';">
                📅
            </div>
            '''
            href += '</a>'
            
            st.markdown(href, unsafe_allow_html=True)

        st.markdown(
            styles.badge(typ_label_short, bg="#F3F4F6", color="#333") + 
            styles.badge(druh_akce.upper(), bg="#E5E7EB", color="#555"), 
            unsafe_allow_html=True
        )
        
        # Info blok
        st.markdown("<div style='margin-top: 20px; font-size: 0.95rem; color: #444;'>", unsafe_allow_html=True)
        st.write(f"📍 **Místo:** {akce['místo']}")
        
        if akce['datum'] != akce['datum_do']:
            st.write(f"🗓️ **Termín:** {akce['datum'].strftime('%d.%m.')} – {akce['datum_do'].strftime('%d.%m.%Y')}")
        else:
             st.write(f"🗓️ **Datum:** {akce['datum'].strftime('%d.%m.%Y')}")
        
        if kategorie_txt:
            st.write(f"🎯 **Kategorie:** {kategorie_txt}")
        st.markdown("</div>", unsafe_allow_html=True)

        # 1. Popis (Info bublina)
        if pd.notna(akce['popis']): 
            st.info(f"{akce['popis']}", icon="ℹ️")
        
        # ZDE BYLA ČÁRA (st.markdown("---")) - ODSTRANĚNO

        # 2. Deadline (Barevný box)
        if je_po_deadlinu:
            st.error(f"⛔ **DEADLINE BYL:** {deadline_str}")
        elif je_dnes_deadline:
            st.warning(f"⚠️ **DNES JE DEADLINE!** ({deadline_str})")
        else:
            st.success(f"📅 **Deadline:** {deadline_str}")

        # 3. 🌦️ POČASÍ
        if main_lat and main_lon:
            forecast = utils.get_forecast(main_lat, main_lon, akce['datum'])
            
            if forecast:
                w_icon, w_text = utils.get_weather_emoji(forecast['code'])
                temp = round(forecast['temp_max'])
                rain = forecast['precip']
                wind = forecast['wind']
                
                bg_weather = "#eff6ff" if rain > 1 else "#f9fafb" 
                border_weather = "#bfdbfe" if rain > 1 else "#e5e7eb"

                st.markdown(f"""
                <div style="
                    margin-top: 10px; /* Odstup od Deadlinu */
                    margin-bottom: 20px;
                    padding: 10px; 
                    background-color: {bg_weather}; 
                    border: 1px solid {border_weather}; 
                    border-radius: 10px; 
                    display: flex; 
                    align-items: center; 
                    gap: 15px;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                ">
                    <div style="font-size: 2rem;">{w_icon}</div>
                    <div style="line-height: 1.2;">
                        <div style="font-weight: 700; color: #1f2937;">{w_text}, {temp}°C</div>
                        <div style="font-size: 0.85rem; color: #4b5563;">
                            💧 {rain} mm  •  💨 {wind} km/h
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # 4. ORIS Link
        if je_zavod_obecne:
            st.caption("Přihlášky probíhají v systému ORIS.")
            link_target = str(akce['odkaz']).strip() if 'odkaz' in df_akce.columns and pd.notna(akce['odkaz']) else "https://oris.orientacnisporty.cz/"
            if je_stafeta: st.warning("⚠️ **ŠTAFETY:** Přihlaš se i ZDE (vpravo) kvůli soupiskám!")
            
            st.markdown(f"""
            <a href="{link_target}" target="_blank" style="text-decoration:none;">
                <div style="background-color: #2563EB; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold;">
                    👉 Otevřít ORIS
                </div>
            </a>
            """, unsafe_allow_html=True)

    with col_form:
        delete_key_state = f"confirm_delete_{unique_key}"
        with stylable_container(
            key=f"form_cont_{unique_key}",
            css_styles="{border: 1px solid #E5E7EB; border-radius: 12px; padding: 20px; background-color: #F9FAFB; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);}"
        ):
            if not je_po_deadlinu and delete_key_state not in st.session_state:
                st.markdown("<h4 style='margin-top:0;'>✍️ Interní tabulka</h4>", unsafe_allow_html=True)
                if je_zavod_obecne and not je_stafeta:
                    st.markdown("""<div style="background-color: #FEF2F2; border: 1px solid #FCA5A5; color: #B91C1C; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-weight: bold; font-size: 0.9em; display: flex; align-items: center;"><span style="font-size: 1.2em; margin-right: 8px;">⚠️</span>Je nutné se přihlásit i v ORISu!</div>""", unsafe_allow_html=True)

                form_key = f"form_{unique_key}"
                with st.form(key=form_key, clear_on_submit=True):
                    if kategorie_txt and kategorie_txt.lower() != "všichni": st.warning(f"Doporučení: **{kategorie_txt}**")
                    vybrane_jmeno = st.selectbox("Jméno", options=seznam_jmen, index=None, placeholder="Vyber ze seznamu...")
                    nove_jmeno = st.text_input("Nebo nové jméno")
                    poznamka_input = st.text_input("Poznámka")
                    c_check1, c_check2 = st.columns(2)
                    doprava_input = c_check1.checkbox("🚗 Sháním odvoz")
                    ubytovani_input = False
                    if "trénink" not in typ_udalosti: ubytovani_input = c_check2.checkbox("🛏️ Společné ubytko")
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    with stylable_container(key=f"submit_btn_{unique_key}", css_styles="button {background-color: #16A34A !important; color: white !important; border: none !important; transform: translateY(-10px) !important;}"):
                        odeslat_btn = st.form_submit_button("Zapsat se")
                    
                    if odeslat_btn:
                        finalni_jmeno = nove_jmeno.strip() if nove_jmeno else vybrane_jmeno
                        if finalni_jmeno:
                            try:
                                aktualni = conn.read(worksheet="prihlasky", ttl=0)
                                if 'id_akce' not in aktualni.columns: aktualni['id_akce'] = ""
                                aktualni['id_akce'] = aktualni['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
                                duplicita = not aktualni[(aktualni['id_akce'] == akce_id_str) & (aktualni['jméno'] == finalni_jmeno)].empty
                                if duplicita: st.warning(f"⚠️ {finalni_jmeno}, na této akci už jsi!")
                                else:
                                    hodnota_dopravy = "Ano 🚗" if doprava_input else ""
                                    hodnota_ubytovani = "Ano 🛏️" if ubytovani_input else ""
                                    novy_zaznam = pd.DataFrame([{"id_akce": akce_id_str, "název": akce['název'], "jméno": finalni_jmeno, "poznámka": poznamka_input, "doprava": hodnota_dopravy, "ubytování": hodnota_ubytovani, "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                                    conn.update(worksheet="prihlasky", data=pd.concat([aktualni, novy_zaznam], ignore_index=True))
                                    if finalni_jmeno not in seznam_jmen:
                                        try:
                                            aktualni_jmena = data_managerconn.read(worksheet="jmena", ttl=0)
                                            conn.update(worksheet="jmena", data=pd.concat([aktualni_jmena, pd.DataFrame([{"jméno": finalni_jmeno}])], ignore_index=True))
                                        except: pass

                                    data_manager.refresh_prihlasky()
                                    
                                    with styles.st_lottie_spinner(lottie_success, key=f"anim_{unique_key}"): time.sleep(2)
                                    st.toast(f"✅ {finalni_jmeno} zapsán(a)!")
                                    st.rerun()
                            except Exception as e: st.error(f"Chyba: {e}")
                        else: st.warning("Vyplň jméno!")
            elif je_po_deadlinu: st.info("🔒 Tabulka uzavřena. Kontaktuj trenéra.")

    # --- MAPA (DOLE) ---
    st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)
    if body_k_vykresleni:
        st.markdown("<div style='margin-bottom: 10px; font-weight: bold; font-size: 1.1em;'>🗺️ Místo srazu / Parkování:</div>", unsafe_allow_html=True)
        start_lat, start_lon, _ = body_k_vykresleni[0]
        m = folium.Map(location=[start_lat, start_lon], tiles="OpenStreetMap")
        min_lat, max_lat, min_lon, max_lon = 90, -90, 180, -180
        
        for i, (b_lat, b_lon, b_nazev) in enumerate(body_k_vykresleni):
            if b_lat < min_lat: min_lat = b_lat
            if b_lat > max_lat: max_lat = b_lat
            if b_lon < min_lon: min_lon = b_lon
            if b_lon > max_lon: max_lon = b_lon
            
            barva, ikona, prefix = "blue", "info-sign", "glyphicon"
            if len(body_k_vykresleni) == 1: barva, ikona = "red", "flag"
            else:
                if i == 0: barva, ikona, prefix = "blue", "car", "fa"
                elif i == 1: barva, ikona = "red", "flag"

            folium.Marker([b_lat, b_lon], popup=b_nazev, tooltip=b_nazev, icon=folium.Icon(color=barva, icon=ikona, prefix=prefix)).add_to(m)

        sw, ne = [min_lat - 0.005, min_lon - 0.005], [max_lat + 0.005, max_lon + 0.005]
        m.fit_bounds([sw, ne])
        st_data = st_folium(m, height=320, width=750, returned_objects=[], key=f"map_{unique_key}")

        link_mapy_cz = mapa_raw if "http" in mapa_raw and ("mapy.cz" in mapa_raw or "mapy.com" in mapa_raw) else f"https://mapy.cz/turisticka?q={start_lat},{start_lon}"
        link_google = f"https://www.google.com/maps/search/?api=1&query={start_lat},{start_lon}"
        link_waze = f"https://waze.com/ul?ll={start_lat},{start_lon}&navigate=yes"

        st.markdown(f"""
        <div style="display: flex; gap: 10px; margin-top: -10px; margin-bottom: 20px; justify-content: space-between;">
            <a href="{link_mapy_cz}" target="_blank" style="text-decoration:none; flex: 1;"><div style="background-color: white; border: 1px solid #E5E7EB; border-radius: 8px; padding: 12px; text-align: center; color: #B91C1C; font-weight: 700; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">🌲 Otevřít Mapy.cz</div></a>
            <a href="{link_google}" target="_blank" style="text-decoration:none; flex: 1;"><div style="background-color: white; border: 1px solid #E5E7EB; border-radius: 8px; padding: 12px; text-align: center; color: #2563EB; font-weight: 700; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">🚗 Google Maps</div></a>
            <a href="{link_waze}" target="_blank" style="text-decoration:none; flex: 1;"><div style="background-color: white; border: 1px solid #E5E7EB; border-radius: 8px; padding: 12px; text-align: center; color: #3b82f6; font-weight: 700; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">🚙 Waze</div></a>
        </div>""", unsafe_allow_html=True)
    elif mapa_raw: st.warning("⚠️ Mapa se nenačetla.")

    # --- SEZNAM ---
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    if akce_id_str: 
        lidi = df_prihlasky[df_prihlasky['id_akce'] == akce_id_str].copy()
        lidi = lidi.fillna("") 
    else: 
        lidi = pd.DataFrame()
    st.markdown(f"#### 👥 Zapsaní ({len(lidi)})")
    
    # Mazání
    if delete_key_state in st.session_state:
        clovek = st.session_state[delete_key_state]
        with st.container():
            st.warning(f"⚠️ Opravdu smazat: **{clovek}**?")
            c1, c2 = st.columns(2)
            if c1.button("✅ ANO", key=f"y_{unique_key}"):
                df_curr = conn.read(worksheet="prihlasky", ttl=0)
                df_curr['id_akce'] = df_curr['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
                conn.update(worksheet="prihlasky", data=df_curr[~((df_curr['id_akce'] == akce_id_str) & (df_curr['jméno'] == clovek))])
                del st.session_state[delete_key_state]
                data_manager.refresh_prihlasky()
                st.toast("🗑️ Smazáno."); time.sleep(1); st.rerun()
            if c2.button("❌ ZPĚT", key=f"n_{unique_key}"): del st.session_state[delete_key_state]; st.rerun()

    if not lidi.empty:
        h1, h2, h3, h4, h5, h6 = st.columns([0.4, 2.0, 1.5, 0.6, 0.6, 0.5]) 
        h1.markdown("<b style='color:#9CA3AF'>#</b>", unsafe_allow_html=True); h2.markdown("<b>Jméno</b>", unsafe_allow_html=True); h3.markdown("<b>Poznámka</b>", unsafe_allow_html=True); h4.markdown("🚗", unsafe_allow_html=True); h5.markdown("🛏️", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 5px 0 10px 0; border-top: 1px solid #E5E7EB;'>", unsafe_allow_html=True)
        for i, (idx, row) in enumerate(lidi.iterrows()):
            bg = "#F3F4F6" if i % 2 == 0 else "white"
            pad = "10px 5px 25px 5px !important" if i % 2 == 0 else "0px 5px 10px 5px !important"
            with stylable_container(key=f"r_{unique_key}_{idx}", css_styles=f"{{background-color: {bg}; border-radius: 6px; padding: {pad}; margin-bottom: 2px; display: flex; align-items: center; min-height: 40px;}}"):
                c1, c2, c3, c4, c5, c6 = st.columns([0.4, 2.0, 1.5, 0.6, 0.6, 0.5], vertical_alignment="center")
                c1.write(f"{i+1}."); c2.markdown(f"**{row['jméno']}**"); c3.caption(row.get('poznámka', '')); c4.write(row.get('doprava', '')); c5.write(row.get('ubytování', ''))
                if not je_po_deadlinu:
                     with stylable_container(key=f"delc_{unique_key}_{idx}", css_styles="button {margin:0 !important; padding:0 !important; height:auto !important; border:none; background:transparent;}"):
                        if c6.button("🗑️", key=f"d_{unique_key}_{idx}"): st.session_state[delete_key_state] = row['jméno']; st.rerun()
    else: st.caption("Zatím nikdo. Buď první!")

    # === 🆕 SEKCE EXPORTU ===
    if not lidi.empty:
        st.markdown("---")
        # Layout: Vlevo (1/3) export, Vpravo (2/3) prázdno
        c_export, c_dummy = st.columns([1, 2])
        
        with c_export:
            # Rozbalovací menu
            with st.expander("🔐 Export pro trenéry"):
                # Input na heslo
                password = st.text_input("Zadej heslo:", type="password", key=f"pwd_{unique_key}")
                
                if password == "8848":
                    st.success("Přístup povolen.")
                    
                    # Generování Excelu do paměti
                    output = BytesIO()
                    # Vybereme jen užitečné sloupce
                    df_to_export = lidi[["jméno", "poznámka", "doprava", "ubytování"]].copy()
                    
                    # Uložení do Excelu (bez indexu)
                    df_to_export.to_excel(output, index=False, sheet_name='Soupiska')
                    excel_data = output.getvalue()
                    
                    file_name_safe = re.sub(r'[^\w\s-]', '', akce['název']).strip().replace(' ', '_')
                    
                    # Tlačítko ke stažení
                    st.download_button(
                        label="📥 Stáhnout Excel",
                        data=excel_data,
                        file_name=f"{file_name_safe}_soupiska.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_xls_{unique_key}"
                    )
                elif password:
                    st.error("❌ Špatné heslo.")
    
    # --- HLAVIČKA S LOGEM ---
col_dummy, col_title, col_help = st.columns([1, 10, 1], vertical_alignment="center")

with col_title:
    # Cesta k tvému logu
    logo_path = "logo_rbk.jpg" 
    
    # Zkusíme načíst lokální logo, jinak placeholder
    logo_b64 = utils.get_base64_image(logo_path)
    
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
    with st.popover("❔", help="Nápověda a Legenda"):
        # --- 1. LEGENDA BAREV ---
        st.markdown("<h3 style='margin-bottom:10px;'>🎨 Legenda barev</h3>", unsafe_allow_html=True)
        st.markdown("""
        <div style="display: grid; gap: 10px; font-size: 0.9rem;">
            <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; border-radius: 6px; background: linear-gradient(90deg, #EF4444, #F59E0B, #10B981); margin-right: 10px;"></span><b>MČR / Mistrovství</b></div>
            <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; border-radius: 6px; background: #DC2626; margin-right: 10px;"></span><b>Závod ŽA</b> (Licence A)</div>
            <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; border-radius: 6px; background: #EA580C; margin-right: 10px;"></span><b>Závod ŽB</b> (Licence B)</div>
            <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; border-radius: 6px; background: #D97706; margin-right: 10px;"></span><b>Soustředění</b> (Přednostní)</div>
            <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; border-radius: 6px; background: #2563EB; margin-right: 10px;"></span><b>Oblastní žebříček</b></div>
            <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; border-radius: 6px; background: #4B5563; margin-right: 10px;"></span><b>Zimní liga</b></div> <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; border-radius: 6px; background: #0D9488; margin-right: 10px;"></span><b>Ostatní závody</b></div>
            <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; border-radius: 6px; background: #9333EA; margin-right: 10px;"></span><b>Štafety</b></div>
            <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; border-radius: 6px; background: #16A34A; margin-right: 10px;"></span><b>Trénink</b></div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # --- 2. NÁVOD ---
        st.markdown("### 📖 Rychlý návod")
        st.markdown("""
        1.  👆 **Klikni na akci** v kalendáři pro zobrazení detailů.
        2.  ✍️ **Zapiš se:** Vyber své jméno, zaškrtni, jestli chceš **odvoz 🚗** nebo **společné spaní 🛏️**, a dej *Zapsat se*.
        3.  ⚠️ **Závody:** Tato tabulka slouží jen pro **dopravu a ubytování**! Na samotný závod se musíš vždy přihlásit přes **ORIS**.
        4.  🗑️ **Odhlášení:** Pokud jsi přihlášený a termín ještě nevypršel, můžeš se smazat kliknutím na ikonu koše v seznamu.
        """)

# --- 2. PŘIPOJENÍ A NAČTENÍ DAT ---
conn = data_manager.get_connection()
df_akce = data_manager.load_akce()
df_prihlasky = data_manager.load_prihlasky()
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
        
        # Logika barev (stejná jako předtím)
        if days_left == 0:
            bg_color, border_color, text_color, icon, time_msg = "#FEF2F2", "#EF4444", "#B91C1C", "🚨", "DNES!"
        elif days_left <= 3:
            bg_color, border_color, text_color, icon, time_msg = "#FFFBEB", "#F59E0B", "#B45309", "⚠️", f"Za {days_left} dny"
        else:
            bg_color, border_color, text_color, icon, time_msg = "#ECFDF5", "#10B981", "#047857", "📅", row['deadline'].strftime('%d.%m.')

        # Unikátní klíč pro dashboard (aby se nehádal s kalendářem)
        unique_key_dash = f"dash_{row['id']}"

        with cols_d[i]:
            # Použijeme stylable_container k nastylování tlačítka popoveru
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
                    white-space: pre-wrap !important; /* Dovolí odřádkování */
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
                # Text tlačítka složíme z ikony, názvu a deadlinu
                label_text = f"{icon}\n{row['název']}\n{time_msg}"
                
                # Samotný popover
                with st.popover(label_text, use_container_width=True):
                    vykreslit_detail_akce(row, unique_key_dash)

    st.markdown("<div style='margin-bottom: 25px'></div>", unsafe_allow_html=True)
    
    # --- NAVIGACE MĚSÍCŮ ---
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
                
                akce_id_str = str(akce['id']) if 'id' in df_akce.columns else ""
                unique_key = f"{akce_id_str}_{aktualni_den.strftime('%Y%m%d')}"

                # 1. Definice typu události a druhu
                typ_udalosti = str(akce['typ']).lower().strip() if 'typ' in df_akce.columns and pd.notna(akce['typ']) else ""
                druh_akce = str(akce['druh']).lower().strip() if 'druh' in df_akce.columns and pd.notna(akce['druh']) else "ostatní"
                
                # 2. Pomocné proměnné (TOTO MUSÍ BÝT PŘED PODMÍNKAMI!)
                zavodni_slova = ["závod", "mčr", "žebříček", "liga", "mistrovství", "štafety", "ža", "žb"]
                je_zavod_obecne = any(s in typ_udalosti for s in zavodni_slova)

                # 3. LOGIKA BAREV
                style_key = "default"

                if "mčr" in typ_udalosti or "mistrovství" in typ_udalosti:
                    style_key = "mcr"
                elif "ža" in typ_udalosti or "žebříček a" in typ_udalosti:
                    style_key = "za"
                elif "žb" in typ_udalosti or "žebříček b" in typ_udalosti:
                    style_key = "zb"
                elif "soustředění" in typ_udalosti:
                    style_key = "soustredeni"
                elif "oblastní" in typ_udalosti or "žebříček" in typ_udalosti:
                    style_key = "oblastni"
                elif "zimní liga" in typ_udalosti or "bzl" in typ_udalosti:
                    style_key = "zimni_liga"
                elif "štafety" in typ_udalosti:
                    style_key = "stafety"
                elif "trénink" in typ_udalosti:
                    style_key = "trenink"
                elif je_zavod_obecne:
                    style_key = "zavod"
                    
                # 4. Načtení stylu z konfigurace
                vybrany_styl = styles.BARVY_AKCI.get(style_key, styles.BARVY_AKCI["default"])

                # 5. Ikony a Text tlačítka
                ikony_mapa = { "les": "🌲", "krátká trať": "🌲", "klasická trať": "🌲", "sprint": "🏙️", "nočák": "🌗" }
                emoji_druh = ikony_mapa.get(druh_akce, "🏃")
                
                nazev_full = akce['název']
                display_text = nazev_full.split('-')[0].strip() if '-' in nazev_full else nazev_full
                final_text = f"{emoji_druh} {display_text}".strip()
                
                if je_po_deadlinu:
                    final_text = "🔒 " + final_text

                # 6. Vykreslení tlačítka s Popoverem
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
                        vykreslit_detail_akce(akce, unique_key)
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
        # Nová syntaxe: width="stretch" místo use_container_width=True
        l1.image("logo1.jpg", width="stretch") 
        l2.image("logo2.jpg", width="stretch")
        
    with col_center:
        st.markdown("<div style='text-align: center; color: #9CA3AF; font-size: 0.8em; font-family: sans-serif;'><b>Členská sekce RBK</b> • Designed by Broschman • v1.2.20.5<br>&copy; 2026 All rights reserved</div>", unsafe_allow_html=True)
        
    with col_right:
        r1, r2 = st.columns(2)
        # Nová syntaxe: width="stretch" místo use_container_width=True
        r1.image("logo3.jpg", width="stretch")
        r2.image("logo4.jpg", width="stretch")

st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)
