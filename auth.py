import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import data_manager
import time
import base64

def check_password():
    """Vrátí True, pokud je uživatel přihlášen. Řeší cookies, roli i bezpečné odhlášení."""
    
    # 1. Pokud už v této relaci víme, že je přihlášen, neřešíme nic a pouštíme ho dál
    if st.session_state.get("password_correct"):
        return True

    # Inicializace manageru (bez cache, aby neházel warning)
    cookie_manager = stx.CookieManager(key="auth_mgr_v3")
    
    # 2. LOGIKA ODHLÁŠENÍ: Pokud uživatel v tomto tabu klikl na "Odhlásit", 
    # ignorujeme sušenky a nutíme ho k manuálnímu loginu.
    if st.session_state.get("explicit_logout", False):
        cookie_manager.delete("rbk_login_token")
        cookie_hodnota = None
    else:
        cookie_hodnota = cookie_manager.get("rbk_login_token")

    # 3. AUTOMATICKÉ PŘIHLÁŠENÍ (Remember Me)
    if cookie_hodnota:
        try:
            dekodovano = base64.b64decode(cookie_hodnota).decode('utf-8')
            ulozeny_uzivatel, ulozene_heslo = dekodovano.split('|', 1)
            
            # Načtení databáze pro ověření role a hesla
            conn_jmena = data_manager.get_connection()
            df_jmena = conn_jmena.read(worksheet="jmena", ttl=0)
            col_name = 'jméno' if 'jméno' in df_jmena.columns else 'Jméno'
            col_pin = 'PIN' if 'PIN' in df_jmena.columns else 'pin'
            col_role = 'role' if 'role' in df_jmena.columns else 'Role'
            
            df_jmena[col_pin] = df_jmena[col_pin].astype(str).str.replace(r'\.0$', '', regex=True)
            mask = df_jmena[col_name] == ulozeny_uzivatel
            
            if not df_jmena[mask].empty:
                correct_pin = str(df_jmena.loc[mask, col_pin].values[0]).replace('\u00A0', '').lstrip("'").strip()
                if str(ulozene_heslo).strip() == correct_pin:
                    # Nastavení session state pro app.py (Jméno i Role!)
                    st.session_state["password_correct"] = True
                    st.session_state["prihlaseny_uzivatel"] = ulozeny_uzivatel
                    st.session_state["role"] = str(df_jmena.loc[mask, col_role].values[0]) if col_role in df_jmena.columns else ""
                    st.session_state["explicit_logout"] = False
                    return True
                else:
                    cookie_manager.delete("rbk_login_token")
        except Exception:
            pass

    # 4. PŘIHLAŠOVACÍ FORMULÁŘ
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
        vybrane_jmeno = st.selectbox(
            "Jméno", 
            options=dostupna_jmena, 
            index=None, 
            placeholder="Začni psát...",
            help="Napiš jméno, potvrď ENTEREM a pak TABULÁTOREM skoč na heslo."
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
            mask = df_jmena[col_name] == vybrane_jmeno
            
            if not df_jmena[mask].empty:
                correct_pin = str(df_jmena.loc[mask, col_pin].values[0]).replace('\u00A0', '').lstrip("'").strip()
                if str(zadane_heslo).strip() == correct_pin:
                    # Úspěšný manuální login - rušíme blokádu a nastavujeme stavy
                    st.session_state["password_correct"] = True
                    st.session_state["prihlaseny_uzivatel"] = vybrane_jmeno
                    st.session_state["role"] = str(df_jmena.loc[mask, col_role].values[0]) if col_role in df_jmena.columns else ""
                    st.session_state["explicit_logout"] = False
                    
                    # Uložit do sušenky šifrovaně
                    cookie_str = f"{vybrane_jmeno}|{zadane_heslo}"
                    cookie_hodnota = base64.b64encode(cookie_str.encode('utf-8')).decode('utf-8')
                    expires = datetime.now() + timedelta(days=30)
                    cookie_manager.set("rbk_login_token", cookie_hodnota, expires_at=expires)
                    
                    st.success("✅ Přihlášeno!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("😕 Špatný PIN")
        except Exception as e:
            st.error(f"Chyba: {e}")
    return False

def logout():
    """Odhlásí uživatele a nastaví trvalou blokádu pro auto-login v rámci relace."""
    cookie_manager = stx.CookieManager(key="auth_mgr_v3")
    cookie_manager.delete("rbk_login_token")
    
    # Vymažeme data o přihlášení ze session state
    for key in ["password_correct", "prihlaseny_uzivatel", "role"]:
        if key in st.session_state:
            del st.session_state[key]
            
    # Nastavíme blokádu - dokud uživatel tab nezavře, sušenka ho sama nepřihlásí
    st.session_state["explicit_logout"] = True
    st.rerun()
