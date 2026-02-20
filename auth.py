import streamlit as st
import extra_streamlit_components as stx
import hmac
import time
from datetime import datetime, timedelta
import pandas as pd
import data_manager  # Přidán import kvůli čtení z databáze

# Konfigurace
COOKIE_EXPIRY_DAYS = 30
COOKIE_NAME = "rbk_login_token"

def check_password():
    """
    Vrátí True = Uživatel je uvnitř (známe jeho identitu).
    Vrátí False = Uživatel vidí formulář nebo se ověřuje.
    """
    
    # 1. VIP FAST TRACK (Okamžitá kontrola v paměti pro dané sezení) 🏎️
    if st.session_state.get("is_logged_in", False) and "prihlaseny_uzivatel" in st.session_state:
        return True

    # Načtení databáze jmen a PINů
    try:
        conn = data_manager.get_connection()
        df_jmena = conn.read(worksheet="jmena", ttl=0)
        # Ošetření velikosti písmen v hlavičce tabulky
        col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
        col_pin = 'PIN' if 'PIN' in df_jmena.columns else 'pin'
    except Exception as e:
        st.error("Chyba při načítání databáze.")
        return False

    # 2. BLESKOVÉ ČTENÍ PRO NEJVĚJŠÍ STREAMLIT (1.35+) ⚡
    if hasattr(st, 'context') and hasattr(st.context, 'cookies'):
        native_cookie = st.context.cookies.get(COOKIE_NAME)
        # Očekáváme formát "Jméno|PIN"
        if native_cookie and "|" in native_cookie:
            saved_name, saved_pin = native_cookie.split("|", 1)
            # Vyčištění PINu v databázi (kdyby Google Sheets vracel např. 1234.0)
            df_pins_clean = df_jmena[col_pin].astype(str).str.replace(r'\.0$', '', regex=True)
            match = df_jmena[(df_jmena[col_name] == saved_name) & (df_pins_clean == saved_pin)]
            
            if not match.empty:
                st.session_state["is_logged_in"] = True
                st.session_state["prihlaseny_uzivatel"] = saved_name
                return True

    # 3. INICIALIZACE COOKIE MANAGERU 
    cookie_manager = stx.CookieManager(key="auth_cookie_manager")
    cookie_value = cookie_manager.get(COOKIE_NAME)
    
    # 4. ANTI-FLASH LOGIKA 🛡️
    if "cookie_manager_mounted" not in st.session_state:
        st.session_state["cookie_manager_mounted"] = True
        st.markdown("<div style='text-align: center; margin-top: 80px; color: gray; font-family: sans-serif;'>Ověřuji identitu... 🌲</div>", unsafe_allow_html=True)
        return False

    # 5. KONTROLA HESLA Z COOKIE (z druhého běhu)
    if cookie_value and "|" in str(cookie_value):
        saved_name, saved_pin = str(cookie_value).split("|", 1)
        df_pins_clean = df_jmena[col_pin].astype(str).str.replace(r'\.0$', '', regex=True)
        match = df_jmena[(df_jmena[col_name] == saved_name) & (df_pins_clean == saved_pin)]
        
        if not match.empty:
            st.session_state["is_logged_in"] = True
            st.session_state["prihlaseny_uzivatel"] = saved_name
            return True

    # 6. LOGIN FORMULÁŘ
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.header("🌲 Vítej v klubu")
        
        with st.form("login_form"):
            seznam_lidi = sorted(df_jmena[col_name].dropna().unique().tolist())
            vybrane_jmeno = st.selectbox("Kdo jsi?", options=seznam_lidi)
            zadavany_pin = st.text_input("Zadej svůj 4místný PIN", type="password")
            
            submit = st.form_submit_button("Vstoupit", type="primary", use_container_width=True)
            
            if submit:
                spravny_radek = df_jmena[df_jmena[col_name] == vybrane_jmeno]
                if not spravny_radek.empty:
                    real_pin = str(spravny_radek.iloc[0].get(col_pin, '')).strip()
                    if real_pin.endswith('.0'):
                        real_pin = real_pin[:-2]
                        
                    if real_pin and zadavany_pin.strip() == real_pin:
                        st.session_state["is_logged_in"] = True 
                        st.session_state["prihlaseny_uzivatel"] = vybrane_jmeno
                        
                        expires = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
                        cookie_hodnota = f"{vybrane_jmeno}|{real_pin}"
                        cookie_manager.set(COOKIE_NAME, cookie_hodnota, expires_at=expires)
                        
                        st.success(f"✅ Přihlášeno jako {vybrane_jmeno}!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ Špatný PIN.")
                else:
                    st.error("❌ Uživatel nenalezen.")
                    
        st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em; margin-top: 20px;'>Členská sekce RBK</div>", unsafe_allow_html=True)

    return False
