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
    Vrátí False = Uživatel vidí formulář nebo se ověřuje.
    """
    correct_password = str(st.secrets["general"]["password"])
    
    # 1. VIP FAST TRACK (Okamžitá kontrola v paměti pro dané sezení) 🏎️
    if st.session_state.get("is_logged_in", False):
        return True

    # 2. BLESKOVÉ ČTENÍ PRO NEJVĚJŠÍ STREAMLIT (1.35+) ⚡
    # Pokud máš aktualizovaný server, projde to tady s 0 ms zpožděním.
    if hasattr(st, 'context') and hasattr(st.context, 'cookies'):
        native_cookie = st.context.cookies.get(COOKIE_NAME)
        if native_cookie and hmac.compare_digest(str(native_cookie), correct_password):
            st.session_state["is_logged_in"] = True
            return True

    # 3. INICIALIZACE COOKIE MANAGERU (Pro starší verze a pro kontrolu)
    cookie_manager = stx.CookieManager(key="auth_cookie_manager")
    cookie_value = cookie_manager.get(COOKIE_NAME)
    
    # 4. ANTI-FLASH LOGIKA (Opravená) 🛡️
    # Při úplně prvním načtení stránky (kdy komponenta ještě neposlala data z prohlížeče)
    # nesmíme kreslit login formulář. Místo toho ukážeme "načítání".
    if "cookie_manager_mounted" not in st.session_state:
        st.session_state["cookie_manager_mounted"] = True
        st.markdown("<div style='text-align: center; margin-top: 80px; color: gray; font-family: sans-serif;'>Ověřuji zabezpečení... 🌲</div>", unsafe_allow_html=True)
        # Vrátíme False, čímž app.py nepokračuje dál.
        # Komponenta se mezitím načte v prohlížeči, pošle cookies a SAMA bleskově vyvolá rerun!
        return False

    # 5. KONTROLA HESLA Z COOKIE
    # Nyní už jsme ve druhém běhu, data dorazila
    if cookie_value and hmac.compare_digest(str(cookie_value), correct_password):
        st.session_state["is_logged_in"] = True
        return True

    # 6. LOGIN FORMULÁŘ (Data dorazila, uživatel opravdu nemá platnou cookie)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.header("🌲 Vítej v klubu")
        
        with st.form("login_form"):
            password_input = st.text_input("Zadej heslo", type="password")
            submit = st.form_submit_button("Vstoupit", type="primary", use_container_width=True)
            
            if submit:
                if hmac.compare_digest(password_input, correct_password):
                    st.session_state["is_logged_in"] = True 
                    expires = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
                    cookie_manager.set(COOKIE_NAME, password_input, expires_at=expires)
                    st.success("✅ Přihlášeno!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Špatné heslo.")
                    
        st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em; margin-top: 20px;'>Členská sekce RBK</div>", unsafe_allow_html=True)

    return False
