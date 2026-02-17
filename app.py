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
                
                # STATICKÝ NADPIS (Už se nemění = žádné blikání/načítání)
                st.markdown("<h4 style='margin-top:0; margin-bottom: 15px;'>✍️ Přihláška</h4>", unsafe_allow_html=True)
                
                if je_zavod_obecne and not je_stafeta:
                    st.markdown("""<div style="background-color: #FEF2F2; border: 1px solid #FCA5A5; color: #B91C1C; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-weight: bold; font-size: 0.9em; display: flex; align-items: center;"><span style="font-size: 1.2em; margin-right: 8px;">⚠️</span>Je nutné se přihlásit i v ORISu!</div>""", unsafe_allow_html=True)

                form_key = f"form_{unique_key}"
                
                # VŠE JE TEĎ UVNITŘ FORMULÁŘE (clear_on_submit=True pro vyčištění po odeslání)
                with st.form(key=form_key, clear_on_submit=True): 
                    if kategorie_txt and kategorie_txt.lower() != "všichni": 
                        st.warning(f"Doporučení: **{kategorie_txt}**")
                    
                    # 1. VÝBĚR LIDÍ
                    vybrana_jmena = st.multiselect(
                        "Vyber členy", 
                        options=seznam_jmen, 
                        placeholder="Klikni a vyber..."
                    )
                    
                    nove_jmeno = st.text_input("Nebo nové jméno (pokud není v seznamu)")
                    poznamka_input = st.text_input("Poznámka (společná)")
                    
                    # Sestavení seznamu
                    lidi_k_zapisu = []
                    if vybrana_jmena: lidi_k_zapisu.extend(vybrana_jmena)
                    if nove_jmeno.strip(): 
                        # .title() pro hezká velká písmena
                        lidi_k_zapisu.append(nove_jmeno.strip().title())

                    st.markdown("<br>", unsafe_allow_html=True)

                    # --- CHECKBOXY (UBYTOVÁNÍ + DOPRAVA) VEDLE SEBE ---
                    c_ubyt, c_dopr = st.columns(2)
                    
                    # A) Ubytování
                    ubytovani_input = False
                    with c_ubyt:
                        if "trénink" not in typ_udalosti:
                            deadline_ubyt = pd.to_datetime(akce.get('deadline_ubytovani'), dayfirst=True, errors='coerce')
                            zobrazit_ubyt = True
                            if pd.notnull(deadline_ubyt) and datetime.now() > deadline_ubyt:
                                zobrazit_ubyt = False

                            if zobrazit_ubyt:
                                ubytovani_input = st.checkbox("🛏️ Společné ubytko")
                            elif pd.notnull(deadline_ubyt):
                                st.caption("🔒 Deadline ubytování uplynul")
                        else:
                            st.write("") # Prázdné místo u tréninků

                    # B) Rychlá doprava (NOVINKA)
                    with c_dopr:
                        # Tento checkbox rovnou hodí člověka na "Waiting list"
                        rychla_doprava_input = st.checkbox("🚗 Chci odvoz")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # --- TLAČÍTKA ---
                    c_btn_zapis, c_btn_doprava = st.columns([1, 1.2], gap="small")
                    
                    with c_btn_zapis:
                        odeslat_btn = st.form_submit_button("Zapsat se", type="primary", use_container_width=True)
                        
                    with c_btn_doprava:
                        doprava_btn = st.form_submit_button("🚗 Řešit dopravu", use_container_width=True)
                    
                    # --- LOGIKA ODESLÁNÍ ---
                    if odeslat_btn:
                        if not lidi_k_zapisu:
                            st.warning("Musíš vybrat alespoň jedno jméno.")
                        else:
                            # -----------------------------------------------------
                            # KROK 1: ULOŽENÍ NOVÝCH JMEN
                            # -----------------------------------------------------
                            try:
                                df_jmena_db = conn.read(worksheet="jmena", ttl=0)
                                col_name = 'jméno' if 'jméno' in df_jmena_db.columns else 'Jméno'
                                existujici = set(df_jmena_db[col_name].astype(str).str.strip().values)
                                
                                nova_jmena_list = []
                                for clovek in lidi_k_zapisu:
                                    cist_jmeno = str(clovek).strip().title()
                                    if cist_jmeno and cist_jmeno not in existujici:
                                        if cist_jmeno not in [x[col_name] for x in nova_jmena_list]:
                                            nova_jmena_list.append({col_name: cist_jmeno})
                                
                                if nova_jmena_list:
                                    df_new = pd.DataFrame(nova_jmena_list)
                                    df_final_jmena = pd.concat([df_jmena_db, df_new], ignore_index=True)
                                    df_final_jmena = df_final_jmena.sort_values(by=col_name)
                                    conn.update(worksheet="jmena", data=df_final_jmena)
                                    st.cache_data.clear()
                                    st.toast(f"💾 Uložena nová jména: {len(nova_jmena_list)}", icon="✅")
                            except Exception as e:
                                print(f"Chyba při ukládání jmen: {e}") 

                            # -----------------------------------------------------
                            # KROK 2: PŘIHLÁŠKA NA AKCI
                            # -----------------------------------------------------
                            try:
                                aktualni_data = data_manager.load_prihlasky()
                                novy_list_prihlasek = []
                                hodnota_ubyt = "Ano 🛏️" if ubytovani_input else ""
                                
                                # Nastavení dopravy podle checkboxu
                                hodnota_dopravy = "Hledám odvoz 🙋‍♂️" if rychla_doprava_input else ""

                                # Ošetření poznámky (tvrdá mezera proti #NAME?)
                                clean_poznamka = str(poznamka_input).strip()
                                if clean_poznamka.startswith(("=", "+", "-", "@")):
                                    clean_poznamka = "\u00A0" + clean_poznamka
                                
                                for clovek in lidi_k_zapisu:
                                    clovek = str(clovek).strip().title()
                                    
                                    if aktualni_data[(aktualni_data['id_akce']==akce_id_str) & (aktualni_data['jméno']==clovek)].empty:
                                        novy_list_prihlasek.append({
                                            "id_akce": akce_id_str, 
                                            "název": akce['název'], 
                                            "jméno": clovek, 
                                            "poznámka": clean_poznamka, 
                                            "doprava": hodnota_dopravy, # ZDE SE Zapíše "Hledám odvoz"
                                            "ubytování": hodnota_ubyt, 
                                            "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        })

                                if novy_list_prihlasek:
                                    final_df = pd.concat([aktualni_data, pd.DataFrame(novy_list_prihlasek)], ignore_index=True)
                                    conn.update(worksheet="prihlasky", data=final_df)
                                    
                                    with st_lottie_spinner(styles.lottie_success, key=f"anim_{unique_key}"): 
                                        time.sleep(1)
                                    st.toast(f"✅ Zapsáno {len(novy_list_prihlasek)} lidí.")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.warning("Všichni vybraní už jsou zapsaní.")
                            except Exception as e: 
                                st.error(f"Chyba při zápisu: {e}")

                    elif doprava_btn:
                        if lidi_k_zapisu:
                            # 1. Uložení jmen
                            try:
                                df_jmena_db = conn.read(worksheet="jmena", ttl=0)
                                col_name = 'jméno' if 'jméno' in df_jmena_db.columns else 'Jméno'
                                existujici = set(df_jmena_db[col_name].astype(str).str.strip().values)
                                nova_jmena_list = []
                                
                                for clovek in lidi_k_zapisu:
                                    cist_jmeno = str(clovek).strip().title()
                                    if cist_jmeno and cist_jmeno not in existujici:
                                        if cist_jmeno not in [x[col_name] for x in nova_jmena_list]:
                                            nova_jmena_list.append({col_name: cist_jmeno})
                                
                                if nova_jmena_list:
                                    df_new = pd.DataFrame(nova_jmena_list)
                                    df_final_jmena = pd.concat([df_jmena_db, df_new], ignore_index=True)
                                    df_final_jmena = df_final_jmena.sort_values(by=col_name)
                                    conn.update(worksheet="jmena", data=df_final_jmena)
                                    st.cache_data.clear()
                                    st.toast(f"💾 Uložena nová jména", icon="✅")
                            except Exception as e:
                                print(f"Chyba jmena: {e}")

                            # 2. Dialog
                            clean_poznamka_dialog = str(poznamka_input).strip()
                            if clean_poznamka_dialog.startswith(("=", "+", "-", "@")):
                                clean_poznamka_dialog = "\u00A0" + clean_poznamka_dialog
                                
                            lidi_clean = [str(x).strip().title() for x in lidi_k_zapisu]
                            
                            utils.show_doprava_dialog(
                                akce_id=akce_id_str,
                                nazev_akce=akce['název'],
                                datum_akce=akce['datum'].strftime('%d.%m.'),
                                input_jmena=lidi_clean,
                                in_poznamka=clean_poznamka_dialog,
                                in_ubytovani=ubytovani_input
                            )
                        else:
                            st.warning("Nejdřív vyber lidi.")
                            
            elif je_po_deadlinu: 
                st.info("🔒 Tabulka uzavřena. Kontaktuj trenéra.")
                
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

    # --- SEZNAM (FINAL FIX - ROBOTO MONO + FUNKČNÍ IKONA) ---
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    st.markdown(f"#### 👥 Zapsaní ({len(lidi)})")

    # --- NOVINKA: DASHBOARD DOPRAVY (KARTY AUT) ---
    if not lidi.empty:
        # 1. PŘÍPRAVA DAT
        ridici_data = [] 
        cekaliste = []    
        
        # A) Najdeme řidiče a čekající
        for _, r in lidi.iterrows():
            dopr = str(r.get('doprava', ''))
            
            if "Řidič" in dopr:
                kapacita = 4 
                import re
                match_kap = re.search(r'(\d+)\s*míst', dopr)
                if match_kap:
                    kapacita = int(match_kap.group(1))
                
                info_text = ""
                if "," in dopr:
                    info_text = dopr.split(",", 1)[1].strip().replace(")", "")
                
                ridici_data.append({
                    "jmeno": r['jméno'],
                    "kapacita": kapacita,
                    "info": info_text,
                    "pasazeri": []
                })
            elif "Hledám" in dopr or "Chci" in dopr:
                cekaliste.append(r['jméno'])

        # B) Přiřadíme pasažéry k řidičům
        for _, r in lidi.iterrows():
            dopr = str(r.get('doprava', ''))
            if "Řidič" in dopr or "Hledám" in dopr or "Chci" in dopr or not dopr or dopr == "nan":
                continue
            
            for ridic in ridici_data:
                if ridic['jmeno'] in dopr:
                    ridic['pasazeri'].append(r['jméno'])
                    break

        # 2. VYKRESLENÍ DASHBOARDU
        
        # A) ČEKACÍ LISTINA (Varování)
        if cekaliste:
            st.error(f"🚨 **Hledají odvoz ({len(cekaliste)}):** {', '.join(cekaliste)}")
        
        # B) KARTY AUT (HTML STYL)
        if ridici_data:
            cols = st.columns(2)
            
            for i, auto in enumerate(ridici_data):
                # Výpočty stavu
                obsazeno = len(auto['pasazeri'])
                celkem_mist = auto['kapacita']
                
                if celkem_mist > 0:
                    percent = min((obsazeno / celkem_mist) * 100, 100)
                else:
                    percent = 0
                
                # Určení barev
                if obsazeno > celkem_mist:
                    status_color = "#EF4444"
                    bg_color = "#FEF2F2"
                    border_color = "#FECACA"
                    status_icon = "🚨"
                    status_text = "Přeplněno!"
                    detail_text = f"{obsazeno} z {celkem_mist}"
                elif obsazeno == celkem_mist:
                    status_color = "#F59E0B"
                    bg_color = "#FFFBEB"
                    border_color = "#FDE68A"
                    status_icon = "👌"
                    status_text = "Plno"
                    detail_text = f"{obsazeno} z {celkem_mist}"
                else:
                    volno = celkem_mist - obsazeno
                    status_color = "#10B981"
                    bg_color = "#ECFDF5"
                    border_color = "#A7F3D0"
                    status_icon = "✅"
                    status_text = f"Volno: {volno}"
                    detail_text = f"{obsazeno} z {celkem_mist}"

                info_label = auto['info'] if auto['info'] else "Řidič"
                
                # HTML ŠABLONA (zarovnaná doleva)
                html_card = f"""
<div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 12px; padding: 10px 15px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; gap: 10px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
<div style="display: flex; gap: 10px; align-items: center; min-width: 110px;">
<div style="text-align: left;">
<div style="font-size: 0.7rem; color: #6B7280; font-weight: 600; text-transform: uppercase;">{info_label}</div>
<div style="font-size: 0.95rem; font-weight: 800; color: #1F2937; white-space: nowrap;">{auto['jmeno']}</div>
</div>
</div>
<div style="width: 1px; height: 30px; background-color: {border_color};"></div>
<div style="text-align: center; min-width: 70px;">
<div style="font-size: 0.8rem; font-weight: 700; color: {status_color}; white-space: nowrap;">{status_icon} {status_text}</div>
<div style="font-size: 0.65rem; color: #6B7280;">{detail_text}</div>
</div>
<div style="flex-grow: 1; max-width: 120px;">
<div style="background-color: rgba(255,255,255,0.6); border-radius: 10px; height: 8px; width: 100%; overflow: hidden; border: 1px solid {border_color};">
<div style="background-color: {status_color}; width: {percent}%; height: 100%; border-radius: 10px; transition: width 0.5s ease-in-out;"></div>
</div>
</div>
</div>
"""
                
                # Vykreslení do správného sloupce
                col_index = i % 2
                with cols[col_index]:
                    st.markdown(html_card, unsafe_allow_html=True)
                    
                    if auto['pasazeri']:
                        with st.expander(f"Seznam ({len(auto['pasazeri'])})"):
                            for p in auto['pasazeri']:
                                st.caption(f"• {p}")
                    else:
                        st.markdown("<div style='margin-bottom: 10px'></div>", unsafe_allow_html=True)
    # --- KONEC DASHBOARDU ---
        
    # 1. IMPORT FONTU + CSS
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;600&display=swap');

        /* Font pouze pro text v hlavičce (necháváme ikony napokoji) */
        div[data-testid="stExpander"] summary p {
            font-family: 'Roboto Mono', monospace !important;
            font-size: 0.85rem !important;
            font-weight: 500 !important;
            color: #374151 !important;
            letter-spacing: -0.5px;
            margin-bottom: 0 !important;
        }
        
        div[data-testid="stExpander"] summary p span {
             font-family: 'Roboto Mono', monospace !important;
        }

        div[data-testid="stExpander"] summary:hover p {
            color: #111827 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- POMOCNÁ FUNKCE ---
    def format_cell(text, width):
        """Ořízne text a doplní TVRDÉ MEZERY (\u00A0)."""
        text = str(text)
        if len(text) > width:
            text = text[:width-2] + ".."
        spaces_needed = width - len(text)
        return text + ("\u00A0" * spaces_needed)

    if not lidi.empty:
        # Definice šířek sloupců
        W_INDEX = 4
        W_JMENO = 20
        W_DOPRAVA = 22
        
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
            
            # --- CHYTRÉ ZPRACOVÁNÍ DOPRAVY ---
            dopr_raw = str(row.get('doprava', ''))
            
            if not dopr_raw or dopr_raw == "nan": 
                d_text = "⚪ Bez dopravy"
            
            elif "Řidič" in dopr_raw: 
                d_text = "🚙 Řidič"
            
            elif "Spolujízda" in dopr_raw or "Jedu s" in dopr_raw:
                clean = dopr_raw.replace("Spolujízda:", "").replace("Spolujízda", "").replace("Jedu s:", "").strip()
                d_text = f"➡️ {clean}"
            
            elif "Chci" in dopr_raw or "Hledám" in dopr_raw:
                # Zde je ta změna: Pokud je tam závorka s místem, vytáhneme ji!
                if "(" in dopr_raw and ")" in dopr_raw:
                    # Vytáhneme text mezi závorkami
                    try:
                        start = dopr_raw.find("(") + 1
                        end = dopr_raw.find(")")
                        misto = dopr_raw[start:end].strip()
                        # Pokud je místo krátké, zobrazíme ho celé, jinak zkrátíme
                        if len(misto) > 12: misto = misto[:10] + "."
                        d_text = f"🙋‍♂️ {misto}"
                    except:
                        d_text = "🙋‍♂️ Hledá odvoz"
                else:
                    d_text = "🙋‍♂️ Hledá odvoz"
            
            else: 
                d_text = "❓ Nevyřešeno"
            
            dopr_formatted = format_cell(d_text, W_DOPRAVA)
            
            # Ikony + Poznámka
            ubyt_raw = str(row.get('ubytování', ''))
            ubyt_icon = "🛏️" if ubyt_raw and "Ano" in ubyt_raw else ""
            poznamka = row.get('poznámka', '')
            extra_info = f" {ubyt_icon}"
            if poznamka: extra_info += f"  📝 {poznamka}"

            header_text = f"{idx_formatted}{jmeno_formatted}{dopr_formatted}{extra_info}"

            # 2. VYKRESLENÍ
            with stylable_container(key=f"exp_place_{unique_key}_{i}", css_styles=zebra_style):
                st.markdown(f"<div style='margin-bottom: 8px;'>", unsafe_allow_html=True)
                
                with st.expander(header_text, expanded=False):
                    
                    # Tady zobrazíme detailní info pro řidiče, pokud někdo hledá odvoz
                    if "Hledám" in dopr_raw or "Chci" in dopr_raw:
                        # Pokud je tam specifikované místo, zvýrazníme ho modře
                        if "(" in dopr_raw:
                            st.info(f"📍 **Poptávka:** {dopr_raw}")
                        else:
                            st.caption(f"Stav dopravy: {dopr_raw}")
                    else:
                        st.caption(f"Celé jméno: {row['jméno']}")

                    # Upravili jsme poměry sloupců, aby se tam vešla 3 tlačítka
                    c_btn_doprava, c_btn_edit, c_btn_delete = st.columns([2.2, 1, 0.8], gap="small")
                    
                    with c_btn_doprava:
                        btn_type = "primary" if "Řidič" in dopr_raw else "secondary"
                        if st.button("🔧 Doprava", key=f"btn_dopr_{unique_key}_{i}", use_container_width=True, type=btn_type, help="Nastavit nebo změnit dopravu"):
                            utils.show_doprava_dialog(
                                akce_id_str, 
                                akce['název'], 
                                akce['datum'].strftime('%d.%m.'), 
                                row['jméno']
                            )
                            
                    with c_btn_edit:
                        # TLAČÍTKO PRO ÚPRAVU
                        if st.button("✏️ Upravit", key=f"btn_edit_{unique_key}_{i}", use_container_width=True, help="Změnit poznámku nebo ubytování"):
                            utils.show_edit_dialog(
                                akce_id=akce_id_str,
                                nazev_akce=akce['název'],
                                jmeno=row['jméno'],
                                aktualni_poznamka=row['poznámka'],
                                aktualni_ubytovani=row['ubytování'],
                                # TENTO ŘÁDEK TAM CHYBĚL:
                                deadline_ubyt_raw=akce.get('deadline_ubytovani') 
                            )
                            
                    with c_btn_delete:
                        # Zjistíme, jestli je zrovna tento řádek ve stavu "Potvrzení smazání"
                        je_k_smazani = (delete_key_state in st.session_state) and (st.session_state[delete_key_state] == row['jméno'])

                        if je_k_smazani:
                            # --- STAV: POTVRZENÍ (Opravdu smazat?) ---
                            # Malý text "Opravdu?" místo velkého warningu, aby se to vešlo
                            st.markdown("<div style='text-align: center; color: #EF4444; font-weight: bold; font-size: 0.8rem; margin-bottom: 2px;'>Opravdu?</div>", unsafe_allow_html=True)
                            
                            col_y, col_n = st.columns(2, gap="small")
                            
                            # Tlačítko ANO
                            with col_y:
                                if st.button("✅", key=f"yes_exp_{unique_key}_{i}", use_container_width=True, type="primary"):
                                    try:
                                        # 1. Načteme aktuální data (čerstvá)
                                        df_curr = conn.read(worksheet="prihlasky", ttl=0)
                                        
                                        # 2. Fix formátu ID akce (aby sedělo str vs float)
                                        if 'id_akce' in df_curr.columns:
                                            df_curr['id_akce'] = df_curr['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
                                        
                                        # 3. Vyfiltrujeme řádek, který chceme smazat
                                        # (Necháme všechno, co NENÍ (tato akce A toto jméno))
                                        df_to_keep = df_curr[~((df_curr['id_akce'] == akce_id_str) & (df_curr['jméno'] == row['jméno']))]
                                        
                                        # 4. Uložíme zpět do Google Sheets
                                        conn.update(worksheet="prihlasky", data=df_to_keep)
                                        
                                        # 5. Pokud to byl řidič, musíme vyřešit jeho pasažéry (aby tam nezůstali viset)
                                        utils.handle_driver_removal(conn, akce_id_str, row['jméno'])
                                        
                                        # 6. Vyčistíme stav a obnovíme stránku
                                        del st.session_state[delete_key_state]
                                        st.toast("✅ Odhlášeno.")
                                        time.sleep(0.5)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Chyba při mazání: {e}")

                            # Tlačítko NE (Zrušit)
                            with col_n:
                                if st.button("❌", key=f"no_exp_{unique_key}_{i}", use_container_width=True):
                                    del st.session_state[delete_key_state]
                                    st.rerun()

                        elif not je_po_deadlinu:
                            # --- STAV: IKONA KOŠE (Standardní zobrazení) ---
                            # Zobrazí se jen pokud ještě není po deadlinu
                            if st.button("🗑️", key=f"del_exp_{unique_key}_{i}", use_container_width=True, help="Odhlásit se"):
                                st.session_state[delete_key_state] = row['jméno']
                                st.rerun()
                    
                    if poznamka:
                        st.text(f"Poznámka: {poznamka}")

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
                    vykreslit_detail_akce(akce, unique_key)

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
