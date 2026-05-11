import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import data_manager
import time
import base64

def check_password():
    """Vrátí `True`, pokud má uživatel správné heslo. Využívá GSheets pro hesla."""
    
    # 1. Povolíme vstup těm, kteří už jsou přihlášeni
    if st.session_state.get("password_correct", False):
        return True

    # Inicializujeme cookie manager napřímo (bez @st.cache_resource, aby neházel chybu)
    cookie_manager = stx.CookieManager(key="auth_cookie")
    
    # 2. TVRDÁ BLOKÁDA PRO ODHLÁŠENÍ: Pokud je aktivní odhlášení, ignoruj sušenku
    if st.session_state.get("logout_active", False):
        cookie_manager.delete("rbk_login_token")
        cookie_hodnota = None
    else:
        cookie_hodnota = cookie_manager.get("rbk_login_token")

    # 3. Kontrola cookies a automatické přihlášení
    if cookie_hodnota:
        try:
            dekodovano = base64.b64decode(cookie_hodnota).decode('utf-8')
            ulozeny_uzivatel, ulozene_heslo = dekodovano.split('|', 1)
            
            conn_jmena = data_manager.get_connection()
            df_jmena = conn_jmena.read(worksheet="jmena", ttl=0)
            
            col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
            col_pin = 'PIN' if 'PIN' in df_jmena.columns else 'pin'
            col_role = 'role' if 'role' in df_jmena.columns else 'Role'
            
            df_jmena[col_pin] = df_jmena[col_pin].astype(str).str.replace(r'\.0$', '', regex=True)

            mask = df_jmena[col_name] == ulozeny_uzivatel
            if not df_jmena[mask].empty:
                correct_pin = df_jmena.loc[mask, col_pin].values[0]
                correct_pin = str(correct_pin).replace('\u00A0', '').lstrip("'").strip()
                
                if str(ulozene_heslo).strip() == correct_pin:
                    st.session_state["password_correct"] = True
                    st.session_state["username"] = ulozeny_uzivatel
                    # KRITICKÉ: Doplnění proměnných pro app.py
                    st.session_state["prihlaseny_uzivatel"] = ulozeny_uzivatel
                    st.session_state["role"] = str(df_jmena.loc[mask, col_role].values[0]) if col_role in df_jmena.columns else ""
                    return True
                else:
                    cookie_manager.delete("rbk_login_token")
            else:
                 cookie_manager.delete("rbk_login_token")
        except Exception as e:
            pass 

    # 4. Není přihlášen, zobrazit formulář
    if not st.session_state.get("password_correct", False):
        try:
            conn_jmena = data_manager.get_connection()
            df_jmena = conn_jmena.read(worksheet="jmena", ttl=300)
            col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
            dostupna_jmena = df_jmena[col_name].dropna().tolist()
        except Exception as e:
            st.error(f"Nelze načíst databázi uživatelů: {e}")
            dostupna_jmena = []

        st.markdown("<h1 style='text-align: center;'>Zadejte heslo k sekci:</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # CHYTRÝ SELECTBOX PRO TABULÁTOR
            vybrane_jmeno = st.selectbox(
                "Jméno", 
                options=dostupna_jmena, 
                index=None, 
                placeholder="Začni psát...",
                help="Napiš jméno, potvrď ENTEREM a TABULÁTOREM skoč na heslo.",
                key="username"
            )
            zadane_heslo = st.text_input("PIN (Heslo)", type="password", key="password")
            btn_login = st.button("Přihlásit se")

        if btn_login and st.session_state["username"]:
            try:
                conn_jmena = data_manager.get_connection()
                df_jmena = conn_jmena.read(worksheet="jmena", ttl=0)
                
                col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
                col_pin = 'PIN' if 'PIN' in df_jmena.columns else 'pin'
                col_role = 'role' if 'role' in df_jmena.columns else 'Role'

                df_jmena[col_pin] = df_jmena[col_pin].astype(str).str.replace(r'\.0$', '', regex=True)

                if st.session_state["username"] in df_jmena[col_name].values:
                    mask = df_jmena[col_name] == st.session_state["username"]
                    correct_pin = df_jmena.loc[mask, col_pin].values[0]
                    correct_pin = str(correct_pin).replace('\u00A0', '').lstrip("'").strip()
                    zade_heslo = str(st.session_state["password"]).strip()

                    if zade_heslo == correct_pin:
                        st.session_state["password_correct"] = True
                        
                        # KRITICKÉ: Doplnění proměnných pro app.py a smazání blokády odhlášení
                        st.session_state["prihlaseny_uzivatel"] = st.session_state["username"]
                        st.session_state["role"] = str(df_jmena.loc[mask, col_role].values[0]) if col_role in df_jmena.columns else ""
                        st.session_state["logout_active"] = False

                        cookie_str = f"{st.session_state['username']}|{zade_heslo}"
                        cookie_hodnota = base64.b64encode(cookie_str.encode('utf-8')).decode('utf-8')
                        expires = datetime.now() + timedelta(days=30)
                        cookie_manager.set("rbk_login_token", cookie_hodnota, expires_at=expires)
                        
                        st.success("✅ Přihlášení úspěšné!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("😕 Nesprávné heslo")
                else:
                     st.error("Uživatel nenalezen.")
            except Exception as e:
                st.error(f"Chyba při ověřování: {e}")
        return False
    
    return True

def logout():
    """Odhlásí uživatele a zablokuje opětovné automatické přihlášení."""
    
    # 1. Čistka lokální paměti
    for key in ["password_correct", "username", "password", "prihlaseny_uzivatel", "role"]:
        if key in st.session_state:
            del st.session_state[key]
            
    # 2. Nahodíme tvrdou blokádu proti cookies
    st.session_state["logout_active"] = True
    
    st.rerun()
