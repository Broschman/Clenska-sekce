import streamlit as st
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import time
import json

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
    
    /* ZÁKLADNÍ VZHLED TLAČÍTKA V KALENDÁŘI (Barvy se dodají přes JS) */
    div[data-testid="column"] button {
        border-radius: 6px !important;
        width: 100% !important;
        height: auto !important;
        min-height: 50px !important;
        border: 1px solid #ddd !important;
        text-align: left !important;
        color: #333 !important;
        padding: 6px 10px !important;
        line-height: 1.2 !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        transition: transform 0.1s;
    }
    div[data-testid="column"] button:hover {
        transform: scale(1.02);
        z-index: 2;
        border-color: #999 !important;
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
        * <span style='color:#2E7D32'><b>■</b></span> **Trénink**
        * <span style='color:#C62828'><b>■</b></span> **Závody** (ŽA, ŽB, Oblastní)
        * <span style='color:#F57F17'><b>■</b></span> **MČR** (Mistrovství)
        * <span style='color:#E65100'><b>■</b></span> **Štafety**
        * <span style='color:#6A1B9A'><b>■</b></span> **Soustředění**
        * <span style='color:#1565C0'><b>■</b></span> **Zimní liga**
        
        **Tipy:**
        * **🚗 Doprava:** Pokud nemáš odvoz, zaškrtni *"Sháním odvoz"*.
        * **🗑️ Odhlášení:** Klikni na koš a pak potvrď tlačítkem **ANO**.
        * **🏆 Štafety:** Hlas se v ORISu i ZDE.
        * **⚠️ Deadline:** Pokud je deadline dnes, máš poslední šanci!
        """, unsafe_allow_html=True)
        
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
    df_akce['datum'] = pd.to_datetime(df_akce['datum'], dayfirst=True, errors='coerce').dt.date
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

# Zde budeme sbírat styly pro všechna tlačítka, abychom je pak poslali do JS
buttons_to_style = []

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
                je_dnes_deadline = dnes == akce['deadline']
                
                akce_id_str = str(akce['id']) if 'id' in df_akce.columns else ""

                # DATA
                typ_udalosti = str(akce['typ']).lower().strip() if 'typ' in df_akce.columns and pd.notna(akce['typ']) else ""
                druh_akce = str(akce['druh']).lower().strip() if 'druh' in df_akce.columns and pd.notna(akce['druh']) else "ostatní"
                
                je_stafeta = "štafety" in typ_udalosti
                zavodni_slova = ["závod", "mčr", "žebříček", "liga", "mistrovství", "štafety"]
                je_zavod = any(s in typ_udalosti for s in zavodni_slova)

                # --- URČENÍ BARVY POZADÍ (BEZ EMOJI) ---
                bg_color = "#f0f0f0" # Default šedá
                border_color = "#ccc"
                text_color = "#333"

                if "trénink" in typ_udalosti:
                    bg_color = "#E8F5E9" # Světle zelená
                    border_color = "#2E7D32" # Tmavě zelená
                    text_color = "#1B5E20"
                elif "soustředění" in typ_udalosti:
                    bg_color = "#F3E5F5" # Fialová
                    border_color = "#8E24AA"
                    text_color = "#4A148C"
                elif "štafety" in typ_udalosti:
                    bg_color = "#FFF3E0" # Oranžová
                    border_color = "#EF6C00"
                    text_color = "#E65100"
                elif "mčr" in typ_udalosti or "mistrovství" in typ_udalosti:
                    bg_color = "#FFF8E1" # Zlatá
                    border_color = "#FFD700"
                    text_color = "#F57F17"
                elif "zimní liga" in typ_udalosti:
                    bg_color = "#E3F2FD" # Modrá
                    border_color = "#1565C0"
                    text_color = "#0D47A1"
                elif je_zavod:
                    bg_color = "#FFEBEE" # Červená
                    border_color = "#C62828"
                    text_color = "#B71C1C"

                ikony_mapa = {
                    "les": "🌲", "krátká trať": "🌲", "klasická trať": "🌲",
                    "sprint": "🏙️", "nočák": "🌗"
                }
                emoji_druh = ikony_mapa.get(druh_akce, "")

                # TEXT TLAČÍTKA (ČISTÝ, BEZ BARVY)
                display_text_full = f"{emoji_druh} {akce['název']}".strip()
                if je_po_deadlinu: 
                    display_text_full = "🔒 " + display_text_full
                
                # Zkrácení pro zobrazení
                label_tlacitka = display_text_full
                if '-' in label_tlacitka:
                    label_tlacitka = label_tlacitka.split('-')[0].strip()

                # ULOŽENÍ STYLU PRO JS (Podle přesného textu)
                buttons_to_style.append({
                    "text": label_tlacitka,
                    "bg": bg_color,
                    "border": border_color,
                    "color": text_color
                })

                # --- POPOVER ---
                with st.popover(label_tlacitka, use_container_width=True):
                    col_info, col_form = st.columns([1.2, 1], gap="medium")
                    
                    with col_info:
                        st.markdown(f"### {akce['název']}")
                        
                        if je_stafeta: typ_label = "ŠTAFETY"
                        elif "mčr" in typ_udalosti: typ_label = "MČR"
                        elif je_zavod: typ_label = "ZÁVOD"
                        elif "soustředění" in typ_udalosti: typ_label = "SOUSTŘEDĚNÍ"
                        else: typ_label = "TRÉNINK"
                        
                        st.caption(f"Typ akce: {typ_label} ({druh_akce.upper()})")
                        st.write(f"**📍 Místo:** {akce['místo']}")
                        
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

                        if je_zavod:
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
                        
                        if (not je_zavod or je_stafeta):
                            if not je_po_deadlinu and delete_key_state not in st.session_state:
                                nadpis_form = "✍️ Soupiska" if je_stafeta else "✍️ Přihláška"
                                st.markdown(f"#### {nadpis_form}")
                                
                                form_key = f"form_{akce_id_str}"
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
                        elif je_zavod:
                            pass

                    st.divider()

                    if not je_zavod or je_stafeta:
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
                            if col_conf1.button("✅ ANO", key=f"yes_{akce_id_str}"):
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
                            if col_conf2.button("❌ ZPĚT", key=f"no_{akce_id_str}"):
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
                                    if c5.button("🗑️", key=f"del_{akce_id_str}_{idx}"):
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

# --- 6. JS INJECTION: BARVENÍ TLAČÍTEK ---
# Převedeme seznam stylů na JSON, aby mu JS rozuměl
styles_json = json.dumps(buttons_to_style)

js_code = f"""
<script>
    const styles = {styles_json};

    function applyStyles() {{
        const buttons = window.parent.document.querySelectorAll('div[data-testid="column"] button');
        
        buttons.forEach(btn => {{
            // Najdeme odpovídající styl podle textu tlačítka
            const match = styles.find(s => btn.innerText.includes(s.text));
            
            if (match) {{
                btn.style.backgroundColor = match.bg;
                btn.style.borderLeft = '6px solid ' + match.border;
                btn.style.color = match.color;
            }}
        }});
    }}

    // Spustíme hned a pak opakovaně (kvůli překreslování Streamlitu)
    applyStyles();
    setInterval(applyStyles, 500);
</script>
"""
components.html(js_code, height=0, width=0)

# --- PATIČKA ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #aaa; font-size: 0.8em; font-family: sans-serif; padding-bottom: 20px;'>
    <b>Členská sekce RBK</b> • Designed by Broschman<br>
    &copy; 2026 All rights reserved
</div>
""", unsafe_allow_html=True)
