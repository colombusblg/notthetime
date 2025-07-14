import openai
import os
import tiktoken  # si tu ne l'as pas, installe avec `pip install tiktoken`
import streamlit as st

def get_openai_client():
    """Configuration robuste de l'API OpenAI pour Streamlit"""
    try:
        # Essaie d'abord les secrets Streamlit (pour le déploiement)
        api_key = st.secrets["OPENAI_API_KEY"]
        st.success("✅ Clé OpenAI configurée depuis les secrets Streamlit")
    except (KeyError, AttributeError):
        # Fallback vers les variables d'environnement (pour le développement local)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            st.success("✅ Clé OpenAI configurée depuis les variables d'environnement")
        else:
            st.error("❌ Clé OpenAI manquante dans les secrets Streamlit ET les variables d'environnement")
            st.stop()
    
    # Vérification du format de la clé
    if not api_key or not api_key.startswith("sk-"):
        st.error("❌ Format de clé OpenAI invalide")
        st.stop()
    
    return openai.OpenAI(api_key=api_key)

# Initialisation du client OpenAI
client = get_openai_client()

def truncate_text(text, max_tokens=3000):
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    tokens = enc.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
    return enc.decode(tokens)

def summarize_emails(mails):
    full_text = "\n\n".join(mail['body'] for mail in mails)
    truncated_text = truncate_text(full_text, max_tokens=3000)  # limite à 3000 tokens

    messages = [
        {"role": "system", "content": "Tu es un assistant qui résume des mails."},
        {"role": "user", "content": f"Voici les mails à résumer :\n{truncated_text}"}
    ]

    try:
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
    messages = [
        {"role": "system", "content": "Tu es un assistant qui aide à rédiger des emails professionnels."},
        {"role": "user", "content": f"Voici un mail reçu :\n{email_body}\n\nJe souhaite répondre avec cette intention :\n{prompt}"}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=700,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"❌ Erreur lors de l'appel OpenAI : {str(e)}")
        return f"Erreur : {str(e)}"