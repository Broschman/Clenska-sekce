import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import data_manager
import time
import base64

def check_password():
    """Vrátí `True`, pokud má uživatel správné heslo. Využívá GSheets pro hesla."""
    
    cookie_manager = stx.CookieManager(key="auth_cookie_manager")
    
    if st.session_state.get("logout_in_progress", False):
        cookie_hodnota = None
    else:
        cookie_hodnota = cookie_manager.get("rbk_login_token")

    if cookie_hodnota:
        try:
            dekodovano = base64.b64decode(cookie_hodnota).decode('utf-8')
            ulozeny_uzivatel, ulozene_heslo = dekodovano.split('|', 1)
            
            # OPRAVA: Kontrolujeme správný klíč 'prihlaseny_uzivatel'
            if st.session_state.get("password_correct", False) and st.session_state.get("prihlaseny_uzivatel") == ulozeny_uzivatel:
                 return True
            
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
                    # OPRAVA: Správné ukládání jména a ROLE
                    st.session_state["password_correct"] = True
                    st.session_state["prihlaseny_uzivatel"] = ulozeny_uzivatel
                    
                    if col_role in df_jmena.columns:
                        st.session_state["role"] = str(df_jmena.loc[mask, col_role].values[0])
                    else:
                        st.session_state["role"] = ""
                        
                    st.session_state["logout_in_progress"] = False
                    return True
                else:
                    cookie_manager.delete("rbk_login_token")
            else:
                 cookie_manager.delete("rbk_login_token")
        except Exception:
            pass

    if not st.session_state.get("password_correct", False):
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
            # Nevážeme to na klíč ve state, protože si to pak ručně uložíme do správných
            vybrane_jmeno = st.selectbox(
                "Jméno", 
                options=dostupna_jmena, 
                index=None, 
                placeholder="Začni psát své jméno...",
                help="Napiš první písmena, potvrď ENTEREM a pak Tabulátorem skoč na heslo."
            )
            zadane_heslo = st.text_input("PIN (Heslo)", type="password")
            btn_login = st.button("Přihlásit se")

        if btn_login and vybrane_jmeno:
            try:
                conn_jmena = data_manager.get_connection()
                df_jmena = conn_jmena.read(worksheet="jmena", ttl=0)
                col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
                col_pin = 'PIN' if 'PIN' in df_jmena.columns else 'pin'
                col_role = 'role' if 'role' in df_jmena.columns else 'Role'
                
                df_jmena[col_pin] = df_jmena[col_pin].astype(str).str.replace(r'\.0$', '', regex=True)

                if vybrane_jmeno in df_jmena[col_name].values:
                    mask = df_jmena[col_name] == vybrane_jmeno
                    correct_pin = df_jmena.loc[mask, col_pin].values[0]
                    correct_pin = str(correct_pin).replace('\u00A0', '').lstrip("'").strip()
                    
                    if str(zadane_heslo).strip() == correct_pin:
                        # OPRAVA: Správné proměnné
                        st.session_state["password_correct"] = True
                        st.session_state["prihlaseny_uzivatel"] = vybrane_jmeno
                        
                        if col_role in df_jmena.columns:
                            st.session_state["role"] = str(df_jmena.loc[mask, col_role].values[0])
                        else:
                            st.session_state["role"] = ""
                        
                        cookie_str = f"{vybrane_jmeno}|{zadane_heslo}"
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
                st.error(f"Chyba: {e}")
        elif btn_login:
            st.warning("Vyber prosím svoje jméno ze seznamu nápovědy.")
        return False
    
    return True

def logout():
    """Bezpečně odhlásí uživatele."""
    st.session_state["logout_in_progress"] = True
    
    cookie_manager = stx.CookieManager(key="auth_cookie_manager")
    cookie_manager.delete("rbk_login_token")
    
    # OPRAVA: Mažeme všechny proměnné, které jsme vytvořili
    for key in ["password_correct", "prihlaseny_uzivatel", "role"]:
        if key in st.session_state:
            del st.session_state[key]
            
    st.rerun()
