import streamlit as st
import google.generativeai as genai
import pandas as pd
import data_manager 
from google.api_core import exceptions
import time

# === KONFIGURACE ===
AVATAR_BOT = "🤖" 
AVATAR_USER = "👤"
MODEL_NAME = "gemini-flash-latest" # Stabilní verze

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
    st.caption(f"Online (v1.5/Latest).")

    # 1. Definice Nástrojů
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

    # 3. Inicializace Modelu
    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME, 
            tools=tools_list,
            system_instruction=system_instruction
        )
    except Exception as e:
        st.error(f"❌ Chyba modelu: {e}")
        return

    # 4. Historie
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "model", "parts": ["Zdar šampione! 🌲 Jsem připraven. Co podnikneme?"]}
        ]

    # Vykreslení historie
    for msg in st.session_state.chat_history:
        role = "user" if msg["role"] == "user" else "model"
        icon = AVATAR_USER if role == "user" else AVATAR_BOT
        
        text_content = ""
        parts = msg.get("parts", [])
        if isinstance(parts, list):
            for p in parts:
                if isinstance(p, str): text_content += p
                elif hasattr(p, "text"): text_content += p.text
                # Ignorujeme function calls v historii, aby to nepadalo
        elif isinstance(parts, str):
            text_content = parts
            
        if text_content:
            st.chat_message(role, avatar=icon).write(text_content)

    # 5. Chat Input
    if prompt := st.chat_input("Tvůj pokyn..."):
        st.chat_message("user", avatar=AVATAR_USER).write(prompt)
        st.session_state.chat_history.append({"role": "user", "parts": [prompt]})

        try:
            # Zapneme automatické volání funkcí
            chat = model.start_chat(
                history=st.session_state.chat_history[:-1],
                enable_automatic_function_calling=True 
            )
            
            with st.chat_message("model", avatar=AVATAR_BOT):
                with st.spinner("Mákám na tom..."):
                    response = chat.send_message(prompt)
                    
                    # === ZÁCHRANNÁ SÍŤ PRO TEXT ===
                    bot_text = ""
                    try:
                        # Pokusíme se získat text (výsledek)
                        bot_text = response.text
                    except ValueError:
                        # Pokud to spadne, znamená to, že bot vrátil jen VOLÁNÍ FUNKCE, ale ne výsledek.
                        # Vytáhneme info o tom, co chtěl udělat.
                        debug_parts = []
                        for part in response.parts:
                            if fn := part.function_call:
                                args = ", ".join(f"{k}='{v}'" for k, v in fn.args.items())
                                debug_parts.append(f"🔧 **Volám funkci:** `{fn.name}({args})`")
                                debug_parts.append("*(Automatické spuštění selhalo, zkontroluj logy nebo knihovnu)*")
                            else:
                                debug_parts.append(str(part))
                        bot_text = "\n\n".join(debug_parts)
                    
                    if not bot_text: 
                        bot_text = "⚠️ (Odpověď je prázdná)"

                    st.markdown(bot_text)
                    # Ukládáme jen textovou reprezentaci, abychom nerozbili historii
                    st.session_state.chat_history.append({"role": "model", "parts": [bot_text]})
        
        except exceptions.ResourceExhausted:
             st.error("❌ Limit API vyčerpán. Dej si pauzu.")
        except Exception as e:
             st.error(f"Chyba: {str(e)}")
