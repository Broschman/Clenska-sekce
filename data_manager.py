import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import timedelta, date

# ... Konstanty (ID, URL) zůstávají stejné ...
SHEET_ID = "1LaojGRVAGtWmfQZ4DfDXDyiZs1TO7Fck4HRgT8Pyook"
URL_AKCE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=akce"
URL_PRIHLASKY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=prihlasky"
URL_JMENA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=jmena"
URL_AUTA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=auta"

def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

# --- PŘIDEJ DO data_manager.py ---
from datetime import datetime

def sign_up_user(event_name_or_id: str, user_name: str, note: str = "", transport: str = "") -> str:
    """
    Funkce pro přihlášení uživatele na akci. Bot ji bude volat.
    
    Args:
        event_name_or_id: ID akce nebo přibližný název.
        user_name: Jméno člena (musí být přesné, nebo ho zkusíme najít).
        note: Poznámka k přihlášce.
        transport: Preferovaná doprava (text).
    """
    # 1. Načíst akce a najít tu správnou
    df_akce = load_akce()
    
    # Zkusíme najít podle ID
    target_event = df_akce[df_akce['id'] == str(event_name_or_id)]
    
    # Pokud nenajdeme podle ID, zkusíme full-text v názvu (fuzzy search pro bota)
    if target_event.empty:
        # Hledáme case-insensitive
        mask = df_akce['název'].str.contains(str(event_name_or_id), case=False, na=False)
        target_event = df_akce[mask]

    if target_event.empty:
        return f"❌ Akci '{event_name_or_id}' jsem nenašel. Zkus být přesnější."
    
    if len(target_event) > 1:
        found_names = ", ".join(target_event['název'].tolist())
        return f"⚠️ Našel jsem více akcí: {found_names}. Upřesni to prosím."

    # Máme jednu akci
    row_akce = target_event.iloc[0]
    akce_id = str(row_akce['id'])
    akce_nazev = row_akce['název']

    # 2. Načíst přihlášky a zkontrolovat duplicitu
    df_prihlasky = load_prihlasky()
    
    # Check, jestli už tam není
    if not df_prihlasky.empty:
        is_there = ((df_prihlasky['id_akce'] == akce_id) & (df_prihlasky['jméno'] == user_name)).any()
        if is_there:
            return f"ℹ️ {user_name} už je na akci '{akce_nazev}' přihlášený."

    # 3. Zápis do DB
    conn = get_connection()
    novy_zaznam = pd.DataFrame([{
        "id_akce": akce_id, 
        "název": akce_nazev, 
        "jméno": user_name,
        "poznámka": note, 
        "doprava": transport, 
        "ubytování": "",
        "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "id_auto": ""
    }])
    
    try:
        updated_df = pd.concat([df_prihlasky, novy_zaznam], ignore_index=True)
        conn.update(worksheet="prihlasky", data=updated_df)
        return f"✅ Hotovo! Přihlásil jsem '{user_name}' na '{akce_nazev}'."
    except Exception as e:
        return f"❌ Chyba při zápisu: {e}"

def get_event_info(query: str) -> str:
    """
    Najde informace o akci podle dotazu (pro bota, aby nemusel číst celý kontext, pokud je to složité).
    """
    df = load_akce()
    # Jednoduchý filtr
    mask = df['název'].str.contains(query, case=False, na=False) | df['místo'].str.contains(query, case=False, na=False)
    results = df[mask]
    
    if results.empty:
        return "Žádnou takovou akci nevidím."
    
    output = ""
    for _, row in results.iterrows():
        output += f"📍 {row['název']} ({row['datum']}) v {row['místo']}\n"
    return output

# --- PŘIDAT NA KONEC data_manager.py ---

def sign_out_user(event_name_or_id: str, user_name: str) -> str:
    """
    Odhlásí uživatele z akce (smaže záznam z Google Sheets).
    """
    # 1. Identifikace akce (stejná logika jako u sign_up)
    df_akce = load_akce()
    target_event = df_akce[df_akce['id'] == str(event_name_or_id)]
    
    if target_event.empty:
        mask = df_akce['název'].str.contains(str(event_name_or_id), case=False, na=False)
        target_event = df_akce[mask]

    if target_event.empty:
        return f"❌ Akci '{event_name_or_id}' nemůžu najít. Zkus přesnější název."
    
    # Bereme první shodu
    row_akce = target_event.iloc[0]
    akce_id = str(row_akce['id'])
    akce_nazev = row_akce['název']

    # 2. Načtení přihlášek
    df_prihlasky = load_prihlasky()
    
    if df_prihlasky.empty:
         return f"ℹ️ Na akci '{akce_nazev}' nikdo není, takže tě nemůžu odhlásit."

    # 3. Kontrola, jestli tam uživatel je
    mask_user = (df_prihlasky['id_akce'] == akce_id) & (df_prihlasky['jméno'] == user_name)
    
    if not mask_user.any():
        return f"ℹ️ Uživatel '{user_name}' na akci '{akce_nazev}' vůbec není."

    # 4. Smazání (Filtrujeme vše KROMĚ daného uživatele na dané akci)
    df_new = df_prihlasky[~mask_user]
    
    try:
        conn = get_connection()
        conn.update(worksheet="prihlasky", data=df_new)
        return f"✅ Hotovo. Odhlásil jsem '{user_name}' z akce '{akce_nazev}'."
    except Exception as e:
        return f"❌ Chyba při mazání: {e}"

