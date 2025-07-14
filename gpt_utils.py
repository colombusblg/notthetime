import openai
import os
import tiktoken
import streamlit as st
from database_utils import save_email_summary, get_email_summary, save_email_reply

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
    """Génère un résumé des emails - avec mise en cache en DB"""
    try:
        # Si c'est un seul email avec un ID, vérifier le cache
        if len(mails) == 1 and mails[0].get('db_id'):
            user_id = st.session_state.get('user_id')
            email_db_id = mails[0]['db_id']
            if user_id and email_db_id:
                cached_summary = get_email_summary(user_id, email_db_id)
                if cached_summary:
                    return cached_summary['summary_text']
        
        # Générer le résumé
        full_text = "\n\n".join(mail['body'] for mail in mails)
        truncated_text = truncate_text(full_text, max_tokens=3000)

        messages = [
            {"role": "system", "content": "Tu es un assistant qui résume des mails."},
            {"role": "user", "content": f"Voici les mails à résumer :\n{truncated_text}"}
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000,
        )
        
        summary = response.choices[0].message.content
        
        # Sauvegarder en cache si c'est un seul email
        if len(mails) == 1 and mails[0].get('db_id'):
            user_id = st.session_state.get('user_id')
            email_db_id = mails[0]['db_id']
            if user_id and email_db_id:
                save_email_summary(user_id, email_db_id, summary)
        
        return summary
        
    except Exception as e:
        st.error(f"❌ Erreur lors de l'appel OpenAI : {str(e)}")
        return f"Erreur : {str(e)}"

def generate_reply(email_body, prompt, email_db_id=None):
    """Génère une réponse à un email - avec sauvegarde en DB"""
    try:
        messages = [
            {"role": "system", "content": "Tu es un assistant qui aide à rédiger des emails professionnels."},
            {"role": "user", "content": f"Voici un mail reçu :\n{email_body}\n\nJe souhaite répondre avec cette intention :\n{prompt}"}
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=700,
        )
        
        reply = response.choices[0].message.content.strip()
        
        # Sauvegarder la réponse en base de données
        user_id = st.session_state.get('user_id')
        if user_id and email_db_id:
            reply_id = save_email_reply(user_id, email_db_id, prompt, reply, reply, was_sent=False)
            # Stocker l'ID de la réponse dans la session pour le suivi
            st.session_state['current_reply_id'] = reply_id
        
        return reply
        
    except Exception as e:
        st.error(f"❌ Erreur lors de l'appel OpenAI : {str(e)}")
        return f"Erreur : {str(e)}"