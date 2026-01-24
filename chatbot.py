import streamlit as st
import google.generativeai as genai
import pandas as pd
import data_manager  # Importujeme naše funkce
from google.api_core import retry

# === KONFIGURACE ===
AVATAR_BOT = "bot_avatar.png" # Pokud máš
AVATAR_USER = "👤"

def init_gemini():
    """Inicializace s API klíčem"""
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"⚠️ Chybí API klíč! ({e})")
        return False

def prepare_context_summary(df):
    """
    Vytvoří stručný přehled nejbližších akcí pro system prompt.
    Neposíláme celou historii, jen budoucnost, abychom šetřili tokeny.
    """
    if df is None or df.empty:
        return "Zatím žádné akce."
    
    # Filtr na budoucí akce (nechceme historii z roku 2024)
    today = pd.to_datetime("today").date()
    future_df = df[df['datum'] >= today].sort_values('datum').head(15) # Top 15 nejbližších
    
    text = "TERMÍNOVKA (Nejbližší akce):\n"
    for _, row in future_df.iterrows():
        text += f"- ID: {row['id']} | {row['datum'].strftime('%d.%m.')} | {row['název']} | Místo: {row['místo']} | Typ: {row['typ']}\n"
    return text

def main(df_akce):
    if not init_gemini():
        return

    st.markdown("### 🤖 Cyber-Coach v2.0")
    st.caption("Jsem připraven na akci. Můžu tě přihlásit na závody!")

    # 1. Definice Nástrojů (Tools)
    # Tady říkáme Gemini: "Když potřebuješ přihlásit, použij tuhle funkci"
    tools_list = [
        data_manager.sign_up_user,
        data_manager.get_event_info # Volitelné, pokud chceš dedikované hledání
    ]

    # 2. Kontext
    data_context = prepare_context_summary(df_akce)
    
    system_instruction = f"""
    Jsi Cyber-Coach, drsný ale nápomocný AI asistent pro orientační běžce.
    Máš přístup k databázi akcí a funkcím pro správu týmu.
    
    {data_context}
    
    PRAVIDLA:
    1. Oslovuj uživatele 'šampione' nebo 'běžče'.
    2. Když uživatel chce přihlásit sebe nebo někoho jiného, VŽDY použij nástroj `sign_up_user`.
    3. Pokud chybí jméno nebo název akce pro přihlášení, zeptej se na ně.
    4. Buď stručný. Používej orienťácký slang (lampiony, dohledávka, ražení).
    """

    # 3. Model s Tools
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash", # Doporučuji 2.0 Flash nebo 1.5 Flash pro rychlost/cenu
        tools=tools_list,
        system_instruction=system_instruction
    )

    # 4. Chat History v Session State
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "model", "parts": ["Zdar šampione! 🌲 Vidím termínovku. Chceš někam přihlásit?"]}
        ]

    # Vykreslení historie
    for msg in st.session_state.chat_history:
        role = "user" if msg["role"] == "user" else "model"
        icon = AVATAR_USER if role == "user" else "🤖"
        
        # Problém: Gemini history ukládá objekty, Streamlit chce text. 
        # Musíme vytáhnout text z 'parts'.
        text_content = ""
        if isinstance(msg["parts"], list):
            for part in msg["parts"]:
                if isinstance(part, str): text_content += part
                elif hasattr(part, "text"): text_content += part.text
        elif isinstance(msg["parts"], str):
            text_content = msg["parts"]
            
        if text_content:
            st.chat_message(role, avatar=icon).write(text_content)

    # 5. Zpracování vstupu
    if prompt := st.chat_input("Napiš instrukci (např: Přihlas mě na MČR)"):
        # Uložit user message
        st.session_state.chat_history.append({"role": "user", "parts": [prompt]})
        st.chat_message("user", avatar=AVATAR_USER).write(prompt)

        # Start Chat Session
        # Pozor: Pro function calling je lepší nechat 'automatic_function_calling' povolený
        chat = model.start_chat(history=st.session_state.chat_history[:-1])
        
        with st.chat_message("model", avatar="🤖"):
            with st.spinner("Processing computation..."):
                try:
                    # Odeslání zprávy (model si sám zavolá funkci, pokud potřebuje)
                    response = chat.send_message(prompt)
                    
                    # Gemini library ve Streamlitu automaticky vykoná funkci lokálně, 
                    # pokud je správně nakonfigurována, ale pro plnou kontrolu 
                    # je někdy třeba manuální smyčka. Nicméně 'tools' parametr v GenerativeModel
                    # by měl v Python SDK zajistit automatické provedení v rámci `send_message` (tzv. Turn-based logic),
                    # POKUD je enable_automatic_function_calling=True (což je default).
                    
                    # Výstup textu
                    bot_text = response.text
                    st.write(bot_text)
                    
                    # Uložení do historie
                    st.session_state.chat_history.append({"role": "model", "parts": [bot_text]})
                    
                except Exception as e:
                    st.error(f"System Error: {e}")
                    # Debug pro vývojáře
                    # st.write(response.parts)
