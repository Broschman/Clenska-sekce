import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import time

# --- 1. NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="OB Klub - Kalendář", page_icon="🌲", layout="wide")

# --- CSS VZHLED ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }

    h1 {
        color: #2E7D32; 
        text-align: center !important;
        font-weight: 800;
        letter-spacing: -1px;
        margin: 0;
        padding-bottom: 20px;
    }

    /* === MEGA BUBLINA (POPOVER) === */
    /* Roztáhneme ji na 800px (nebo 95% šířky mobilu) */
    div[data-testid="stPopoverBody"] {
        width: 800px !important;
        max-width: 95vw !important;
        max-height: 85vh !important;
        padding: 20px !important; /* Více místa uvnitř */
    }

    /* TLAČÍTKO NÁPOVĚDY */
    div[data-testid="column"] div[data-testid="stPopover"] > button {
        border-radius: 50% !important;
        width: 35px !important;
        height: 35px !important;
        border: 1px solid #ccc !important;
        color: #555 !important;
        background-color: white !important;
        padding: 0 !important;
    }

    /* PLOVOUCÍ TLAČÍTKO */
    .floating-container {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 9999;
    }
    .floating-container button {
        background-color: #FFC107 !important;
        color: #333 !important;
        border: none !important;
        border-radius: 50px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3) !important;
        font-weight: bold !important;
        padding: 10px 20px !important;
        height: 50px !important;
        transition: transform 0.2s !important;
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

# --- HLAVIČKA ---
col_dummy, col_title, col_help = st.columns([1, 10, 1], vertical_alignment="center")

with col_title:
    st.title("🌲 Tréninkový kalendář")

with col_help:
    with st.popover("❔", help="Nápověda"):
        st.markdown("### 💡 Nápověda")
        st.info("📱 **Mobil:** Otoč telefon na šířku.")
        st.divider()
        st.markdown("**Legenda:**")
        st.markdown("🏆 **Závod**")
        st.markdown("🌲 Les | 🏙️ Sprint | 🌗 Nočák")
        st.markdown("🔒 Uzavřeno")


# --- 2. PŘIPOJENÍ A NAČTENÍ DAT ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_ID = "1lW6DpUQBSm5heSO_HH9lDzm0x7t1eo8dn6FpJHh2y6U"

url_akce = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=akce"
url_prihlasky = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=prihlasky"
url_jmena = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=jmena"
url_navrhy = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=navrhy"

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

col_nav1, col_nav2, col_nav3 = st.columns([2, 5, 2])
with col_nav1:
    if st.button("⬅️ Předchozí měsíc", use_container_width=True):
        curr = st.session_state.vybrany_datum
        prev_month = curr.replace(day=1) - timedelta(days=1)
        st.session_state.vybrany_datum = prev_month.replace(day=1)

with col_nav3:
    if st.button("Další měsíc ➡️", use_container_width=True):
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

