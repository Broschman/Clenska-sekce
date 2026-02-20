import streamlit as st
import requests
import re
import time
import base64
import os
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime, date, timedelta
from urllib.parse import urlparse, parse_qs
from io import BytesIO
from streamlit_extras.stylable_container import stylable_container
import streamlit.components.v1 as components
from streamlit_lottie import st_lottie_spinner
import data_manager
import styles

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

# --- POČASÍ A KALENDÁŘ ---

def get_weather_emoji(wmo_code):
    """Převede WMO kód počasí na emoji a text."""
    if wmo_code == 0: return "☀️", "Jasno"
    if wmo_code in [1, 2, 3]: return "⛅", "Polojasno"
    if wmo_code in [45, 48]: return "🌫️", "Mlha"
    if wmo_code in [51, 53, 55]: return "🚿", "Mrholení"
    if wmo_code in [61, 63, 65]: return "🌧️", "Déšť"
    if wmo_code in [71, 73, 75]: return "❄️", "Sníh"
    if wmo_code in [80, 81, 82]: return "💧", "Přeháňky"
    if wmo_code in [95, 96, 99]: return "⚡", "Bouřky"
    return "🌡️", "Neznámé"

@st.cache_data(ttl=3600)
def get_forecast(lat, lon, target_date):
    """Stáhne předpověď z Open-Meteo."""
    try:
        days_diff = (target_date - date.today()).days
        if days_diff < 0 or days_diff > 10:
            return None

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            # PŘIDÁNO "sunset" DO SEZNAMU:
            "daily": ["weathercode", "temperature_2m_max", "precipitation_sum", "windspeed_10m_max", "sunset"],
            "timezone": "auto",
            "start_date": target_date.strftime("%Y-%m-%d"),
            "end_date": target_date.strftime("%Y-%m-%d")
        }
        
        r = requests.get(url, params=params, timeout=2)
        data = r.json()
        
        if "daily" in data:
            d = data["daily"]
            return {
                "code": d["weathercode"][0],
                "temp_max": d["temperature_2m_max"][0],
                "precip": d["precipitation_sum"][0],
                "wind": d["windspeed_10m_max"][0],
                "sunset": d["sunset"][0]  # <--- PŘIDÁNO TOTO (vrací formát "2023-10-25T17:45")
            }
        return None
    except:
        return None

def dms_to_decimal(dms_str):
    """Převede souřadnice ve formátu DMS (stupně, minuty, vteřiny) na decimal."""
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

def parse_map_coordinates(mapa_raw, nazev_akce="Bod"):
    """
    Z textového odkazu (mapy.cz, google maps) nebo souřadnic vytáhne seznam bodů.
    Vrací: list of tuples (lat, lon, nazev)
    """
    body = []
    mapa_raw = str(mapa_raw).strip()
    
    if not mapa_raw:
        return []

    try:
        # 1. Je to URL?
        if "http" in mapa_raw:
            parsed = urlparse(mapa_raw)
            params = parse_qs(parsed.query)
            
            # Mapy.cz 'ud' parametry (vlastní body)
            if 'ud' in params:
                uds = params['ud']
                uts = params.get('ut', [])
                for i, ud_val in enumerate(uds):
                    parts = ud_val.split(',')
                    if len(parts) >= 2:
                        lat, lon = dms_to_decimal(parts[0]), dms_to_decimal(parts[1])
                        if lat and lon:
                            nazev = uts[i] if i < len(uts) else f"Bod {i+1}"
                            body.append((lat, lon, nazev))
            
            # Pokud nejsou 'ud', zkusíme střed mapy (x, y nebo q)
            if not body:
                lat, lon = None, None
                if 'x' in params and 'y' in params:
                    lon, lat = float(params['x'][0]), float(params['y'][0])
                elif 'q' in params:
                    q_parts = params['q'][0].replace(' ', '').split(',')
                    if len(q_parts) >= 2: lat, lon = float(q_parts[0]), float(q_parts[1])
                
                if lat and lon:
                    body.append((lat, lon, nazev_akce))
        
        # 2. Nejsou to jen souřadnice oddělené středníkem?
        else:
            raw_parts = mapa_raw.split(';')
            for part in raw_parts:
                part = part.strip()
                if not part: continue
                # Vyčistit bordel okolo čísel
                clean_text = re.sub(r'[^\d.,]', ' ', part)
                num_parts = clean_text.replace(',', ' ').split()
                num_parts = [p for p in num_parts if len(p) > 0]
                
                if len(num_parts) >= 2:
                    v1, v2 = float(num_parts[0]), float(num_parts[1])
                    # Detekce prohozených souřadnic (ČR je cca 48-51 N, 12-19 E)
                    if 12 <= v1 <= 19 and 48 <= v2 <= 52: lat, lon = v2, v1
                    else: lat, lon = v1, v2
                    body.append((lat, lon, f"Bod {len(body)+1}"))
    except:
        pass
        
    return body

