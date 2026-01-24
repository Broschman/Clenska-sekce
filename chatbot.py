import streamlit as st
import google.generativeai as genai
import pandas as pd
import data_manager 
from google.api_core import exceptions
import time

# === KONFIGURACE ===
AVATAR_BOT = "🤖" 
AVATAR_USER = "👤"
# Používáme stabilní alias (funguje na všech verzích)
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
    st.caption(f"Online (Manual Function Calling).")

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

    # 3. Inicializace Modelu
    # DŮLEŽITÉ: Zde NEMÁME 'tools=tools_list' v konstruktoru, abychom to řídili ručně? 
    # NE, tools tam být musí, aby model věděl, že je má. Ale automatiku vypneme v chatu.
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

    # Vykreslení zpráv (bez function calls)
    for msg in st.session_state.chat_history:
        role = "user" if msg["role"] == "user" else "model"
        icon = AVATAR_USER if role == "user" else AVATAR_BOT
        
        text_content = ""
        parts = msg.get("parts", [])
        if isinstance(parts, list):
            for p in parts:
                if isinstance(p, str): text_content += p
                elif hasattr(p, "text"): text_content += p.text
                # Function calls ignorujeme při vykreslování historie
        elif isinstance(parts, str):
            text_content = parts
            
        if text_content:
            st.chat_message(role, avatar=icon).write(text_content)

    # 5. Chat Input
    if prompt := st.chat_input("Tvůj pokyn..."):
        st.chat_message("user", avatar=AVATAR_USER).write(prompt)
        st.session_state.chat_history.append({"role": "user", "parts": [prompt]})

        try:
            # Start chatu BEZ automatiky (budeme si to řídit sami)
            chat = model.start_chat(history=st.session_state.chat_history[:-1])
            
            with st.chat_message("model", avatar=AVATAR_BOT):
                with st.spinner("Mákám na tom..."):
                    # 1. První dotaz
                    response = chat.send_message(prompt)
                    
                    # 2. SMYČKA PRO ZPRACOVÁNÍ FUNKCÍ
                    # Dokud model vrací function_call, my ho musíme vykonat
                    loop_limit = 5 # Pojistka proti nekonečné smyčce
                    while response.parts and response.parts[0].function_call and loop_limit > 0:
                        loop_limit -= 1
                        
                        # A) Co chce model zavolat?
                        fc = response.parts[0].function_call
                        fn_name = fc.name
                        fn_args = dict(fc.args) # Argumenty funkce
                        
                        st.caption(f"🔧 Volám funkci: `{fn_name}`...")
                        
                        # B) Router - Rozřazení na funkce v data_manager
                        result_data = None
                        try:
                            if fn_name == "sign_up_user":
                                result_data = data_manager.sign_up_user(**fn_args)
                            elif fn_name == "sign_out_user":
                                result_data = data_manager.sign_out_user(**fn_args)
                            elif fn_name == "get_event_info":
                                result_data = data_manager.get_event_info(**fn_args)
                            else:
                                result_data = f"Error: Neznámá funkce {fn_name}"
                        except Exception as e:
                            result_data = f"Error při vykonávání funkce: {e}"

                        # C) Vrátíme výsledek modelu
                        # Model si to přečte a buď vygeneruje text, nebo zavolá další funkci
                        response = chat.send_message(
                            genai.protos.Content(
                                parts=[genai.protos.Part(
                                    function_response=genai.protos.FunctionResponse(
                                        name=fn_name,
                                        response={"result": result_data}
                                    )
                                )]
                            )
                        )
                    
                    # 3. Konec smyčky - Tady už MUSÍ být text
                    bot_text = response.text
                    st.markdown(bot_text)
                    st.session_state.chat_history.append({"role": "model", "parts": [bot_text]})
        
        except exceptions.ResourceExhausted:
             st.error("❌ Došel limit požadavků. Dej si chvilku pauzu.")
        except ValueError:
             # Pokud i po smyčce není text (velmi vzácné), zachytíme to
             st.error("⚠️ Model vrátil nestandardní odpověď (asi se zasekl při volání funkce).")
        except Exception as e:
             st.error(f"Chyba: {str(e)}")
