import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import timedelta, date

# ... Konstanty (ID, URL) zůstávají stejné ...
SHEET_ID = "1lW6DpUQBSm5heSO_HH9lDzm0x7t1eo8dn6FpJHh2y6U"
URL_AKCE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=akce"
URL_PRIHLASKY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=prihlasky"
URL_JMENA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=jmena"

def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

# --- 1. AKCE (Cachujeme, aby kalendář neblikal) ---
@st.cache_data(ttl=3600) 
def load_akce():
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

# --- 3. JMÉNA (Taky raději bez cache, pro jistotu, nebo s cachem) ---
@st.cache_data(ttl=3600)
def load_jmena():
    try:
        df = pd.read_csv(URL_JMENA)
        return sorted(df['jméno'].dropna().unique().tolist())
    except: return []