# INLINE CSS PRO TLAČÍTKA KALENDÁŘE
st.markdown("""
<style>
div[data-testid="column"] button {
    border-radius: 8px !important;
    width: 100% !important;
    height: auto !important;
    min-height: 55px !important;
    background-color: #ffffff !important;
    border: 1px solid #e0e0e0 !important;
    text-align: left !important;
    color: #333 !important;
    padding: 8px 10px !important;
    line-height: 1.3 !important;
}
div[data-testid="column"] button {
    border-left: 5px solid #4CAF50 !important;
}
div[data-testid="column"] button:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.1) !important;
    border-color: #2E7D32 !important;
}
</style>
""", unsafe_allow_html=True)


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

            # AKCE
            akce_dne = df_akce[df_akce['datum'] == aktualni_den]
            for _, akce in akce_dne.iterrows():
                je_po_deadlinu = dnes > akce['deadline']
                
                # DATA
                typ_udalosti = str(akce['typ']).lower().strip() if 'typ' in df_akce.columns and pd.notna(akce['typ']) else ""
                druh_akce = str(akce['druh']).lower().strip() if 'druh' in df_akce.columns and pd.notna(akce['druh']) else "ostatní"
                je_zavod = "závod" in typ_udalosti

                # IKONY
                ikony_mapa = {"les": "🌲", "sprint": "🏙️", "nočák": "🌗"}
                emoji_druh = ikony_mapa.get(druh_akce, "🏃")
                if je_zavod: emoji_final = f"🏆{emoji_druh}"
                else: emoji_final = emoji_druh
                
                if je_po_deadlinu: display_ikona = f"🔒 {emoji_final}"
                else: display_ikona = emoji_final

                nazev_full = akce['název']
                if '-' in nazev_full:
                    display_text = nazev_full.split('-')[0].strip()
                else:
                    display_text = nazev_full
                
                label_tlacitka = f"{display_ikona} {display_text}"
                
                # --- POPOVER (DETAIL AKCE) ---
                with st.popover(label_tlacitka, use_container_width=True):
                    
                    # HLAVNÍ NADPIS PŘES CELOU ŠÍŘKU
                    st.markdown(f"### {nazev_full}")
                    st.markdown("---")

                    # ROZDĚLENÍ NA DVA SLOUPCE (INFO | FORMULÁŘ)
                    col_info, col_form = st.columns(2, gap="large")

                    # === LEVÝ SLOUPEC: INFORMACE ===
                    with col_info:
                        st.markdown("#### ℹ️ Informace")
                        
                        popis_typu = f"ZÁVOD 🏆 ({druh_akce.upper()})" if je_zavod else f"TRÉNINK ({druh_akce.upper()})"
                        st.caption(f"**Typ akce:** {popis_typu}")
                        
                        st.write(f"**📍 Místo:** {akce['místo']}")
                        
                        if pd.notna(akce['popis']):
                            st.info(f"{akce['popis']}")
                        
                        deadline_str = akce['deadline'].strftime('%d.%m.%Y')
                        if je_po_deadlinu:
                            st.error(f"⛔ **Deadline:** {deadline_str} (Uzavřeno)")
                        else:
                            st.write(f"📅 **Deadline:** {deadline_str}")

                    # === PRAVÝ SLOUPEC: FORMULÁŘ / ORIS ===
                    with col_form:
                        st.markdown("#### ✍️ Přihláška")
                        
                        delete_key_state = f"confirm_delete_{akce['název']}"

                        # A) JE TO ZÁVOD
                        if je_zavod:
                            if je_po_deadlinu:
                                st.warning("Termín přihlášek vypršel.")
                                st.caption("Zkontroluj ORIS, zda není možné dohlášení.")
                            else:
                                st.write("Tohle je oficiální závod.")
                                odkaz_zavodu = str(akce['odkaz']).strip() if 'odkaz' in df_akce.columns and pd.notna(akce['odkaz']) else ""
                                link_target = odkaz_zavodu if odkaz_zavodu else "https://oris.orientacnisporty.cz/"
                                st.success("Registrace probíhá na svazovém webu.")
                                st.markdown(f"👉 [**OTEVŘÍT PŘIHLÁŠKY (ORIS)**]({link_target})")
                        
                        # B) JE TO TRÉNINK
                        else:
                            if je_po_deadlinu:
                                st.warning("Přihlašování je již uzavřeno.")
                            elif delete_key_state in st.session_state:
                                st.info("Probíhá odhlašování...")
                            else:
                                form_key = f"form_{akce['název']}_{aktualni_den}"
                                with st.form(key=form_key, clear_on_submit=True):
                                    vybrane_jmeno = st.selectbox("👤 Jméno", options=seznam_jmen, index=None, placeholder="Vyber ze seznamu...")
                                    nove_jmeno = st.text_input("...nebo napiš Nové jméno")
                                    poznamka_input = st.text_input("Poznámka (auto, odvoz...)")
                                    odeslat_btn = st.form_submit_button("✅ Přihlásit se", use_container_width=True)
                                    
                                    if odeslat_btn:
                                        finalni_jmeno = nove_jmeno.strip() if nove_jmeno else vybrane_jmeno
                                        if finalni_jmeno:
                                            uspesne_zapsano = False
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
                                                        aktualni_jmena = conn.read(worksheet="jmena", ttl=0)
                                                        novy_clen = pd.DataFrame([{"jméno": finalni_jmeno}])
                                                        updated_jmena = pd.concat([aktualni_jmena, novy_clen], ignore_index=True)
                                                        conn.update(worksheet="jmena", data=updated_jmena)
                                                    except: pass
                                                uspesne_zapsano = True
                                            except Exception as e:
                                                st.error(f"Chyba zápisu: {e}")
                                            
                                            if uspesne_zapsano:
                                                st.success(f"✅ Přihlášeno!")
                                                time.sleep(0.5)
                                                st.rerun()
                                        else: st.warning("Vyplň jméno!")

                    # ==========================================
                    # 3. SPODNÍ ČÁST: TABULKA ÚČASTNÍKŮ
                    # ==========================================
                    if not je_zavod:
                        st.markdown("---")
                        lidi = df_prihlasky[df_prihlasky['název'] == akce['název']].copy()
                        
                        st.markdown(f"#### 👥 Seznam přihlášených ({len(lidi)})")

                        # SEKCE PRO MAZÁNÍ (Zobrazí se nad tabulkou, když někdo klikne na koš)
                        if delete_key_state in st.session_state:
                            clovek_ke_smazani = st.session_state[delete_key_state]
                            with st.container(border=True):
                                st.warning(f"⚠️ Opravdu chceš odhlásit: **{clovek_ke_smazani}**?")
                                col_conf1, col_conf2 = st.columns(2)
                                if col_conf1.button("✅ ANO, Odhlásit", key=f"yes_{akce['název']}", use_container_width=True):
                                    smazano_ok = False
                                    try:
                                        df_curr = conn.read(worksheet="prihlasky", ttl=0)
                                        mask = (df_curr['název'] == akce['název']) & (df_curr['jméno'] == clovek_ke_smazani)
                                        df_clean = df_curr[~mask]
                                        conn.update(worksheet="prihlasky", data=df_clean)
                                        smazano_ok = True
                                    except Exception as e:
                                        st.error(f"Chyba mazání: {e}")
                                    if smazano_ok:
                                        del st.session_state[delete_key_state]
                                        st.success("Odhlášeno!")
                                        time.sleep(0.5)
                                        st.rerun()
                                if col_conf2.button("❌ Zrušit", key=f"no_{akce['název']}", use_container_width=True):
                                    del st.session_state[delete_key_state]
                                    st.rerun()

                        # PŘEHLEDNÁ TABULKA
                        if not lidi.empty:
                            # Streamlit dataframe je super pro přehled
                            # Upravíme data pro zobrazení
                            display_df = lidi[['jméno', 'poznámka', 'čas zápisu']].copy()
                            # Reset indexu, aby začínal od 1
                            display_df.index = range(1, len(display_df) + 1)
                            
                            # Použijeme st.dataframe s nastavením šířky
                            # Ale musíme tam dostat tlačítka na mazání.
                            # Protože st.dataframe neumí tlačítka uvnitř, použijeme raději cyklus columns,
                            # ale uděláme ho graficky hezčí (jako řádky tabulky).
                            
                            # Záhlaví "tabulky"
                            h1, h2, h3, h4 = st.columns([0.5, 3, 3, 1])
                            h1.markdown("**#**")
                            h2.markdown("**Jméno**")
                            h3.markdown("**Poznámka**")
                            h4.markdown("**Akce**")
                            st.divider()

                            for i, (idx, row) in enumerate(lidi.iterrows()):
                                c1, c2, c3, c4 = st.columns([0.5, 3, 3, 1], vertical_alignment="center")
                                c1.write(f"{i+1}.")
                                c2.write(f"**{row['jméno']}**")
                                c3.write(f"{row['poznámka']}")
                                
                                if not je_po_deadlinu:
                                    if c4.button("🗑️", key=f"del_{akce['název']}_{idx}"):
                                        st.session_state[delete_key_state] = row['jméno']
                                        st.rerun()
                                else:
                                    c4.write("🔒")
                                
                                # Decentní oddělovač
                                st.markdown("<hr style='margin: 2px 0; border-top: 1px solid #f0f0f0;'>", unsafe_allow_html=True)

                        else:
                            st.info("Zatím se nikdo nepřihlásil. Buď první! 🚀")

