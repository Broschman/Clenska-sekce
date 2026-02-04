import streamlit as st
import extra_streamlit_components as stx
import hmac
import time
from datetime import datetime, timedelta

# Nastavení expirace cookie
COOKIE_EXPIRY_DAYS = 30
COOKIE_NAME = "rbk_login_token"

def check_password():
    """
    Vrátí True, pokud je uživatel ověřen.
    Vrátí False, pokud ne (a zobrazí login formulář).
    """
    
    # 1. Inicializace Cookie Manageru
    cookie_manager = stx.CookieManager(key="auth_cookie_manager")
    
    # 2. Načtení cookie
    cookie_value = cookie_manager.get(COOKIE_NAME)
    correct_password = str(st.secrets["general"]["password"])
    
    # --- A) COOKIE NALEZENA A JE SPRÁVNÁ ---
    if cookie_value and hmac.compare_digest(str(cookie_value), correct_password):
        return True

    # --- B) UŽIVATEL PRÁVĚ ZADAL HESLO (SESSION STATE) ---
    if st.session_state.get("password_correct", False):
        return True

    # --- C) FIX PROBLIKÁVÁNÍ (ANTI-FLASH) ⚡ ---
    # Pokud cookie je None, může to znamenat, že se jen nestihla načíst.
    # Zkontrolujeme, jestli už jsme zkusili "počkat" (pomocí flagu v session_state).
    
    if cookie_value is None and "auth_check_completed" not in st.session_state:
        # Jsme tu poprvé. Cookie je None. Nevykreslíme formulář, ale vynutíme RERUN.
        # Tím dáme CookieManageru čas, aby načetl data z prohlížeče.
        st.session_state["auth_check_completed"] = True
        try:
            st.rerun() # Okamžitý restart skriptu
        except AttributeError:
            # Fallback pro starší verze Streamlitu
            st.experimental_rerun()
        return False

    # --- D) COOKIE OPRAVDU NENÍ (ZOBRAZIT FORMULÁŘ) ---
    # Sem se dostaneme jen tehdy, pokud ani po RERUNu cookie nebyla nalezena.
    # Tzn. uživatel opravdu není přihlášený.
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.header("🌲 Vítej v klubu")
        
        with st.form("login_form"):
            password_input = st.text_input("Zadej heslo", type="password")
            submit = st.form_submit_button("Vstoupit", type="primary", use_container_width=True)
            
            if submit:
                if hmac.compare_digest(password_input, correct_password):
                    st.session_state["password_correct"] = True
                    
                    # Uložení cookie
                    expires = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
                    cookie_manager.set(COOKIE_NAME, password_input, expires_at=expires)
                    
                    st.success("✅ Přihlášeno!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Špatné heslo.")
                    
        st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em; margin-top: 20px;'>Členská sekce RBK</div>", unsafe_allow_html=True)

    return False
