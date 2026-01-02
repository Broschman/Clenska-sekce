import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import calendar

# --- 1. NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="OB Klub - Kalendář", page_icon="🌲", layout="wide")

# --- CSS VZHLED (FANCY DESIGN + FIXY) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }

    h1 {
        color: #2E7D32; 
        text-align: center;
        font-weight: 800;
        letter-spacing: -1px;
        margin-bottom: 30px;
    }

    /* KARTY AKCÍ */
    div[data-testid="stPopover"] > button {
        white-space: normal !important;
        word-break: keep-all !important;
        overflow-wrap: normal !important;
        hyphens: none !important;
        
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-left: 5px solid #4CAF50 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
        
        color: #333 !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        
        text-align: left !important;
        height: auto !important;
        min-height: 50px;
        width: 100% !important;
        padding: 6px 10px !important;
        line-height: 1.3 !important;
        transition: all 0.2s ease-in-out !important;
    }

    div[data-testid="stPopover"] > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.15) !important;
        border-color: #4CAF50 !important;
    }

    /* NAVIGACE */
    div[data-testid="stButton"] > button {
        border-radius: 20px !important;
        font-weight: bold !important;
        border: none !important;
        background-color: #f0f2f6 !important;
        color: #555 !important;
        transition: 0.2s;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #e0e2e6 !important;
        color: #000 !important;
    }

    /* DNEŠNÍ DEN */
    .today-box {
        background: linear-gradient(135deg, #FF4B4B 0%, #FF9068 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 15px;
        font-weight: bold;
        box-shadow: 0 3px 6px rgba(255, 75, 75, 0.3);
        display: inline-block;
        margin-bottom: 8px;
    }

    .day-number {
        font-size: 1.1em;
        font-weight: 700;
        color: #444;
        margin-bottom: 8px;
        display: block;
        text-align: center;
    }

    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("🌲 Tréninkový kalendář")

# --- 2. PŘIPOJENÍ A NAČTENÍ DAT ---
conn = st.connection("gsheets", type=GSheetsConnection)
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
    st.error("⚠️ Chyba načítání dat. Zkontroluj tabulku.")
    st.stop()

# --- 3. LOGIKA KALENDÁŘE ---
if 'vybrany_datum' not in st.session_state:
    st.session_state.vybrany_datum = date.today()

col_nav1, col_nav2, col_nav3 = st.columns([2, 5, 2])
with col_nav1:
    if st.button("⬅️ Předchozí měsíc"):
        curr = st.session_state.vybrany_datum
        prev_month = curr.replace(day=1) - timedelta(days=1)
        st.session_state.vybrany_datum = prev_month.replace(day=1)
with col_nav3:
    if st.button("Další měsíc ➡️"):
        curr = st.session_state.vybrany_datum
        next_month = (curr.replace(day=28) + timedelta(days=4)).replace(day=1)
        st.session_state.vybrany_datum = next_month

rok = st.session_state.vybrany_datum.year
mesic = st.session_state.vybrany_datum.month
ceske_mesice = ["", "Leden", "Únor", "Březen", "Duben", "Květen", "Červen", "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"]

with col_nav2:
    st.markdown(f"<h2 style='text-align: center; color: #333; margin-top: -5px; font-weight: 300;'>{ceske_mesice[mesic]} <b>{rok}</b></h2>", unsafe_allow_html=True)

# --- 4. VYKRESLENÍ MŘÍŽKY ---
cal = calendar.Calendar(firstweekday=0)
month_days = cal.monthdayscalendar(rok, mesic)

dny_v_tydnu = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
cols_header = st.columns(7)
for i, d in enumerate(dny_v_tydnu):
    cols_header[i].markdown(f"<div style='text-align: center; color: #888; text-transform: uppercase; font-size: 0.8rem; margin-bottom: 10px;'>{d}</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 0 0 20px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

dnes = date.today()

for tyden in month_days:
    cols = st.columns(7, gap="small")
    for i, den_cislo in enumerate(tyden):
        with cols[i]:
            if den_cislo == 0:
                st.write("")
                continue
            
            aktualni_den = date(rok, mesic, den_cislo)
            
            if aktualni_den == dnes:
                st.markdown(f"<div style='text-align: center;'><span class='today-box'>{den_cislo}</span></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='day-number'>{den_cislo}</span>", unsafe_allow_html=True)

            # --- VYKRESLOVÁNÍ AKCÍ ---
            akce_dne = df_akce[df_akce['datum'] == aktualni_den]
            for _, akce in akce_dne.iterrows():
                je_po_deadlinu = dnes > akce['deadline']
                
                # --- 1. ZJIŠTĚNÍ TYPU A IKONY ---
                # Načteme typ z tabulky, převedeme na malá písmena a odstraníme mezery
                typ_akce = str(akce['typ']).lower().strip() if 'typ' in df_akce.columns and pd.notna(akce['typ']) else "ostatní"
                
                # Mapa ikon podle typu
                ikony_mapa = {
                    "les": "🌲",
                    "sprint": "🏙️",
                    "nočák": "🌗"
                }
                # Vybere ikonu, pokud typ nezná, dá běžce
                emoji_typ = ikony_mapa.get(typ_akce, "🏃")
                
                # Pokud je zamčeno, přidáme zámek, jinak necháme jen typ
                if je_po_deadlinu:
                    finalni_ikona = f"🔒 {emoji_typ}"
                else:
                    finalni_ikona = emoji_typ

                # --- 2. OŘEZÁNÍ NÁZVU (Před pomlčkou) ---
                nazev_full = akce['název']
                if '-' in nazev_full:
                    display_text = nazev_full.split('-')[0].strip()
                else:
                    display_text = nazev_full
                
                # Výsledný text na tlačítku
                label_tlacitka = f"{finalni_ikona} {display_text}"
                
                with st.popover(label_tlacitka, use_container_width=True):
                    # --- DETAIL AKCE ---
                    st.markdown(f"### {nazev_full}")
                    
                    # Tady zobrazíme ten typ i textově
                    st.caption(f"Typ tréninku: {typ_akce.upper()}")
                    
                    st.write(f"**📍 Místo:** {akce['místo']}")
                    popis_txt = akce['popis'] if pd.notna(akce['popis']) else ""
                    st.info(f"📝 {popis_txt}")
                    
                    deadline_str = akce['deadline'].strftime('%d.%m.%Y')
                    if je_po_deadlinu:
                        st.error(f"⛔ Přihlášky uzavřeny (Deadline: {deadline_str})")
                    else:
                        st.caption(f"📅 Deadline přihlášek: {deadline_str}")

                    st.divider()
                    lidi = df_prihlasky[df_prihlasky['název'] == akce['název']].copy()
                    st.write(f"**👥 Přihlášeno: {len(lidi)}**")
                    if not lidi.empty:
                        lidi.index = range(1, len(lidi) + 1)
                        st.dataframe(lidi[['jméno', 'poznámka']], use_container_width=True)
                    else:
                        st.caption("Zatím nikdo.")

                    if not je_po_deadlinu:
                        st.write("#### ✍️ Nová přihláška")
                        form_key = f"form_{akce['název']}_{aktualni_den}"
                        with st.form(key=form_key, clear_on_submit=True):
                            jmeno_input = st.text_input("Jméno a příjmení")
                            poznamka_input = st.text_input("Poznámka")
                            odeslat_btn = st.form_submit_button("Přihlásit se")
                            if odeslat_btn and jmeno_input:
                                novy = pd.DataFrame([{
                                    "název": akce['název'],
                                    "jméno": jmeno_input,
                                    "poznámka": poznamka_input,
                                    "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }])
                                try:
                                    aktualni = conn.read(worksheet="prihlasky", ttl=0)
                                    updated = pd.concat([aktualni, novy], ignore_index=True)
                                    conn.update(worksheet="prihlasky", data=updated)
                                    st.success("✅ Zapsáno!")
                                    st.rerun()
                                except:
                                    st.error("Chyba zápisu.")

    st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)

# --- PATIČKA ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #aaa; font-size: 0.8em; font-family: sans-serif;'>
    <b>Členská sekce RBK</b> • Designed by Broschman<br>
    &copy; 2026 All rights reserved
</div>
""", unsafe_allow_html=True)