def export_admin_section(lidi, nazev_akce, unique_key):
    """
    Izolovaná sekce pro export s automatickým stahováním po zadání hesla.
    """
    conn = data_manager.get_connection()

    if not lidi.empty:
        st.markdown("---")
        c_export, c_dummy = st.columns([1, 2])
        
        with c_export:
            export_state_key = f"export_open_{unique_key}"
            is_open = st.session_state.get(export_state_key, False)
            btn_label = "🔓 Zavřít export" if is_open else "🔐 Export pro trenéry"
            
            if st.button(btn_label, key=f"btn_toggle_exp_{unique_key}"):
                st.session_state[export_state_key] = not is_open
                st.rerun()

            if st.session_state.get(export_state_key, False):
                with stylable_container(
                    key=f"cont_exp_{unique_key}",
                    css_styles="{background-color: #f9fafb; padding: 15px; border-radius: 8px; border: 1px solid #e5e7eb; margin-top: 10px;}"
                ):
                    # Input s nápovědou (tooltip), že stačí Enter
                    password = st.text_input("Zadej heslo (a stiskni Enter):", type="password", key=f"pwd_{unique_key}", help="Po zadání hesla stiskni Enter a soubor se sám stáhne.")
                    
                    if password == "8848":
                        # 1. Příprava dat
                        output = BytesIO()
                        df_to_export = lidi[["jméno", "poznámka", "doprava", "ubytování"]].copy()
                        df_to_export.to_excel(output, index=False, sheet_name='Soupiska')
                        excel_data = output.getvalue()
                        b64 = base64.b64encode(excel_data).decode()
                        file_name_safe = re.sub(r'[^\w\s-]', '', nazev_akce).strip().replace(' ', '_')
                        full_file_name = f"{file_name_safe}_soupiska.xlsx"

                        st.success("✅ Heslo přijato. Stahování...")

                        # 2. Vytvoření skrytého odkazu (kotvy) pomocí HTML
                        # Tento odkaz není vidět (display:none), ale nese data
                        download_link_html = f"""
                        <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" 
                           download="{full_file_name}" 
                           id="auto_download_link_{unique_key}" 
                           style="display:none;">Download</a>
                        """
                        st.markdown(download_link_html, unsafe_allow_html=True)

                        # 3. JavaScript, který na ten skrytý odkaz klikne
                        # Musíme chvíli počkat (setTimeout), než se HTML vykreslí do DOMu
                        components.html(f"""
                        <script>
                            setTimeout(function() {{
                                const link = window.parent.document.getElementById('auto_download_link_{unique_key}');
                                if (link) {{
                                    link.click();
                                }}
                            }}, 500);
                        </script>
                        """, height=0)

                        # 4. Pro jistotu necháme i manuální tlačítko (kdyby prohlížeč blokoval skripty)
                        st.download_button(
                            label="📥 Stáhnout znovu (pokud se nestáhlo)",
                            data=excel_data,
                            file_name=full_file_name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_xls_{unique_key}"
                        )
                        
                    elif password:
                        st.error("❌ Špatné heslo.")

                # Scroll script (zůstává)
                components.html("""
                <script>
                    const popovers = window.parent.document.querySelectorAll('[data-testid="stPopoverBody"]');
                    if (popovers.length > 0) {
                        const lastPopover = popovers[popovers.length - 1];
                        setTimeout(() => {
                            lastPopover.scrollTo({ top: lastPopover.scrollHeight, behavior: 'smooth' });
                        }, 100);
                    }
                </script>
                """, height=0)

