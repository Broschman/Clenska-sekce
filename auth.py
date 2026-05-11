import streamlit as st
import extra_streamlit_components as argostick  # CookieManager
from data_manager import get_jmena_df
import time

# Konstanta pro název cookie
COOKIE_NAME = "rbk_auth_token"

def get_manager():
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = argostick.CookieManager()
    return st.session_state.cookie_manager

def check_password():
    """
    Vrací True, pokud je uživatel autentizován.
    Řeší flow: Kontrola cookie -> Odhlášení -> Login Form.
    """
    cookie_manager = get_manager()
    
    # 1. Inicializace stavu, pokud neexistuje
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = None
    if "user_role" not in st.session_state:
        st.session_state["user_role"] = "user"

    # 2. Načtení cookies (musíme chvíli počkat, než komponenta zareaguje)
    cookies = cookie_manager.get_all()
    auth_cookie = cookies.get(COOKIE_NAME)

    # 3. LOGIKA ODHLÁŠENÍ (Triggerováno z app.py přes session_state)
    if st.session_state.get("logout_requested", False):
        cookie_manager.delete(COOKIE_NAME)
        st.session_state["authenticated"] = False
        st.session_state["user_name"] = None
        st.session_state["logout_requested"] = False
        st.rerun()

    # 4. AUTOMATICKÉ PŘIHLÁŠENÍ PŘES COOKIE
    # Pokud nejsme v session_state přihlášení, ale máme platnou cookie
    if not st.session_state["authenticated"] and auth_cookie:
        df_jmena = get_jmena_df()
        # Cookie ukládáme ve formátu "Jméno|PIN"
        if "|" in auth_cookie:
            c_name, c_pin = auth_cookie.split("|")
            user_match = df_jmena[
                (df_jmena['jméno'] == c_name) & 
                (df_jmena['PIN'].astype(str) == str(c_pin))
            ]
            
            if not user_match.empty:
                st.session_state["authenticated"] = True
                st.session_state["user_name"] = c_name
                st.session_state["user_role"] = user_match.iloc[0].get('role', 'user')
                return True
            else:
                # Neplatná cookie - smazat
                cookie_manager.delete(COOKIE_NAME)

    # 5. POKUD JE PŘIHLÁŠENO (ze session_state), končíme
    if st.session_state["authenticated"]:
        return True

    # 6. LOGIN FORMULÁŘ (Pokud nic jiného neprošlo)
    st.markdown("""
        <style>
            .login-container {
                max-width: 400px;
                margin: 100px auto;
                padding: 2rem;
                background: rgba(10, 10, 10, 0.9);
                border: 2px solid #00f3ff;
                border-radius: 15px;
                box-shadow: 0 0 20px rgba(0, 243, 255, 0.2);
                text-align: center;
            }
        </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.title("⚡ Členská sekce RBK")
        st.subheader("Vstup pro šampiony")
        
        df_jmena = get_jmena_df()
        seznam_jmen = sorted(df_jmena['jméno'].unique().tolist())
        
        col1, col2 = st.columns([1, 1])
        with col1:
            vybrane_jmeno = st.selectbox("Vyber své jméno", [""] + seznam_jmen, label_visibility="collapsed")
        with col2:
            zadany_pin = st.text_input("Zadej PIN", type="password", placeholder="PIN", label_visibility="collapsed")

        if st.button("Vstoupit do arény", use_container_width=True):
            if vybrane_jmeno and zadany_pin:
                user_match = df_jmena[
                    (df_jmena['jméno'] == vybrane_jmeno) & 
                    (df_jmena['PIN'].astype(str) == str(zadany_pin))
                ]
                
                if not user_match.empty:
                    # Úspěch! Nastavit session i cookie
                    st.session_state["authenticated"] = True
                    st.session_state["user_name"] = vybrane_jmeno
                    st.session_state["user_role"] = user_match.iloc[0].get('role', 'user')
                    
                    # Uložit na 30 dní
                    cookie_manager.set(COOKIE_NAME, f"{vybrane_jmeno}|{zadany_pin}", expires_at=time.time() + 2592000)
                    st.success("Vítej zpět!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Špatné jméno nebo PIN, zkus to znova.")
            else:
                st.warning("Musíš vyplnit oboje, šampione.")
                
    return False

def logout():
    """Pomocná funkce volaná z bočního panelu nebo nastavení"""
    st.session_state["logout_requested"] = True
    st.rerun()
