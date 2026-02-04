import streamlit as st
import extra_streamlit_components as stx
import hmac
import time
from datetime import datetime, timedelta

# Nastavení expirace cookie (30 dní)
COOKIE_EXPIRY_DAYS = 30
COOKIE_NAME = "rbk_login_token"

def check_password():
    """
    Hlavní funkce pro ověření.
    """
    
    # 1. Inicializace Cookie Manageru
    cookie_manager = stx.CookieManager(key="auth_cookie_manager")
    
    # 2. Načtení existující cookie
    # dayfirst ani errors zde nejsou potřeba, get vrací string nebo None
    cookie_value = cookie_manager.get(COOKIE_NAME)
    
    # Získání správného hesla
    correct_password = str(st.secrets["general"]["password"])
    
    # A) KONTROLA COOKIE 🍪 (Pokud sedí, pouštíme dál)
    if cookie_value and hmac.compare_digest(str(cookie_value), correct_password):
        return True

    # B) KONTROLA SESSION STATE (Pro případ, že uživatel heslo právě zadal)
    if st.session_state.get("password_correct", False):
        return True

    # --- ANTI-FLASH LOGIKA ⚡ ---
    # Pokud cookie je None (prázdná), může to znamenat dvě věci:
    # 1. Uživatel je nový.
    # 2. Uživatel je starý, ale knihovna ještě nestihla načíst cookie z prohlížeče.
    # Abychom neukazovali formulář ve scénáři 2 (což způsobí bliknutí),
    # při úplně prvním průchodu jen "čekáme" a nevykreslíme formulář.
    
    if cookie_value is None:
        if "auth_cookie_checked" not in st.session_state:
            # Jsme tu poprvé po F5. Nevíme, jestli cookie existuje.
            st.session_state["auth_cookie_checked"] = True
            
            # Zobrazíme jen spinner nebo prázdno a ukončíme běh.
            # Knihovna stx sama vyvolá rerun, jakmile načte data,
            # takže se kód spustí znovu a spadne buď do A) (úspěch) nebo do C) (formulář).
            with st.spinner("Ověřuji přihlášení..."):
                time.sleep(0.5) # Malá pauza pro jistotu
                return False
                
    # C) LOGIN FORMULÁŘ
    # Sem dojdeme jen tehdy, pokud cookie načtena byla a je špatná/žádná,
    # NEBO pokud už proběhl ten "čekací" první průchod.
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.header("🌲 Vítej v klubu")
        
        with st.form("login_form"):
            password_input = st.text_input("Zadej heslo", type="password")
            submit = st.form_submit_button("Vstoupit", type="primary", use_container_width=True)
            
            if submit:
                # Porovnání hesel
                if hmac.compare_digest(password_input, correct_password):
                    # 1. Uložíme do Session State
                    st.session_state["password_correct"] = True
                    
                    # 2. Uložíme Cookie
                    expires = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
                    cookie_manager.set(COOKIE_NAME, password_input, expires_at=expires)
                    
                    st.success("✅ Přihlášeno!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Špatné heslo.")
                    
        st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em; margin-top: 20px;'>Členská sekce RBK</div>", unsafe_allow_html=True)

    return False
