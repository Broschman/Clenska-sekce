import streamlit as st
import requests
import re
import base64
import os
import time
import pandas as pd
from datetime import datetime, date, timedelta
from urllib.parse import urlparse, parse_qs
from io import BytesIO
from streamlit_extras.stylable_container import stylable_container
from streamlit_lottie import st_lottie_spinner
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components

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

# utils.py

@st.dialog("🚗 Správa dopravy")
def show_doprava_dialog(akce_id, nazev_akce, datum_akce, pre_jmeno, in_poznamka=None, in_ubytovani=None):
    """
    Modální okno pro řešení dopravy.
    """
    conn = data_manager.get_connection()
    
    # Čerstvá data
    df_auta = data_manager.load_auta()
    df_lidi = data_manager.load_prihlasky()
    
    # Filtry
    auta_akce = df_auta[df_auta['id_akce'] == akce_id].copy()
    lidi_akce = df_lidi[df_lidi['id_akce'] == akce_id].copy()
    
    obsazenost = {}
    if not lidi_akce.empty and 'id_auto' in lidi_akce.columns:
        obsazenost = lidi_akce[lidi_akce['id_auto'] != ""].groupby('id_auto').size().to_dict()

    st.markdown(f"**{nazev_akce}** ({datum_akce})")
    
    # 1. Načíst seznam
    seznam_jmen = data_manager.load_jmena()
    
    # 2. Ošetřit vstup (str a strip)
    target_jmeno = str(pre_jmeno).strip() if pre_jmeno else None
    
    # 3. Pokud jméno existuje, ale není v seznamu, přidáme ho
    if target_jmeno and target_jmeno not in seznam_jmen:
        seznam_jmen.append(target_jmeno)
        seznam_jmen.sort()
        
    # 4. Najít index (pro případ, že NENÍ vynucené jméno)
    idx_jmeno = None
    if target_jmeno:
        try:
            idx_jmeno = seznam_jmen.index(target_jmeno)
        except ValueError:
            idx_jmeno = None

    # ### --- FIX PROTI VAROVÁNÍ ---
    # Pokud máme target_jmeno, vnutíme ho do Session State.
    # ZÁROVEŇ musíme vynulovat 'idx_jmeno', aby se nehádal parametr 'index' se 'session_state'.
    if target_jmeno:
        st.session_state.diag_jmeno = target_jmeno
        idx_jmeno = None  # <--- TOTO VYŘEŠÍ VAROVÁNÍ
    # ### --------------------------

    # 5. Vykreslit selectbox
    # Pokud je idx_jmeno None, Streamlit použije hodnotu z key="diag_jmeno" (což chceme).
    vybrane_jmeno = st.selectbox(
        "Kdo jsi?", 
        options=seznam_jmen, 
        index=idx_jmeno, 
        key="diag_jmeno", 
        disabled=(target_jmeno is not None)
    )
    
    st.markdown("---")

    if vybrane_jmeno:
        # Zjištění stavu z DB
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
            elif "Chci" in dopr_txt: stav_dopravy = "waiting"
        
        # Rozhodovací logika dat
        final_poznamka = in_poznamka if in_poznamka is not None else db_poznamka
        final_ubytovani_txt = ("Ano 🛏️" if in_ubytovani else "") if in_ubytovani is not None else db_ubytovani

        role = st.radio("Možnosti dopravy:", 
                 ["Nic (Zrušit dopravu)", "🚙 Nabízím auto (Řidič)", "🙋‍♂️ Hledám odvoz (Pasažér)"],
                 index=1 if stav_dopravy == "driver" else (2 if stav_dopravy in ["passenger", "waiting"] else 0)
        )
        st.markdown("<br>", unsafe_allow_html=True)

        # --- A) ŘIDIČ ---
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
            
            if st.button("💾 Uložit nastavení", type="primary", use_container_width=True):
                df_clean_auta = df_auta[~((df_auta['id_akce'] == akce_id) & (df_auta['ridic'] == vybrane_jmeno))]
                nove_auto_row = pd.DataFrame([{
                    "id_akce": akce_id, "ridic": vybrane_jmeno, 
                    "kapacita": novy_kap, "cas": novy_cas, "misto": novy_misto, "poznamka": ""
                }])
                conn.update(worksheet="auta", data=pd.concat([df_clean_auta, nove_auto_row], ignore_index=True))
                
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

        # --- B) PASAŽÉR (S časem i místem a řazením) ---
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
                    if misto_txt: 
                        if info_part: info_part += f", {misto_txt}"
                        else: info_part = misto_txt
                    
                    label = f"🚙 {ridic} ({volno} volných)"
                    if info_part: label += f" - {info_part}"
                    
                    if volno <= 0: label = f"⚠️ {ridic} (PLNO - Jsi tu)"
                    
                    dostupna_auta_list.append({ "label": label, "ridic_id": ridic, "volno": volno })
            
            dostupna_auta_list.sort(key=lambda x: x['volno'], reverse=True)
            
            options_auta = [item['label'] for item in dostupna_auta_list]
            mapa_aut = {item['label']: item['ridic_id'] for item in dostupna_auta_list}
            
            wait_label = "⏳ Čekací listina (zatím nemám auto)"
            options_auta.append(wait_label)
            mapa_aut[wait_label] = ""

            idx_select = 0
            if stav_dopravy == "waiting":
                idx_select = len(options_auta) - 1
            elif stav_dopravy == "passenger" and id_auto_curr:
                for idx, item_label in enumerate(options_auta):
                    if mapa_aut.get(item_label) == id_auto_curr:
                        idx_select = idx
                        break

            vybrane_label = st.selectbox("Ke komu?", options_auta, index=idx_select)
            target_ridic = mapa_aut[vybrane_label]
            
            if st.button("💾 Uložit změnu", type="primary", use_container_width=True):
                if stav_dopravy == "driver":
                    handle_driver_removal(conn, akce_id, vybrane_jmeno)
                    df_lidi = data_manager.load_prihlasky()

                df_clean_lidi = df_lidi[~((df_lidi['id_akce'] == akce_id) & (df_lidi['jméno'] == vybrane_jmeno))]
                dopr_text = f"Spolujízda: {target_ridic}" if target_ridic else "Chci odvoz 🙋‍♂️"
                
                novy_clovek = pd.DataFrame([{
                    "id_akce": akce_id, "název": nazev_akce, "jméno": vybrane_jmeno,
                    "poznámka": final_poznamka,
                    "doprava": dopr_text, 
                    "ubytování": final_ubytovani_txt,
                    "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "id_auto": target_ridic
                }])
                conn.update(worksheet="prihlasky", data=pd.concat([df_clean_lidi, novy_clovek], ignore_index=True))
                st.rerun()

        # --- C) ZRUŠIT ---
        else:
            if st.button("🗑️ Smazat dopravu", use_container_width=True):
                if stav_dopravy == "driver":
                    handle_driver_removal(conn, akce_id, vybrane_jmeno)
                    df_lidi = data_manager.load_prihlasky()

                df_clean_lidi = df_lidi[~((df_lidi['id_akce'] == akce_id) & (df_lidi['jméno'] == vybrane_jmeno))]
                novy_clovek = pd.DataFrame([{
                    "id_akce": akce_id, "název": nazev_akce, "jméno": vybrane_jmeno,
                    "poznámka": final_poznamka, 
                    "doprava": "", 
                    "ubytování": final_ubytovani_txt,
                    "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "id_auto": ""
                }])
                conn.update(worksheet="prihlasky", data=pd.concat([df_clean_lidi, novy_clovek], ignore_index=True))
                st.rerun()
                
