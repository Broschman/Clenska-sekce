import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. NASTAVENÍ STRÁNKY ---
st.set_page_config(
    page_title="OB Klub - Termínovka",
    page_icon="🌲",
    layout="centered"
)

st.title("🌲 Kalendář akcí a přihlášky")
st.write("Klikni na akci pro zobrazení detailů a přihlášení.")

# --- 2. PŘIPOJENÍ K DATŮM ---
# ttl=0 znamená "Time To Live = 0", tedy nenačítat z cache, ale vždy čerstvé z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_akce = conn.read(worksheet="akce", ttl=0)
    df_prihlasky = conn.read(worksheet="prihlasky", ttl=0)
except Exception as e:
    st.error("⚠️ Nepodařilo se načíst data. Zkontroluj nastavení Secrets.")
    st.stop()

# --- 3. ČIŠTĚNÍ A PŘÍPRAVA DAT ---
# Převedeme sloupce s daty na opravdové datum (aby fungovalo řazení a porovnávání)
# 'coerce' znamená, že když je tam nesmysl, udělá z toho NaT (Not a Time), místo aby spadla aplikace
df_akce['datum'] = pd.to_datetime(df_akce['datum'], errors='coerce').dt.date
df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], errors='coerce').dt.date

# Vyhodíme řádky, kde chybí datum (pokud bys měl v tabulce prázdné řádky navíc)
df_akce = df_akce.dropna(subset=['datum'])

# Seřadíme chronologicky
df_akce = df_akce.sort_values(by='datum')

# Dnešní datum pro kontrolu deadlinů
dnes = datetime.now().date()

# --- 4. HLAVNÍ SMYČKA - Vykreslení akcí ---
# Iterujeme přes seřazené akce
for index, akce in df_akce.iterrows():
    
    # Zjistíme, jestli je ještě možné se hlásit
    je_po_deadlinu = dnes > akce['deadline']
    
    # Ikona podle stavu
    ikona = "🔒" if je_po_deadlinu else "✅"
    
    # Formátování data pro hezký výpis (např. 15.03.2026)
    datum_str = akce['datum'].strftime('%d.%m.%Y')
    deadline_str = akce['deadline'].strftime('%d.%m.%Y')
    
    # Text, který je vidět na zavřené kartě
    label_karty = f"{ikona} {datum_str} | {akce['název']} (Deadline: {deadline_str})"
    
    # --- 5. ROZBALOVACÍ KARTA (EXPANDER) ---
    with st.expander(label_karty):
        
        # A) Informace o akci
        st.markdown(f"**📍 Místo:** {akce['místo']}")
        st.markdown(f"**📝 Popis:** {akce['popis']}")
        
        st.divider()
        
        # B) Seznam přihlášených
        # Vyfiltrujeme lidi jen pro tuhle konkrétní akci
        lide_na_akci = df_prihlasky[df_prihlasky['název'] == akce['název']]
        
        st.write(f"**👥 Přihlášeno: {len(lide_na_akci)}**")
        
        if not lide_na_akci.empty:
            # Zobrazíme tabulku bez indexu (číslování řádků 0,1,2...)
            st.dataframe(
                lide_na_akci[['jméno', 'poznámka']], 
                hide_index=True, 
                use_container_width=True
            )
        else:
            st.info("Zatím nikdo. Buď první!")
            
        st.divider()

        # C) Přihlašovací formulář (JEN POKUD NENÍ PO DEADLINU)
        if not je_po_deadlinu:
            st.write("#### Nová přihláška")
            
            # Každý formulář musí mít unikátní klíč (key), jinak Streamlit zblbne
            with st.form(key=f"form_{index}", clear_on_submit=True):
                jmeno_input = st.text_input("Jméno a příjmení")
                poznamka_input = st.text_input("Poznámka (auto, kategorie, čip...)")
                
                submit_btn = st.form_submit_button("Odeslat přihlášku")
                
                if submit_btn:
                    if jmeno_input:
                        # Vytvoření nového záznamu
                        novy_radek = pd.DataFrame([{
                            "název": akce['název'],
                            "jméno": jmeno_input,
                            "poznámka": poznamka_input,
                            "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }])
                        
                        # Spojení a uložení
                        updated_df = pd.concat([df_prihlasky, novy_radek], ignore_index=True)
                        
                        try:
                            conn.update(worksheet="prihlasky", data=updated_df)
                            st.success("Jsi tam! 🎉")
                            st.rerun() # Refresh stránky, aby se jméno hned objevilo v seznamu
                        except Exception as e:
                            st.error(f"Chyba při zápisu: {e}")
                    else:
                        st.warning("Musíš vyplnit jméno.")
        else:
            st.warning(f"🚫 Přihlašování bylo ukončeno {deadline_str}.")

# --- 6. PATIČKA ---
st.markdown("---")
st.caption("Systém pro OB Klub | Vytvořeno v Pythonu + Streamlit")
