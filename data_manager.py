import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import timedelta, date

# Konstanty
SHEET_ID = "1lW6DpUQBSm5heSO_HH9lDzm0x7t1eo8dn6FpJHh2y6U"
URL_AKCE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=akce"
URL_PRIHLASKY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=prihlasky"
URL_JMENA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=jmena"

def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Stáhne a zpracuje všechna data (Akce, Přihlášky, Jména)"""
    # 1. Akce
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
    except Exception as e:
        st.error(f"Chyba akce: {e}")
        df_akce = pd.DataFrame()

    # 2. Přihlášky
    try:
        df_prihlasky = pd.read_csv(URL_PRIHLASKY)
        if 'doprava' not in df_prihlasky.columns: df_prihlasky['doprava'] = ""
        if 'ubytování' not in df_prihlasky.columns: df_prihlasky['ubytování'] = ""
        if 'id_akce' not in df_prihlasky.columns: df_prihlasky['id_akce'] = ""
        df_prihlasky['id_akce'] = df_prihlasky['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
    except:
        df_prihlasky = pd.DataFrame(columns=["id_akce", "název", "jméno", "poznámka", "doprava", "ubytování", "čas zápisu"])

    # 3. Jména
    try:
        df_jmena = pd.read_csv(URL_JMENA)
        seznam_jmen = sorted(df_jmena['jméno'].dropna().unique().tolist())
    except:
        seznam_jmen = []

    return df_akce, df_prihlasky, seznam_jmen
