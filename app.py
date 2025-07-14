import streamlit as st
from mail_utils import get_all_emails_with_local_history, send_email
from gpt_utils import summarize_emails, generate_reply
from auth_utils import login_form, logout, is_authenticated
from datetime import datetime, date

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

# Choix de la date avec un datepicker Streamlit (par défaut aujourd'hui)
selected_date = st.date_input("📅 Filtrer les mails depuis cette date :", value=date.today())

def parse_email_date(date_str):
    """
    Convertit la date d'entête mail en objet datetime.
    Supporte plusieurs formats classiques du header Date.
    """
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",  # Exemple : 'Fri, 11 Jul 2025 10:30:00 +0200'
        "%a, %d %b %Y %H:%M:%S",     # Sans fuseau horaire
        "%d %b %Y %H:%M:%S %z",      # Sans jour semaine
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

if not mails:
    st.warning("Aucun mail trouvé.")
    st.stop()

# Filtrer les mails selon la date sélectionnée
filtered_mails = []
for mail in mails:
    mail_date_str = mail.get("date", "")
    mail_datetime = parse_email_date(mail_date_str)
    if mail_datetime is None:
        # Si on ne peut pas parser la date, on ignore le mail
        continue
    # Comparaison uniquement sur la date (sans l'heure)
    if mail_datetime.date() >= selected_date:
        filtered_mails.append(mail)

if not filtered_mails:
    st.warning(f"Aucun mail trouvé depuis le {selected_date.strftime('%d %b %Y')}.")
    st.stop()

# Afficher le nombre de mails trouvés
st.info(f"📊 {len(filtered_mails)} mail(s) trouvé(s) depuis le {selected_date.strftime('%d %b %Y')}")

mail_options = [f"{i+1}. {mail['subject']} – {mail['from']}" for i, mail in enumerate(filtered_mails)]
selected_index = st.selectbox("✉️ Choisissez un mail à traiter :", range(len(mail_options)), format_func=lambda i: mail_options[i])
selected_mail = filtered_mails[selected_index]

st.markdown("### 📌 Résumé du mail")
with st.spinner("🤖 Génération du résumé..."):
    summary = summarize_emails([selected_mail])
st.info(summary)

with st.expander("📄 Afficher le contenu complet du mail"):
    st.markdown(f"**De:** {selected_mail['from']}")
    st.markdown(f"**Sujet:** {selected_mail['subject']}")
    st.markdown(f"**Date:** {selected_mail['date']}")
    st.markdown("**Corps du message:**")
    st.text(selected_mail['body'])

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
                # Nettoyer la réponse générée après envoi
                del st.session_state["generated_reply"]
                st.rerun()
            else:
                st.error("❌ Erreur lors de l'envoi de la réponse")

# Afficher des statistiques en bas
st.markdown("---")
st.markdown("### 📊 Statistiques")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📧 Mails totaux", len(mails))
with col2:
    st.metric("🔍 Mails filtrés", len(filtered_mails))
with col3:
    st.metric("👤 Utilisateur", st.session_state.get('user_email', 'N/A').split('@')[0])

    try:
    data = supabase.table("users").select("*").limit(1).execute()
    st.write("Accès à la table users OK :", data)
except Exception as e:
st.error(f"Erreur d'accès à la table users : {e}")