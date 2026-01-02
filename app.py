import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import calendar

# --- 1. NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="OB Klub - Kalendář", page_icon="🌲", layout="wide")
st.title("🌲 Tréninkový kalendář")

# --- CSS ÚPRAVY VZHLEDU ---
# Toto zajistí, že se text v tlačítkách neláme uprostřed slova a tlačítko se natáhne
st.markdown("""
<style>
    div[data-testid="stPopover"] > button {
        white-space: normal !important;     /* Povolí text na více řádků */
        word-break: normal !important;      /* ZAKÁŽE dělení slov uprostřed (žádné Bos-kovice) */
        overflow-wrap: anywhere !important; /* Dlouhá slova se zalomí jen v mezerách */
        text-align: center !important;      /* Zarovnání na střed */
        height: auto !important;            /* Výška se přizpůsobí obsahu */
        min-height: 55px;                   /* Aby tlačítka v řádku lícovala */
        padding: 4px !important;            
        line-height: 1.3 !important;        
        border-radius: 8px !important;      /* Trochu kulatější rohy */
    }
    
    /* Zvýraznění dnešního dne v kalendáři */
    .today-box {
        border: 2px solid #FF4B4B;
        padding: 5px;
        border-radius: 5px;
        text-align: center;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. PŘIPOJENÍ A NAČTENÍ DAT ---
# Inicializace konektoru (bere si údaje ze Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

SHEET_ID = "1lW6DpUQBSm5heSO_HH9lDzm0x7t1eo8dn6FpJHh2y6U"
# Odkazy pro super-rychlé čtení (CSV export)
url_akce = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=akce"
url_prihlasky = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=prihlasky"

try:
    # 1. Načtení akcí
    df_akce = pd.read_csv(url_akce)
    # Převod na datum (ošetření českého formátu i chyb)
    df_akce['datum'] = pd.to_datetime(df_akce['datum'], dayfirst=True, errors='coerce').dt.date
    df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], dayfirst=True, errors='coerce').dt.date
    # Vyhodíme řádky, kde chybí datum
    df_akce = df_akce.dropna(subset=['datum'])
    
    # 2. Načtení přihlášek
    try:
        df_prihlasky = pd.read_csv(url_prihlasky)
    except:
        # Kdyby byl list prázdný, vytvoříme prázdnou kostru
        df_prihlasky = pd.DataFrame(columns=["název", "jméno", "poznámka", "čas zápisu"])
        
except Exception as e:
    st.error("⚠️ Chyba načítání dat. Zkontroluj, zda je Google Tabulka veřejná (nebo máš správná Secrets).")
    st.stop()

# --- 3. LOGIKA KALENDÁŘE (Měsíc/Rok) ---
if 'vybrany_datum' not in st.session_state:
    st.session_state.vybrany_datum = date.today()

# Navigace (Šipky a název měsíce)
col_nav1, col_nav2, col_nav3 = st.columns([1, 6, 1])

with col_nav1:
    if st.button("⬅️ Předchozí"):
        curr = st.session_state.vybrany_datum
        # Skok na poslední den minulého měsíce a pak na první
        prev_month = curr.replace(day=1) - timedelta(days=1)
        st.session_state.vybrany_datum = prev_month.replace(day=1)

with col_nav3:
    if st.button("Další ➡️"):
        curr = st.session_state.vybrany_datum
        # Skok o měsíc dopředu
        next_month = (curr.replace(day=28) + timedelta(days=4)).replace(day=1)
        st.session_state.vybrany_datum = next_month

# Zobrazení názvu měsíce
rok = st.session_state.vybrany_datum.year
mesic = st.session_state.vybrany_datum.month
ceske_mesice = ["", "Leden", "Únor", "Březen", "Duben", "Květen", "Červen", "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"]

with col_nav2:
    st.markdown(f"<h2 style='text-align: center; margin-top: -10px;'>{ceske_mesice[mesic]} {rok}</h2>", unsafe_allow_html=True)

# --- 4. VYKRESLENÍ MŘÍŽKY KALENDÁŘE ---
# firstweekday=0 znamená, že týden začíná v Pondělí
cal = calendar.Calendar(firstweekday=0)
month_days = cal.monthdayscalendar(rok, mesic)

# Záhlaví dnů (Po, Út...)
dny_v_tydnu = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
cols_header = st.columns(7)
for i, d in enumerate(dny_v_tydnu):
    cols_header[i].markdown(f"**{d}**", unsafe_allow_html=True)
st.divider()

dnes = date.today()

# Hlavní smyčka pro vykreslení týdnů a dnů
for tyden in month_days:
    cols = st.columns(7, gap="small")
    
    for i, den_cislo in enumerate(tyden):
        with cols[i]:
            if den_cislo == 0:
                # Prázdné políčko (den z jiného měsíce)
                st.write("") 
                continue
            
            aktualni_den = date(rok, mesic, den_cislo)
            
            # Zvýraznění dnešního dne
            if aktualni_den == dnes:
                st.markdown(f"<div class='today-box'><b>{den_cislo}</b> (Dnes)</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align: center; margin-bottom: 5px;'><b>{den_cislo}</b></div>", unsafe_allow_html=True)

            # --- VYKRESLENÍ AKCÍ PRO TENTO DEN ---
            akce_dne = df_akce[df_akce['datum'] == aktualni_den]
            
            for _, akce in akce_dne.iterrows():
                je_po_deadlinu = dnes > akce['deadline']
                ikona = "🔒" if je_po_deadlinu else "✅"
                
                nazev_full = akce['název']
                
                # Zkracování názvu pro mřížku (aby se to vešlo)
                # Ale CSS zajistí, že se to zalomí a "neroztrhne" slovo
                if len(nazev_full) > 22:
                    label_tlacitka = f"{ikona} {nazev_full[:20]}.."
                else:
                    label_tlacitka = f"{ikona} {nazev_full}"
                
                # --- POPOVER (Bublina s detaily) ---
                with st.popover(label_tlacitka, use_container_width=True):
                    # Hlavička bubliny
                    st.markdown(f"### {nazev_full}")
                    st.write(f"**📍 Místo:** {akce['místo']}")
                    
                    # Popis (pokud chybí, zobrazíme prázdný řetězec)
                    popis_txt = akce['popis'] if pd.notna(akce['popis']) else ""
                    st.info(f"📝 {popis_txt}")
                    
                    # Deadline info
                    deadline_str = akce['deadline'].strftime('%d.%m.%Y')
                    if je_po_deadlinu:
                        st.error(f"⛔ Přihlášky uzavřeny (Deadline: {deadline_str})")
                    else:
                        st.caption(f"📅 Deadline přihlášek: {deadline_str}")

                    st.divider()
                    
                    # --- SEZNAM PŘIHLÁŠENÝCH ---
                    # Filtrujeme lidi pro tuto konkrétní akci
                    lidi = df_prihlasky[df_prihlasky['název'] == akce['název']].copy()
                    
                    st.write(f"**👥 Přihlášeno: {len(lidi)}**")
                    
                    if not lidi.empty:
                        # Tady zajistíme číslování od 1
                        lidi.index = range(1, len(lidi) + 1)
                        st.dataframe(lidi[['jméno', 'poznámka']], use_container_width=True)
                    else:
                        st.caption("Zatím nikdo, buď první!")

                    # --- PŘIHLAŠOVACÍ FORMULÁŘ ---
                    if not je_po_deadlinu:
                        st.write("#### ✍️ Nová přihláška")
                        # Unikátní klíč pro formulář (aby se nehádaly mezi sebou)
                        form_key = f"form_{akce['název']}_{aktualni_den}"
                        
                        with st.form(key=form_key, clear_on_submit=True):
                            jmeno_input = st.text_input("Jméno a příjmení")
                            poznamka_input = st.text_input("Poznámka")
                            
                            odeslat_btn = st.form_submit_button("Přihlásit se")
                            
                            if odeslat_btn:
                                if jmeno_input:
                                    # 1. Příprava dat
                                    novy_zaznam = pd.DataFrame([{
                                        "název": akce['název'],
                                        "jméno": jmeno_input,
                                        "poznámka": poznamka_input,
                                        "čas zápisu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }])
                                    
                                    # 2. Zápis do Google Sheets
                                    try:
                                        # Načteme aktuální stav (aby se nepřepsala data někoho, kdo se hlásil teď)
                                        aktualni_data = conn.read(worksheet="prihlasky", ttl=0)
                                        updated_df = pd.concat([aktualni_data, novy_zaznam], ignore_index=True)
                                        
                                        conn.update(worksheet="prihlasky", data=updated_df)
                                        st.success("✅ Úspěšně přihlášeno!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error("Chyba při zápisu. Zkontroluj připojení.")
                                else:
                                    st.warning("⚠️ Musíš vyplnit jméno.")

    # Čára pod každým týdnem pro lepší přehlednost
    st.divider()

# --- PATIČKA ---
st.caption("🌲 Tréninkový systém OB | Data uložena v Google Sheets")
