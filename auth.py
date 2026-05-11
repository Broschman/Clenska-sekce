import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import data_manager
import time
import base64

def check_password():
    """Vrátí `True`, pokud má uživatel správné heslo. Využívá GSheets pro hesla."""
    
    @st.cache_resource
    def get_cookie_manager():
        # Důležité: key musí být unikátní pro tuto instanci
        return stx.CookieManager(key="auth_cookie_manager")
    
    cookie_manager = get_cookie_manager()
    
    # POJISTKA PRO ODHLÁŠENÍ: Pokud jsme právě klikli na odhlásit, ignorujeme cookies
    if st.session_state.get("logout_in_progress", False):
        cookie_hodnota = None
    else:
        cookie_hodnota = cookie_manager.get("rbk_login_token")

    # Kontrola cookies a automatické přihlášení
    if cookie_hodnota:
        try:
            dekodovano = base64.b64decode(cookie_hodnota).decode('utf-8')
            ulozeny_uzivatel, ulozene_heslo = dekodovano.split('|', 1)
            
            if st.session_state.get("password_correct", False) and st.session_state.get("username") == ulozeny_uzivatel:
                 return True
            
            conn_jmena = data_manager.get_connection()
            df_jmena = conn_jmena.read(worksheet="jmena", ttl=0)
            col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
            col_pin = 'PIN' if 'PIN' in df_jmena.columns else 'pin'
            
            df_jmena[col_pin] = df_jmena[col_pin].astype(str).str.replace(r'\.0$', '', regex=True)
            mask = df_jmena[col_name] == ulozeny_uzivatel
            
            if not df_jmena[mask].empty:
                correct_pin = df_jmena.loc[mask, col_pin].values[0]
                correct_pin = str(correct_pin).replace('\u00A0', '').lstrip("'").strip()
                
                if str(ulozene_heslo).strip() == correct_pin:
                    st.session_state["password_correct"] = True
                    st.session_state["username"] = ulozeny_uzivatel
                    # Resetujeme vlajku odhlášení, protože jsme úspěšně uvnitř
                    st.session_state["logout_in_progress"] = False
                    return True
                else:
                    cookie_manager.delete("rbk_login_token")
            else:
                 cookie_manager.delete("rbk_login_token")
        except Exception:
            pass

    # Pokud není přihlášen, zobrazíme login form
    if not st.session_state.get("password_correct", False):
        # Jakmile se dostaneme k formě, už odhlášení nepovažujeme za aktivní
        st.session_state["logout_in_progress"] = False
        
        try:
            conn_jmena = data_manager.get_connection()
            df_jmena = conn_jmena.read(worksheet="jmena", ttl=300)
            col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
            dostupna_jmena = df_jmena[col_name].dropna().tolist()
        except Exception:
            dostupna_jmena = []

        st.markdown("<h1 style='text-align: center;'>Zadejte heslo k sekci:</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.selectbox(
                "Jméno", 
                options=dostupna_jmena, 
                index=None, 
                placeholder="Začni psát své jméno...",
                key="username"
            )
            st.text_input("PIN (Heslo)", type="password", key="password")
            btn_login = st.button("Přihlásit se")

        if btn_login and st.session_state.get("username"):
            try:
                conn_jmena = data_manager.get_connection()
                df_jmena = conn_jmena.read(worksheet="jmena", ttl=0)
                col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
                col_pin = 'PIN' if 'PIN' in df_jmena.columns else 'pin'
                df_jmena[col_pin] = df_jmena[col_pin].astype(str).str.replace(r'\.0$', '', regex=True)

                if st.session_state["username"] in df_jmena[col_name].values:
                    mask = df_jmena[col_name] == st.session_state["username"]
                    correct_pin = df_jmena.loc[mask, col_pin].values[0]
                    correct_pin = str(correct_pin).replace('\u00A0', '').lstrip("'").strip()
                    
                    if str(st.session_state["password"]).strip() == correct_pin:
                        st.session_state["password_correct"] = True
                        
                        cookie_str = f"{st.session_state['username']}|{st.session_state['password']}"
                        cookie_hodnota = base64.b64encode(cookie_str.encode('utf-8')).decode('utf-8')
                        expires = datetime.now() + timedelta(days=30)
                        cookie_manager.set("rbk_login_token", cookie_hodnota, expires_at=expires)
                        
                        st.success("✅ Přihlášení úspěšné!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("😕 Nesprávné heslo")
            except Exception as e:
                st.error(f"Chyba: {e}")
        return False
    
    return True

def logout():
    """Bezpečně odhlásí uživatele."""
    # Nastavíme vlajku, aby se ignorovaly sušenky v příštím cyklu
    st.session_state["logout_in_progress"] = True
    
    cookie_manager = stx.CookieManager(key="auth_cookie_manager")
    cookie_manager.delete("rbk_login_token")
    
    # Vyčištění session state
    for key in ["password_correct", "username", "password"]:
        if key in st.session_state:
            del st.session_state[key]
            
    st.rerun()
