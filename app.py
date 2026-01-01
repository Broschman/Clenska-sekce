import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="OB Klub - Termínovka", page_icon="🌲", layout="centered")
st.title("🌲 Kalendář akcí a přihlášky")

# --- 2. PŘIPOJENÍ ---
# Používáme oficiální konektor. Aby fungoval zápis, musí být tabulka sdílená jako "Editor".
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Načtení dat (ttl=0 vynutí čerstvá data)
    df_akce = conn.read(worksheet="akce", ttl=0)
    df_prihlasky = conn.read(worksheet="prihlasky", ttl=0)
    
    # Ošetření: Pokud je tabulka prázdná, vytvoříme prázdný DataFrame se správnými sloupci
    if df_prihlasky.empty:
        df_prihlasky = pd.DataFrame(columns=["název", "jméno", "poznámka", "čas zápisu"])

except Exception as e:
    st.error("⚠️ Chyba připojení k Google Tabulce.")
    st.markdown(f"**Detail chyby:** `{e}`")
    st.info("Zkontroluj v Secrets, zda je odkaz správný a tabulka má listy 'akce' a 'prihlasky'.")
    st.stop()

# --- 3. ZPRACOVÁNÍ DAT ---
# Převod datumu - dayfirst=True je důležité pro český formát (25.1. vs 1.25.)
try:
    df_akce['datum'] = pd.to_datetime(df_akce['datum'], dayfirst=True, errors='coerce').dt.date
    df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], dayfirst=True, errors='coerce').dt.date
    
    # Odstraníme akce, které nemají datum (prázdné řádky)
    df_akce = df_akce.dropna(subset=['datum'])
    
    # Seřadíme
    df_akce = df_akce.sort_values(by='datum')
except Exception as e:
    st.error(f"Chyba ve formátu data v tabulce: {e}")
    st.stop()

dnes = datetime.now().date()

# --- 4. VYKRESLENÍ AKCÍ ---
if df_akce.empty:
    st.info("Žádné akce k zobrazení.")

for index, akce in df_akce.iterrows():
    # Logika deadlinu
    je_po_deadlinu = dnes > akce['deadline']
    ikona = "🔒" if je_po_deadlinu else "✅"
    
    datum_str = akce['datum'].strftime('%d.%m.%Y')
    deadline_str = akce['deadline'].strftime('%d.%m.%Y')
    
    label = f"{ikona} {datum_str} | {akce['název']}"
    
    with st.expander(label):
        # A) Detail akce
        st.markdown(f"**📍 Místo:** {akce['místo']}")
        st.info(f"📝 **Popis:** {akce['popis']}")
        st.caption(f"Deadline přihlášek: {deadline_str}")
        
        st.divider()
        
        # B) Seznam přihlášených
        filtrovane_prihlasky = df_prihlasky[df_prihlasky['název'] == akce['název']]
        pocet = len(filtrovane_prihlasky)
        
        st.write(f"**👥 Přihlášeno ({pocet}):**")
        
        if pocet > 0:
            st.dataframe(filtrovane_prihlasky[['jméno', 'poznámka']], hide_index=True, use_container_width=True)
        else:
            st.write("Zatím nikdo.")

        # C) Přihlašovací formulář
        if not je_po_deadlinu:
            st.write("---")
            st.write("#### ✍️ Nová přihláška")
            
            with st.form(key=f"form_{index}", clear_on_submit=True):
                jmeno = st.text_input("Jméno a příjmení")
                poznamka = st.text_input("Poznámka")
                odeslat = st.form_submit_button("Přihlásit se")
                
                if odeslat:
                    if jmeno:
                        # Vytvoření řádku
                        novy_zaznam = pd.DataFrame([{
                            "název": akce['název'],
                            "jméno": jmeno,
                            "poznámka": poznamka,
                            "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }])
                        
                        # Aktualizace dat
                        updated_df = pd.concat([df_prihlasky, novy_zaznam], ignore_index=True)
                        
                        try:
                            # Zápis do Google Sheets
                            conn.update(worksheet="prihlasky", data=updated_df)
                            st.success("Přihlášeno! 🎉")
                            st.rerun()
                        except Exception as e:
                            st.error("Nepodařilo se zapsat do tabulky. Zkontroluj, zda je tabulka sdílená jako 'Editor' pro všechny s odkazem.")
                    else:
                        st.warning("Musíš vyplnit jméno.")
        else:
            st.error("Termín přihlášek již vypršel.")
            
# --- 5. PATIČKA ---
st.markdown("---")
st.caption("Systém pro OB Klub | Data jsou uložena v Google Sheets")
