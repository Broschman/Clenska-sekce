import streamlit as st
import extra_streamlit_components as stx
import hmac
import time
from datetime import datetime, timedelta

# Nastavení expirace cookie (např. 30 dní)
COOKIE_EXPIRY_DAYS = 30
COOKIE_NAME = "rbk_login_token"

def check_password():
    """
    Hlavní funkce pro ověření.
    Vrátí True = Uživatel je přihlášen (buď má cookie, nebo právě zadal heslo).
    Vrátí False = Uživatel není přihlášen (zobrazí se formulář).
    """
    
    # 1. Inicializace Cookie Manageru
    # Pozor: klíč musí být unikátní pro celou appku
    cookie_manager = stx.CookieManager(key="auth_cookie_manager")
    
    # Načtení existující cookie
    cookie_value = cookie_manager.get(name=COOKIE_NAME)
    
    # Získání správného hesla ze secrets
    correct_password = st.secrets["general"]["password"]
    
    # A) KONTROLA COOKIE (Rychlý průchod)
    # Pokud cookie existuje a shoduje se s heslem (v reálu bychom hashovali, ale pro klub stačí toto)
    if cookie_value and hmac.compare_digest(str(cookie_value), str(correct_password)):
        return True

    # B) KONTROLA SESSION STATE (Pro případ, že cookie ještě nedoběhla)
    if st.session_state.get("password_correct", False):
        return True

    # C) LOGIN FORMULÁŘ
    # Pokud nejsme přihlášeni, ukážeme okno
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.header("🌲 Vítej v klubu")
        
        with st.form("login_form"):
            password_input = st.text_input("Zadej heslo", type="password")
            submit = st.form_submit_button("Vstoupit", type="primary", use_container_width=True)
            
            if submit:
                if hmac.compare_digest(password_input, correct_password):
                    # 1. Uložíme do Session State (pro okamžitou reakci)
                    st.session_state["password_correct"] = True
                    
                    # 2. Uložíme Cookie (pro příští návštěvu)
                    expires = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
                    cookie_manager.set(COOKIE_NAME, password_input, expires_at=expires)
                    
                    st.success("✅ Přihlášeno! Vítej.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Špatné heslo.")
                    
        st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em; margin-top: 20px;'>Členská sekce RBK</div>", unsafe_allow_html=True)

    # Zastavíme vykonávání zbytku appky, dokud není login hotov
    return False