st.markdown("<div style='margin-bottom: 50px'></div>", unsafe_allow_html=True)


# --- 5. PLOVOUCÍ TLAČÍTKO "NÁVRH" ---
st.markdown('<div class="floating-container">', unsafe_allow_html=True)

with st.popover("💡 Návrh na zlepšení"):
    st.markdown("### 🛠️ Máš nápad?")
    st.write("Napiš nám, co vylepšit v aplikaci nebo na tréninku.")
    
    with st.form("form_navrhy", clear_on_submit=True):
        text_navrhu = st.text_area("Tvůj návrh:", height=100)
        odeslat_navrh = st.form_submit_button("Odeslat návrh")
        
        if odeslat_navrh and text_navrhu:
            uspesne_odeslano = False
            novy_navrh = pd.DataFrame([{
                "datum": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "text": text_navrhu
            }])
            try:
                try:
                    aktualni_navrhy = conn.read(worksheet="navrhy", ttl=0)
                    updated_navrhy = pd.concat([aktualni_navrhy, novy_navrh], ignore_index=True)
                except:
                    updated_navrhy = novy_navrh
                conn.update(worksheet="navrhy", data=updated_navrhy)
                uspesne_odeslano = True
            except Exception as e:
                st.error(f"Chyba: {e}")
            
            if uspesne_odeslano:
                st.toast("✅ Díky! Tvůj návrh byl uložen.")

st.markdown('</div>', unsafe_allow_html=True)

# --- PATIČKA ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #aaa; font-size: 0.8em; font-family: sans-serif; padding-bottom: 20px;'>
    <b>Členská sekce RBK</b> • Design by Broschman & Gemini<br>
    &copy; 2026 All rights reserved
</div>
""", unsafe_allow_html=True)
