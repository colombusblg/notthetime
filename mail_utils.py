import streamlit as st
from gpt_utils import summarize_emails, generate_reply
from auth_utils import login_form, logout, is_authenticated
from datetime import datetime, date
import os

# Configuration OpenAI
os.environ["OPENAI_API_KEY"] = st.secrets.get("OPENAI_API_KEY", "")

st.set_page_config(page_title="Assistant Mail", layout="centered")

# Vérifier l'authentification
if not is_authenticated():
    login_form()
    st.stop()

# Interface principale pour les utilisateurs connectés
col1, col2 = st.columns([3, 1])

with col1:
    st.title("📬 Assistant Mail – Résumé et Réponses")

with col2:
    st.markdown(f"**👤 Connecté:** {st.session_state.get('user_email', 'Utilisateur')}")
    if st.button("🚪 Déconnexion"):
        logout()

# Choix de la date avec un datepicker Streamlit
selected_date = st.date_input("📅 Filtrer les mails depuis cette date :", value=date.today())

def parse_email_date(date_str):
    """Convertit la date d'entête mail en objet datetime"""
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S",
        "%d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except Exception:
            continue
    return None

with st.spinner("🔄 Chargement des mails..."):
    mails = get_all_emails_with_local_history()

    from supabase import create_client, Client
import os

SUPABASE_URL = st.secrets["https://rpwmjydoqnexqryptecf.supabase.co"]
SUPABASE_KEY = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJwd21qeWRvcW5leHFyeXB0ZWNmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI0OTYwNDAsImV4cCI6MjA2ODA3MjA0MH0.W70oVTXwR9zYac9pF3RUsJOe9O_tPuyhcYrk8cr3vrQ"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_email_history(user_id, email_from, subject, email_date, body):
    data = {
        "user_id": user_id,
        "email_from": email_from,
        "subject": subject,
        "email_date": email_date,
        "body": body
    }
    response = supabase.table("email_history").insert(data).execute()
    if response.error:
        print(f"Erreur sauvegarde email : {response.error}")
    else:
        print("Email sauvegardé en base")


if not mails:
    st.warning("Aucun mail trouvé.")
    st.stop()

# Filtrer les mails selon la date sélectionnée
filtered_mails = []
for mail in mails:
    mail_date_str = mail.get("date", "")
    mail_datetime = parse_email_date(mail_date_str)
    if mail_datetime is None:
        continue
    if mail_datetime.date() >= selected_date:
        filtered_mails.append(mail)

if not filtered_mails:
    st.warning(f"Aucun mail trouvé depuis le {selected_date.strftime('%d %b %Y')}.")
    st.stop()

# Afficher le nombre de mails trouvés
st.info(f"📊 {len(filtered_mails)} mail(s) trouvé(s) depuis le {selected_date.strftime('%d %b %Y')}")

# Sélection du mail
mail_options = [f"{i+1}. {mail['subject']} – {mail['from']}" for i, mail in enumerate(filtered_mails)]
selected_index = st.selectbox("✉️ Choisissez un mail à traiter :", range(len(mail_options)), format_func=lambda i: mail_options[i])
selected_mail = filtered_mails[selected_index]

# Résumé du mail
st.markdown("### 📌 Résumé du mail")
with st.spinner("🤖 Génération du résumé..."):
    summary = summarize_emails([selected_mail])
st.info(summary)

# Affichage du contenu complet
with st.expander("📄 Afficher le contenu complet du mail"):
    st.markdown(f"**De:** {selected_mail['from']}")
    st.markdown(f"**Sujet:** {selected_mail['subject']}")
    st.markdown(f"**Date:** {selected_mail['date']}")
    st.markdown("**Corps du message:**")
    st.text(selected_mail['body'])

# Génération et envoi de réponse
st.markdown("### 🤖 Générer et envoyer une réponse")

with st.form("reply_form"):
    user_prompt = st.text_input(
        "💭 Expliquez ce que vous voulez répondre", 
        placeholder="ex: 'Refuser poliment', 'Demander plus d'infos', 'Accepter la proposition'..."
    )

    generated_reply = st.text_area(
        "✍️ Réponse générée (modifiable avant envoi)",
        value=st.session_state.get("generated_reply", ""),
        height=300,
        placeholder="La réponse générée apparaîtra ici..."
    )

    col1, col2 = st.columns(2)
    with col1:
        generate = st.form_submit_button("💬 Générer une réponse", use_container_width=True)
    with col2:
        send = st.form_submit_button("📤 Envoyer la réponse", use_container_width=True)

    if generate and user_prompt:
        with st.spinner("🤖 GPT rédige une réponse..."):
            reply = generate_reply(selected_mail["body"], user_prompt)
            st.session_state["generated_reply"] = reply
            st.rerun()

    if send and st.session_state.get("generated_reply"):
        with st.spinner("📤 Envoi de la réponse..."):
            success = send_email(
                to=selected_mail["from"],
                subject="Re: " + selected_mail["subject"],
                body=st.session_state["generated_reply"]
            )
            if success:
                st.success("✅ Réponse envoyée avec succès !")
                del st.session_state["generated_reply"]
                st.rerun()
            else:
                st.error("❌ Erreur lors de l'envoi de la réponse")

# Statistiques
st.markdown("---")
st.markdown("### 📊 Statistiques")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📧 Mails totaux", len(mails))
with col2:
    st.metric("🔍 Mails filtrés", len(filtered_mails))
with col3:
    st.metric("👤 Utilisateur", st.session_state.get('user_email', 'N/A').split('@')[0])