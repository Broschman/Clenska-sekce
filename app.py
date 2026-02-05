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

def vykreslit_detail_akce(akce, unique_key):
    """
    Vykreslí kompletní obsah popoveru.
    """
    # --- 1. PŘÍPRAVA DAT (SOUŘADNICE) ---
    mapa_raw = str(akce['mapa']).strip() if 'mapa' in df_akce.columns and pd.notna(akce['mapa']) else ""
    
    # Použití nové utils funkce pro parsování
    body_k_vykresleni = utils.parse_map_coordinates(mapa_raw, akce['název']) 
    main_lat, main_lon = None, None
    
    if body_k_vykresleni:
        main_lat, main_lon, _ = body_k_vykresleni[0]

    # Fallback: Zkusíme zjistit polohu podle názvu místa
    if (not main_lat or not main_lon) and akce['místo']:
        found_lat, found_lon = utils.get_coords_from_place(str(akce['místo']))
        if found_lat and found_lon:
            main_lat, main_lon = found_lat, found_lon

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

    if akce_id_str:
        # Živé načítání přihlášek
        df_full = data_manager.load_prihlasky()
        lidi = df_full[df_full['id_akce'] == akce_id_str].copy()
        lidi = lidi.fillna("") 
    else: 
        lidi = pd.DataFrame()

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
            b64 = base64.b64encode(ics_data.encode('utf-8')).decode()
            # Volání styles pro tlačítko
            st.markdown(styles.get_ics_button_html(b64, akce["název"]), unsafe_allow_html=True)
                
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
        
        # 2. Deadline (Barevný box)
        if je_po_deadlinu:
            st.error(f"⛔ **DEADLINE BYL:** {deadline_str}")
        elif je_dnes_deadline:
            st.warning(f"⚠️ **DNES JE DEADLINE!** ({deadline_str})")
        else:
            st.success(f"📅 **Deadline:** {deadline_str}")

        # --- NOVINKA: CHYTRÝ DEADLINE UBYTOVÁNÍ 🛏️ ---
        raw_ubyt = akce.get('deadline_ubytovani')
        
        # dayfirst=True -> Říká pandasu, že formát je DD.MM.YYYY (český)
        # errors='coerce' -> Když tam někdo napíše blbost (text), hodí to NaT (prázdno) a nespadne to
        deadline_ubyt = pd.to_datetime(raw_ubyt, dayfirst=True, errors='coerce') 
        
        if pd.notnull(deadline_ubyt) and deadline_ubyt != akce['deadline']:
            ubyt_str = deadline_ubyt.strftime('%d.%m.')
            
            if deadline_ubyt.hour != 0 or deadline_ubyt.minute != 0:
                ubyt_str += deadline_ubyt.strftime(' %H:%M')
            
            st.markdown(f"""
                <div style="margin-top: -10px; margin-bottom: 15px; padding-left: 5px; color: #4B5563; font-size: 0.9rem;">
                    🛏️ <b>Deadline ubytování:</b> {ubyt_str}
                </div>
            """, unsafe_allow_html=True)
            
        # 3. 🌦️ POČASÍ + 🌑 ZÁPAD SLUNCE
        if main_lat and main_lon:
            forecast = utils.get_forecast(main_lat, main_lon, akce['datum'])
            
            if forecast:
                w_icon, w_text = utils.get_weather_emoji(forecast['code'])
                temp = round(forecast['temp_max'])
                rain = forecast['precip']
                wind = forecast['wind']
                
                # Zjištění času západu slunce
                sunset_raw = forecast.get('sunset')
                html_zapad = "" 
                
                if "nočák" in druh_akce and sunset_raw:
                    try:
                        sunset_time = sunset_raw.split('T')[1]
                        html_zapad = f"""<div style="text-align: right; border-left: 1px solid #d1d5db; padding-left: 15px; margin-left: 15px;"><div style="font-size: 1.5rem; line-height: 1;">🌑</div><div style="font-size: 0.7rem; font-weight: bold; color: #1f2937; text-transform: uppercase;">Západ</div><div style="font-size: 0.9rem; color: #4b5563;">{sunset_time}</div></div>"""
                    except: pass

                # Volání styles pro počasí
                st.markdown(
                    styles.get_weather_card_html(w_icon, w_text, temp, rain, wind, html_zapad), 
                    unsafe_allow_html=True
                )
                
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
                with st.form(key=form_key, clear_on_submit=False): # POZOR: clear_on_submit dej na False, jinak se jméno smaže než se otevře dialog!
                    if kategorie_txt and kategorie_txt.lower() != "všichni": 
                        st.warning(f"Doporučení: **{kategorie_txt}**")
                    
                    # Inputy
                    vybrane_jmeno = st.selectbox("Jméno", options=seznam_jmen, index=None, placeholder="Vyber ze seznamu...")
                    nove_jmeno = st.text_input("Nebo nové jméno")
                    poznamka_input = st.text_input("Poznámka")
                    
                    c_check1, c_check2 = st.columns(2)
                    doprava_input = c_check1.checkbox("🚗 Sháním odvoz")
                    
                    # --- LOGIKA UBYTOVÁNÍ START ---
                    ubytovani_input = False
                    
                    # Ubytování řešíme jen pokud to není trénink
                    if "trénink" not in typ_udalosti:
                        # ZDE JSME PŘIDALI dayfirst=True
                        deadline_ubyt = pd.to_datetime(akce.get('deadline_ubytovani'), dayfirst=True, errors='coerce')
                        
                        zobrazit_ubyt = True

                        # Pokud deadline existuje A už vypršel -> skryjeme
                        if pd.notnull(deadline_ubyt) and datetime.now() > deadline_ubyt:
                            zobrazit_ubyt = False

                        if zobrazit_ubyt:
                            ubytovani_input = c_check2.checkbox("🛏️ Společné ubytko")
                        elif pd.notnull(deadline_ubyt):
                            # Volitelné: Informace, proč tam ten checkbox není
                            c_check2.caption("🔒 Deadline ubytování uplynul")
                    # --- LOGIKA UBYTOVÁNÍ END ---
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # --- TLAČÍTKA (uvnitř formuláře) ---
                    c_btn_zapis, c_btn_doprava = st.columns([1, 1], gap="small")
                    
                    with c_btn_zapis:
                        # Hlavní tlačítko pro zápis
                        odeslat_btn = st.form_submit_button("Zapsat se", type="primary", use_container_width=True)
                        
                    with c_btn_doprava:
                        # Tlačítko pro dopravu
                        doprava_btn = st.form_submit_button("🚗 Řešit dopravu", use_container_width=True)
                    
                    # --- LOGIKA ODESLÁNÍ ---
                    # 1. Zjistíme jméno (musí být definováno PŘED podmínkami tlačítek)
                    finalni_jmeno = nove_jmeno.strip() if nove_jmeno else vybrane_jmeno
                    
                    # === VARIANT A: Klikl na ZAPSAT SE ===
                    if odeslat_btn:
                        if finalni_jmeno:
                            try:
                                # 1. Kontrola duplicity
                                full_df = data_manager.load_prihlasky()
                                duplicita = not full_df[(full_df['id_akce'] == akce_id_str) & (full_df['jméno'] == finalni_jmeno)].empty
                                
                                if duplicita:
                                    st.warning(f"⚠️ {finalni_jmeno}, na této akci už jsi!")
                                else:
                                    hodnota_dopravy = "Ano 🚗" if doprava_input else ""
                                    hodnota_ubytovani = "Ano 🛏️" if ubytovani_input else ""
                                    cas_zapisu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    
                                    # 2. Příprava řádku s přihláškou
                                    novy_zaznam = pd.DataFrame([{
                                        "id_akce": akce_id_str, 
                                        "název": akce['název'], 
                                        "jméno": finalni_jmeno, 
                                        "poznámka": poznamka_input, 
                                        "doprava": hodnota_dopravy, 
                                        "ubytování": hodnota_ubytovani, 
                                        "čas zápisu": cas_zapisu
                                    }])
                                    
                                    # 3. Zápis přihlášky do Google Sheets
                                    aktualni_data = data_manager.load_prihlasky()
                                    update_data = pd.concat([aktualni_data, novy_zaznam], ignore_index=True)
                                    conn.update(worksheet="prihlasky", data=update_data)
                                    
                                    # 4. ULOŽENÍ NOVÉHO JMÉNA (pokud je nové)
                                    if finalni_jmeno not in seznam_jmen:
                                        try:
                                            jmena_df = conn.read(worksheet="jmena")
                                            nove_jmeno_df = pd.DataFrame([{"jméno": finalni_jmeno}])
                                            conn.update(worksheet="jmena", data=pd.concat([jmena_df, nove_jmeno_df], ignore_index=True))
                                        except Exception as e:
                                            print(f"Chyba jména: {e}")

                                    # 5. Animace úspěchu
                                    with st_lottie_spinner(styles.lottie_success, key=f"anim_{unique_key}"): 
                                        time.sleep(1)
                                    
                                    st.toast(f"✅ {finalni_jmeno} zapsán(a)!")
                                    time.sleep(1)
                                    st.rerun()

                            except Exception as e: 
                                st.error(f"Chyba zápisu: {e}")
                        else: 
                            st.warning("Musíš vyplnit jméno!")

                    # === VARIANT B: Klikl na DOPRAVU ===
                    elif doprava_btn:
                        if finalni_jmeno:
                            # Zavoláme dialog a předáme mu jméno z formuláře
                            utils.show_doprava_dialog(
                                akce_id=akce_id_str,
                                nazev_akce=akce['název'],
                                datum_akce=akce['datum'].strftime('%d.%m.'),
                                pre_jmeno=finalni_jmeno,
                                in_poznamka=poznamka_input,
                                in_ubytovani=ubytovani_input
                            )
                        else:
                            st.warning("Nejdřív vyber nebo napiš jméno, abych věděl, pro koho tu dopravu řešíme.")

            # --- KONEC FORMULÁŘE ---
            # Tento elif patří k podmínce "if not je_po_deadlinu" o úroveň výš (mimo form)
            elif je_po_deadlinu: 
                st.info("🔒 Tabulka uzavřena. Kontaktuj trenéra. luckapetr@volny.cz (602 214 725)")
                
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

        # Volání styles pro tlačítka map
        st.markdown(styles.get_map_buttons_html(link_mapy_cz, link_google, link_waze), unsafe_allow_html=True)

    elif mapa_raw: st.warning("⚠️ Mapa se nenačetla.")

    # --- SEZNAM (EXPANDERY - ROBOTO MONO) ---
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    st.markdown(f"#### 👥 Zapsaní ({len(lidi)})")

    # 1. IMPORT FONTU + CSS
    # Načteme 'Roboto Mono' - vypadá skoro jako běžné písmo, ale drží šířku.
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;600&display=swap');

        /* Aplikace fontu na hlavičku expanderu */
        div[data-testid="stExpander"] summary, 
        div[data-testid="stExpander"] summary p,
        div[data-testid="stExpander"] summary span {
            font-family: 'Roboto Mono', monospace !important;
            font-size: 0.85rem !important;
            font-weight: 500 !important; /* Střední tučnost, aby to nebylo moc tlusté */
            color: #374151 !important;   /* Tmavě šedá, ne čistě černá */
            letter-spacing: -0.5px;      /* Jemně scvrkneme, ať se tam toho vejde víc */
        }
        
        /* Skrytí hover efektu */
        div[data-testid="stExpander"] summary:hover {
            color: #111827 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- POMOCNÁ FUNKCE PRO ZAROVNÁNÍ ---
    def format_cell(text, width):
        """Ořízne text a doplní TVRDÉ MEZERY (\u00A0)."""
        text = str(text)
        if len(text) > width:
            text = text[:width-2] + ".."
        spaces_needed = width - len(text)
        return text + ("\u00A0" * spaces_needed)

    if not lidi.empty:
        # Definice šířek
        W_INDEX = 4
        W_JMENO = 21
        W_DOPRAVA = 24
        
        for i, (idx, row) in enumerate(lidi.iterrows()):
            
            # --- ZEBRA BARVY ---
            bg_color = "#FFFFFF" if i % 2 == 0 else "#F1F5F9"
            border_color = "#E5E7EB" if i % 2 == 0 else "#CBD5E1"
            
            zebra_style = f"""
            div[data-testid="stExpander"] {{
                background-color: {bg_color} !important;
                border: 1px solid {border_color} !important;
                border-radius: 8px !important;
                margin-bottom: 0px !important;
            }}
            .streamlit-expanderHeader {{
                background-color: {bg_color} !important;
            }}
            div[data-testid="stExpanderDetails"] {{
                background-color: {bg_color} !important;
            }}
            """
            
            # 1. PŘÍPRAVA DAT
            idx_formatted = format_cell(f"{i+1}.", W_INDEX)
            jmeno_formatted = format_cell(row['jméno'], W_JMENO)
            
            # Doprava
            dopr_raw = str(row.get('doprava', ''))
            if not dopr_raw or dopr_raw == "nan": d_text = "⚪ Bez dopravy"
            elif "Řidič" in dopr_raw: d_text = "🚙 Řidič"
            elif "Spolujízda" in dopr_raw or "Jedu s" in dopr_raw:
                clean = dopr_raw.replace("Spolujízda:", "").replace("Spolujízda", "").replace("Jedu s:", "").strip()
                d_text = f"➡️ {clean}"
            elif "Chci" in dopr_raw or "Hledám" in dopr_raw: d_text = "🙋‍♂️ Hledá odvoz"
            else: d_text = "❓ Nevyřešeno"
            
            dopr_formatted = format_cell(d_text, W_DOPRAVA)
            
            # Ikony + Poznámka
            ubyt_raw = str(row.get('ubytování', ''))
            ubyt_icon = "🛏️" if ubyt_raw and "Ano" in ubyt_raw else ""
            poznamka = row.get('poznámka', '')
            extra_info = f" {ubyt_icon}"
            if poznamka: extra_info += f"  📝 {poznamka}"

            header_text = f"{idx_formatted}{jmeno_formatted}{dopr_formatted}{extra_info}"

            # 2. VYKRESLENÍ
            with stylable_container(key=f"exp_robo_{unique_key}_{i}", css_styles=zebra_style):
                st.markdown(f"<div style='margin-bottom: 8px;'>", unsafe_allow_html=True)
                
                with st.expander(header_text, expanded=False):
                    
                    st.caption(f"Celé jméno: {row['jméno']}")
                    c_btn_doprava, c_btn_delete = st.columns([3, 1], gap="medium")
                    
                    with c_btn_doprava:
                        btn_type = "primary" if "Řidič" in dopr_raw else "secondary"
                        if st.button("🔧 Nastavit / Změnit dopravu", key=f"btn_exp_{unique_key}_{i}", use_container_width=True, type=btn_type):
                            utils.show_doprava_dialog(akce_id_str, akce['název'], akce['datum'].strftime('%d.%m.'), row['jméno'])
                            
                    with c_btn_delete:
                        je_k_smazani = (delete_key_state in st.session_state) and (st.session_state[delete_key_state] == row['jméno'])
                        if je_k_smazani:
                            st.warning("Opravdu?")
                            col_y, col_n = st.columns(2)
                            if col_y.button("✅", key=f"yes_exp_{unique_key}_{i}", use_container_width=True):
                                df_curr = conn.read(worksheet="prihlasky", ttl=0)
                                df_curr['id_akce'] = df_curr['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
                                conn.update(worksheet="prihlasky", data=df_curr[~((df_curr['id_akce'] == akce_id_str) & (df_curr['jméno'] == row['jméno']))])
                                utils.handle_driver_removal(conn, akce_id_str, row['jméno'])
                                del st.session_state[delete_key_state]
                                st.rerun()
                            if col_n.button("❌", key=f"no_exp_{unique_key}_{i}", use_container_width=True):
                                del st.session_state[delete_key_state]
                                st.rerun()
                        elif not je_po_deadlinu:
                             if st.button("🗑️ Smazat", key=f"del_exp_{unique_key}_{i}", use_container_width=True):
                                 st.session_state[delete_key_state] = row['jméno']
                                 st.rerun()
                    
                    if poznamka:
                        st.info(f"Poznámka: {poznamka}")

                st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.info("Zatím nikdo. Buď první!")
    
    # === 🆕 VOLÁNÍ IZOLOVANÉ SEKCE Z UTILS ===
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
