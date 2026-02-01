import streamlit as st
import pandas as pd
from datetime import date, timedelta
import styles
import utils
import data_manager
import chatbot

# === CONFIG ===
st.set_page_config(page_title="Kalendář RBK", page_icon="🌲", layout="wide")
styles.load_css()
styles.inject_mobile_warning()

# === HLAVIČKA ===
st.markdown(f"""
    <h1>
        <span class="gradient-text">🌲 Kalendář</span>
        <img src="https://cdn-icons-png.flaticon.com/512/2051/2051939.png" class="header-logo">
    </h1>
""", unsafe_allow_html=True)

# === NAČTENÍ DAT ===
df_akce = data_manager.load_akce()
dnes = date.today()

# === DASHBOARD (Hořící termíny - LIGHT verze) ===
deadlines = df_akce[df_akce['deadline'] >= dnes].sort_values('deadline').head(4)
if not deadlines.empty:
    cols = st.columns(len(deadlines))
    for i, (_, row) in enumerate(deadlines.iterrows()):
        days = (row['deadline'] - dnes).days
        msg = "Dnes!" if days == 0 else f"Za {days} dní"
        icon = "🚨" if days <= 3 else "📅"
        
        # Používáme nativní Streamlit kontejnery - jsou rychlé
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"**{icon} {row['název']}**")
                st.caption(f"Deadline: {row['deadline'].strftime('%d.%m.')} ({msg})")
                with st.popover("Otevřít"):
                    utils.vykreslit_detail_akce(row, f"dash_{row['id']}")

st.divider()

# === KALENDÁŘ ===
if 'vybrany_datum' not in st.session_state: st.session_state.vybrany_datum = date.today()

c1, c2, c3 = st.columns([1, 3, 1])
if c1.button("⬅️ Předchozí měsíc"):
    st.session_state.vybrany_datum = (st.session_state.vybrany_datum.replace(day=1) - timedelta(days=1))
if c3.button("Další měsíc ➡️"):
    st.session_state.vybrany_datum = (st.session_state.vybrany_datum.replace(day=28) + timedelta(days=4))

# Název měsíce
mesice = ["", "Leden", "Únor", "Březen", "Duben", "Květen", "Červen", "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"]
curr_m = st.session_state.vybrany_datum.month
curr_y = st.session_state.vybrany_datum.year
c2.markdown(f"<h2 style='text-align:center'>{mesice[curr_m]} {curr_y}</h2>", unsafe_allow_html=True)

# Generování mřížky kalendáře (Zjednodušeno)
import calendar
cal = calendar.Calendar(firstweekday=0)
month_days = cal.monthdayscalendar(curr_y, curr_m)

# Dny v týdnu
cols = st.columns(7)
for i, d in enumerate(["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]):
    cols[i].markdown(f"<div style='text-align:center; font-weight:bold; color:#666'>{d}</div>", unsafe_allow_html=True)

# Dny
for week in month_days:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day == 0: continue
            
            # Číslo dne
            if date(curr_y, curr_m, day) == dnes:
                st.markdown(f"<span class='today-box'>{day}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"**{day}**")
            
            # Akce dne
            datum_dne = date(curr_y, curr_m, day)
            akce_dne = df_akce[(df_akce['datum'] <= datum_dne) & (df_akce['datum_do'] >= datum_dne)]
            
            for _, akce in akce_dne.iterrows():
                # Tady používáme čistá tlačítka
                typ = str(akce.get('typ', 'default')).lower()
                style_key = "default"
                if "mčr" in typ: style_key = "mcr"
                elif "trénink" in typ: style_key = "trenink"
                # ... (další typy)
                
                label = f"{akce['název'][:15]}..."
                with st.popover(label, use_container_width=True):
                    utils.vykreslit_detail_akce(akce, f"cal_{akce['id']}_{day}")

# === PLOVOUCÍ CHATBOT (Jednoduché tlačítko) ===
st.markdown('<div class="floating-container">', unsafe_allow_html=True)
with st.popover("🤖"):
    chatbot.main(df_akce)
st.markdown('</div>', unsafe_allow_html=True)

# === PATIČKA ===
st.markdown(styles.get_footer_html(), unsafe_allow_html=True)
