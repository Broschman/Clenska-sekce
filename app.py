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
st.markdown("Klikni na akci pro zobrazení **popisu** a přihlášení.")

# --- 2. PŘIPOJENÍ K DATŮM ---
# ttl=0 zajistí, že se data načtou čerstvá při každém reloadu
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Načteme oba listy. Ujisti se, že v Google Sheets se jmenují přesně takto (malými písmeny)
    df_akce = conn.read(worksheet="akce", ttl=0)
    df_prihlasky = conn.read(worksheet="prihlasky", ttl=0)
except Exception as e:
    st.error(f"⚠️ Chyba připojení: {e}. Zkontroluj secrets.toml a název listů v tabulce.")
    st.stop()

# --- 3. ČIŠTĚNÍ A PŘÍPRAVA DAT ---
# Převedeme sloupce na datum. Pokud je buňka prázdná nebo chybná, Pandas to zvládne (errors='coerce')
df_akce['datum'] = pd.to_datetime(df_akce['datum'], errors='coerce').dt.date
df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], errors='coerce').dt.date

# Odstraníme řádky, kde chybí datum (často prázdné řádky na konci tabulky)
df_akce = df_akce.dropna(subset=['datum'])

# Seřadíme akce chronologicky
df_akce = df_akce.sort_values(by='datum')

# Dnešní datum pro kontrolu deadlinů
dnes = datetime.now().date()

# --- 4. VYKRESLENÍ AKCÍ ---
if df_akce.empty:
    st.info("Zatím nejsou vypsané žádné akce.")
else:
    for index, akce in df_akce.iterrows():
        
        # Kontrola deadlinu
        je_po_deadlinu = dnes > akce['deadline']
        ikona = "🔒" if je_po_deadlinu else "✅"
        
        # Formátování data (např. 15.03.2026)
        datum_str = akce['datum'].strftime('%d.%m.%Y')
        deadline_str = akce['deadline'].strftime('%d.%m.%Y')
        
        # Hlavička karty (to, co je vidět vždy)
        label_karty = f"{ikona} {datum_str} | {akce['název']} (Deadline: {deadline_str})"
        
        # --- ROZBALOVACÍ ČÁST ---
        with st.expander(label_karty):
            
            # ZDE SE ZOBRAZUJE NOVÝ SLOUPEC 'POPIS'
            st.markdown(f"**📍 Místo:** {akce['místo']}")
            
            # Ošetření, kdyby byl popis prázdný (NaN)
            popis_text = akce['popis'] if pd.notna(akce['popis']) else "Bez popisu."
            st.info(f"📝 **Popis akce:**\n\n{popis_text}")
            
            st.divider()
            
            # Seznam přihlášených
            lide_na_akci = df_prihlasky[df_prihlasky['název'] == akce['název']]
            st.write(f"**👥 Přihlášeno: {len(lide_na_akci)}**")
            
            if not lide_na_akci.empty:
                st.dataframe(
                    lide_na_akci[['jméno', 'poznámka']], 
                    hide_index=True, 
                    use_container_width=True
                )
            else:
                st.write("Buď první!")

            st.divider()

            # Formulář pro přihlášení (jen pokud není po deadlinu)
            if not je_po_deadlinu:
                st.write("#### Nová přihláška")
                with st.form(key=f"form_{index}", clear_on_submit=True):
                    jmeno_input = st.text_input("Jméno a příjmení")
                    poznamka_input = st.text_input("Poznámka (auto, čip, kategorie...)")
                    
                    submit_btn = st.form_submit_button("Odeslat přihlášku")
                    
                    if submit_btn:
                        if jmeno_input:
                            # Vytvoření nového řádku
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
                                st.success(f"✅ {jmeno_input} úspěšně přihlášen/a!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Chyba při zápisu: {e}")
                        else:
                            st.warning("⚠️ Vyplň prosím aspoň jméno.")
            else:
                st.warning(f"⛔ Přihlašování ukončeno ({deadline_str}).")

# --- 5. PATIČKA ---
st.markdown("---")
st.caption("Systém pro OB Klub | Data jsou uložena v Google Sheets")