def handle_driver_removal(conn, akce_id, driver_name):
    """
    Když se ruší řidič (smazání nebo změna role), tato funkce:
    1. Smaže jeho auto z listu 'auta'.
    2. Najde všechny jeho pasažéry v 'prihlasky' a hodí je na 'waiting list'.
    """
    try:
        # 1. SMAZÁNÍ AUTA
        df_auta = data_manager.load_auta()
        if not df_auta.empty:
            # Filtr: Necháme všechna auta KROMĚ toho, co patří tomuto řidiči na této akci
            maska_auto = ~((df_auta['id_akce'] == akce_id) & (df_auta['ridic'] == driver_name))
            df_new_auta = df_auta[maska_auto]
            
            # Pokud došlo ke změně (řádek existoval), uložíme
            if len(df_new_auta) < len(df_auta):
                conn.update(worksheet="auta", data=df_new_auta)

        # 2. PŘESUN PASAŽÉRŮ NA ČEKAČKU
        df_lidi = data_manager.load_prihlasky()
        if not df_lidi.empty and 'id_auto' in df_lidi.columns:
            # Najdeme lidi, co mají ve sloupci id_auto jméno tohoto řidiče
            maska_pasazeri = (df_lidi['id_akce'] == akce_id) & (df_lidi['id_auto'] == driver_name)
            
            if maska_pasazeri.any():
                # Resetujeme jejich status
                df_lidi.loc[maska_pasazeri, 'id_auto'] = ""
                # Přepíšeme text dopravy, aby věděli, že se něco stalo
                df_lidi.loc[maska_pasazeri, 'doprava'] = "Chci odvoz 🙋‍♂️ (Zrušeno auto)"
                
                conn.update(worksheet="prihlasky", data=df_lidi)
                return True # Signál, že jsme někoho updatovali
    except Exception as e:
        print(f"Chyba při mazání řidiče: {e}")
    return False

