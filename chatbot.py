import streamlit as st
import google.generativeai as genai
import pandas as pd
import data_manager 
import time
from google.api_core import exceptions

# === KONFIGURACE ===
AVATAR_BOT = "🤖" 
AVATAR_USER = "👤"

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
    """Vytvoří stručný přehled budoucích akcí pro kontext modelu."""
    if df is None or df.empty:
        return "Zatím žádné plánované akce."
    
    today = pd.to_datetime("today").date()
    # Převedeme datum na datetime pro porovnání
    if not pd.api.types.is_datetime64_any_dtype(df['datum']):
        df['datum'] = pd.to_datetime(df['datum']).dt.date
        
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
    st.caption("Jsem online. Napiš třeba 'Přihlas mě na MČR'.")

    # 1. Definice Nástrojů (Tools)
    tools_list = [
        data_manager.sign_up_user,
        data_manager.sign_out_user,
        data_manager.get_event_info
    ]

    # 2. Kontext
    data_context = prepare_context_summary(df_akce)
    
    # 3. System Prompt
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

    # 4. Inicializace modelu - PŘEPÍNÁME NA STABILNÍ VERZI 1.5
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", # ZMĚNA: 2.0 dělala problémy s limity
        tools=tools_list,
        system_instruction=system_instruction
    )

    # 5. Historie
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

    # 6. Chat Input s RETRY logikou
    if prompt := st.chat_input("Tvůj pokyn..."):
        st.chat_message("user", avatar=AVATAR_USER).write(prompt)
        st.session_state.chat_history.append({"role": "user", "parts": [prompt]})

        chat = model.start_chat(history=st.session_state.chat_history[:-1])
        
        with st.chat_message("model", avatar=AVATAR_BOT):
            with st.spinner("Mákám na tom..."):
                # Retry smyčka (max 3 pokusy)
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = chat.send_message(prompt)
                        bot_text = response.text
                        st.write(bot_text)
                        st.session_state.chat_history.append({"role": "model", "parts": [bot_text]})
                        break # Úspěch, vyskakujeme ze smyčky
                    
                    except exceptions.ResourceExhausted:
                        # Chyba 429 - Quota Exceeded
                        wait_time = 5 * (attempt + 1)
                        if attempt < max_retries - 1:
                            st.warning(f"⚠️ Přehřívám se (Limit API). Chladím motory... ({wait_time}s)")
                            time.sleep(wait_time)
                            continue
                        else:
                            st.error("❌ Došly mi síly (Quota Exceeded). Zkus to za chvíli.")
                    
                    except Exception as e:
                        st.error(f"Chyba systému: {str(e)}")
                        break