@st.dialog("🚗 Správa dopravy")
def show_doprava_dialog(akce_id, nazev_akce, datum_akce, input_jmena, in_poznamka=None, in_ubytovani=None):
    """
    Chytrý modální dialog.
    - Pokud dostane string (jedno jméno) -> Zobrazí detail jednotlivce.
    - Pokud dostane list (více jmen) -> Zobrazí hromadnou správu (Rodina/Skupina).
    """
    conn = data_manager.get_connection()
    
    # 1. Normalizace vstupu na seznam
    if isinstance(input_jmena, str):
        target_list = [input_jmena]
        is_group = False
    elif isinstance(input_jmena, list):
        target_list = [j for j in input_jmena if j] # Odstraní prázdné
        is_group = (len(target_list) > 1)
    else:
        st.error("Chyba vstupu dialogu.")
        return

    if not target_list:
        st.warning("Nebyla vybrána žádná jména.")
        return

    st.markdown(f"**{nazev_akce}** ({datum_akce})")
    
    # Načtení dat
    df_auta = data_manager.load_auta()
    df_lidi = data_manager.load_prihlasky()
    auta_akce = df_auta[df_auta['id_akce'] == akce_id].copy()
    
    # ---------------------------------------------------------
    # SCÉNÁŘ A: SKUPINA (Rodina, více lidí)
    # ---------------------------------------------------------
    if is_group:
        jmena_str = ", ".join(target_list)
        st.info(f"👥 Řešíš dopravu pro: **{jmena_str}**")
        
        st.markdown("### Jak pojede tato skupina?")
        rezim = st.radio("Možnosti:", [
            "🤷‍♂️ Neřešit (Zrušit dopravu všem)",
            "🙋‍♂️ Hledáme odvoz (Všichni chtějí svézt)",
            "🚙 Máme auto (Jeden řídí, ostatní se vezou)"
        ])
        
        st.markdown("---")
        
        # 1. MÁME AUTO
        if "Máme auto" in rezim:
            c1, c2 = st.columns([2, 1])
            ridic = c1.selectbox("Kdo z nich řídí?", options=target_list)
            kapacita = c2.number_input("Kapacita (celkem)", 1, 9, 5)
            cas = st.text_input("Čas odjezdu", placeholder="např. 17:00")
            misto = st.text_input("Místo odjezdu", placeholder="např. Loděnice")
            
            st.caption(f"💡 {ridic} bude řidič, ostatní ({len(target_list)-1}) budou jeho pasažéři.")
            
            if st.button("💾 Uložit skupinu (Auto)", type="primary", use_container_width=True):
                # A) Smazat stará auta všech zúčastněných
                for osoba in target_list:
                    handle_driver_removal(conn, akce_id, osoba)
                
                # B) Vytvořit nové auto
                df_auta_curr = data_manager.load_auta() # Reload po smazání
                nove_auto = pd.DataFrame([{
                    "id_akce": akce_id, "ridic": ridic, 
                    "kapacita": kapacita, "cas": cas, "misto": misto, "poznamka": "Skupina"
                }])
                conn.update(worksheet="auta", data=pd.concat([df_auta_curr, nove_auto], ignore_index=True))
                
                # C) Update lidí
                df_lidi_curr = data_manager.load_prihlasky()
                # Projdeme lidi a aktualizujeme je (přepisujeme řádky)
                
                # Nejprve odstraníme staré záznamy těchto lidí
                maska_lidi = (df_lidi_curr['id_akce'] == akce_id) & (df_lidi_curr['jméno'].isin(target_list))
                df_clean = df_lidi_curr[~maska_lidi]
                
                new_rows = []
                # Najdeme původní záznamy kvůli poznámkám a ubytku (chceme je zachovat)
                original_rows = df_lidi_curr[maska_lidi].set_index('jméno')
                
                for osoba in target_list:
                    # Zachování původních dat
                    orig = original_rows.loc[osoba] if osoba in original_rows.index else pd.Series()
                    pozn = orig.get('poznámka', in_poznamka or "")
                    ubyt = orig.get('ubytování', ("Ano 🛏️" if in_ubytovani else ""))
                    
                    if osoba == ridic:
                        dopr, auto_id = "Řidič 🚙", ""
                    else:
                        dopr, auto_id = f"Spolujízda: {ridic}", ridic
                        
                    new_rows.append({
                        "id_akce": akce_id, "název": nazev_akce, "jméno": osoba,
                        "poznámka": pozn, "doprava": dopr, "ubytování": ubyt,
                        "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "id_auto": auto_id
                    })
                
                conn.update(worksheet="prihlasky", data=pd.concat([df_clean, pd.DataFrame(new_rows)], ignore_index=True))
                st.rerun()

        # 2. HLEDÁME ODVOZ
        elif "Hledáme" in rezim:
            pref_misto = st.text_input("Odkud chcete jet? (nepovinné)", placeholder="např. Brno-Lesná")
            text_dopravy = f"Hledám odvoz 🙋‍♂️ ({pref_misto})" if pref_misto else "Chci odvoz 🙋‍♂️"
            
            if st.button("💾 Uložit skupinu (Pasažéři)", type="primary", use_container_width=True):
                # Smazat případná auta, kdyby někdo z nich byl dřív řidič
                for osoba in target_list:
                    handle_driver_removal(conn, akce_id, osoba)
                
                df_lidi_curr = data_manager.load_prihlasky()
                maska_lidi = (df_lidi_curr['id_akce'] == akce_id) & (df_lidi_curr['jméno'].isin(target_list))
                df_clean = df_lidi_curr[~maska_lidi]
                original_rows = df_lidi_curr[maska_lidi].set_index('jméno')
                
                new_rows = []
                for osoba in target_list:
                    orig = original_rows.loc[osoba] if osoba in original_rows.index else pd.Series()
                    pozn = orig.get('poznámka', in_poznamka or "")
                    ubyt = orig.get('ubytování', ("Ano 🛏️" if in_ubytovani else ""))
                    
                    new_rows.append({
                        "id_akce": akce_id, "název": nazev_akce, "jméno": osoba,
                        "poznámka": pozn, "doprava": text_dopravy, "ubytování": ubyt,
                        "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "id_auto": ""
                    })
                
                conn.update(worksheet="prihlasky", data=pd.concat([df_clean, pd.DataFrame(new_rows)], ignore_index=True))
                st.rerun()

        # 3. ZRUŠIT / NEŘEŠIT
        else:
            if st.button("🗑️ Vymazat dopravu všem", use_container_width=True):
                for osoba in target_list:
                    handle_driver_removal(conn, akce_id, osoba)
                
                # Prosté smazání sloupce doprava
                df_lidi_curr = data_manager.load_prihlasky()
                maska_lidi = (df_lidi_curr['id_akce'] == akce_id) & (df_lidi_curr['jméno'].isin(target_list))
                df_clean = df_lidi_curr[~maska_lidi]
                original_rows = df_lidi_curr[maska_lidi].set_index('jméno')
                
                new_rows = []
                for osoba in target_list:
                    orig = original_rows.loc[osoba] if osoba in original_rows.index else pd.Series()
                    pozn = orig.get('poznámka', in_poznamka or "")
                    ubyt = orig.get('ubytování', ("Ano 🛏️" if in_ubytovani else ""))
                    
                    new_rows.append({
                        "id_akce": akce_id, "název": nazev_akce, "jméno": osoba,
                        "poznámka": pozn, "doprava": "", "ubytování": ubyt,
                        "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "id_auto": ""
                    })
                conn.update(worksheet="prihlasky", data=pd.concat([df_clean, pd.DataFrame(new_rows)], ignore_index=True))
                st.rerun()

    # ---------------------------------------------------------
    # SCÉNÁŘ B: JEDNOTLIVEC (Původní logika)
    # ---------------------------------------------------------
    else:
        # Tady použijeme tvůj původní kód pro jednotlivce, jen mírně upravený
        # Vytáhneme jméno ze seznamu
        vybrane_jmeno = target_list[0]
        
        # Filtry dat pro jednotlivce
        lidi_akce = df_lidi[df_lidi['id_akce'] == akce_id].copy()
        aktualni_zaznam = lidi_akce[lidi_akce['jméno'] == vybrane_jmeno]
        
        stav_dopravy = "Nevyřešeno"
        id_auto_curr = ""
        db_poznamka = ""
        db_ubytovani = ""
        
        if not aktualni_zaznam.empty:
            dopr_txt = str(aktualni_zaznam.iloc[0]['doprava'])
            id_auto_curr = str(aktualni_zaznam.iloc[0].get('id_auto', ''))
            db_poznamka = aktualni_zaznam.iloc[0]['poznámka']
            db_ubytovani = aktualni_zaznam.iloc[0]['ubytování']
            
            if "Řidič" in dopr_txt: stav_dopravy = "driver"
            elif "Jedu s" in dopr_txt or "Spolujízda" in dopr_txt: stav_dopravy = "passenger"
            elif "Chci" in dopr_txt or "Hledám" in dopr_txt: stav_dopravy = "waiting"
        
        final_poznamka = in_poznamka if in_poznamka is not None else db_poznamka
        final_ubytovani_txt = ("Ano 🛏️" if in_ubytovani else "") if in_ubytovani is not None else db_ubytovani

        st.markdown(f"👤 **{vybrane_jmeno}**")

        role = st.radio("Možnosti dopravy:", 
                 ["Nic (Zrušit dopravu)", "🚙 Nabízím auto (Řidič)", "🙋‍♂️ Hledám odvoz (Pasažér)"],
                 index=1 if stav_dopravy == "driver" else (2 if stav_dopravy in ["passenger", "waiting"] else 0)
        )
        st.markdown("<br>", unsafe_allow_html=True)
        
        obsazenost = {}
        if not lidi_akce.empty and 'id_auto' in lidi_akce.columns:
            obsazenost = lidi_akce[lidi_akce['id_auto'] != ""].groupby('id_auto').size().to_dict()

        # --- JEDNOTLIVEC: ŘIDIČ ---
        if "Nabízím" in role:
            c1, c2 = st.columns(2)
            moje_auto = auta_akce[auta_akce['ridic'] == vybrane_jmeno]
            def_kap, def_cas, def_misto = 5, "", ""
            if not moje_auto.empty:
                def_kap = int(moje_auto.iloc[0]['kapacita'])
                def_cas = str(moje_auto.iloc[0]['cas'])
                def_misto = str(moje_auto.iloc[0]['misto'])

            novy_kap = c1.number_input("Kapacita", 1, 9, def_kap)
            novy_cas = c2.text_input("Čas", value=def_cas, placeholder="např. 17:00")
            novy_misto = st.text_input("Místo", value=def_misto, placeholder="např. Loděnice")
            
            if st.button("💾 Uložit", type="primary", use_container_width=True):
                # Update auta
                df_clean_auta = df_auta[~((df_auta['id_akce'] == akce_id) & (df_auta['ridic'] == vybrane_jmeno))]
                nove_auto_row = pd.DataFrame([{
                    "id_akce": akce_id, "ridic": vybrane_jmeno, 
                    "kapacita": novy_kap, "cas": novy_cas, "misto": novy_misto, "poznamka": ""
                }])
                conn.update(worksheet="auta", data=pd.concat([df_clean_auta, nove_auto_row], ignore_index=True))
                # Update člověka
                df_clean_lidi = df_lidi[~((df_lidi['id_akce'] == akce_id) & (df_lidi['jméno'] == vybrane_jmeno))]
                novy_clovek = pd.DataFrame([{
                    "id_akce": akce_id, "název": nazev_akce, "jméno": vybrane_jmeno,
                    "poznámka": final_poznamka, "doprava": "Řidič 🚙", 
                    "ubytování": final_ubytovani_txt,
                    "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "id_auto": ""
                }])
                conn.update(worksheet="prihlasky", data=pd.concat([df_clean_lidi, novy_clovek], ignore_index=True))
                st.rerun()

        # --- JEDNOTLIVEC: PASAŽÉR ---
        elif "Hledám" in role:
            dostupna_auta_list = []
            for i, (_, row_auto) in enumerate(auta_akce.iterrows()):
                ridic = str(row_auto['ridic'])
                if ridic == vybrane_jmeno: continue 
                kap = int(row_auto['kapacita'])
                obs = obsazenost.get(ridic, 0)
                volno = kap - 1 - obs 
                
                if volno > 0 or ridic == id_auto_curr:
                    cas_txt = str(row_auto['cas']).strip() if pd.notna(row_auto['cas']) else ""
                    misto_txt = str(row_auto['misto']).strip() if pd.notna(row_auto['misto']) else ""
                    info_part = ""
                    if cas_txt: info_part += cas_txt
                    if misto_txt: info_part += f", {misto_txt}" if info_part else misto_txt
                    
                    label = f"🚙 {ridic} ({volno} volných)"
                    if info_part: label += f" - {info_part}"
                    dostupna_auta_list.append({ "label": label, "ridic_id": ridic, "volno": volno })
            
            dostupna_auta_list.sort(key=lambda x: x['volno'], reverse=True)
            options_auta = [item['label'] for item in dostupna_auta_list]
            mapa_aut = {item['label']: item['ridic_id'] for item in dostupna_auta_list}
            
            wait_label = "⏳ Čekací listina"
            options_auta.append(wait_label)
            mapa_aut[wait_label] = ""

            idx_select = 0
            if stav_dopravy == "waiting": idx_select = len(options_auta) - 1
            elif stav_dopravy == "passenger" and id_auto_curr:
                for idx, item_label in enumerate(options_auta):
                    if mapa_aut.get(item_label) == id_auto_curr:
                        idx_select = idx
                        break

            vybrane_label = st.selectbox("Ke komu?", options_auta, index=idx_select)
            target_ridic = mapa_aut[vybrane_label]
            
            preferovane_misto = ""
            if not target_ridic:
                preferovane_misto = st.text_input("Odkud chceš jet?", placeholder="např. Brno")
            
            if st.button("💾 Uložit", type="primary", use_container_width=True):
                if stav_dopravy == "driver":
                    handle_driver_removal(conn, akce_id, vybrane_jmeno)
                    df_lidi = data_manager.load_prihlasky()

                df_clean_lidi = df_lidi[~((df_lidi['id_akce'] == akce_id) & (df_lidi['jméno'] == vybrane_jmeno))]
                dopr_text = f"Spolujízda: {target_ridic}" if target_ridic else (f"Hledám odvoz 🙋‍♂️ ({preferovane_misto})" if preferovane_misto else "Chci odvoz 🙋‍♂️")
                
                novy_clovek = pd.DataFrame([{
                    "id_akce": akce_id, "název": nazev_akce, "jméno": vybrane_jmeno,
                    "poznámka": final_poznamka, "doprava": dopr_text, 
                    "ubytování": final_ubytovani_txt,
                    "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "id_auto": target_ridic
                }])
                conn.update(worksheet="prihlasky", data=pd.concat([df_clean_lidi, novy_clovek], ignore_index=True))
                st.rerun()
        else:
            if st.button("🗑️ Smazat dopravu", use_container_width=True):
                if stav_dopravy == "driver":
                    handle_driver_removal(conn, akce_id, vybrane_jmeno)
                    df_lidi = data_manager.load_prihlasky()
                df_clean_lidi = df_lidi[~((df_lidi['id_akce'] == akce_id) & (df_lidi['jméno'] == vybrane_jmeno))]
                novy_clovek = pd.DataFrame([{
                    "id_akce": akce_id, "název": nazev_akce, "jméno": vybrane_jmeno,
                    "poznámka": final_poznamka, "doprava": "", "ubytování": final_ubytovani_txt,
                    "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "id_auto": ""
                }])
                conn.update(worksheet="prihlasky", data=pd.concat([df_clean_lidi, novy_clovek], ignore_index=True))
                st.rerun()                
