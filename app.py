import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. NASTAVENÍ ---
st.set_page_config(page_title="OB Klub - Termínovka", page_icon="🌲", layout="centered")
st.title("🌲 Kalendář akcí a přihlášky")

# Připojení pro ZÁPIS (používá údaje ze Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. NAČTENÍ DAT ---
# Používáme ten tvůj osvědčený způsob přes CSV odkaz pro rychlé čtení
SHEET_ID = "1lW6DpUQBSm5heSO_HH9lDzm0x7t1eo8dn6FpJHh2y6U"
url_akce = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=akce"
url_prihlasky = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=prihlasky"

try:
    # Načtení akcí
    df_akce = pd.read_csv(url_akce)
    df_akce['datum'] = pd.to_datetime(df_akce['datum'], dayfirst=True, errors='coerce').dt.date
    df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], dayfirst=True, errors='coerce').dt.date
    df_akce = df_akce.dropna(subset=['datum']).sort_values(by='datum')
    
    # Načtení přihlášek
    try:
        df_prihlasky = pd.read_csv(url_prihlasky)
    except:
        # Kdyby byl list prázdný, vytvoříme prázdnou tabulku
        df_prihlasky = pd.DataFrame(columns=["název", "jméno", "poznámka", "čas zápisu"])

except Exception as e:
    st.error("Chyba při načítání dat. Zkontroluj formát data v Excelu.")
    st.stop()

dnes = datetime.now().date()

# --- 3. VYKRESLENÍ ---
for index, akce in df_akce.iterrows():
    je_po_deadlinu = dnes > akce['deadline']
    ikona = "🔒" if je_po_deadlinu else "✅"
    
    label = f"{ikona} {akce['datum'].strftime('%d.%m.')} | {akce['název']}"
    
    with st.expander(label):
        # Detaily
        st.markdown(f"**📍 Místo:** {akce['místo']}")
        popis = akce['popis'] if 'popis' in akce and pd.notna(akce['popis']) else ""
        st.info(f"📝 {popis}")
        
        # Seznam lidí
        lidi = df_prihlasky[df_prihlasky['název'] == akce['název']]
        st.write(f"**👥 Přihlášeno: {len(lidi)}**")
        if not lidi.empty:
            st.table(lidi[['jméno', 'poznámka']])
        else:
            st.caption("Nikdo není přihlášen.")

        # --- TADY JE TA ZMĚNA: FUNKČNÍ PŘIHLÁŠENÍ ---
        st.divider()
        if not je_po_deadlinu:
            st.write("#### ✍️ Nová přihláška")
            with st.form(key=f"form_{index}", clear_on_submit=True):
                jmeno = st.text_input("Jméno a příjmení")
                poznamka = st.text_input("Poznámka")
                
                odeslat = st.form_submit_button("Odeslat přihlášku")
                
                if odeslat:
                    if jmeno:
                        # 1. Vytvoříme nový řádek
                        novy_radek = pd.DataFrame([{
                            "název": akce['název'],
                            "jméno": jmeno,
                            "poznámka": poznamka,
                            "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }])
                        
                        # 2. Spojíme se starými daty (načteme je pro jistotu čerstvá přes konektor)
                        try:
                            # Tady použijeme konektor jen pro ten moment zápisu
                            aktualni_data = conn.read(worksheet="prihlasky", ttl=0)
                            updated_df = pd.concat([aktualni_data, novy_radek], ignore_index=True)
                            
                            # 3. Zapíšeme zpět
                            conn.update(worksheet="prihlasky", data=updated_df)
                            
                            st.success("✅ Jsi tam! Přihláška uložena.")
                            st.rerun() # Refresh stránky
                        except Exception as e:
                            st.error(f"Chyba zápisu: {e}")
                            st.caption("Zkontroluj, zda má tabulka sdílení 'Editor' pro všechny s odkazem.")
                    else:
                        st.warning("Napiš aspoň jméno.")
        else:
            st.error("Termín přihlášek vypršel.")

st.write("---")
st.caption("Systém OB Klub")
