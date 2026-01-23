import streamlit as st
import google.generativeai as genai
import os

# === KONFIGURACE ===
AVATAR_PATH = "bot_avatar.png"  # Změň, pokud to máš ve složce (např. "assets/bot_avatar.png")
SYSTEM_INSTRUCTION = """
Jsi Cyber-Coach, elitní AI asistent pro orientační běžce. 
Jsi stručný, motivující a používáš orienťácký slang (lampiony, postupy, ražení).
Tvým úkolem je pomáhat uživateli s plánováním závodů, dopravou a tréninkem.
Oslovuj uživatele 'šampione'.
Když se něco povede, použij emoji 🔥 nebo 🌲.
"""

def init_gemini():
    """Nastartuje spojení s Google API"""
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"⚠️ Chybí API klíč v secrets! ({e})")
        return False

def get_avatar_image():
    """Načte obrázek avatara, nebo vrátí emoji, pokud soubor chybí"""
    if os.path.exists(AVATAR_PATH):
        return AVATAR_PATH
    return "🤖" # Fallback, kdyby obrázek neexistoval

def main():
    # 1. Inicializace API
    if not init_gemini():
        return

    # 2. Inicializace historie chatu (aby si pamatoval, co jste řešili)
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "model", "content": "Zdar šampione! 🌲 Jsem připraven. Co pro tebe můžu udělat?"}
        ]

    # 3. Načtení modelu
    model = genai.GenerativeModel(
        # ZKUS TUTO VARIANTU (často funguje lépe):
        model_name="gemini-1.5-flash-latest", 
        # POKUD BY ANI TO NEŠLO, DEJ TAM OSVĚDČENOU KLASIKU: "gemini-pro"
        system_instruction=SYSTEM_INSTRUCTION
    )

    # 4. Vykreslení historie chatu
    avatar_img = get_avatar_image()
    
    for msg in st.session_state.messages:
        # Tady se rozhoduje o ikonce (User vs Bot)
        icon = avatar_img if msg["role"] == "model" else "👤"
        st.chat_message(msg["role"], avatar=icon).write(msg["content"])

    # 5. Vstup od uživatele
    if prompt := st.chat_input("Zadej instrukce..."):
        # Zobrazit dotaz uživatele hned
        st.chat_message("user", avatar="👤").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Získat odpověď od modelu
        try:
            # Vytvoříme chat session s historií
            chat = model.start_chat(history=[
                {"role": m["role"], "parts": [m["content"]]} 
                for m in st.session_state.messages[:-1] # Vše kromě poslední (tu posíláme teď)
            ])
            
            response = chat.send_message(prompt)
            bot_reply = response.text
            
            # Zobrazit odpověď
            st.chat_message("model", avatar=avatar_img).write(bot_reply)
            st.session_state.messages.append({"role": "model", "content": bot_reply})
            
        except Exception as e:
            st.error(f"Chyba spojení s Matrixem: {e}")