def handle_driver_removal(conn, akce_id, ridic_jmeno):
    """
    Komplexní úklid po řidiči:
    1. Smaže auto z tabulky 'auta'.
    2. Najde jeho pasažéry v 'prihlasky' a resetuje jim stav.
    """
    akce_id = str(akce_id) # Pojistka, ať porovnáváme stringy
    
    # --- 1. SMAZÁNÍ AUTA Z TABULKY 'auta' ---
    # Musíme načíst aktuální stav aut, abychom nesmazali něco, co tam přibylo před vteřinou
    df_auta = data_manager.load_auta()
    
    if not df_auta.empty:
        # Najdeme řádek s tímto řidičem na této akci
        maska_auto = (df_auta['id_akce'] == akce_id) & (df_auta['ridic'] == ridic_jmeno)
        
        # Pokud takové auto existuje, smažeme ho (necháme jen ty ostatní - tilda ~ znamená negaci)
        if not df_auta[maska_auto].empty:
            novy_seznam_aut = df_auta[~maska_auto]
            conn.update(worksheet="auta", data=novy_seznam_aut)
            # print(f"Auto řidiče {ridic_jmeno} smazáno.") # Debug

    # --- 2. RESET PASAŽÉRŮ (Změna na "Chci odvoz") ---
    df_lidi = data_manager.load_prihlasky()
    
    maska_pasazeri = (df_lidi['id_akce'] == akce_id) & (df_lidi['id_auto'] == ridic_jmeno)
    
    if df_lidi[maska_pasazeri].empty:
        return # Nikdo s ním nejel, hotovo.
        
    # Update pasažérů
    updated_rows = df_lidi[maska_pasazeri].copy()
    updated_rows['id_auto'] = ""
    updated_rows['doprava'] = "Hledám odvoz 🙋‍♂️ (⚠️ HLEDÁM AUTO)"
    
    # Spojíme nedotčené řádky s těmi upravenými a nahrajeme zpět
    df_clean = df_lidi[~maska_pasazeri]
    df_final = pd.concat([df_clean, updated_rows], ignore_index=True)
    
    conn.update(worksheet="prihlasky", data=df_final)

