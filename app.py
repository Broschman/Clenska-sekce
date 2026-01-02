            import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import calendar

# --- 1. NASTAVENÍ ---
st.set_page_config(page_title="OB Klub - Kalendář", page_icon="🌲", layout="wide") # Layout wide pro kalendář
st.title("🌲 Tréninkový kalendář")

# Připojení (Secrets musí být nastaveny z minulého kroku)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. NAČTENÍ DAT ---
SHEET_ID = "1lW6DpUQBSm5heSO_HH9lDzm0x7t1eo8dn6FpJHh2y6U"
url_akce = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=akce"
url_prihlasky = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=prihlasky"

try:
    # Akce
    df_akce = pd.read_csv(url_akce)
    df_akce['datum'] = pd.to_datetime(df_akce['datum'], dayfirst=True, errors='coerce').dt.date
    df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], dayfirst=True, errors='coerce').dt.date
    df_akce = df_akce.dropna(subset=['datum'])
    
    # Přihlášky
    try:
        df_prihlasky = pd.read_csv(url_prihlasky)
    except:
        df_prihlasky = pd.DataFrame(columns=["název", "jméno", "poznámka", "čas zápisu"])
except Exception as e:
    st.error("Chyba načítání dat. Zkontroluj Google Tabulku.")
    st.stop()

# --- 3. OVLÁDÁNÍ KALENDÁŘE (Měsíc/Rok) ---
if 'vybrany_datum' not in st.session_state:
    st.session_state.vybrany_datum = date.today()

col_nav1, col_nav2, col_nav3 = st.columns([1, 5, 1])

with col_nav1:
    if st.button("⬅️ Předchozí"):
        # Posun o měsíc zpět
        curr = st.session_state.vybrany_datum
        prev_month = curr.replace(day=1) - timedelta(days=1)
        st.session_state.vybrany_datum = prev_month.replace(day=1)

with col_nav3:
    if st.button("Další ➡️"):
        # Posun o měsíc vpřed
        curr = st.session_state.vybrany_datum
        # Trik na získání dalšího měsíce
        next_month = (curr.replace(day=28) + timedelta(days=4)).replace(day=1)
        st.session_state.vybrany_datum = next_month

# Zobrazení aktuálního měsíce
rok = st.session_state.vybrany_datum.year
mesic = st.session_state.vybrany_datum.month
ceske_mesice = ["", "Leden", "Únor", "Březen", "Duben", "Květen", "Červen", "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"]

with col_nav2:
    st.markdown(f"<h3 style='text-align: center;'>{ceske_mesice[mesic]} {rok}</h3>", unsafe_allow_html=True)

# --- 4. VYKRESLENÍ MŘÍŽKY KALENDÁŘE ---
# Nastavíme kalendář na pondělí (firstweekday=0)
cal = calendar.Calendar(firstweekday=0)
month_days = cal.monthdayscalendar(rok, mesic)

# Hlavička dnů
dny_v_tydnu = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
cols = st.columns(7)
for i, d in enumerate(dny_v_tydnu):
    cols[i].markdown(f"**{d}**")

# Procházíme týdny a dny
dnes = date.today()

for tyden in month_days:
    cols = st.columns(7, gap="small") # Mřížka týdne
    for i, den_cislo in enumerate(tyden):
        with cols[i]:
            if den_cislo == 0:
                # Prázdné políčko (den patří do jiného měsíce)
                st.write("") 
                continue
            
            # Vytvoření data pro tento den
            aktualni_den = date(rok, mesic, den_cislo)
            
            # Najdeme akce pro tento den
            akce_dne = df_akce[df_akce['datum'] == aktualni_den]
            
            # Vytvoříme kontejner (rámeček) pro den
            # Zvýrazníme dnešní den
            border_style = True
            if aktualni_den == dnes:
                st.markdown(f"**🔴 {den_cislo}**") # Dnešek červeně
            else:
                st.markdown(f"**{den_cislo}**")

            # Pokud je akce, vykreslíme ji
            for _, akce in akce_dne.iterrows():
                je_po_deadlinu = dnes > akce['deadline']
                ikona = "🔒" if je_po_deadlinu else "✅"
                
                # POPOVER - Bublina, co vyskočí po kliknutí
                with st.popover(f"{ikona} {akce['název']}", use_container_width=True):
                    st.markdown(f"### {akce['název']}")
                    st.write(f"**📍 Místo:** {akce['místo']}")
                    st.info(f"📝 {akce['popis']}")
                    st.caption(f"Deadline: {akce['deadline'].strftime('%d.%m.%Y')}")
                    
                    st.divider()
                    
                    # 1. ČÍSLOVANÝ SEZNAM PŘIHLÁŠENÝCH (OD 1)
                    lidi = df_prihlasky[df_prihlasky['název'] == akce['název']].copy()
                    
                    if not lidi.empty:
                        # Reset indexu, aby začínal od 1
                        lidi.index = range(1, len(lidi) + 1)
                        st.write(f"**👥 Přihlášeno: {len(lidi)}**")
                        st.dataframe(lidi[['jméno', 'poznámka']], use_container_width=True)
                    else:
                        st.write("Zatím nikdo.")
                    
                    # 2. PŘIHLAŠOVACÍ FORMULÁŘ
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
                                    # Pro zápis načteme čerstvá data přes konektor
                                    curr_data = conn.read(worksheet="prihlasky", ttl=0)
                                    updated = pd.concat([curr_data, novy], ignore_index=True)
                                    conn.update(worksheet="prihlasky", data=updated)
                                    st.success("Zapsáno!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Chyba: {e}")

    st.divider() # Čára pod týdnem
             
