import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import timedelta, date
import difflib

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
    Funkce pro přihlášení.
    VYLEPŠENÍ:
    1. Kontrola Deadlinu.
    2. Inteligentní oprava jména podle databáze (Pepa -> Pepu -> Pepa Vopršálek).
    3. Automatická Velká Písmena.
    """
    # 1. OPRAVA JMÉNA (Autocorrect)
    # Nejdřív základní formátování: odstranit mezery, velká písmena
    clean_name = str(user_name).strip().title()
    final_name = clean_name
    
    # Načteme známá jména
    known_names = load_jmena()
    
    if known_names:
        # Zkusíme najít nejpodobnější jméno v DB (řeší překlepy i skloňování)
        # cutoff=0.6 znamená, že shoda musí být aspoň 60%
        matches = difflib.get_close_matches(clean_name, known_names, n=1, cutoff=0.6)
        
        if matches:
            final_name = matches[0] # Našli jsme shodu! (např. "Pepa Vopršálek")
        else:
            # Pokud nenašel přesnou shodu, zkusíme alespoň najít, jestli uživatel nezadal jen "Pepa"
            # a v DB je "Pepa Vopršálek"
            partial_matches = [name for name in known_names if clean_name in name]
            if len(partial_matches) == 1:
                final_name = partial_matches[0]

    # 2. Hledání akce (Logika zůstává)
    df_akce = load_akce()
    target_event = df_akce[df_akce['id'] == str(event_name_or_id)]
    
    if target_event.empty:
        mask = df_akce['název'].str.contains(str(event_name_or_id), case=False, na=False)
        target_event = df_akce[mask]

    if target_event.empty:
        return f"❌ Akci '{event_name_or_id}' jsem nenašel."
    
    if len(target_event) > 1:
        names = ", ".join(target_event['název'].tolist())
        return f"⚠️ Našel jsem více akcí: {names}. Buď konkrétnější."

    row_akce = target_event.iloc[0]
    akce_id = str(row_akce['id'])
    akce_nazev = row_akce['název']

    # 3. Deadline Check
    today = date.today()
    deadline = row_akce.get('deadline')
    if isinstance(deadline, pd.Timestamp): deadline = deadline.date()
    
    if deadline and today > deadline:
        return f"⛔ Pozdě! Deadline pro '{akce_nazev}' byl {deadline.strftime('%d.%m.')}."

    # 4. Kontrola duplicit
    df_prihlasky = load_prihlasky()
    if not df_prihlasky.empty:
        is_there = ((df_prihlasky['id_akce'] == akce_id) & (df_prihlasky['jméno'] == final_name)).any()
        if is_there:
            return f"ℹ️ {final_name} už je na akci '{akce_nazev}'."

    # 5. Zápis
    conn = get_connection()
    novy_zaznam = pd.DataFrame([{
        "id_akce": akce_id, 
        "název": akce_nazev, 
        "jméno": final_name,  # Používáme opravené jméno
        "poznámka": note, 
        "doprava": transport, 
        "ubytování": "",
        "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "id_auto": ""
    }])
    
    try:
        updated_df = pd.concat([df_prihlasky, novy_zaznam], ignore_index=True)
        conn.update(worksheet="prihlasky", data=updated_df)
        
        # Pokud jméno nebylo v DB, přidáme ho tam (aby příště fungoval našeptávač)
        if final_name not in known_names:
             try:
                j_df = conn.read(worksheet="jmena")
                conn.update(worksheet="jmena", data=pd.concat([j_df, pd.DataFrame([{"jméno": final_name}])], ignore_index=True))
             except: pass
             
        return f"✅ Hotovo! Přihlásil jsem '{final_name}' na '{akce_nazev}'."
    except Exception as e:
        return f"❌ Chyba zápisu: {e}"
        
def sign_out_user(event_name_or_id: str, user_name: str) -> str:
    """Odhlásí uživatele (Také by nemělo jít po deadlinu, ale často se to toleruje - nechám na tobě)."""
    # 1. Identifikace akce
    df_akce = load_akce()
    target_event = df_akce[df_akce['id'] == str(event_name_or_id)]
    
    if target_event.empty:
        mask = df_akce['název'].str.contains(str(event_name_or_id), case=False, na=False)
        target_event = df_akce[mask]

    if target_event.empty:
        return f"❌ Akci '{event_name_or_id}' nemůžu najít."
    
    row_akce = target_event.iloc[0]
    akce_id = str(row_akce['id'])
    akce_nazev = row_akce['název']

    # === DEADLINE CHECK PRO ODHLÁŠENÍ (Volitelné) ===
    # Pokud chceš zakázat i odhlašování po termínu, odkomentuj toto:
    """
    today = date.today()
    deadline = row_akce.get('deadline')
    if isinstance(deadline, pd.Timestamp): deadline = deadline.date()
    if deadline and today > deadline:
         return f"⛔ Už je po deadlinu! Z '{akce_nazev}' se sám neodhlásíš. Napiš trenérovi."
    """

    # 2. Načtení a Smazání
    df_prihlasky = load_prihlasky()
    mask_user = (df_prihlasky['id_akce'] == akce_id) & (df_prihlasky['jméno'] == user_name)
    
    if not mask_user.any():
        return f"ℹ️ Uživatel '{user_name}' na akci není."

    df_new = df_prihlasky[~mask_user]
    
    try:
        conn = get_connection()
        conn.update(worksheet="prihlasky", data=df_new)
        return f"✅ Hotovo. Odhlásil jsem '{user_name}' z akce '{akce_nazev}'."
    except Exception as e:
        return f"❌ Chyba při mazání: {e}"

def get_event_info(query: str) -> str:
    df = load_akce()
    mask = df['název'].str.contains(query, case=False, na=False) | df['místo'].str.contains(query, case=False, na=False)
    results = df[mask]
    
    if results.empty:
        return "Žádnou takovou akci nevidím."
    
    output = ""
    for _, row in results.iterrows():
        d = row['datum'].strftime('%d.%m.') if hasattr(row['datum'], 'strftime') else str(row['datum'])
        output += f"📍 {row['název']} ({d}) v {row['místo']}\n"
    return output
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
    
# --- 1. AKCE (Cachujeme, aby kalendář neblikal) ---
# @st.cache_data(ttl=3600) 
def load_akce():
    # print("STAHUJI AKCE Z WEBU...")
    try:
        df_akce = pd.read_csv(URL_AKCE)
        
        # 1. Základní data a časy
        df_akce['datum'] = pd.to_datetime(df_akce['datum'], dayfirst=True, errors='coerce').dt.date
        
        if 'datum_do' in df_akce.columns:
            df_akce['datum_do'] = pd.to_datetime(df_akce['datum_do'], dayfirst=True, errors='coerce').dt.date
            df_akce['datum_do'] = df_akce['datum_do'].fillna(df_akce['datum'])
        else:
            df_akce['datum_do'] = df_akce['datum']
            
        df_akce = df_akce.dropna(subset=['datum'])
        
        # 2. Hlavní Deadline
        df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], dayfirst=True, errors='coerce').dt.date
        
        def get_deadline(row):
            if pd.isna(row['deadline']):
                return row['datum'] - timedelta(days=14)
            return row['deadline']
        
        df_akce['deadline'] = df_akce.apply(get_deadline, axis=1)

        # === 3. DEADLINE UBYTOVÁNÍ (NOVÉ) ===
        # Pokud sloupec v tabulce neexistuje, vytvoříme ho
        if 'deadline_ubytovani' not in df_akce.columns:
            df_akce['deadline_ubytovani'] = pd.NaT

        df_akce['deadline_ubytovani'] = pd.to_datetime(df_akce['deadline_ubytovani'], dayfirst=True, errors='coerce').dt.date

        # Logika: Pokud není vyplněn deadline ubytování, platí hlavní deadline
        def get_accom_deadline(row):
            if pd.isna(row['deadline_ubytovani']):
                return row['deadline']
            return row['deadline_ubytovani']

        df_akce['deadline_ubytovani'] = df_akce.apply(get_accom_deadline, axis=1)
        # ====================================
        
        if 'id' in df_akce.columns:
            df_akce['id'] = df_akce['id'].astype(str).str.replace(r'\.0$', '', regex=True)
            
        return df_akce
    except Exception as e:
        # print(f"Chyba load_akce: {e}")
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