@st.dialog("✏️ Úprava přihlášky")
def show_edit_dialog(akce_id, nazev_akce, jmeno, aktualni_poznamka, aktualni_ubytovani, deadline_ubyt_raw):
    st.write(f"👤 **{jmeno}**")
    st.caption(f"Akce: {nazev_akce}")
    
    # 1. Poznámka
    def_poznamka = str(aktualni_poznamka).replace('\u00A0', '').strip()
    nova_poznamka = st.text_input("Poznámka", value=def_poznamka)
    
    # 2. Ubytování (s kontrolou deadlinu)
    is_ubyt = "Ano" in str(aktualni_ubytovani)
    
    # Zpracování deadlinu
    je_po_deadline_ubyt = False
    deadline_info = ""
    
    if deadline_ubyt_raw:
        try:
            d_ubyt = pd.to_datetime(deadline_ubyt_raw, dayfirst=True, errors='coerce')
            if pd.notnull(d_ubyt):
                if datetime.now() > d_ubyt:
                    je_po_deadline_ubyt = True
                    deadline_info = d_ubyt.strftime('%d.%m. %H:%M')
        except:
            pass

    st.markdown("<br>", unsafe_allow_html=True)

    # --- LOGIKA ZOBRAZENÍ CHECKBOXU ---
    if je_po_deadline_ubyt:
        st.markdown(f"🔒 **Ubytování uzavřeno** ({deadline_info})")
        
        if is_ubyt:
            st.info("✅ Máš objednáno (nelze zrušit).")
            nove_ubytovani = True # Musíme zachovat stávající stav
        else:
            st.warning("❌ Nemáš objednáno (nelze přidat).")
            nove_ubytovani = False # Musíme zachovat stávající stav
    else:
        # Jsme před deadlinem -> můžeme měnit
        nove_ubytovani = st.checkbox("🛏️ Společné ubytko", value=is_ubyt)

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("💾 Uložit změny", type="primary", use_container_width=True):
        conn = data_manager.get_connection()
        df = data_manager.load_prihlasky()
        
        # Ošetření poznámky (tvrdá mezera proti #NAME?)
        clean_poznamka = nova_poznamka.strip()
        if clean_poznamka.startswith(("=", "+", "-", "@")):
            clean_poznamka = "\u00A0" + clean_poznamka
            
        final_ubyt_text = "Ano 🛏️" if nove_ubytovani else ""
        
        # Najdeme řádek a upravíme ho
        maska = (df['id_akce'] == str(akce_id)) & (df['jméno'] == jmeno)
        
        if not df[maska].empty:
            df.loc[maska, 'poznámka'] = clean_poznamka
            df.loc[maska, 'ubytování'] = final_ubyt_text
            
            conn.update(worksheet="prihlasky", data=df)
            st.toast("✅ Údaje aktualizovány")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Chyba: Přihláška nenalezena.")

