import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.title("🕵️ Diagnostika Tabulky")

# Připojení
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    st.info("Zkouším načíst první list v tabulce (ať se jmenuje jakkoliv)...")
    
    # read() bez parametrů načte první list, co najde
    df = conn.read(ttl=0)
    
    st.success("✅ Připojení k souboru FUNGUJE!")
    st.write("Tohle jsem našel v prvním listu:")
    st.dataframe(df)
    
    st.warning("Pokud tohle vidíš, tak Secrets jsou nastavené správně.")
    st.write("Problém je tedy POUZE v názvu listu 'akce' vs. to, co máš v Excelu.")

except Exception as e:
    st.error("❌ Stále chyba připojení.")
    st.code(str(e))
    st.write("Pokud je chyba 404, zkontroluj, zda URL v Secrets neobsahuje na konci '/edit#gid=...'")
