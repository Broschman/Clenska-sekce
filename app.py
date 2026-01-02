import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import calendar

# --- 1. NASTAVENÍ ---
st.set_page_config(page_title="OB Klub - Kalendář", page_icon="🌲", layout="wide")
st.title("🌲 Tréninkový kalendář")

# --- CSS HACK: Oprava lámání slov v tlačítkách ---
st.markdown("""
<style>
    /* Zacílíme na tlačítka v kalendáři (popovery) */
    div[data-testid="stPopover"] > button {
        white-space: normal !important;   /* Povolí zalamování řádků */
        word-wrap: break-word !important; /* Zalamuje jen celá slova, ne uprostřed */
        height: auto !important;          /* Tlačítko se natáhne podle textu */
        min-height: 50px;                 /* Minimální výška, aby to vypadalo jednotně */
        padding: 5px !important;          /* Trochu místa uvnitř */
        line-height: 1.2 !important;      /* Menší řádkování ať se tam toho víc vleze */
    }
</style>
""", unsafe_allow_html=True)

# Připojení
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. NAČTENÍ DAT ---
SHEET_ID = "1lW6DpUQBSm5heSO_HH9lDzm0x7t1eo8dn6FpJHh2y6U"
url_akce = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=akce"
url_prihlasky = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=prihlasky"

try:
    df_akce = pd.read_csv(url_akce)
    df_akce['datum'] = pd.to_datetime(df_akce['datum'], dayfirst=True, errors='coerce').dt.date
    df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], dayfirst=True, errors='coerce').dt.date
    df_akce = df_akce.dropna(subset=['datum'])
    
    try:
        df_prihlasky = pd.read_csv(url_prihlasky)
    except:
        df_prihlasky = pd.DataFrame(columns=["název", "jméno", "poznámka", "čas zápisu"])
except Exception as e:
    st.error("Chyba načítání dat. Zkontroluj Google Tabulku.")
    st.stop()

# --- 3. OVLÁDÁNÍ KALENDÁŘE ---
if 'vybrany_datum' not in st.session_state:
    st.session_state.vybrany_datum = date.today()

col_nav1, col_nav2, col_nav3 = st.columns([1, 5, 1])

with col_nav1:
    if st.button("⬅️ Předchozí"):
        curr = st.session_state.vybrany_datum
        prev_month = curr.replace(day=1) - timedelta(days=1)
        st.session_state.vybrany_datum = prev_month.replace(day=1)

with col_nav3:
    if st.button("Další ➡️"):
        curr = st.session_state.vybrany_datum
        next_month = (curr.replace(day=28) + timedelta(days=4)).replace(day=1)
        st.session_state.vybrany_datum = next_month

rok = st.session_state.vybrany_datum.year
mesic = st.session_state.vybrany_datum.month
ceske_mesice = ["", "Leden", "Únor", "Březen", "Duben", "Květen", "Červen", "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"]

with col_nav2:
    st.markdown(f"<h3 style='text-align: center;'>{ceske_mesice[mesic]} {rok}</h3>", unsafe_allow_html=True)

# --- 4. VYKRESLENÍ MŘÍŽKY ---
cal = calendar.Calendar(firstweekday=0)
month_days = cal.monthdayscalendar(rok, mesic)

dny_v_tydnu = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
cols = st.columns(7)
for i, d in enumerate(dny_v_tydnu):
    cols[i].markdown(f"**{d}**")

dnes = date.today()

for tyden in month_days:
    cols = st.columns(7, gap="small")
    for i, den_cislo in enumerate(tyden):
        with cols[i]:
            if den_cislo == 0:
                st.write("") 
                continue
            
            aktualni_den = date(rok, mesic, den_cislo)
            akce_dne = df_akce[df_akce['datum'] == aktualni_den]
            
            # Číslo dne
            if aktualni_den == dnes:
                st.markdown(f"**🔴 {den_cislo}**")
            else:
                st.markdown(f"**{den_cislo}**")

            # Výpis akcí
            for _, akce in akce_dne.iterrows():
                je_po_deadlinu = dnes > akce['deadline']
                ikona = "🔒" if je_po_deadlinu else "✅"
                
                # Zkrácení názvu pro tlačítko (aby nebyl přes půl obrazovky)
                nazev_full = akce['název']
                # Pokud je delší než 20 znaků, zkrátíme ho a dáme tři tečky
                if len(nazev_full) > 20:
                    label_tlacitka = f"{ikona} {nazev_full[:18]}.."
                else:
                    label_tlacitka = f"{ikona} {nazev_full}"
                
                # POPOVER (Bublina)
                with st.popover(label_tlacitka, use_container_width=True):
                    # Uvnitř už ukazujeme plný název
                    st.markdown(f"### {nazev_full}")
                    st.write(f"**📍 Místo:** {akce['místo']}")
                    st.info(f"📝 {akce['popis']}")
                    st.caption(f"Deadline: {akce['deadline'].strftime('%d.%m.%Y')}")
                    
                    st.divider()
                    
                    # Seznam přihlášených
                    lidi = df_prihlasky[df_prihlasky['název'] == akce['název']].copy()
                    
                    if not lidi.empty:
                        lidi.index = range(1, len(lidi) + 1)
                        st.write(f"**👥 Přihlášeno: {len(lidi)}**")
                        st.dataframe(lidi[['jméno', 'poznámka']], use_container_width=True)
                    else:
                        st.write("Zatím nikdo.")
                    
                    # Přihláška
                    if not je_po_deadlinu:
                        st.write("#### ✍️ Nová přihláška")
                        with st.form(key=f"form_{akce['název']}_{den_cislo}"):
                            jmeno = st.text_input("Jméno")
                            poznamka = st.text_input("Poznámka")
                            odeslat = st.form_submit_button("Přihlásit")
                            
                            if odeslat and jmeno:
                                novy = pd.DataFrame([{
                                    "název": akce['název'],
                                    "jméno": jmeno,
                                    "poznámka": poznamka,
                                    "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }])
                                
                                try:
                                    curr_data = conn.read(worksheet="prihlasky", ttl=0)
                                    updated = pd.concat([curr_data, novy], ignore_index=True)
                                    conn.update(worksheet="prihlasky", data=updated)
                                    st.success("Zapsáno!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Chyba: {e}")

    st.divider()
        