def vykreslit_detail_akce(akce, unique_key, conn, seznam_jmen):
    """
    Vykreslí kompletní obsah popoveru (přesunuto z app.py).
    """
    akce_id_str = str(akce.get('id', akce.get('id_akce', ''))).replace('.0', '')
    
    # ---------------------------------------------------------
    # 1. BEZPEČNÉ NAČTENÍ DAT
    # ---------------------------------------------------------
    try:
        df_reg = data_manager.load_prihlasky()
    except:
        df_reg = pd.DataFrame()

    if df_reg.empty or 'id_akce' not in df_reg.columns:
        lidi = pd.DataFrame(columns=['id_akce', 'jméno', 'doprava', 'poznámka', 'ubytování'])
    else:
        df_reg['id_akce'] = df_reg['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
        lidi = df_reg[df_reg['id_akce'] == akce_id_str].fillna("")

    # --- PŘÍPRAVA DAT PRO UI ---
    mapa_raw = str(akce.get('mapa', '')).strip() if pd.notna(akce.get('mapa')) else ""
    body_k_vykresleni = parse_map_coordinates(mapa_raw, akce.get('název', '')) 
    main_lat, main_lon = None, None
    
    if body_k_vykresleni:
        main_lat, main_lon, _ = body_k_vykresleni[0]

    if (not main_lat or not main_lon) and akce.get('místo'):
        found_lat, found_lon = get_coords_from_place(str(akce['místo']))
        if found_lat and found_lon:
            main_lat, main_lon = found_lat, found_lon

    typ_udalosti = str(akce.get('typ', '')).lower().strip() if pd.notna(akce.get('typ')) else ""
    druh_akce = str(akce.get('druh', '')).lower().strip() if pd.notna(akce.get('druh')) else "ostatní"
    kategorie_txt = str(akce.get('kategorie', '')).strip() if pd.notna(akce.get('kategorie')) else ""
    
    je_stafeta = "štafety" in typ_udalosti
    je_zavod_obecne = any(s in typ_udalosti for s in ["závod", "mčr", "žebříček", "liga", "mistrovství", "štafety", "ža", "žb"])
    
    dnes = date.today()
    je_po_deadlinu = False
    je_dnes_deadline = False
    deadline_str = ""
    
    if akce.get('deadline') and pd.notna(akce['deadline']):
        try:
            d_deadline = pd.to_datetime(akce['deadline']).date() if isinstance(akce['deadline'], pd.Timestamp) else akce['deadline']
            je_po_deadlinu = dnes > d_deadline
            je_dnes_deadline = dnes == d_deadline
            deadline_str = d_deadline.strftime('%d.%m.%Y')
        except:
            pass

    nazev_full = akce.get('název', '')

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
        c_head, c_cal = st.columns([0.85, 0.15], gap="small", vertical_alignment="center")
        with c_head:
            st.markdown(f"<h3 style='margin:0; padding:0;'>{nazev_full}</h3>", unsafe_allow_html=True)
        with c_cal:
            ics_data = generate_ics(akce)
            b64 = base64.b64encode(ics_data.encode('utf-8')).decode()
            st.markdown(styles.get_ics_button_html(b64, akce.get("název", "Akce")), unsafe_allow_html=True)
                
        st.markdown(
            styles.badge(typ_label_short, bg="#F3F4F6", color="#333") + 
            styles.badge(druh_akce.upper(), bg="#E5E7EB", color="#555"), 
            unsafe_allow_html=True
        )
        
        st.markdown("<div style='margin-top: 20px; font-size: 0.95rem; color: #444;'>", unsafe_allow_html=True)
        st.write(f"📍 **Místo:** {akce.get('místo', '')}")
        
        if akce.get('datum') != akce.get('datum_do'):
            st.write(f"🗓️ **Termín:** {akce['datum'].strftime('%d.%m.')} – {akce['datum_do'].strftime('%d.%m.%Y')}")
        else:
             st.write(f"🗓️ **Datum:** {akce['datum'].strftime('%d.%m.%Y')}")
        
        if kategorie_txt:
            st.write(f"🎯 **Kategorie:** {kategorie_txt}")
        st.markdown("</div>", unsafe_allow_html=True)

        if pd.notna(akce.get('popis')) and str(akce.get('popis')).strip(): 
            st.info(f"{akce['popis']}", icon="ℹ️")
        
        if je_po_deadlinu:
            st.error(f"⛔ **DEADLINE BYL:** {deadline_str}")
        elif je_dnes_deadline:
            st.warning(f"⚠️ **DNES JE DEADLINE!** ({deadline_str})")
        else:
            st.success(f"📅 **Deadline:** {deadline_str}")

        raw_ubyt = akce.get('deadline_ubytovani')
        deadline_ubyt = pd.to_datetime(raw_ubyt, dayfirst=True, errors='coerce') 
        
        if pd.notnull(deadline_ubyt) and deadline_ubyt != akce.get('deadline'):
            ubyt_str = deadline_ubyt.strftime('%d.%m.')
            if deadline_ubyt.hour != 0 or deadline_ubyt.minute != 0:
                ubyt_str += deadline_ubyt.strftime(' %H:%M')
            st.markdown(f"""
                <div style="margin-top: -10px; margin-bottom: 15px; padding-left: 5px; color: #4B5563; font-size: 0.9rem;">
                    🛏️ <b>Deadline ubytování:</b> {ubyt_str}
                </div>
            """, unsafe_allow_html=True)
            
        # POČASÍ + ZÁPAD SLUNCE
        if main_lat and main_lon:
            forecast = get_forecast(main_lat, main_lon, akce['datum'])
            if forecast:
                w_icon, w_text = get_weather_emoji(forecast['code'])
                temp = round(forecast['temp_max'])
                rain = forecast['precip']
                wind = forecast['wind']
                
                sunset_raw = forecast.get('sunset')
                html_zapad = "" 
                if "nočák" in druh_akce and sunset_raw:
                    try:
                        sunset_time = sunset_raw.split('T')[1]
                        html_zapad = f"""<div style="text-align: right; border-left: 1px solid #d1d5db; padding-left: 15px; margin-left: 15px;"><div style="font-size: 1.5rem; line-height: 1;">🌑</div><div style="font-size: 0.7rem; font-weight: bold; color: #1f2937; text-transform: uppercase;">Západ</div><div style="font-size: 0.9rem; color: #4b5563;">{sunset_time}</div></div>"""
                    except: pass

                st.markdown(
                    styles.get_weather_card_html(w_icon, w_text, temp, rain, wind, html_zapad), 
                    unsafe_allow_html=True
                )
                
        # --- ORIS a LIVELOX LINKY ---
        link_oris = str(akce.get('odkaz', '')).strip() if pd.notna(akce.get('odkaz')) else ""
        link_livelox = str(akce.get('livelox', '')).strip() if pd.notna(akce.get('livelox')) else ""

        # Zjistíme, co vlastně máme k dispozici
        ma_oris = je_zavod_obecne or (link_oris and link_oris != "nan")
        ma_livelox = link_livelox and link_livelox != "nan"

        if ma_oris or ma_livelox:
            # 1. Dynamický text nad tlačítky
            if ma_oris and not ma_livelox:
                st.caption("Přihlášky probíhají v systému ORIS.")
            elif ma_livelox and not ma_oris:
                st.caption("🗺️ Nahrání stop a analýza postupů:")
            else:
                st.caption("Odkazy na systém a rozbory:")

            if je_stafeta: 
                st.warning("⚠️ **ŠTAFETY:** Přihlaš se i ZDE (vpravo) kvůli soupiskám!")
            
            # Příprava HTML kódů pro tlačítka
            target_oris = link_oris if link_oris else "https://oris.orientacnisporty.cz/"
            
            html_oris = f"""
            <a href="{target_oris}" target="_blank" style="text-decoration:none;">
                <div style="background-color: #2563EB; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 0.9rem; transition: 0.3s;">
                    👉 ORIS
                </div>
            </a>
            """
            
            html_livelox = f"""
            <a href="{link_livelox}" target="_blank" style="text-decoration:none;">
                <div style="background-color: #db2777; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 0.9rem; transition: 0.3s;">
                    🗺️ Livelox
                </div>
            </a>
            """

            # 2. Chytré vykreslení (2 sloupce, nebo plná šířka)
            if ma_oris and ma_livelox:
                c_oris, c_livelox = st.columns(2)
                with c_oris:
                    st.markdown(html_oris, unsafe_allow_html=True)
                with c_livelox:
                    st.markdown(html_livelox, unsafe_allow_html=True)
            elif ma_oris:
                st.markdown(html_oris, unsafe_allow_html=True)
            elif ma_livelox:
                st.markdown(html_livelox, unsafe_allow_html=True)
                
    with col_form:
        delete_key_state = f"confirm_delete_{unique_key}"
        with stylable_container(
            key=f"form_cont_{unique_key}",
            css_styles="{border: 1px solid #E5E7EB; border-radius: 12px; padding: 20px; background-color: #F9FAFB; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);}"
        ):
            if not je_po_deadlinu and delete_key_state not in st.session_state:
                st.markdown("<h4 style='margin-top:0; margin-bottom: 15px;'>✍️ Přihláška</h4>", unsafe_allow_html=True)
                
                if je_zavod_obecne and not je_stafeta:
                    st.markdown("""<div style="background-color: #FEF2F2; border: 1px solid #FCA5A5; color: #B91C1C; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-weight: bold; font-size: 0.9em; display: flex; align-items: center;"><span style="font-size: 1.2em; margin-right: 8px;">⚠️</span>Je nutné se přihlásit i v ORISu!</div>""", unsafe_allow_html=True)

                form_key = f"form_{unique_key}"
                with st.form(key=form_key, clear_on_submit=True): 
                    if kategorie_txt and kategorie_txt.lower() != "všichni": 
                        st.warning(f"Doporučení: **{kategorie_txt}**")
                    
                    vybrana_jmena = st.multiselect("Vyber členy", options=seznam_jmen, placeholder="Klikni a vyber...")
                    nove_jmeno = st.text_input("Nebo nové jméno (pokud není v seznamu)")
                    poznamka_input = st.text_input("Poznámka (společná)")
                    
                    lidi_k_zapisu = []
                    if vybrana_jmena: lidi_k_zapisu.extend(vybrana_jmena)
                    if nove_jmeno.strip(): 
                        lidi_k_zapisu.append(nove_jmeno.strip().title())

                    st.markdown("<br>", unsafe_allow_html=True)

                    c_ubyt, c_dopr = st.columns(2)
                    
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
                            st.write("") 

                    with c_dopr:
                        rychla_doprava_input = st.checkbox("🚗 Chci odvoz")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    c_btn_zapis, c_btn_doprava = st.columns([1, 1.2], gap="small")
                    
                    with c_btn_zapis:
                        odeslat_btn = st.form_submit_button("Zapsat se", type="primary", use_container_width=True)
                    with c_btn_doprava:
                        doprava_btn = st.form_submit_button("🚗 Doprava (Dialog)", use_container_width=True)
                    
                    if odeslat_btn:
                        if not lidi_k_zapisu:
                            st.warning("Musíš vybrat alespoň jedno jméno.")
                        else:
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

                            try:
                                aktualni_data = data_manager.load_prihlasky()
                                novy_list_prihlasek = []
                                hodnota_ubyt = "Ano 🛏️" if ubytovani_input else ""
                                hodnota_dopravy = "Hledám odvoz 🙋‍♂️" if rychla_doprava_input else ""

                                clean_poznamka = str(poznamka_input).strip()
                                if clean_poznamka.startswith(("=", "+", "-", "@")):
                                    clean_poznamka = "\u00A0" + clean_poznamka
                                
                                for clovek in lidi_k_zapisu:
                                    clovek = str(clovek).strip().title()
                                    if aktualni_data[(aktualni_data['id_akce']==akce_id_str) & (aktualni_data['jméno']==clovek)].empty:
                                        novy_list_prihlasek.append({
                                            "id_akce": akce_id_str, 
                                            "název": akce.get('název', ''), 
                                            "jméno": clovek, 
                                            "poznámka": clean_poznamka, 
                                            "doprava": hodnota_dopravy,
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

                            clean_poznamka_dialog = str(poznamka_input).strip()
                            if clean_poznamka_dialog.startswith(("=", "+", "-", "@")):
                                clean_poznamka_dialog = "\u00A0" + clean_poznamka_dialog
                                
                            lidi_clean = [str(x).strip().title() for x in lidi_k_zapisu]
                            
                            show_doprava_dialog(
                                akce_id=akce_id_str,
                                nazev_akce=akce.get('název', ''),
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

        st.markdown(styles.get_map_buttons_html(link_mapy_cz, link_google, link_waze), unsafe_allow_html=True)
    elif mapa_raw: 
        st.warning("⚠️ Mapa se nenačetla.")

    # --- SEZNAM ---
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    st.markdown(f"#### 👥 Zapsaní ({len(lidi)})")

    # --- DASHBOARD DOPRAVY ---
    if not lidi.empty:
        ridici_data = [] 
        cekaliste = []    
        
        for _, r in lidi.iterrows():
            dopr = str(r.get('doprava', ''))
            if "Řidič" in dopr:
                kapacita = 4 
                match_kap = re.search(r'(\d+)\s*míst', dopr)
                if match_kap: kapacita = int(match_kap.group(1))
                
                info_text = dopr.split(",", 1)[1].strip().replace(")", "") if "," in dopr else ""
                
                ridici_data.append({"jmeno": r['jméno'], "kapacita": kapacita, "info": info_text, "pasazeri": []})
            elif "Hledám" in dopr or "Chci" in dopr:
                cekaliste.append(r['jméno'])

        for _, r in lidi.iterrows():
            dopr = str(r.get('doprava', ''))
            if "Řidič" in dopr or "Hledám" in dopr or "Chci" in dopr or not dopr or dopr == "nan": continue
            for ridic in ridici_data:
                if ridic['jmeno'] in dopr:
                    ridic['pasazeri'].append(r['jméno'])
                    break

        if cekaliste:
            st.error(f"🚨 **Hledají odvoz ({len(cekaliste)}):** {', '.join(cekaliste)}")
        
        if ridici_data:
            cols = st.columns(2)
            for i, auto in enumerate(ridici_data):
                obsazeno = len(auto['pasazeri'])
                celkem_mist = auto['kapacita']
                percent = min((obsazeno / celkem_mist) * 100, 100) if celkem_mist > 0 else 0
                
                if obsazeno > celkem_mist:
                    status_color, bg_color, border_color, status_icon, status_text = "#EF4444", "#FEF2F2", "#FECACA", "🚨", "Přeplněno!"
                elif obsazeno == celkem_mist:
                    status_color, bg_color, border_color, status_icon, status_text = "#F59E0B", "#FFFBEB", "#FDE68A", "👌", "Plno"
                else:
                    status_color, bg_color, border_color, status_icon, status_text = "#10B981", "#ECFDF5", "#A7F3D0", "✅", f"Volno: {celkem_mist - obsazeno}"

                info_label = auto['info'] if auto['info'] else "Řidič"
                detail_text = f"{obsazeno} z {celkem_mist}"
                
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
                col_index = i % 2
                with cols[col_index]:
                    st.markdown(html_card, unsafe_allow_html=True)
                    if auto['pasazeri']:
                        with st.expander(f"Seznam ({len(auto['pasazeri'])})"):
                            for p in auto['pasazeri']: st.caption(f"• {p}")
                    else:
                        st.markdown("<div style='margin-bottom: 10px'></div>", unsafe_allow_html=True)

    # --- LIST LIDI ---
    def format_cell(text, width):
        text = str(text)
        if len(text) > width: text = text[:width-2] + ".."
        return text + ("\u00A0" * (width - len(text)))

    if not lidi.empty:
        W_INDEX, W_JMENO, W_DOPRAVA = 4, 20, 22
        
        for i, (idx, row) in enumerate(lidi.iterrows()):
            bg_color = "#FFFFFF" if i % 2 == 0 else "#F1F5F9"
            border_color = "#E5E7EB" if i % 2 == 0 else "#CBD5E1"
            
            zebra_style = f"""
            div[data-testid="stExpander"] {{ background-color: {bg_color} !important; border: 1px solid {border_color} !important; border-radius: 8px !important; margin-bottom: 0px !important; }}
            .streamlit-expanderHeader {{ background-color: {bg_color} !important; }}
            div[data-testid="stExpanderDetails"] {{ background-color: {bg_color} !important; }}
            """
            
            idx_formatted = format_cell(f"{i+1}.", W_INDEX)
            jmeno_formatted = format_cell(row['jméno'], W_JMENO)
            
            dopr_raw = str(row.get('doprava', ''))
            if not dopr_raw or dopr_raw == "nan": d_text = "⚪ Bez dopravy"
            elif "Řidič" in dopr_raw: d_text = "🚙 Řidič"
            elif "Spolujízda" in dopr_raw or "Jedu s" in dopr_raw:
                clean = dopr_raw.replace("Spolujízda:", "").replace("Spolujízda", "").replace("Jedu s:", "").strip()
                d_text = f"➡️ {clean}"
            elif "Chci" in dopr_raw or "Hledám" in dopr_raw:
                if "(" in dopr_raw and ")" in dopr_raw:
                    try:
                        start = dopr_raw.find("(") + 1
                        misto = dopr_raw[start:dopr_raw.find(")")].strip()
                        if len(misto) > 12: misto = misto[:10] + "."
                        d_text = f"🙋‍♂️ {misto}"
                    except: d_text = "🙋‍♂️ Hledá odvoz"
                else: d_text = "🙋‍♂️ Hledá odvoz"
            else: d_text = "❓ Nevyřešeno"
            
            dopr_formatted = format_cell(d_text, W_DOPRAVA)
            
            ubyt_raw = str(row.get('ubytování', ''))
            ubyt_icon = "🛏️" if ubyt_raw and "Ano" in ubyt_raw else ""
            poznamka = row.get('poznámka', '')
            extra_info = f" {ubyt_icon}" + (f"  📝 {poznamka}" if poznamka else "")

            header_text = f"{idx_formatted}{jmeno_formatted}{dopr_formatted}{extra_info}"

            with stylable_container(key=f"exp_place_{unique_key}_{i}", css_styles=zebra_style):
                st.markdown(f"<div style='margin-bottom: 8px;'>", unsafe_allow_html=True)
                with st.expander(header_text, expanded=False):
                    if "Hledám" in dopr_raw or "Chci" in dopr_raw:
                        if "(" in dopr_raw: st.info(f"📍 **Poptávka:** {dopr_raw}")
                        else: st.caption(f"Stav dopravy: {dopr_raw}")
                    else: st.caption(f"Celé jméno: {row['jméno']}")

                    c_btn_doprava, c_btn_edit, c_btn_delete = st.columns([2.2, 1, 0.8], gap="small")
                    
                    with c_btn_doprava:
                        btn_type = "primary" if "Řidič" in dopr_raw else "secondary"
                        if st.button("🔧 Doprava", key=f"btn_dopr_{unique_key}_{i}", use_container_width=True, type=btn_type):
                            show_doprava_dialog(akce_id_str, akce.get('název', ''), akce['datum'].strftime('%d.%m.'), row['jméno'])
                            
                    with c_btn_edit:
                        if st.button("✏️ Upravit", key=f"btn_edit_{unique_key}_{i}", use_container_width=True):
                            show_edit_dialog(akce_id=akce_id_str, nazev_akce=akce.get('název', ''), jmeno=row['jméno'], aktualni_poznamka=row.get('poznámka', ''), aktualni_ubytovani=row.get('ubytování', ''), deadline_ubyt_raw=akce.get('deadline_ubytovani'))
                            
                    with c_btn_delete:
                        delete_key_state = f"confirm_delete_{unique_key}"
                        je_k_smazani = (delete_key_state in st.session_state) and (st.session_state[delete_key_state] == row['jméno'])

                        if je_k_smazani:
                            st.markdown("<div style='text-align: center; color: #EF4444; font-weight: bold; font-size: 0.8rem; margin-bottom: 2px;'>Opravdu?</div>", unsafe_allow_html=True)
                            col_y, col_n = st.columns(2, gap="small")
                            with col_y:
                                if st.button("✅", key=f"yes_exp_{unique_key}_{i}", use_container_width=True, type="primary"):
                                    try:
                                        df_curr = conn.read(worksheet="prihlasky", ttl=0)
                                        if 'id_akce' in df_curr.columns: df_curr['id_akce'] = df_curr['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
                                        df_to_keep = df_curr[~((df_curr['id_akce'] == akce_id_str) & (df_curr['jméno'] == row['jméno']))]
                                        conn.update(worksheet="prihlasky", data=df_to_keep)
                                        handle_driver_removal(conn, akce_id_str, row['jméno'])
                                        del st.session_state[delete_key_state]
                                        st.toast("✅ Odhlášeno.")
                                        time.sleep(0.5)
                                        st.rerun()
                                    except Exception as e: st.error(f"Chyba při mazání: {e}")
                            with col_n:
                                if st.button("❌", key=f"no_exp_{unique_key}_{i}", use_container_width=True):
                                    del st.session_state[delete_key_state]
                                    st.rerun()
                        elif not je_po_deadlinu:
                            if st.button("🗑️", key=f"del_exp_{unique_key}_{i}", use_container_width=True):
                                st.session_state[delete_key_state] = row['jméno']
                                st.rerun()
                    if poznamka: st.text(f"Poznámka: {poznamka}")
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Zatím nikdo. Buď první!")
    
    export_admin_section(lidi, akce.get('název', ''), unique_key)
