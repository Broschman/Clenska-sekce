import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import calendar

# --- 1. NASTAVENÍ STRÁNKY (MOBILNÍ REŽIM) ---
# Změna na "centered" = aplikace na výšku
st.set_page_config(page_title="OB Klub - Kalendář", page_icon="🌲", layout="centered")

# --- CSS VZHLED + HORIZONTÁLNÍ SCROLL ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }
    
    /* === HLAVNÍ TRIK: HORIZONTÁLNÍ SCROLOVÁNÍ === */
    
    /* 1. Kontejner pro sloupce (týden) */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;     /* ZAKÁZAT zalamování na další řádek */
        overflow-x: auto !important;      /* POVOLIT posouvání do boku */
        padding-bottom: 10px !important;  /* Místo pro posuvník */
        gap: 5px !important;              /* Mezery mezi dny */
    }
    
    /* 2. Jednotlivé sloupce (dny) */
    div[data-testid="column"] {
        min-width: 100px !important;      /* KAŽDÝ DEN MÁ GARANTOVANOU ŠÍŘKU */
        flex: 0 0 auto !important;        /* Nesmršťovat se */
        width: 100px !important;          /* Fixní šířka */
    }

    /* Nadpis */
    h1 {
        color: #2E7D32; 
        text-align: center;
        font-weight: 800;
        letter-spacing: -1px;
        margin-bottom: 20px;
        font-size: 1.8rem;
    }

    /* KARTY AKCÍ (Tlačítka) */
    div[data-testid="stPopover"] > button {
        white-space: normal !important;
        word-break: keep-all !important;
        overflow-wrap: normal !important;
        hyphens: none !important;
        
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-left: 4px solid #4CAF50 !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        
        color: #333 !important;
        font-size: 0.75rem !important;    /* Menší písmo pro mobil */
        font-weight: 600 !important;
        
        text-align: left !important;
        height: auto !important;
        min-height: 45px;
        width: 100% !important;
        padding: 4px 6px !important;
        line-height: 1.2 !important;
    }

    /* NAVIGACE (Předchozí/Další) */
    /* Zde musíme trochu obejít to globální nastavení šířky sloupců */
    /* Tlačítka budou taky scrolovací, ale to na mobilu nevadí */
    div[data-testid="stButton"] > button {
        border-radius: 20px !important;
        font-weight: bold !important;
        border: none !important;
        background-color: #f0f2f6 !important;
        color: #555 !important;
        width: 100% !important;
        font-size: 0.8rem !important;
    }

    /* DNEŠNÍ DEN */
    .today-box {
        background: linear-gradient(135deg, #FF4B4B 0%, #FF9068 100%);
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-weight: bold;
        font-size: 0.9rem;
        box-shadow: 0 2px 5px rgba(255, 75, 75, 0.3);
        display: inline-block;
        margin-bottom: 5px;
    }

    .day-number {
        font-size: 1rem;
        font-weight: 700;
        color: #444;
        margin-bottom: 5px;
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
url_jmena = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=jmena"

try:
    df_akce = pd.read_csv(url_akce)
    df_akce['datum'] = pd.to_datetime(df_akce['datum'], dayfirst=True, errors='coerce').dt.date
    df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], dayfirst=True, errors='coerce').dt.date
    df_akce = df_akce.dropna(subset=['datum'])
    
    try:
        df_prihlasky = pd.read_csv(url_prihlasky)
    except:
        df_prihlasky = pd.DataFrame(columns=["název", "jméno", "poznámka", "čas zápisu"])
        
    try:
        df_jmena = pd.read_csv(url_jmena)
        seznam_jmen = sorted(df_jmena['jméno'].dropna().unique().tolist())
    except:
        seznam_jmen = []
        
except Exception as e:
    st.error("⚠️ Chyba načítání dat.")
    st.stop()

# --- 3. LOGIKA KALENDÁŘE ---
if 'vybrany_datum' not in st.session_state:
    st.session_state.vybrany_datum = date.today()

# Navigace (i ta bude mít teď fixní šířku sloupců, ale to nevadí)
col_nav1, col_nav2, col_nav3 = st.columns([2, 4, 2])
with col_nav1:
    if st.button("⬅️"):
        curr = st.session_state.vybrany_datum
        prev_month = curr.replace(day=1) - timedelta(days=1)
        st.session_state.vybrany_datum = prev_month.replace(day=1)