# --- 1. AKCE (Cachujeme, aby kalendář neblikal) ---
# @st.cache_data(ttl=3600) 
def load_akce():
    print("STAHUJI AKCE Z WEBU...")
    try:
        df_akce = pd.read_csv(URL_AKCE)
        # ... (zbytek logiky preprocessingu akcí, stejné jako dřív) ...
        df_akce['datum'] = pd.to_datetime(df_akce['datum'], dayfirst=True, errors='coerce').dt.date
        if 'datum_do' in df_akce.columns:
            df_akce['datum_do'] = pd.to_datetime(df_akce['datum_do'], dayfirst=True, errors='coerce').dt.date
            df_akce['datum_do'] = df_akce['datum_do'].fillna(df_akce['datum'])
        else:
            df_akce['datum_do'] = df_akce['datum']
        df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], dayfirst=True, errors='coerce').dt.date
        df_akce = df_akce.dropna(subset=['datum'])
        def get_deadline(row):
            return row['datum'] - timedelta(days=14) if pd.isna(row['deadline']) else row['deadline']
        df_akce['deadline'] = df_akce.apply(get_deadline, axis=1)
        if 'id' in df_akce.columns:
            df_akce['id'] = df_akce['id'].astype(str).str.replace(r'\.0$', '', regex=True)
        return df_akce
    except:
        return pd.DataFrame()

# --- 2. PŘIHLÁŠKY (BEZ CACHE = ŽIVÉ ČTENÍ) ---
# Tady jsme smazali @st.cache_data. Pokaždé se načtou čerstvá data.
def load_prihlasky():
    try:
        df = pd.read_csv(URL_PRIHLASKY)
        if 'doprava' not in df.columns: df['doprava'] = ""
        if 'ubytování' not in df.columns: df['ubytování'] = ""
        if 'id_akce' not in df.columns: df['id_akce'] = ""
        df['id_akce'] = df['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
        return df
    except:
        return pd.DataFrame(columns=["id_akce", "název", "jméno", "poznámka", "doprava", "ubytování", "čas zápisu"])
def load_prihlasky_pro_akci(id_akce):
    """Stáhne přihlášky jen pro konkrétní akci. To je mnohem rychlejší."""
    try:
        # Tady použijeme SQL-like query jazyk Google Sheets pro filtraci přímo na serveru Googlu!
        # Tím se stáhne jen pár řádků místo tisíců.
        query = f"select * where A = '{id_akce}'" # Předpokládáme, že sloupec A je id_akce. Pokud ne, musíme to upravit.
        # Ale pro jistotu (protože nevíme písmena sloupců) stáhneme vše a vyfiltrujeme v Pythonu, 
        # pokud je ten soubor malý (do 5000 řádků je to v pohodě).
        
        # Varianta A (stále stahuje vše, ale v separátní funkci):
        df = load_prihlasky() # Použijeme tu existující funkci
        return df[df['id_akce'] == str(id_akce)]
    except:
        return pd.DataFrame()
# --- 3. JMÉNA ---
def load_jmena():
    try:
        df = pd.read_csv(URL_JMENA)
        return sorted(df['jméno'].dropna().unique().tolist())
    except: return []

# --- 4. AUTA (NOVÉ) ---
def load_auta():
    try:
        df = pd.read_csv(URL_AUTA)
        # Ošetření, aby sloupce existovaly, i když je list prázdný
        expected_cols = ["id_akce", "ridic", "kapacita", "cas", "misto", "poznamka"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        
        df['id_akce'] = df['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
        return df
    except Exception as e:
        print(f"Chyba načítání aut: {e}")
        return pd.DataFrame(columns=["id_akce", "ridic", "kapacita", "cas", "misto", "poznamka"])
