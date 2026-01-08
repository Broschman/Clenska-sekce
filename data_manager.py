import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Tvé ID sheetu
SHEET_ID = "1lW6DpUQBSm5heSO_HH9lDzm0x7t1eo8dn6FpJHh2y6U"

# URL adresy (stejné jako u tebe)
URL_AKCE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=akce"
URL_PRIHLASKY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=prihlasky"
URL_JMENA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=jmena"
URL_NAVRHY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=navrhy"

def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

# --- ZRYCHLENÍ: Cachujeme Akce na 60 minut ---
@st.cache_data(ttl=3600)
def load_akce():
    try:
        df_akce = pd.read_csv(URL_AKCE)
        # Tvůj původní preprocessing kód:
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
        st.error(f"Chyba načítání akcí: {e}")
        return pd.DataFrame()

# --- ZRYCHLENÍ: Cachujeme Přihlášky (s možností refresh) ---
@st.cache_data(ttl=60)
def load_prihlasky():
    try:
        df = pd.read_csv(URL_PRIHLASKY)
        if 'doprava' not in df.columns: df['doprava'] = ""
        if 'ubytování' not in df.columns: df['ubytování'] = "" # Přidal jsem pro jistotu
        if 'id_akce' not in df.columns: df['id_akce'] = ""
        df['id_akce'] = df['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
        return df
    except:
        return pd.DataFrame(columns=["id_akce", "název", "jméno", "poznámka", "doprava", "čas zápisu"])

@st.cache_data(ttl=3600)
def load_jmena():
    try:
        df = pd.read_csv(URL_JMENA)
        return sorted(df['jméno'].dropna().unique().tolist())
    except: return []

# Funkce pro vymazání cache po zápisu
def clear_cache():
    st.cache_data.clear()
