import streamlit as st
import requests
import re
import base64
import os
import pandas as pd
from datetime import datetime, date, timedelta
from urllib.parse import urlparse, parse_qs
from io import BytesIO
from streamlit_extras.stylable_container import stylable_container
import streamlit.components.v1 as components
import data_manager

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
def show_doprava_dialog(akce_id, nazev_akce, datum_akce, pre_jmeno, in_poznamka, in_ubytovani):
    """
    Modální okno pro řešení dopravy.
    Nyní přijímá i poznámku a ubytování z hlavního formuláře, aby se vše uložilo naráz.
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
    
    # Pokud jméno nebylo vybráno venku, dáme možnost ho vybrat tady
    idx_jmeno = None
    seznam_jmen = data_manager.load_jmena()
    if pre_jmeno and pre_jmeno in seznam_jmen:
        idx_jmeno = seznam_jmen.index(pre_jmeno)

    vybrane_jmeno = st.selectbox("Kdo jsi?", options=seznam_jmen, index=idx_jmeno, key="diag_jmeno", disabled=(pre_jmeno is not None))
    
    st.markdown("---")

    if vybrane_jmeno:
        # Zjištění stavu
        aktualni_zaznam = lidi_akce[lidi_akce['jméno'] == vybrane_jmeno]
        stav_dopravy = "Nevyřešeno"
        id_auto_curr = ""
        
        if not aktualni_zaznam.empty:
            dopr_txt = str(aktualni_zaznam.iloc[0]['doprava'])
            id_auto_curr = str(aktualni_zaznam.iloc[0].get('id_auto', ''))
            if "Řidič" in dopr_txt: stav_dopravy = "driver"
            elif "Jedu s" in dopr_txt or "Spolujízda" in dopr_txt: stav_dopravy = "passenger"
            elif "Chci" in dopr_txt: stav_dopravy = "waiting"
        
        role = st.radio("Možnosti dopravy:", 
                 ["Nic (Zrušit dopravu)", "🚙 Nabízím auto (Řidič)", "🙋‍♂️ Hledám odvoz (Pasažér)"],
                 index=1 if stav_dopravy == "driver" else (2 if stav_dopravy in ["passenger", "waiting"] else 0)
        )
        
        st.markdown("<br>", unsafe_allow_html=True)

        # --- A) ŘIDIČ ---
        if "Nabízím" in role:
            c1, c2 = st.columns(2)
            moje_auto = auta_akce[auta_akce['ridic'] == vybrane_jmeno]
            def_kap, def_cas, def_misto = 4, "17:00", "Loděnice"
            
            if not moje_auto.empty:
                def_kap = int(moje_auto.iloc[0]['kapacita'])
                def_cas = str(moje_auto.iloc[0]['cas'])
                def_misto = str(moje_auto.iloc[0]['misto'])

            novy_kap = c1.number_input("Kapacita", 1, 9, def_kap)
            novy_cas = c2.text_input("Čas", def_cas)
            novy_misto = st.text_input("Místo", def_misto)
            
            if st.button("💾 Založit auto a ZAPSAT SE", type="primary", use_container_width=True):
                # 1. Auto
                df_clean_auta = df_auta[~((df_auta['id_akce'] == akce_id) & (df_auta['ridic'] == vybrane_jmeno))]
                nove_auto_row = pd.DataFrame([{
                    "id_akce": akce_id, "ridic": vybrane_jmeno, 
                    "kapacita": novy_kap, "cas": novy_cas, "misto": novy_misto, "poznamka": ""
                }])
                conn.update(worksheet="auta", data=pd.concat([df_clean_auta, nove_auto_row], ignore_index=True))
                
                # 2. Přihláška (Použijeme poznámku zvenku!)
                df_clean_lidi = df_lidi[~((df_lidi['id_akce'] == akce_id) & (df_lidi['jméno'] == vybrane_jmeno))]
                
                novy_clovek = pd.DataFrame([{
                    "id_akce": akce_id, "název": nazev_akce, "jméno": vybrane_jmeno,
                    "poznámka": in_poznamka, # <--- TADY SE POUŽIJE TO Z HLAVNÍ STRÁNKY
                    "doprava": "Řidič 🚙", 
                    "ubytování": "Ano 🛏️" if in_ubytovani else "",
                    "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "id_auto": ""
                }])
                conn.update(worksheet="prihlasky", data=pd.concat([df_clean_lidi, novy_clovek], ignore_index=True))
                st.rerun()

        # --- B) PASAŽÉR ---
        elif "Hledám" in role:
            options_auta = ["⏳ Čekací listina (zatím nemám auto)"]
            mapa_aut = {"⏳ Čekací listina (zatím nemám auto)": ""}
            idx_select = 0
            
            for i, (_, row_auto) in enumerate(auta_akce.iterrows()):
                ridic = str(row_auto['ridic'])
                if ridic == vybrane_jmeno: continue
                
                kap = int(row_auto['kapacita'])
                obs = obsazenost.get(ridic, 0)
                volno = kap - 1 - obs 
                label = f"🚙 {ridic} ({volno} volných) - {row_auto['cas']}"
                if volno <= 0: label = f"❌ {ridic} (PLNO)"
                
                options_auta.append(label)
                mapa_aut[label] = ridic
                if id_auto_curr == ridic: idx_select = len(options_auta) - 1

            vybrane_label = st.selectbox("Ke komu?", options_auta, index=idx_select)
            target_ridic = mapa_aut[vybrane_label]
            
            if st.button("💾 Potvrdit jízdu a ZAPSAT SE", type="primary", use_container_width=True):
                df_clean_lidi = df_lidi[~((df_lidi['id_akce'] == akce_id) & (df_lidi['jméno'] == vybrane_jmeno))]
                dopr_text = f"Spolujízda: {target_ridic}" if target_ridic else "Chci odvoz 🙋‍♂️"
                
                novy_clovek = pd.DataFrame([{
                    "id_akce": akce_id, "název": nazev_akce, "jméno": vybrane_jmeno,
                    "poznámka": in_poznamka, # <--- POUŽITÍ POZNÁMKY
                    "doprava": dopr_text, 
                    "ubytování": "Ano 🛏️" if in_ubytovani else "",
                    "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "id_auto": target_ridic
                }])
                
                if stav_dopravy == "driver": # Úklid pokud byl řidič
                    conn.update(worksheet="auta", data=df_auta[~((df_auta['id_akce'] == akce_id) & (df_auta['ridic'] == vybrane_jmeno))])
                
                conn.update(worksheet="prihlasky", data=pd.concat([df_clean_lidi, novy_clovek], ignore_index=True))
                st.rerun()

        # --- C) ZRUŠIT ---
        else:
            if st.button("🗑️ Smazat dopravu (Zůstat přihlášen)", use_container_width=True):
                df_clean_lidi = df_lidi[~((df_lidi['id_akce'] == akce_id) & (df_lidi['jméno'] == vybrane_jmeno))]
                
                novy_clovek = pd.DataFrame([{
                    "id_akce": akce_id, "název": nazev_akce, "jméno": vybrane_jmeno,
                    "poznámka": in_poznamka, 
                    "doprava": "", 
                    "ubytování": "Ano 🛏️" if in_ubytovani else "",
                    "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "id_auto": ""
                }])
                
                if stav_dopravy == "driver":
                    conn.update(worksheet="auta", data=df_auta[~((df_auta['id_akce'] == akce_id) & (df_auta['ridic'] == vybrane_jmeno))])
                
                conn.update(worksheet="prihlasky", data=pd.concat([df_clean_lidi, novy_clovek], ignore_index=True))
                st.rerun()
