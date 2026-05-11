# auth.py

import streamlit as st
import extra_streamlit_components as stx
import data_manager
import time
import base64

# Používáme v3 pro čistý start po úpravách
COOKIE_NAME = "rbk_auth_v3"

def get_manager():
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager(key="auth_mgr")
    return st.session_state.cookie_manager

def check_password():
    """
    Standardní autentizace pro členskou sekci.
    Flow: Kontrola odhlášení -> Kontrola cookie -> Přihlašovací formulář.
    """
    if st.session_state.get("authenticated", False):
        return True

    manager = get_manager()

    # 1. Zpracování požadavku na odhlášení
    if st.session_state.get("logout_requested", False):
        manager.delete(COOKIE_NAME)
        st.session_state.authenticated = False
        st.session_state.user_name = None
        st.session_state.logout_requested = False
        st.rerun()

    # 2. Automatické přihlášení přes cookie
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
                
                # Očištění PINů z GSheets (odstranění .0 a mezer)
                df_jmena['PIN_clean'] = df_jmena['PIN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                
                match = df_jmena[
                    (df_jmena['jméno'] == c_name) & 
                    (df_jmena['PIN_clean'] == str(c_pin).strip())
                ]
                
                if not match.empty:
                    st.session_state.authenticated = True
                    st.session_state.user_name = c_name
                    st.session_state.user_role = str(match.iloc[0].get('role', 'user')).lower()
                    return True
        except:
            manager.delete(COOKIE_NAME)

    # 3. Přihlašovací formulář s "normálními" texty
    st.markdown("### 🔑 Přihlášení do členské sekce")
    
    df_jmena = data_manager.get_jmena_df()
    seznam_jmen = sorted(df_jmena['jméno'].dropna().unique().tolist())
    
    with st.form("login_form"):
        jmeno = st.selectbox("Vyberte své jméno", [""] + seznam_jmen)
        pin = st.text_input("Zadejte PIN", type="password")
        submit = st.form_submit_button("Přihlásit se", use_container_width=True)
        
        if submit:
            if not jmeno or not pin:
                st.warning("Prosím, vyplňte jméno i PIN.")
            else:
                df_jmena['PIN_clean'] = df_jmena['PIN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                match = df_jmena[(df_jmena['jméno'] == jmeno) & (df_jmena['PIN_clean'] == str(pin).strip())]
                
                if not match.empty:
                    st.session_state.authenticated = True
                    st.session_state.user_name = jmeno
                    st.session_state.user_role = str(match.iloc[0].get('role', 'user')).lower()
                    
                    # Uložení do cookie (base64 pro základní obfuskaci)
                    val_to_save = base64.b64encode(f"{jmeno}|{pin}".encode()).decode()
                    manager.set(COOKIE_NAME, val_to_save)
                    
                    st.success("Přihlášení proběhlo úspěšně.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Nesprávné jméno nebo PIN.")
                    
    return False

def logout():
    """Vyvolá proces odhlášení a smazání cookies."""
    st.session_state.logout_requested = True
    st.rerun()
