import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import timedelta, date

# Konstanty
SHEET_ID = "1lW6DpUQBSm5heSO_HH9lDzm0x7t1eo8dn6FpJHh2y6U"
URL_AKCE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=akce"
URL_PRIHLASKY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=prihlasky"
URL_JMENA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=jmena"
URL_NAVRHY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=navrhy"

def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

# --- 1. AKCE (Mění se málo -> Cache na 1 hodinu) ---
@st.cache_data(ttl=3600)
def load_akce():
    try:
        df_akce = pd.read_csv(URL_AKCE)
        df_akce['datum'] = pd.to_datetime(df_akce['datum'], dayfirst=True, errors='coerce').dt.date
        if 'datum_do' in df_akce.columns:
            df_akce['datum_do'] = pd.to_datetime(df_akce['datum_do'], dayfirst=True, errors='coerce').dt.date
            df_akce['datum_do'] = df_akce['datum_do'].fillna(df_akce['datum'])
        else:
            df_akce['datum_do'] = df_akce['datum']
            
        df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], dayfirst=True, errors='coerce').dt.date
        df_akce = df_akce.dropna(subset=['datum'])
        
        def get_deadline(row):
            if pd.isna(row['deadline']):
                return row['datum'] - timedelta(days=14)
            return row['deadline']
        df_akce['deadline'] = df_akce.apply(get_deadline, axis=1)
        
        if 'id' in df_akce.columns:
            df_akce['id'] = df_akce['id'].astype(str).str.replace(r'\.0$', '', regex=True)
        return df_akce
    except Exception as e:
        # st.error je lepší volat v main app, tady jen vrátíme prázdné
        return pd.DataFrame()

# --- 2. PŘIHLÁŠKY (Mění se často -> Cache na 60 vteřin) ---
@st.cache_data(ttl=60)
def load_prihlasky():
    try:
        df_prihlasky = pd.read_csv(URL_PRIHLASKY)
        if 'doprava' not in df_prihlasky.columns: df_prihlasky['doprava'] = ""
        if 'ubytování' not in df_prihlasky.columns: df_prihlasky['ubytování'] = ""
        if 'id_akce' not in df_prihlasky.columns: df_prihlasky['id_akce'] = ""
        df_prihlasky['id_akce'] = df_prihlasky['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
        return df_prihlasky
    except:
        return pd.DataFrame(columns=["id_akce", "název", "jméno", "poznámka", "doprava", "ubytování", "čas zápisu"])

# --- 3. JMÉNA (Mění se málo -> Cache na 1 hodinu) ---
@st.cache_data(ttl=3600)
def load_jmena():
    try:
        df_jmena = pd.read_csv(URL_JMENA)
        return sorted(df_jmena['jméno'].dropna().unique().tolist())
    except:
        return []

# --- FUNKCE PRO SMAZÁNÍ CACHE (Nutné po zápisu!) ---
def refresh_prihlasky():
    """Smaže cache pouze pro funkci load_prihlasky. Kalendář zůstane v paměti."""
    load_prihlasky.clear()
