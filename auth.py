import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import data_manager
import time
import base64

def check_password():
    """Vrátí `True`, pokud má uživatel správné heslo. Využívá GSheets pro hesla."""
    
    # Anti-flash cookie logika pomocí extra_streamlit_components
    @st.cache_resource
    def get_cookie_manager():
        return stx.CookieManager(key="auth_cookie")
    
    cookie_manager = get_cookie_manager()
    cookie_hodnota = cookie_manager.get("rbk_login_token")

    # Kontrola cookies a automatické přihlášení
    if cookie_hodnota:
        try:
            # Dekódování Base64
            dekodovano = base64.b64decode(cookie_hodnota).decode('utf-8')
            ulozeny_uzivatel, ulozene_heslo = dekodovano.split('|', 1)
            
            # Pokud už víme, že je přihlášen, a cookie sedí, pustíme ho
            if st.session_state.get("password_correct", False) and st.session_state.get("username") == ulozeny_uzivatel:
                 return True
            
            # Validace cookie proti DB
            conn_jmena = data_manager.get_connection()
            df_jmena = conn_jmena.read(worksheet="jmena", ttl=0)
            
            col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
            col_pin = 'PIN' if 'PIN' in df_jmena.columns else 'pin'
            
            # Kritický patch: Očištění databáze (zabití .0 a přetypování na string)
            df_jmena[col_pin] = df_jmena[col_pin].astype(str).str.replace(r'\.0$', '', regex=True)

            mask = df_jmena[col_name] == ulozeny_uzivatel
            if not df_jmena[mask].empty:
                correct_pin = df_jmena.loc[mask, col_pin].values[0]
                # Ošetření: Odstranění záchranného apostrofu zleva
                correct_pin = str(correct_pin).replace('\u00A0', '').lstrip("'").strip()
                
                if str(ulozene_heslo).strip() == correct_pin:
                    st.session_state["password_correct"] = True
                    st.session_state["username"] = ulozeny_uzivatel
                    return True
                else:
                    # Neplatná cookie, mažeme
                    cookie_manager.delete("rbk_login_token")
            else:
                 # Uživatel smazán z DB, ale má cookie -> smazat cookie
                 cookie_manager.delete("rbk_login_token")
        except Exception as e:
            print(f"Chyba při čtení cookies: {e}")
            pass # Chyba v dekódování, ignorujeme

    # Není přihlášen, zobrazit formulář
    if not st.session_state.get("password_correct", False):
        # 1. Zjistit dostupná jména z DB
        try:
            conn_jmena = data_manager.get_connection()
            df_jmena = conn_jmena.read(worksheet="jmena", ttl=300) # Tady stačí cache
            col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
            dostupna_jmena = [""] + df_jmena[col_name].dropna().tolist()
        except Exception as e:
            st.error(f"Nelze načíst databázi uživatelů: {e}")
            dostupna_jmena = [""]

        # 2. Layout formuláře
        st.markdown("<h1 style='text-align: center;'>Zadejte heslo k sekci:</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.selectbox("Jméno", dostupna_jmena, key="username")
            st.text_input("PIN (Heslo)", type="password", key="password")
            btn_login = st.button("Přihlásit se")

        # 3. Logika přihlášení (po kliknutí nebo Enteru)
        if btn_login and st.session_state["username"] != "":
            try:
                # Načtení čistých dat pro kontrolu
                conn_jmena = data_manager.get_connection()
                df_jmena = conn_jmena.read(worksheet="jmena", ttl=0)
                
                col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
                col_pin = 'PIN' if 'PIN' in df_jmena.columns else 'pin'

                # Znovu očištění dat
                df_jmena[col_pin] = df_jmena[col_pin].astype(str).str.replace(r'\.0$', '', regex=True)

                if st.session_state["username"] in df_jmena[col_name].values:
                    # Nalezení hesla
                    mask = df_jmena[col_name] == st.session_state["username"]
                    correct_pin = df_jmena.loc[mask, col_pin].values[0]
                    
                    # KRITICKÉ: odstranění apostrofu, \u00A0 atd.
                    correct_pin = str(correct_pin).replace('\u00A0', '').lstrip("'").strip()
                    zade_heslo = str(st.session_state["password"]).strip()

                    if zade_heslo == correct_pin:
                        st.session_state["password_correct"] = True
                        
                        # Generování a uložení cookies
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
    """Odhlásí uživatele a resetuje stavy."""
    @st.cache_resource
    def get_cookie_manager():
        return stx.CookieManager(key="auth_cookie")
    
    cookie_manager = get_cookie_manager()
    cookie_manager.delete("rbk_login_token")
    
    if "password_correct" in st.session_state:
        del st.session_state["password_correct"]
    if "username" in st.session_state:
        del st.session_state["username"]
    st.rerun()