def vykreslit_detail_akce(akce, unique_key):
    """
    Vykreslí detail akce (Futuristický Dark Mode Design).
    NOVĚ: Deadline ubytování.
    """
    conn = data_manager.get_connection()
    seznam_jmen = data_manager.load_jmena()

    # --- 1. PŘÍPRAVA DAT ---
    mapa_raw = str(akce.get('mapa', '')).strip() if pd.notna(akce.get('mapa')) else ""
    body_k_vykresleni = parse_map_coordinates(mapa_raw, akce.get('název', 'Akce'))
    
    main_lat, main_lon = None, None
    if body_k_vykresleni: main_lat, main_lon, _ = body_k_vykresleni[0]
    
    misto = str(akce.get('místo', ''))
    if (not main_lat or not main_lon) and misto:
        found_lat, found_lon = get_coords_from_place(misto)
        if found_lat and found_lon: main_lat, main_lon = found_lat, found_lon

    akce_id_str = str(akce.get('id', '')).replace('.0', '')
    typ_udalosti = str(akce.get('typ', '')).lower().strip()
    druh_akce = str(akce.get('druh', '')).lower().strip()
    
    zavodni_slova = ["závod", "mčr", "žebříček", "liga", "mistrovství", "štafety", "ža", "žb"]
    je_zavod_obecne = any(s in typ_udalosti for s in zavodni_slova)
    
    # === DEADLINY ===
    dnes = date.today()
    
    # Hlavní deadline
    deadline_val = akce.get('deadline')
    if isinstance(deadline_val, pd.Timestamp): deadline_val = deadline_val.date()
    
    # Deadline ubytování
    deadline_ubyt = akce.get('deadline_ubytovani')
    if isinstance(deadline_ubyt, pd.Timestamp): deadline_ubyt = deadline_ubyt.date()
    
    je_po_deadlinu = False
    je_po_deadlinu_ubyt = False
    
    deadline_str = "?"
    deadline_ubyt_str = "?"
    
    if deadline_val:
        je_po_deadlinu = dnes > deadline_val
        deadline_str = deadline_val.strftime('%d.%m.%Y')

    if deadline_ubyt:
        je_po_deadlinu_ubyt = dnes > deadline_ubyt
        deadline_ubyt_str = deadline_ubyt.strftime('%d.%m.%Y')

    # Má smysl řešit ubytování? (Buď je to vícedenní, nebo to není jen trénink, nebo má explicitní deadline)
    ma_ubytovani = "soustředění" in typ_udalosti or "mčr" in typ_udalosti or akce['datum'] != akce['datum_do']

    lidi = pd.DataFrame()
    if akce_id_str:
        df_full = data_manager.load_prihlasky()
        lidi = df_full[df_full['id_akce'] == akce_id_str].copy().fillna("")

    # --- LAYOUT ---
    col_info, col_form = st.columns([1.2, 1], gap="large")
    
    # === LEVÝ SLOUPEC (INFO) ===
    with col_info:
        c_head, c_cal = st.columns([0.85, 0.15], gap="small", vertical_alignment="center")
        with c_head: st.markdown(f"<h3 style='margin:0; padding:0;'>{akce.get('název', 'Bez názvu')}</h3>", unsafe_allow_html=True)
        with c_cal:
            ics_data = generate_ics(akce)
            b64 = base64.b64encode(ics_data.encode('utf-8')).decode()
            st.markdown(styles.get_ics_button_html(b64, akce.get("název", "")), unsafe_allow_html=True)
        
        st.markdown(styles.badge(typ_udalosti.upper()), unsafe_allow_html=True)
        
        datum_txt = akce['datum'].strftime('%d.%m.%Y')
        if akce['datum'] != akce['datum_do']:
            datum_txt += f" - {akce['datum_do'].strftime('%d.%m.%Y')}"

        st.markdown(f"<div style='margin-top:20px; color:#aaa'>📍 <b>Místo:</b> {misto}<br>🗓️ <b>Datum:</b> {datum_txt}</div>", unsafe_allow_html=True)
        
        popis = akce.get('popis')
        if pd.notna(popis): st.info(popis, icon="ℹ️")
        
        # --- ZOBRAZENÍ DEADLINŮ ---
        c_d1, c_d2 = st.columns(2)
        with c_d1:
            if je_po_deadlinu: 
                st.error(f"⛔ Deadline přihlášek:\n{deadline_str}")
            else: 
                st.success(f"📅 Deadline přihlášek:\n{deadline_str}")
        
        # Zobrazit deadline ubytování jen pokud to dává smysl
        if ma_ubytovani:
            with c_d2:
                if je_po_deadlinu_ubyt:
                     st.warning(f"🛏️ Deadline ubytování:\n{deadline_ubyt_str} (Uzavřeno)")
                else:
                     st.info(f"🛏️ Deadline ubytování:\n{deadline_ubyt_str}")

        if main_lat and main_lon:
            forecast = get_forecast(main_lat, main_lon, akce['datum'])
            if forecast:
                w_icon, w_text = get_weather_emoji(forecast['code'])
                st.markdown(styles.get_weather_card_html(w_icon, w_text, round(forecast['temp_max']), forecast['precip'], forecast['wind']), unsafe_allow_html=True)
        
        if je_zavod_obecne:
            odkaz = str(akce.get('odkaz', 'https://oris.orientacnisporty.cz/'))
            if not odkaz or odkaz == "nan": odkaz = "https://oris.orientacnisporty.cz/"
            st.markdown(f"""<a href="{odkaz}" target="_blank"><div style="background: rgba(0, 243, 255, 0.1); border: 1px solid #00f3ff; color: #ccfcff; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; text-shadow: 0 0 5px #00f3ff;">👉 Otevřít ORIS</div></a>""", unsafe_allow_html=True)

    # === PRAVÝ SLOUPEC (PŘIHLÁŠKA) ===
    with col_form:
        delete_key_state = f"confirm_delete_{unique_key}"
        
        with stylable_container(
            key=f"form_cont_{unique_key}",
            css_styles="{border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; background-color: rgba(255,255,255,0.03);}"
        ):
            if not je_po_deadlinu and delete_key_state not in st.session_state:
                st.markdown("<h4 style='margin-top:0;'>✍️ Přihláška</h4>", unsafe_allow_html=True)
                
                vybrane_jmeno = st.selectbox("Jméno", options=seznam_jmen, index=None, placeholder="Vyber jméno...", key=f"sel_jmeno_{unique_key}")
                nove_jmeno = st.text_input("Nebo nové jméno", key=f"inp_new_{unique_key}")
                poznamka = st.text_input("Poznámka", key=f"inp_note_{unique_key}")
                
                # --- LOGIKA CHECKBOXU UBYTOVÁNÍ ---
                # Defaultně False
                ubyt = False
                
                # Checkbox zobrazíme jen když:
                # 1. Není to jednodenní trénink (pokud nemáš explicitně řečeno jinak)
                # 2. Není po deadlinu ubytování
                if ma_ubytovani:
                    if not je_po_deadlinu_ubyt:
                        ubyt = st.checkbox("🛏️ Společné ubytko", key=f"chk_ubyt_{unique_key}")
                    else:
                        st.caption("🔒 Ubytování již nelze objednat (po deadlinu).")
                
                finalni_jmeno = nove_jmeno.strip() if nove_jmeno else vybrane_jmeno
                st.markdown("<br>", unsafe_allow_html=True)

                c_btn1, c_btn2 = st.columns([1, 1], gap="small")
                with c_btn1:
                    with stylable_container(key=f"c_save_{unique_key}", css_styles="button {width: 100%;}"):
                        if st.button("💾 Zapsat se", key=f"btn_save_{unique_key}", type="primary"):
                            if finalni_jmeno:
                                try:
                                    df_full = data_manager.load_prihlasky()
                                    existujici = df_full[(df_full['id_akce'] == akce_id_str) & (df_full['jméno'] == finalni_jmeno)]
                                    old_dopr, old_id_auto = "", ""
                                    
                                    # Pokud se jen updatuje, zachováme starou hodnotu ubytka, POKUD je po deadlinu a už to měl
                                    puvodni_ubytko = ""
                                    if not existujici.empty:
                                        old_dopr = existujici.iloc[0].get('doprava', "")
                                        old_id_auto = existujici.iloc[0].get('id_auto', "")
                                        puvodni_ubytko = existujici.iloc[0].get('ubytování', "")
                                    
                                    # Finální stav ubytka
                                    final_ubyt_str = ""
                                    if ma_ubytovani:
                                        if je_po_deadlinu_ubyt:
                                            # Pokud je po deadlinu, nemůžeme měnit. Necháme původní.
                                            final_ubyt_str = puvodni_ubytko
                                        else:
                                            # Před deadlinem bere hodnotu z checkboxu
                                            final_ubyt_str = "Ano 🛏️" if ubyt else ""
                                    
                                    df_full = df_full[~((df_full['id_akce'] == akce_id_str) & (df_full['jméno'] == finalni_jmeno))]
                                    novy = pd.DataFrame([{
                                        "id_akce": akce_id_str, "název": akce.get('název', ''), "jméno": finalni_jmeno,
                                        "poznámka": poznamka, "doprava": old_dopr, 
                                        "ubytování": final_ubyt_str,
                                        "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "id_auto": old_id_auto
                                    }])
                                    conn.update(worksheet="prihlasky", data=pd.concat([df_full, novy], ignore_index=True))
                                    
                                    if finalni_jmeno not in seznam_jmen:
                                        try:
                                            j_df = conn.read(worksheet="jmena")
                                            conn.update(worksheet="jmena", data=pd.concat([j_df, pd.DataFrame([{"jméno": finalni_jmeno}])], ignore_index=True))
                                        except: pass

                                    st.toast(f"✅ {finalni_jmeno} uložen!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e: st.error(str(e))
                            else: st.warning("Vyber jméno!")
                with c_btn2:
                    if st.button("🚗 Doprava...", key=f"btn_dopr_{unique_key}", use_container_width=True):
                        if finalni_jmeno:
                            # Pro dopravu posíláme aktuální stav (z DB nebo formuláře)
                            # Pokud uživatel ještě není v DB, pošleme False/None, ale to nevadí
                            show_doprava_dialog(akce_id_str, akce.get('název', ''), akce['datum'].strftime('%d.%m.'), finalni_jmeno, poznamka, ubyt)
                        else: st.warning("Nejdřív vyber jméno!")
            elif je_po_deadlinu: st.info("🔒 Přihlášky uzavřeny.")

    # --- SEZNAM ---
    st.markdown("<hr style='margin: 30px 0; border-top: 1px solid rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    if body_k_vykresleni:
        start_lat, start_lon, _ = body_k_vykresleni[0]
        m = folium.Map(location=[start_lat, start_lon], tiles="CartoDB dark_matter")
        folium.Marker([start_lat, start_lon], tooltip="Sraz").add_to(m)
        st_folium(m, height=250, width=700, key=f"m_{unique_key}", returned_objects=[])

    st.markdown(f"#### 👥 Zapsaní ({len(lidi)})")
    if not lidi.empty:
        h1, h2, h3, h4, h5, h6 = st.columns([0.4, 2.0, 1.5, 1.2, 0.6, 0.5]) 
        h1.markdown("<b style='color:#666'>#</b>", unsafe_allow_html=True)
        h2.markdown("<b>Jméno</b>", unsafe_allow_html=True)
        h3.markdown("<b>Poznámka</b>", unsafe_allow_html=True)
        h4.markdown("<b>Doprava</b>", unsafe_allow_html=True)
        h5.markdown("<b>Ubyt</b>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 5px 0 10px 0; border-top: 1px solid rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
        
        for i, (_, row) in enumerate(lidi.iterrows()):
             bg = "rgba(255, 255, 255, 0.05)" if i % 2 == 0 else "transparent"
             pad = "10px 5px 25px 5px !important" if i % 2 == 0 else "0px 5px 10px 5px !important"
             
             with stylable_container(key=f"r_{unique_key}_{i}", css_styles=f"{{background-color: {bg}; border-radius: 6px; padding: {pad}; margin-bottom: 2px; display: flex; align-items: center; min-height: 40px; color: #e0e0e0;}}"):
                 
                 je_k_smazani = (delete_key_state in st.session_state) and (st.session_state[delete_key_state] == row['jméno'])
                 
                 if je_k_smazani:
                     col_warn, col_yes, col_no = st.columns([3, 1, 1], vertical_alignment="center")
                     col_warn.warning(f"Smazat: **{row['jméno']}**?", icon="⚠️")
                     with stylable_container(key=f"btn_yes_c_{i}", css_styles="button {background-color: rgba(220, 38, 38, 0.3) !important; border: 1px solid #DC2626 !important; color: white !important;}"):
                         if col_yes.button("ANO", key=f"yes_{unique_key}_{i}"):
                             handle_driver_removal(conn, akce_id_str, row['jméno'])
                             df_curr = data_manager.load_prihlasky()
                             df_curr = df_curr[~((df_curr['id_akce'] == akce_id_str) & (df_curr['jméno'] == row['jméno']))]
                             conn.update(worksheet="prihlasky", data=df_curr)
                             del st.session_state[delete_key_state]
                             st.rerun()
                     if col_no.button("ZPĚT", key=f"no_{unique_key}_{i}"):
                         del st.session_state[delete_key_state]
                         st.rerun()
                 else:
                     c1, c2, c3, c4, c5, c6 = st.columns([0.4, 2.0, 1.5, 1.2, 0.6, 0.6], vertical_alignment="center")
                     
                     c1.write(f"{i+1}.")
                     c2.markdown(f"**{row['jméno']}**")
                     c3.caption(row.get('poznámka', ''))
                     
                     dopr = str(row.get('doprava', ''))
                     btn_label = dopr if dopr else "➕"
                     
                     btn_color, btn_bg, btn_border = "#ccc", "rgba(255,255,255,0.05)", "1px solid rgba(255,255,255,0.2)"
                     if "Řidič" in dopr: 
                         btn_color, btn_bg, btn_border = "#39ff14", "rgba(57, 255, 20, 0.1)", "1px solid #39ff14"
                     elif "Spolujízda" in dopr or "Jedu s" in dopr: 
                         btn_color, btn_bg, btn_border = "#00f3ff", "rgba(0, 243, 255, 0.1)", "1px solid #00f3ff"
                         btn_label = dopr.replace("Spolujízda: ", "🚙 ").replace("Jedu s: ", "🚙 ")
                     elif "Chci" in dopr: 
                         btn_color, btn_bg, btn_border = "#ff073a", "rgba(255, 7, 58, 0.1)", "1px solid #ff073a"
                         btn_label = "🙋‍♂️ Chci"

                     transport_css = styles.get_transport_css(btn_bg, btn_color, btn_border)
                     with stylable_container(key=f"cont_btn_d_{unique_key}_{i}", css_styles=transport_css):
                         if c4.button(btn_label, key=f"btn_row_d_{unique_key}_{i}", use_container_width=True):
                             show_doprava_dialog(akce_id_str, akce.get('název', ''), akce['datum'].strftime('%d.%m.'), row['jméno'], None, None)

                     c5.write(row.get('ubytování', ''))

                     if not je_po_deadlinu:
                         delete_css = styles.get_delete_css()
                         with stylable_container(key=f"del_btn_container_{unique_key}_{i}", css_styles=delete_css):
                             if c6.button("🗑️", key=f"del_{unique_key}_{i}", use_container_width=False):
                                 st.session_state[delete_key_state] = row['jméno']
                                 st.rerun()
                                 
    export_admin_section(lidi, akce.get('název', ''), unique_key)
