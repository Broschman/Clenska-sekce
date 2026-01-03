import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import time

# --- 1. NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Kalendář RBK", page_icon="🌲", layout="wide")

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

    /* === ŠIROKÁ BUBLINA === */
    div[data-testid="stPopoverBody"] {
        width: 750px !important;      
        max-width: 95vw !important;   
        max-height: 80vh !important;
    }

    /* Tlačítka nápovědy */
    div[data-testid="column"] div[data-testid="stPopover"] > button {
        border-radius: 50% !important;
        width: 35px !important;
        height: 35px !important;
        border: 1px solid #ccc !important;
        color: #555 !important;
        background-color: white !important;
        padding: 0 !important;
    }

    /* Plovoucí tlačítko */
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
    }
    .floating-container button:hover {
        transform: scale(1.05) !important;
        background-color: #FFD54F !important;
    }

    /* Dnešní den */
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
    
    /* === VZHLED TLAČÍTEK V KALENDÁŘI === */
    div[data-testid="column"] button {
        border: 1px solid #eee !important;
        background-color: white !important;
        width: 100% !important;
        padding: 4px !important;
        border-radius: 8px !important;
        text-align: left !important;
        transition: transform 0.1s;
    }
    
    div[data-testid="column"] button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
        border-color: #ccc !important;
        z-index: 2;
    }
    
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- HLAVIČKA ---
col_dummy, col_title, col_help = st.columns([1, 10, 1], vertical_alignment="center")

with col_title:
    st.title("🌲 Kalendář RBK")

with col_help:
    with st.popover("❔", help="Nápověda k aplikaci"):
        st.markdown("### 💡 Nápověda")
        st.info("📱 **Mobil:** Otoč telefon na šířku.")
        
        st.markdown("""
        **Barevné rozlišení:**
        * :rainbow-background[MČR / Mistrovství]
        * :red-background[Závod ŽA] (Žebříček A)
        * :orange-background[Závod ŽB / Soustředění]
        * :blue-background[Oblastní žebříček]
        * :gray-background[Zimní liga (BZL)]
        * :violet-background[Štafety]
        * :green-background[Trénink]
        
        **Tipy:**
        * **🚗 Doprava:** Pokud nemáš odvoz, zaškrtni *"Sháním odvoz"*.
        * **🗑️ Odhlášení:** Klikni na koš a pak potvrď tlačítkem **ANO**.
        * **⚠️ Deadline:** Pokud je deadline dnes, máš poslední šanci!
        """)
        
        st.divider()
        st.markdown("**Terén:** 🌲 Les | 🏙️ Sprint | 🌗 Nočák")


# --- 2. PŘIPOJENÍ A NAČTENÍ DAT ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_ID = "1lW6DpUQBSm5heSO_HH9lDzm0x7t1eo8dn6FpJHh2y6U"

url_akce = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=akce"
url_prihlasky = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=prihlasky"
url_jmena = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=jmena"
url_navrhy = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=navrhy"

