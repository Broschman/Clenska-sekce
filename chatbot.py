import streamlit as st
import google.generativeai as genai
import os
import pandas as pd

# === KONFIGURACE ===
AVATAR_PATH = "bot_avatar.png"

def init_gemini():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"⚠️ Chybí API klíč v secrets! ({e})")
        return False

def get_avatar_image():
    if os.path.exists(AVATAR_PATH):
        return AVATAR_PATH
    return "🤖"

def prepare_data_context(df):
    """
    Převede tabulku (DataFrame) na textový přehled pro AI.
    Vybíráme jen důležité sloupce, ať ho nezahltíme zbytečnostmi.
    """
    if df is None or df.empty:
        return "Zatím žádné akce v plánu."
    
    # Vybereme jen to podstatné pro konverzaci
    # (Předpokládám, že sloupce se jmenují 'název', 'datum', 'typ', 'přihlášeni'...)
    # Pokud se jmenují jinak, upravíme to.
    readable_df = df.copy()
    
    # Převedeme datum na čitelný string
    if 'datum' in readable_df.columns:
        readable_df['datum'] = readable_df['datum'].apply(lambda x: x.strftime('%d.%m.%Y') if pd.notnull(x) else "Neznámo")
    
    # Vytvoříme textový souhrn (Markdown tabulka)
    context_text = "TADY JE AKTUÁLNÍ SEZNAM AKCÍ V KLUBU:\n"
    context_text += readable_df.to_markdown(index=False)
    return context_text

def main(df=None): # <--- ZMĚNA: Přijímáme DF jako argument
    if not init_gemini():
        return

    # 1. Příprava kontextu (Data z tabulky)
    data_context = prepare_data_context(df)
    
    # 2. Sestavení instrukcí (Systémová + Data)
    FULL_SYSTEM_INSTRUCTION = f"""
    Jsi Cyber-Coach, elitní AI asistent pro orientační běžce.
    Jsi stručný, motivující a používáš orienťácký slang (lampiony, postupy, ražení).
    Tvým úkolem je pomáhat uživateli s plánováním závodů, dopravou a tréninkem.
    Oslovuj uživatele 'šampione'.
    
    {data_context}
    
    Když se uživatel zeptá na nějakou akci, najdi ji v tabulce výše.
    Pokud uživatel chce něco, co není v tabulce, řekni, že o tom nevíš.
    """

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "model", "content": "Zdar šampione! 🌲 Vidím celou termínovku. Na co se chceš zeptat?"}
        ]

    # 3. Načtení modelu
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=FULL_SYSTEM_INSTRUCTION
    )

    avatar_img = get_avatar_image()
    
    # Vykreslení historie
    for msg in st.session_state.messages:
        icon = avatar_img if msg["role"] == "model" else "👤"
        st.chat_message(msg["role"], avatar=icon).write(msg["content"])

    # Chat input
    if prompt := st.chat_input("Zadej instrukce..."):
        st.chat_message("user", avatar="👤").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        try:
            chat = model.start_chat(history=[
                {"role": m["role"], "parts": [m["content"]]} 
                for m in st.session_state.messages[:-1]
            ])
            
            response = chat.send_message(prompt)
            bot_reply = response.text
            
            st.chat_message("model", avatar=avatar_img).write(bot_reply)
            st.session_state.messages.append({"role": "model", "content": bot_reply})
            
        except Exception as e:
            st.error(f"Chyba spojení s Matrixem: {e}")
