import streamlit as st
import requests
import re
import base64
import os
import pandas as pd
from datetime import datetime, date, timedelta
from urllib.parse import urlparse, parse_qs
from io import BytesIO

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
