
import streamlit as st
import extra_streamlit_components as stx
import hmac
import time
from datetime import datetime, timedelta

# Konfigurace
COOKIE_EXPIRY_DAYS = 30
COOKIE_NAME = "rbk_login_token"

def check_password():
    """
    Vrátí True = Uživatel je uvnitř.
    Vrátí False = Uživatel vidí formulář.
    """
    
    # 1. VIP FAST TRACK (Okamžitá kontrola paměti) 🏎️
    # Pokud už víme, že je uživatel přihlášený z minula (v rámci jednoho sezení),
    # rovnou vracíme True. Neřešíme cookies, neřešíme nic. 0 ms zpoždění.
    if st.session_state.get("is_logged_in", False):
        return True

    # 2. Inicializace Cookie Manageru
    # (Toto se provede jen při prvním načtení stránky nebo F5)
    cookie_manager = stx.CookieManager(key="auth_cookie_manager")
    cookie_value = cookie_manager.get(COOKIE_NAME)
    correct_password = str(st.secrets["general"]["password"])
    
    # 3. KONTROLA COOKIE 🍪
    if cookie_value and hmac.compare_digest(str(cookie_value), correct_password):
        # Cookie je platná -> Uložíme do "VIP paměti" a pustíme dál
        st.session_state["is_logged_in"] = True
        return True

    # 4. ANTI-FLASH (Zabránění probliknutí formuláře) ⚡
    # Pokud cookie je None, může to znamenat, že se jen nestihla načíst.
    if cookie_value is None and "auth_check_completed" not in st.session_state:
        st.session_state["auth_check_completed"] = True
        try:
            st.rerun()
        except AttributeError:
            st.experimental_rerun()
        return False

    # 5. LOGIN FORMULÁŘ (Pokud nic výše neklaplo)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.header("🌲 Vítej v klubu")
        
        with st.form("login_form"):
            password_input = st.text_input("Zadej heslo", type="password")
            submit = st.form_submit_button("Vstoupit", type="primary", use_container_width=True)
            
            if submit:
                if hmac.compare_digest(password_input, correct_password):
                    # Úspěch!
                    st.session_state["is_logged_in"] = True # VIP Pass
                    
                    # Uložení cookie na příště
                    expires = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
                    cookie_manager.set(COOKIE_NAME, password_input, expires_at=expires)
                    
                    st.success("✅ Přihlášeno!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Špatné heslo.")
                    
        st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em; margin-top: 20px;'>Členská sekce RBK</div>", unsafe_allow_html=True)

    return False