with col_nav3:
    if st.button("➡️"):
        curr = st.session_state.vybrany_datum
        next_month = (curr.replace(day=28) + timedelta(days=4)).replace(day=1)
        st.session_state.vybrany_datum = next_month

rok = st.session_state.vybrany_datum.year
mesic = st.session_state.vybrany_datum.month
ceske_mesice = ["", "Leden", "Únor", "Březen", "Duben", "Květen", "Červen", "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"]

with col_nav2:
    st.markdown(f"<h3 style='text-align: center; color: #333; margin: 0; padding-top: 5px;'>{ceske_mesice[mesic]} {rok}</h3>", unsafe_allow_html=True)
st.markdown("<div style='margin-bottom: 15px'></div>", unsafe_allow_html=True)

# --- 4. VYKRESLENÍ MŘÍŽKY (S HORIZONTÁLNÍM SCROLLEM) ---
cal = calendar.Calendar(firstweekday=0)
month_days = cal.monthdayscalendar(rok, mesic)

dny_v_tydnu = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
cols_header = st.columns(7)
for i, d in enumerate(dny_v_tydnu):
    cols_header[i].markdown(f"<div style='text-align: center; color: #888; font-size: 0.8rem;'>{d}</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 5px 0 10px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

dnes = date.today()

for tyden in month_days:
    # Tady se děje magie - st.columns(7) se díky CSS roztáhne a půjde scrolovat
    cols = st.columns(7) 
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

            # AKCE
            akce_dne = df_akce[df_akce['datum'] == aktualni_den]
            for _, akce in akce_dne.iterrows():
                je_po_deadlinu = dnes > akce['deadline']
                
                typ_akce = str(akce['typ']).lower().strip() if 'typ' in df_akce.columns and pd.notna(akce['typ']) else "ostatní"
                ikony_mapa = {"les": "🌲", "sprint": "🏙️", "nočák": "🌗"}
                emoji_typ = ikony_mapa.get(typ_akce, "🏃")
                
                finalni_ikona = f"🔒 {emoji_typ}" if je_po_deadlinu else emoji_typ

                nazev_full = akce['název']
                if '-' in nazev_full:
                    display_text = nazev_full.split('-')[0].strip()
                else:
                    display_text = nazev_full
                
                label_tlacitka = f"{finalni_ikona} {display_text}"
                
                with st.popover(label_tlacitka, use_container_width=True):
                    st.markdown(f"### {nazev_full}")
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
                            
                            vybrane_jmeno = st.selectbox(
                                "👤 Jméno", 
                                options=seznam_jmen, 
                                index=None, 
                                placeholder="Vyber nebo piš..."
                            )
                            nove_jmeno = st.text_input("...nebo napiš Nové jméno")
                            
                            poznamka_input = st.text_input("Poznámka")
                            odeslat_btn = st.form_submit_button("Přihlásit se")
                            
                            if odeslat_btn:
                                finalni_jmeno = nove_jmeno.strip() if nove_jmeno else vybrane_jmeno
                                
                                if finalni_jmeno:
                                    novy_zaznam = pd.DataFrame([{
                                        "název": akce['název'],
                                        "jméno": finalni_jmeno,
                                        "poznámka": poznamka_input,
                                        "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }])
                                    try:
                                        aktualni = conn.read(worksheet="prihlasky", ttl=0)
                                        updated = pd.concat([aktualni, novy_zaznam], ignore_index=True)
                                        conn.update(worksheet="prihlasky", data=updated)
                                        
                                        if finalni_jmeno not in seznam_jmen:
                                            try:
                                                aktualni_jmena_df = conn.read(worksheet="jmena", ttl=0)
                                                novy_clen = pd.DataFrame([{"jméno": finalni_jmeno}])
                                                updated_jmena = pd.concat([aktualni_jmena_df, novy_clen], ignore_index=True)
                                                conn.update(worksheet="jmena", data=updated_jmena)
                                            except:
                                                pass

                                        st.success(f"✅ Přihlášeno!")
                                        st.rerun()
                                    except:
                                        st.error("Chyba zápisu.")
                                else:
                                    st.warning("Vyplň jméno!")
    
    # Menší mezera mezi týdny pro kompaktnost na mobilu
    st.markdown("<div style='margin-bottom: 5px'></div>", unsafe_allow_html=True)

# --- PATIČKA ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #aaa; font-size: 0.8em; font-family: sans-serif;'>
    <b>Členská sekce RBK</b><br>
    &copy; 2026 All rights reserved
</div>
""", unsafe_allow_html=True)
    
