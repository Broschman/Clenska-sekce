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
    Vrátí True = Uživatel je uvnitř (bez probliknutí).
    Vrátí False = Uživatel vidí formulář.
    """
    correct_password = str(st.secrets["general"]["password"])
    
    # 1. VIP FAST TRACK (Okamžitá kontrola v rámci jedné session) 🏎️
    if st.session_state.get("is_logged_in", False):
        return True

    # 2. BLESKOVÉ ČTENÍ COOKIES (Nativní Streamlit 1.35+) ⚡
    # Tohle se děje na pozadí, 0 ms zpoždění, nepotřebuje roundtrip do prohlížeče.
    if hasattr(st, 'context') and hasattr(st.context, 'cookies'):
        native_cookie = st.context.cookies.get(COOKIE_NAME)
        if native_cookie and hmac.compare_digest(str(native_cookie), correct_password):
            st.session_state["is_logged_in"] = True
            return True

    # 3. Inicializace Cookie Manageru (už jen pro ZÁPIS nového hesla)
    cookie_manager = stx.CookieManager(key="auth_cookie_manager")

    # Pokud kód došel až sem, uživatel na 100 % nemá platnou cookie.
    # Žádný ANTI-FLASH už nepotřebujeme, protože nativní čtení by ho zachytilo hned.

    # 4. LOGIN FORMULÁŘ
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
                    st.session_state["is_logged_in"] = True 
                    
                    # Uložení cookie na příště přes stx.CookieManager
                    expires = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
                    cookie_manager.set(COOKIE_NAME, password_input, expires_at=expires)
                    
                    st.success("✅ Přihlášeno!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Špatné heslo.")
                    
        st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em; margin-top: 20px;'>Členská sekce RBK</div>", unsafe_allow_html=True)

    return False
