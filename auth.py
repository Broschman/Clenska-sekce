import streamlit as st
import extra_streamlit_components as stx
import time
from datetime import datetime, timedelta
import pandas as pd
import data_manager
import base64

# Konfigurace
COOKIE_EXPIRY_DAYS = 30
COOKIE_NAME = "rbk_login_token"

def check_password():
    if st.session_state.get("is_logged_in", False) and "prihlaseny_uzivatel" in st.session_state:
        return True

    try:
        conn = data_manager.get_connection()
        df_jmena = conn.read(worksheet="jmena", ttl=0)
        col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
        col_pin = 'PIN' if 'PIN' in df_jmena.columns else 'pin'
        col_role = 'role' if 'role' in df_jmena.columns else 'Role'
    except Exception:
        st.error("Chyba při načítání databáze.")
        return False

    # 1. BLESKOVÉ ČTENÍ COOKIES (Base64 + Očištění \u00A0)
    if hasattr(st, 'context') and hasattr(st.context, 'cookies'):
        native_cookie = st.context.cookies.get(COOKIE_NAME)
        if native_cookie:
            try:
                decoded_cookie = base64.b64decode(native_cookie).decode('utf-8')
            except:
                decoded_cookie = str(native_cookie)
                
            if "|" in decoded_cookie:
                saved_name, saved_pin = decoded_cookie.split("|", 1)
                
                # Odstranění neviditelného štítu a nul
                df_pins_clean = df_jmena[col_pin].astype(str).str.replace('\u00A0', '').str.strip().str.replace(r'\.0$', '', regex=True)
                match = df_jmena[(df_jmena[col_name] == saved_name) & (df_pins_clean == saved_pin)]
                
                if not match.empty:
                    st.session_state["is_logged_in"] = True
                    st.session_state["prihlaseny_uzivatel"] = saved_name
                    st.session_state["role"] = str(match.iloc[0].get(col_role, '')).strip().lower()
                    return True

    cookie_manager = stx.CookieManager(key="auth_cookie_manager")
    cookie_value = cookie_manager.get(COOKIE_NAME)
    
    # 2. ANTI-FLASH LOGIKA
    if "cookie_manager_mounted" not in st.session_state:
        st.session_state["cookie_manager_mounted"] = True
        st.markdown("<div style='text-align: center; margin-top: 80px; color: gray; font-family: sans-serif;'>Ověřuji identitu... 🌲</div>", unsafe_allow_html=True)
        return False

    # 3. KONTROLA COOKIES Z MANAGERU (Druhý běh)
    if cookie_value:
        try:
            decoded_cookie = base64.b64decode(str(cookie_value)).decode('utf-8')
        except:
            decoded_cookie = str(cookie_value)
            
        if "|" in decoded_cookie:
            saved_name, saved_pin = decoded_cookie.split("|", 1)
            df_pins_clean = df_jmena[col_pin].astype(str).str.replace('\u00A0', '').str.strip().str.replace(r'\.0$', '', regex=True)
            match = df_jmena[(df_jmena[col_name] == saved_name) & (df_pins_clean == saved_pin)]
            
            if not match.empty:
                st.session_state["is_logged_in"] = True
                st.session_state["prihlaseny_uzivatel"] = saved_name
                st.session_state["role"] = str(match.iloc[0].get(col_role, '')).strip().lower()
                return True

    # 4. LOGIN FORMULÁŘ
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.header("🌲 Vítej v klubu")
        
        with st.form("login_form"):
            seznam_lidi = sorted(df_jmena[col_name].dropna().unique().tolist())
            vybrane_jmeno = st.selectbox("Kdo jsi?", options=seznam_lidi)
            zadavany_pin = st.text_input("Zadej své heslo", type="password")
            
            submit = st.form_submit_button("Vstoupit", type="primary", use_container_width=True)
            
            if submit:
                spravny_radek = df_jmena[df_jmena[col_name] == vybrane_jmeno]
                if not spravny_radek.empty:
                    # Vyčištění PINu z databáze před kontrolou
                    real_pin = str(spravny_radek.iloc[0].get(col_pin, '')).replace('\u00A0', '').strip()
                    if real_pin.endswith('.0'): real_pin = real_pin[:-2]
                        
                    if real_pin and zadavany_pin.strip() == real_pin:
                        st.session_state["is_logged_in"] = True 
                        st.session_state["prihlaseny_uzivatel"] = vybrane_jmeno
                        st.session_state["role"] = str(spravny_radek.iloc[0].get(col_role, '')).strip().lower()
                        
                        expires = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
                        
                        # ZDE JE TEN HACK PRO COOKIES (Base64)
                        cookie_str = f"{vybrane_jmeno}|{real_pin}"
                        cookie_hodnota = base64.b64encode(cookie_str.encode('utf-8')).decode('utf-8')
                        cookie_manager.set(COOKIE_NAME, cookie_hodnota, expires_at=expires)
                        
                        st.success(f"✅ Přihlášeno jako {vybrane_jmeno}!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ Špatné heslo.")
                else:
                    st.error("❌ Uživatel nenalezen.")
                    
        st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em; margin-top: 20px;'>Členská sekce RBK</div>", unsafe_allow_html=True)

    return False
