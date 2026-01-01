import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. NASTAVENÍ APLIKACE ---
st.set_page_config(page_title="OB Klub - Termínovka", page_icon="🌲")
st.title("🌲 Kalendář akcí a přihlášky")

# --- 2. PŘÍMÉ NAČTENÍ DAT (BEZ SECRETS) ---
# Tvoje ID tabulky
SHEET_ID = "1lW6DpUQBSm5heSO_HH9lDzm0x7t1eo8dn6FpJHh2y6U"

# Magické odkazy, které stahují data jako CSV přímo podle názvu listu
# Tohle funguje mnohem spolehlivěji než konektory
url_akce = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=akce"
url_prihlasky = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=prihlasky"

try:
    # Načteme data přímo přes Pandas
    df_akce = pd.read_csv(url_akce)
    df_prihlasky = pd.read_csv(url_prihlasky)

    # --- 3. ÚPRAVA DAT ---
    # Převedeme data na správný formát
    df_akce['datum'] = pd.to_datetime(df_akce['datum'], dayfirst=True, errors='coerce').dt.date
    df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], dayfirst=True, errors='coerce').dt.date
    
    # Vyhodíme prázdné řádky
    df_akce = df_akce.dropna(subset=['datum'])
    df_akce = df_akce.sort_values(by='datum')

except Exception as e:
    st.error("❌ A je to tady zase. Chyba při načítání dat.")
    st.write(f"Detail chyby: {e}")
    st.warning("Jsi si jistý, že máš v Google Tabulce nastaveno 'Všichni s odkazem'?")
    st.stop()

# --- 4. ZOBRAZENÍ KALENDÁŘE ---
dnes = datetime.now().date()

if df_akce.empty:
    st.info("Tabulka je prázdná nebo se nepodařilo načíst řádky.")

for index, akce in df_akce.iterrows():
    je_po_deadlinu = dnes > akce['deadline']
    ikona = "🔒" if je_po_deadlinu else "✅"
    
    label = f"{ikona} {akce['datum'].strftime('%d.%m.')} | {akce['název']}"
    
    with st.expander(label):
        st.markdown(f"**📍 Místo:** {akce['místo']}")
        
        # Ošetření popisu
        popis = akce['popis'] if 'popis' in akce and pd.notna(akce['popis']) else "Bez popisu."
        st.info(f"📝 **Popis:** {popis}")
        
        # Seznam přihlášených
        if 'název' in df_prihlasky.columns:
            lidi = df_prihlasky[df_prihlasky['název'] == akce['název']]
            st.write(f"**👥 Přihlášeno: {len(lidi)}**")
            if not lidi.empty:
                st.table(lidi[['jméno', 'poznámka']])
        
        st.divider()
        
        if not je_po_deadlinu:
             st.write("#### ✍️ Chci se přihlásit")
             st.info("ℹ️ Pro zprovoznění tlačítka 'Odeslat' musíme nejdřív vidět, že funguje čtení kalendáře.")
        else:
            st.error("Termín přihlášek vypršel.")

st.write("---")
st.caption("Verze: Direct CSV Read")
