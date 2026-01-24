import streamlit as st
import google.generativeai as genai
import pandas as pd
import data_manager 
from google.api_core import retry

# === KONFIGURACE ===
AVATAR_BOT = "🤖" 
AVATAR_USER = "👤"

def init_gemini():
    """Inicializace s API klíčem"""
    try:
        # Zkusíme načíst klíč ze secrets, pokud není, vyhodíme chybu
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
    
    # Filtr na budoucí akce + seřazení
    today = pd.to_datetime("today").date()
    # Převedeme datum na datetime pro porovnání, pokud ještě není
    if not pd.api.types.is_datetime64_any_dtype(df['datum']):
        df['datum'] = pd.to_datetime(df['datum']).dt.date
        
    future_df = df[df['datum'] >= today].sort_values('datum').head(20)
    
    text = "AKTUÁLNÍ TERMÍNOVKA (Context Data):\n"
    for _, row in future_df.iterrows():
        # Formát: ID | Datum | Název | Místo
        d = row['datum'].strftime('%d.%m.') if hasattr(row['datum'], 'strftime') else str(row['datum'])
        text += f"- ID: {row['id']} | {d} | {row['název']} | {row['místo']}\n"
    return text

def main(df_akce):
    if not init_gemini():
        return

    st.markdown("### 🤖 Cyber-Coach")
    st.caption("Jsem připraven. Napiš 'Přihlas mě na MČR' nebo 'Kdy je další závod?'")

    # 1. Definice Nástrojů (Tools)
    tools_list = [
        data_manager.sign_up_user,
        data_manager.sign_out_user,
        data_manager.get_event_info
    ]

    # 2. Příprava kontextu dat
    data_context = prepare_context_summary(df_akce)
    
    # 3. System Prompt
    system_instruction = f"""
    Jsi Cyber-Coach, asistent pro orientační běžce (RBK).
    Máš přístup k těmto datům o závodech:
    {data_context}
    
    INSTRUKCE PRO FUNCTION CALLING:
    - Pokud uživatel chce PŘIHLÁSIT (sebe nebo někoho), použij nástroj `sign_up_user`.
    - Pokud uživatel chce ODHLÁSIT, použij nástroj `sign_out_user`.
    - Pokud chybí JMÉNO uživatele (např. napíše jen "přihlas mě"), ZEPTEJ SEHO NA JMÉNO, než zavoláš funkci.
    - Pokud chybí NÁZEV AKCE, zeptej se.
    
    STYL KOMUNIKACE:
    - Stručný, k věci, motivující.
    - Oslovuj 'šampione', 'borče' nebo 'běžče'.
    - Používej emoji (🌲, 🏃, 🧭).
    """

    # 4. Inicializace modelu
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", # Verze 1.5 Flash je rychlá a levná, ideální pro tools
        tools=tools_list,
        system_instruction=system_instruction
    )

    # 5. Historie v Session State
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "model", "parts": ["Zdar šampione! 🌲 Kam to dneska bude? Vidím termínovku, stačí říct."]}
        ]

    # 6. Vykreslení zpráv
    for msg in st.session_state.chat_history:
        role = "user" if msg["role"] == "user" else "model"
        icon = AVATAR_USER if role == "user" else AVATAR_BOT
        
        # Extrakce textu z objektu Gemini (může být složitější při func calling)
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

    # 7. Chat Input & Logic
    if prompt := st.chat_input("Tvůj pokyn..."):
        # Zobrazení user message
        st.chat_message("user", avatar=AVATAR_USER).write(prompt)
        st.session_state.chat_history.append({"role": "user", "parts": [prompt]})

        # Vytvoření chat session s historií
        chat = model.start_chat(history=st.session_state.chat_history[:-1])
        
        with st.chat_message("model", avatar=AVATAR_BOT):
            with st.spinner("Pracuji..."):
                try:
                    # Odeslání zprávy - Gemini automaticky vyřeší Function Calling
                    response = chat.send_message(prompt)
                    
                    # Získání odpovědi
                    bot_text = response.text
                    st.write(bot_text)
                    
                    # Uložení do historie
                    st.session_state.chat_history.append({"role": "model", "parts": [bot_text]})
                    
                except Exception as e:
                    st.error(f"Chyba komunikace: {str(e)}")