try:
    df_akce = pd.read_csv(url_akce)
    # Zpracování data začátku
    df_akce['datum'] = pd.to_datetime(df_akce['datum'], dayfirst=True, errors='coerce').dt.date
    
    # Zpracování data konce (pro vícedenní akce)
    if 'datum_do' in df_akce.columns:
        df_akce['datum_do'] = pd.to_datetime(df_akce['datum_do'], dayfirst=True, errors='coerce').dt.date
        df_akce['datum_do'] = df_akce['datum_do'].fillna(df_akce['datum'])
    else:
        df_akce['datum_do'] = df_akce['datum']

    # Zpracování deadlinu
    df_akce['deadline'] = pd.to_datetime(df_akce['deadline'], dayfirst=True, errors='coerce').dt.date
    df_akce = df_akce.dropna(subset=['datum'])
    
    # --- FIX PRO CHYBĚJÍCÍ DEADLINE ---
    def get_deadline(row):
        if pd.isna(row['deadline']):
            return row['datum'] - timedelta(days=14)
        return row['deadline']

    df_akce['deadline'] = df_akce.apply(get_deadline, axis=1)

    if 'id' in df_akce.columns:
        df_akce['id'] = df_akce['id'].astype(str).str.replace(r'\.0$', '', regex=True)
    
    try:
        df_prihlasky = pd.read_csv(url_prihlasky)
        if 'doprava' not in df_prihlasky.columns: df_prihlasky['doprava'] = ""
        if 'id_akce' not in df_prihlasky.columns: df_prihlasky['id_akce'] = ""
        df_prihlasky['id_akce'] = df_prihlasky['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
    except:
        df_prihlasky = pd.DataFrame(columns=["id_akce", "název", "jméno", "poznámka", "doprava", "čas zápisu"])
        
    try:
        df_jmena = pd.read_csv(url_jmena)
        seznam_jmen = sorted(df_jmena['jméno'].dropna().unique().tolist())
    except:
        seznam_jmen = []
        
except Exception as e:
    st.error(f"⚠️ Chyba načítání dat: {e}")
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

            # AKCE (VÍCEDENNÍ LOGIKA)
            maska_dne = (df_akce['datum'] <= aktualni_den) & (df_akce['datum_do'] >= aktualni_den)
            akce_dne = df_akce[maska_dne]
            
            for _, akce in akce_dne.iterrows():
                je_po_deadlinu = dnes > akce['deadline']
                je_dnes_deadline = dnes == akce['deadline']
                
                akce_id_str = str(akce['id']) if 'id' in df_akce.columns else ""
                
                # --- UNIKÁTNÍ KLÍČ (FIX CHYBY) ---
                # Klíč musí obsahovat i aktuální den, aby se neopakovalo ID u vícedenních akcí
                unique_suffix = f"{akce_id_str}_{aktualni_den.strftime('%Y%m%d')}"

                # DATA
                typ_udalosti = str(akce['typ']).lower().strip() if 'typ' in df_akce.columns and pd.notna(akce['typ']) else ""
                druh_akce = str(akce['druh']).lower().strip() if 'druh' in df_akce.columns and pd.notna(akce['druh']) else "ostatní"
                
                je_stafeta = "štafety" in typ_udalosti
                zavodni_slova = ["závod", "mčr", "žebříček", "liga", "mistrovství", "štafety", "ža", "žb"]
                je_zavod_obecne = any(s in typ_udalosti for s in zavodni_slova)

                # --- BAREVNÉ ROZLIŠENÍ ---
                bg_style = "gray"
                typ_label_short = "AKCE"

                if "mčr" in typ_udalosti or "mistrovství" in typ_udalosti:
                    bg_style = "rainbow"
                    typ_label_short = "MČR"
                elif "ža" in typ_udalosti or "žebříček a" in typ_udalosti:
                    bg_style = "red"
                    typ_label_short = "ŽA"
                elif "žb" in typ_udalosti or "žebříček b" in typ_udalosti:
                    bg_style = "orange"
                    typ_label_short = "ŽB"
                elif "oblastní" in typ_udalosti or "žebříček" in typ_udalosti:
                    bg_style = "blue"
                    typ_label_short = "OBLASTNÍ"
                elif "zimní liga" in typ_udalosti or "bzl" in typ_udalosti:
                    bg_style = "gray"
                    typ_label_short = "ZIMNÍ LIGA"
                elif "štafety" in typ_udalosti:
                    bg_style = "violet"
                    typ_label_short = "ŠTAFETY"
                elif "trénink" in typ_udalosti:
                    bg_style = "green"
                    typ_label_short = "TRÉNINK"
                elif "soustředění" in typ_udalosti:
                    bg_style = "orange"
                    typ_label_short = "SOUSTŘEDĚNÍ"
                elif je_zavod_obecne:
                    bg_style = "blue"
                    typ_label_short = "ZÁVOD"

                ikony_mapa = {
                    "les": "🌲", "krátká trať": "🌲", "klasická trať": "🌲",
                    "sprint": "🏙️", "nočák": "🌗"
                }
                emoji_druh = ikony_mapa.get(druh_akce, "")

                nazev_full = akce['název']
                if '-' in nazev_full:
                    display_text = nazev_full.split('-')[0].strip()
                else:
                    display_text = nazev_full

                final_text = f"{emoji_druh} {display_text}".strip()
                if je_po_deadlinu:
                    final_text = "🔒 " + final_text
                
                label_tlacitka = f":{bg_style}-background[{final_text}]"
                
                # --- POPOVER ---
                with st.popover(label_tlacitka, use_container_width=True):
                    col_info, col_form = st.columns([1.2, 1], gap="medium")
                    
                    with col_info:
                        st.markdown(f"### {nazev_full}")
                        st.caption(f"Typ akce: {typ_label_short} ({druh_akce.upper()})")
                        st.write(f"**📍 Místo:** {akce['místo']}")
                        
                        if akce['datum'] != akce['datum_do']:
                            d_start = akce['datum'].strftime('%d.%m.')
                            d_end = akce['datum_do'].strftime('%d.%m.%Y')
                            st.write(f"**🗓️ Termín:** {d_start} – {d_end}")
                        
                        kategorie_txt = str(akce['kategorie']).strip() if 'kategorie' in df_akce.columns and pd.notna(akce['kategorie']) else ""
                        if kategorie_txt:
                            st.write(f"**🎯 Tato akce je určena pro:** {kategorie_txt}")
                        
                        if pd.notna(akce['popis']): st.info(f"📝 {akce['popis']}")
                        
                        deadline_str = akce['deadline'].strftime('%d.%m.%Y')
                        
                        if je_po_deadlinu:
                            st.error(f"⛔ Přihlášky uzavřeny (Deadline: {deadline_str})")
                        elif je_dnes_deadline:
                            st.warning(f"⚠️ Dnes je deadline! ({deadline_str})")
                        else:
                            st.caption(f"📅 Deadline přihlášek: {deadline_str}")

                        if je_zavod_obecne:
                            st.markdown("---")
                            st.markdown("**Informace k závodu:**")
                            
                            odkaz_zavodu = str(akce['odkaz']).strip() if 'odkaz' in df_akce.columns and pd.notna(akce['odkaz']) else ""
                            link_target = odkaz_zavodu if odkaz_zavodu else "https://oris.orientacnisporty.cz/"
                            
                            st.caption("Přihlášky probíhají v systému ORIS.")
                            if je_stafeta:
                                st.warning("⚠️ **ŠTAFETY:** Přihlaš se **I ZDE (vpravo)** kvůli soupiskám!")
                            
                            st.markdown(f"👉 [**ℹ️ Stránka závodu v ORISu**]({link_target})")

                    with col_form:
                        delete_key_state = f"confirm_delete_{akce_id_str}"
                        
                        if (not je_zavod_obecne or je_stafeta):
                            if not je_po_deadlinu and delete_key_state not in st.session_state:
                                nadpis_form = "✍️ Soupiska" if je_stafeta else "✍️ Přihláška"
                                st.markdown(f"#### {nadpis_form}")
                                
                                # === OPRAVENÝ UNIKÁTNÍ KLÍČ FORMULÁŘE ===
                                form_key = f"form_{unique_suffix}"
                                
                                with st.form(key=form_key, clear_on_submit=True):
                                    if kategorie_txt and kategorie_txt.lower() != "všichni":
                                        st.warning(f"⚠️ Opravdu splňuješ podmínku? Tato akce je určena pro: **{kategorie_txt}**")
                                    
                                    vybrane_jmeno = st.selectbox("Jméno", options=seznam_jmen, index=None, placeholder="Vyber...")
                                    nove_jmeno = st.text_input("...nebo Nové jméno")
                                    poznamka_input = st.text_input("Poznámka")
                                    doprava_input = st.checkbox("🚗 Sháním odvoz")
                                    
                                    odeslat_btn = st.form_submit_button("Zapsat se" if je_stafeta else "Přihlásit se")
                                    
                                    if odeslat_btn:
                                        finalni_jmeno = nove_jmeno.strip() if nove_jmeno else vybrane_jmeno
                                        if finalni_jmeno:
                                            uspesne_zapsano = False
                                            hodnota_dopravy = "Ano 🚗" if doprava_input else ""
                                            
                                            novy_zaznam = pd.DataFrame([{
                                                "id_akce": akce_id_str,
                                                "název": akce['název'],
                                                "jméno": finalni_jmeno,
                                                "poznámka": poznamka_input,
                                                "doprava": hodnota_dopravy,
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
                                                st.error(f"Chyba: {e}")
                                            
                                            if uspesne_zapsano:
                                                st.success(f"✅ Hotovo!")
                                                time.sleep(0.5)
                                                st.rerun()
                                        else: st.warning("Vyplň jméno!")
                            elif je_po_deadlinu:
                                st.info("Přihlašování bylo ukončeno.")
                        elif je_zavod_obecne:
                            pass

                    st.divider()

                    if not je_zavod_obecne or je_stafeta:
                        if akce_id_str:
                            lidi = df_prihlasky[df_prihlasky['id_akce'] == akce_id_str].copy()
                        else:
                            lidi = pd.DataFrame()

                        nadpis_seznam = f"👥 Zájemci o štafetu ({len(lidi)})" if je_stafeta else f"👥 Přihlášeno ({len(lidi)})"
                        st.markdown(f"#### {nadpis_seznam}")

                        if delete_key_state in st.session_state:
                            clovek_ke_smazani = st.session_state[delete_key_state]
                            st.warning(f"⚠️ Opravdu odhlásit: **{clovek_ke_smazani}**?")
                            col_conf1, col_conf2 = st.columns(2)
                            
                            # === OPRAVENÉ UNIKÁTNÍ KLÍČE PRO DELETE POTVRZENÍ ===
                            if col_conf1.button("✅ ANO", key=f"yes_{unique_suffix}"):
                                smazano_ok = False
                                try:
                                    df_curr = conn.read(worksheet="prihlasky", ttl=0)
                                    df_curr['id_akce'] = df_curr['id_akce'].astype(str).str.replace(r'\.0$', '', regex=True)
                                    mask = (df_curr['id_akce'] == akce_id_str) & (df_curr['jméno'] == clovek_ke_smazani)
                                    df_clean = df_curr[~mask]
                                    conn.update(worksheet="prihlasky", data=df_clean)
                                    smazano_ok = True
                                except Exception as e: st.error(f"Chyba: {e}")
                                if smazano_ok:
                                    del st.session_state[delete_key_state]
                                    st.success("Smazáno!")
                                    time.sleep(0.5)
                                    st.rerun()
                            if col_conf2.button("❌ ZPĚT", key=f"no_{unique_suffix}"):
                                del st.session_state[delete_key_state]
                                st.rerun()

                        if not lidi.empty:
                            h1, h2, h3, h4, h5 = st.columns([0.4, 2.0, 2.0, 0.8, 0.5]) 
                            h1.markdown("**#**")
                            h2.markdown("**Jméno**")
                            h3.markdown("**Poznámka**")
                            h4.markdown("Shnáním dopravu 🚗")
                            h5.markdown("") 
                            
                            st.markdown("<hr style='margin: 5px 0 10px 0; border-top: 2px solid #ccc;'>", unsafe_allow_html=True)
                            
                            for i, (idx, row) in enumerate(lidi.iterrows()):
                                c1, c2, c3, c4, c5 = st.columns([0.4, 2.0, 2.0, 0.8, 0.5], vertical_alignment="center")
                                
                                c1.write(f"{i+1}.")
                                c2.markdown(f"**{row['jméno']}**")
                                poznamka_txt = row['poznámka'] if pd.notna(row['poznámka']) else ""
                                c3.caption(poznamka_txt)
                                doprava_val = str(row['doprava']) if pd.notna(row.get('doprava')) else ""
                                c4.write(doprava_val)
                                
                                if not je_po_deadlinu:
                                    # === OPRAVENÝ UNIKÁTNÍ KLÍČ PRO TLAČÍTKO SMAZAT ===
                                    if c5.button("🗑️", key=f"del_{unique_suffix}_{idx}"):
                                        st.session_state[delete_key_state] = row['jméno']
                                        st.rerun()
                                
                                st.markdown("<hr style='margin: 0; border-top: 1px solid #f0f0f0;'>", unsafe_allow_html=True)
                        else:
                            st.caption("Zatím nikdo.")

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
                st.error(f"Chyba při ukládání: {e}")
            
            if uspesne_odeslano:
                st.toast("✅ Díky! Tvůj návrh byl uložen.")

st.markdown('</div>', unsafe_allow_html=True)

# --- PATIČKA ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #aaa; font-size: 0.8em; font-family: sans-serif; padding-bottom: 20px;'>
    <b>Členská sekce RBK</b> • Designed by Broschman<br>
    &copy; 2026 All rights reserved
</div>
""", unsafe_allow_html=True)
