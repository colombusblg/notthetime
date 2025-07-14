import openai
import os
import tiktoken  # si tu ne l'as pas, installe avec `pip install tiktoken`
import streamlit as st

# Initialisation du client OpenAI (une seule ligne suffit)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def truncate_text(text, max_tokens=3000):
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    tokens = enc.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
    return enc.decode(tokens)

def summarize_emails(mails):
    # Debug temporaire - vérification de la clé API
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("❌ Clé OpenAI manquante dans les secrets")
        return "Erreur : clé API manquante"
    elif not api_key.startswith("sk-"):
        st.error("❌ Format de clé OpenAI invalide")
        return "Erreur : format de clé invalide"
    else:
        st.success("✅ Clé OpenAI configurée correctement")
    
    full_text = "\n\n".join(mail['body'] for mail in mails)
    truncated_text = truncate_text(full_text, max_tokens=3000)  # limite à 3000 tokens

    messages = [
        {"role": "system", "content": "Tu es un assistant qui résume des mails."},
        {"role": "user", "content": f"Voici les mails à résumer :\n{truncated_text}"}
    ]

    try:
        # ✅ Utilisation du client au lieu de openai.chat.completions.create
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"❌ Erreur lors de l'appel OpenAI : {str(e)}")
        return f"Erreur : {str(e)}"

def generate_reply(email_body, prompt):
    # Debug temporaire - vérification de la clé API
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("❌ Clé OpenAI manquante dans les secrets")
        return "Erreur : clé API manquante"
    elif not api_key.startswith("sk-"):
        st.error("❌ Format de clé OpenAI invalide")
        return "Erreur : format de clé invalide"
    
    messages = [
        {"role": "system", "content": "Tu es un assistant qui aide à rédiger des emails professionnels."},
        {"role": "user", "content": f"Voici un mail reçu :\n{email_body}\n\nJe souhaite répondre avec cette intention :\n{prompt}"}
    ]

    try:
        # ✅ Utilisation du client au lieu de openai.chat.completions.create
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=700,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"❌ Erreur lors de l'appel OpenAI : {str(e)}")
        return f"Erreur : {str(e)}"