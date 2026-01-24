import streamlit as st
import google.generativeai as genai
import pandas as pd
import data_manager 
from google.api_core import exceptions
import time

# === KONFIGURACE ===
AVATAR_BOT = "🤖" 
AVATAR_USER = "👤"

# POUŽIJEME ALIAS Z TVÉHO SEZNAMU
# Toto obchází chybu 404, protože tento název starší knihovna zná.
MODEL_NAME = "gemini-flash-latest"

def init_gemini():
    """Inicializace s API klíčem"""
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
            genai.configure(api_key=api_key)
            return True
        else:
            st.error("⚠️ Chybí GOOGLE_API_KEY v .streamlit/secrets.toml")
            return False
    except Exception as e:
        st.error(f"⚠️ Chyba inicializace Gemini: {e}")
        return False

def prepare_context_summary(df):
    """Vytvoří stručný přehled budoucích akcí."""
    if df is None or df.empty:
        return "Zatím žádné plánované akce."
    
    today = pd.to_datetime("today").date()
    # Robustní převod data
    if not pd.api.types.is_datetime64_any_dtype(df['datum']):
        df['datum'] = pd.to_datetime(df['datum'], errors='coerce').dt.date
    else:
        df['datum'] = df['datum'].dt.date
        
    future_df = df[df['datum'] >= today].sort_values('datum').head(20)
    
    text = "AKTUÁLNÍ TERMÍNOVKA (Context Data):\n"
    for _, row in future_df.iterrows():
        d = row['datum'].strftime('%d.%m.') if hasattr(row['datum'], 'strftime') else str(row['datum'])
        text += f"- ID: {row['id']} | {d} | {row['název']} | {row['místo']}\n"
    return text

def main(df_akce):
    if not init_gemini():
        return

    st.markdown("### 🤖 Cyber-Coach")
    st.caption(f"Online (Stabilní verze).")

    # 1. Definice Nástrojů (Tools)
    tools_list = [
        data_manager.sign_up_user,
        data_manager.sign_out_user,
        data_manager.get_event_info
    ]

    # 2. Kontext a Prompt
    data_context = prepare_context_summary(df_akce)
    
    system_instruction = f"""
    Jsi Cyber-Coach, asistent pro orientační běžce (RBK).
    Máš přístup k těmto datům:
    {data_context}
    
    INSTRUKCE:
    - Pro PŘIHLÁŠENÍ použij `sign_up_user`.
    - Pro ODHLÁŠENÍ použij `sign_out_user`.
    - Pokud chybí JMÉNO, zeptej se na něj.
    - Oslovuj 'šampione', buď stručný a používej emoji 🌲.
    """

    # 3. Inicializace Modelu (S RETRY LOGIKOU PŘI STARTU)
    model = None
    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME, 
            tools=tools_list,
            system_instruction=system_instruction
        )
    except Exception as e:
        # Pokud ani alias nefunguje, zkusíme tvrdý fallback na 'gemini-pro' (ten je všude)
        st.warning(f"Alias {MODEL_NAME} selhal ({e}). Zkouším záložní 'gemini-pro'.")
        try:
            model = genai.GenerativeModel(
                model_name="gemini-pro", 
                tools=tools_list,
                system_instruction=system_instruction
            )
        except:
            st.error("❌ Kritická chyba: API odmítá všechny názvy modelů. Je nutné aktualizovat knihovnu v requirements.txt.")
            return

    # 4. Historie
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "model", "parts": ["Zdar šampione! 🌲 Jsem připraven. Co podnikneme?"]}
        ]

    # Vykreslení zpráv
    for msg in st.session_state.chat_history:
        role = "user" if msg["role"] == "user" else "model"
        icon = AVATAR_USER if role == "user" else AVATAR_BOT
        
        text_content = ""
        parts = msg.get("parts", [])
        if isinstance(parts, list):
            for p in parts:
                if isinstance(p, str): text_content += p
                elif hasattr(p, "text"): text_content += p.text
        elif isinstance(parts, str):
            text_content = parts
            
        if text_content:
            st.chat_message(role, avatar=icon).write(text_content)

    # 5. Chat Input
    if prompt := st.chat_input("Tvůj pokyn..."):
        st.chat_message("user", avatar=AVATAR_USER).write(prompt)
        st.session_state.chat_history.append({"role": "user", "parts": [prompt]})

        if model:
            try:
                chat = model.start_chat(history=st.session_state.chat_history[:-1])
                
                with st.chat_message("model", avatar=AVATAR_BOT):
                    with st.spinner("Mákám na tom..."):
                        # Odeslání zprávy
                        response = chat.send_message(prompt)
                        bot_text = response.text
                        
                        st.write(bot_text)
                        st.session_state.chat_history.append({"role": "model", "parts": [bot_text]})
            
            except exceptions.ResourceExhausted:
                st.error("❌ Narazil jsi na limit zpráv. Dej si chvilku pauzu.")
            except Exception as e:
                st.error(f"Chyba: {str(e)}")
