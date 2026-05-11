# auth.py

import streamlit as st
import extra_streamlit_components as stx
import data_manager
import time
import base64

# Použijeme tuto verzi cookie
COOKIE_NAME = "rbk_auth_v3"

def get_manager():
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager(key="auth_mgr")
    return st.session_state.cookie_manager

def check_password():
    """
    Hlavní strážce brány. 
    Synchronizováno s app.py (používá 'prihlaseny_uzivatel' a 'role').
    """
    # 1. Pokud už jsme v této session přihlášení, jedeme dál
    if st.session_state.get("authenticated", False):
        return True

    manager = get_manager()

    # 2. LOGOUT LOGIKA
    if st.session_state.get("logout_requested", False):
        manager.delete(COOKIE_NAME)
        st.session_state.authenticated = False
        st.session_state.prihlaseny_uzivatel = None
        st.session_state.role = None
        st.session_state.logout_requested = False
        st.rerun()

    # 3. KONTROLA COOKIE
    cookie_val = None
    if hasattr(st, "context") and COOKIE_NAME in st.context.cookies:
        cookie_val = st.context.cookies[COOKIE_NAME]
    else:
        cookie_val = manager.get(COOKIE_NAME)

    if cookie_val:
        try:
            decoded = base64.b64decode(cookie_val).decode("utf-8")
            if "|" in decoded:
                c_name, c_pin = decoded.split("|")
                df_jmena = data_manager.get_jmena_df()
                
                df_jmena['PIN_clean'] = df_jmena['PIN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                
                match = df_jmena[
                    (df_jmena['jméno'] == c_name) & 
                    (df_jmena['PIN_clean'] == str(c_pin).strip())
                ]
                
                if not match.empty:
                    st.session_state.authenticated = True
                    st.session_state.prihlaseny_uzivatel = c_name  # Sjednoceno s app.py
                    st.session_state.role = str(match.iloc[0].get('role', 'user')).lower()
                    return True
        except:
            manager.delete(COOKIE_NAME)

    # 4. LOGIN FORMULÁŘ
    st.markdown("### 🔑 Přihlášení do členské sekce")
    
    df_jmena = data_manager.get_jmena_df()
    seznam_jmen = sorted(df_jmena['jméno'].dropna().unique().tolist())
    
    with st.form("login_form"):
        jmeno = st.selectbox("Vyberte své jméno", [""] + seznam_jmen)
        pin = st.text_input("Zadejte PIN", type="password")
        submit = st.form_submit_button("Přihlásit se", use_container_width=True)
        
        if submit:
            if not jmeno or not pin:
                st.warning("Prosím vyberte jméno a zadejte PIN.")
            else:
                df_jmena['PIN_clean'] = df_jmena['PIN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                match = df_jmena[(df_jmena['jméno'] == jmeno) & (df_jmena['PIN_clean'] == str(pin).strip())]
                
                if not match.empty:
                    st.session_state.authenticated = True
                    st.session_state.prihlaseny_uzivatel = jmeno  # Sjednoceno s app.py
                    st.session_state.role = str(match.iloc[0].get('role', 'user')).lower()
                    
                    val_to_save = base64.b64encode(f"{jmeno}|{pin}".encode()).decode()
                    manager.set(COOKIE_NAME, val_to_save)
                    
                    st.success("Přihlášení proběhlo úspěšně.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Nesprávné jméno nebo PIN.")
                    
    return False

def logout():
    st.session_state.logout_requested = True
    st.rerun()
