import streamlit as st
from mail_utils import initialize_mails, send_email, parse_email_date
from gpt_utils import summarize_emails, generate_reply
from auth_utils import login_form, logout, is_authenticated
from database_utils import (
    save_email_to_supabase, 
    get_user_emails_from_supabase,
    save_email_summary,
    get_email_summary,
    save_email_reply,
    get_user_preferences,
    save_user_preference,
    get_user_statistics,
    mark_email_as_processed
)
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
user_id = st.session_state.get('user_id')
user_email = st.session_state.get('user_email')

col1, col2 = st.columns([3, 1])

with col1:
    st.title("📬 Assistant Mail – Résumé et Réponses")

with col2:
    st.markdown(f"**👤 Connecté:** {user_email}")
    if st.button("🚪 Déconnexion"):
        logout()

# Charger les préférences utilisateur
user_preferences = get_user_preferences(user_id)
default_date = user_preferences.get("default_filter_date", date.today().isoformat())

# Choix de la date avec un datepicker Streamlit
selected_date = st.date_input(
    "📅 Filtrer les mails depuis cette date :", 
    value=date.fromisoformat(default_date) if default_date else date.today()
)

# Sauvegarder la préférence de date
if selected_date.isoformat() != default_date:
    save_user_preference(user_id, "default_filter_date", selected_date.isoformat())

# Option pour utiliser les données en cache ou recharger
col1, col2 = st.columns([2, 1])
with col1:
    use_cache = st.checkbox("🗄️ Utiliser les données en cache Supabase", value=True)
with col2:
    force_reload = st.button("🔄 Recharger depuis Gmail")

# Initialisation des mails
if 'processed_mails' not in st.session_state or force_reload:
    with st.spinner("🔄 Chargement des mails..."):
        try:
            if use_cache and not force_reload:
                # Charger depuis Supabase
                cached_mails = get_user_emails_from_supabase(user_id, selected_date)
                if cached_mails:
                    # Convertir le format Supabase vers le format attendu
                    st.session_state.processed_mails = []
                    for mail in cached_mails:
                        processed_mail = {
                            'db_id': mail['id'],
                            'subject': mail['subject'],
                            'from': mail['sender'],
                            'to': mail['recipient'],
                            'body': mail['body'],
                            'date': mail['date_received'],
                            'is_processed': mail['is_processed']
                        }
                        st.session_state.processed_mails.append(processed_mail)
                else:
                    # Pas de cache, charger depuis Gmail
                    raw_mails = initialize_mails()
                    st.session_state.processed_mails = []
                    for mail in raw_mails:
                        # Sauvegarder dans Supabase
                        db_id = save_email_to_supabase(user_id, mail)
                        if db_id:
                            mail['db_id'] = db_id
                            st.session_state.processed_mails.append(mail)
            else:
                # Charger depuis Gmail et sauvegarder dans Supabase
                raw_mails = initialize_mails()
                st.session_state.processed_mails = []
                for mail in raw_mails:
                    # Sauvegarder dans Supabase
                    db_id = save_email_to_supabase(user_id, mail)
                    if db_id:
                        mail['db_id'] = db_id
                        st.session_state.processed_mails.append(mail)
                        
        except Exception as e:
            st.error(f"❌ Erreur lors du chargement des mails: {str(e)}")
            st.session_state.processed_mails = []

mails = st.session_state.processed_mails

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

# Vérifier s'il y a déjà un résumé en cache
cached_summary = get_email_summary(user_id, selected_mail['db_id'])

if cached_summary:
    st.info(f"📋 Résumé en cache : {cached_summary['summary_text']}")
    st.caption(f"Généré le {cached_summary['created_at']}")
else:
    with st.spinner("🤖 Génération du résumé..."):
        summary = summarize_emails([selected_mail])
        # Sauvegarder le résumé dans Supabase
        save_email_summary(user_id, selected_mail['db_id'], summary)
        st.info(summary)

# Affichage du contenu complet
with st.expander("📄 Afficher le contenu complet du mail"):
    st.markdown(f"**De:** {selected_mail['from']}")
    st.markdown(f"**Sujet:** {selected_mail['subject']}")
    st.markdown(f"**Date:** {selected_mail['date']}")
    st.markdown(f"**Statut:** {'✅ Traité' if selected_mail.get('is_processed') else '⏳ En attente'}")
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
            # Passer le db_id à la fonction generate_reply
            reply = generate_reply(selected_mail["body"], user_prompt, selected_mail['db_id'])
            st.session_state["generated_reply"] = reply
            # Sauvegarder la réponse générée dans Supabase
            save_email_reply(user_id, selected_mail['db_id'], user_prompt, reply, reply, False)
            st.rerun()

    if send and st.session_state.get("generated_reply"):
        with st.spinner("📤 Envoi de la réponse..."):
            final_reply = st.session_state["generated_reply"]
            success = send_email(
                to=selected_mail["from"],
                subject="Re: " + selected_mail["subject"],
                body=final_reply
            )
            if success:
                # Sauvegarder la réponse envoyée dans Supabase
                save_email_reply(user_id, selected_mail['db_id'], user_prompt, st.session_state["generated_reply"], final_reply, True)
                # Marquer l'email comme traité
                mark_email_as_processed(selected_mail['db_id'])
                st.success("✅ Réponse envoyée avec succès !")
                del st.session_state["generated_reply"]
                st.rerun()
            else:
                st.error("❌ Erreur lors de l'envoi de la réponse")

# Statistiques avancées
st.markdown("---")
st.markdown("### 📊 Statistiques")

# Récupérer les statistiques depuis Supabase
stats = get_user_statistics(user_id)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📧 Mails en cache", stats["total_emails"])
with col2:
    st.metric("🔍 Mails filtrés", len(filtered_mails))
with col3:
    st.metric("📋 Résumés générés", stats["summaries_generated"])
with col4:
    st.metric("📤 Réponses envoyées", stats["replies_sent"])

# Historique des actions récentes
with st.expander("📈 Historique des actions récentes"):
    # Ici vous pourriez ajouter une fonction pour récupérer l'historique
    st.info("Fonctionnalité d'historique à développer selon vos besoins")

# Préférences utilisateur
with st.expander("⚙️ Préférences"):
    st.markdown("**Préférences actuelles:**")
    for key, value in user_preferences.items():
        st.write(f"• {key}: {value}")
    
    # Ajouter des options de préférences
    if st.button("Réinitialiser les préférences"):
        # Logique pour réinitialiser
        st.success("Préférences réinitialisées")