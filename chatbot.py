import streamlit as st
import google.generativeai as genai
import pandas as pd
import data_manager 
import time
from google.api_core import exceptions

# === KONFIGURACE ===
AVATAR_BOT = "🤖" 
AVATAR_USER = "👤"

# SEZNAM MODELŮ K OTESTOVÁNÍ (V POŘADÍ PRIORITY)
# 1. Experimentální 2.0 (často zdarma bez limitů)
# 2. Flash Latest (Alias pro 1.5 Flash - nejstabilnější)
# 3. Flash Lite (Nejrychlejší)
CANDIDATE_MODELS = [
    "gemini-2.0-flash-exp",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-1.5-flash-001"
]

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

def get_working_model(system_instruction, tools_list):
    """
    Tato funkce projde seznam modelů a najde ten, který funguje (nemá limit 0).
    """
    # Pokud už máme vybraný model v session state, použijeme ho a nezdržujeme
    if "valid_model_name" in st.session_state:
        return genai.GenerativeModel(
            model_name=st.session_state.valid_model_name,
            tools=tools_list,
            system_instruction=system_instruction
        )

    # Jinak testujeme
    for model_name in CANDIDATE_MODELS:
        try:
            # Vytvoříme instanci
            model = genai.GenerativeModel(
                model_name=model_name,
                tools=tools_list,
                system_instruction=system_instruction
            )
            
            # Rychlý test - pošleme "ping", abychom zjistili, jestli nás API pustí
            # Stačí count_tokens, to je levné a rychlé
            model.count_tokens("Test")
            
            # Pokud to nehavarovalo, máme vítěze!
            st.session_state.valid_model_name = model_name
            print(f"✅ Nalezen funkční model: {model_name}")
            return model
            
        except Exception as e:
            # Pokud chyba, zkusíme další
            print(f"❌ Model {model_name} selhal: {e}")
            continue
    
    # Pokud selhalo všechno
    st.error("❌ Nepodařilo se najít žádný funkční model Gemini. Zkontroluj API klíč.")
    return None

def prepare_context_summary(df):
    """Vytvoří stručný přehled budoucích akcí."""
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

    # Pokud model ještě nebyl vybrán, ukážeme spinner, že hledáme
    if "valid_model_name" not in st.session_state:
        with st.spinner("🔄 Hledám dostupný AI model..."):
             # Dummy volání pro inicializaci (logika je níže)
             pass

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

    # 3. Získání funkčního modelu (Auto-Discovery)
    model = get_working_model(system_instruction, tools_list)
    
    if not model:
        return # Konec, nenašli jsme model

    # Zobrazíme uživateli, na čem běžíme (pro info)
    used_model = st.session_state.get("valid_model_name", "Unknown")
    st.markdown("### 🤖 Cyber-Coach")
    st.caption(f"Online ({used_model}). Napiš třeba 'Přihlas mě na MČR'.")

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
             st.error("❌ Došel limit požadavků (Quota Exceeded). Zkus to za chvíli.")
        except Exception as e:
             st.error(f"Chyba: {str(e)}")
             # Pokud došlo k chybě modelu, resetujeme výběr, aby se příště zkusil najít jiný
             if "valid_model_name" in st.session_state:
                 del st.session_state.valid_model_name
                 st.rerun()
