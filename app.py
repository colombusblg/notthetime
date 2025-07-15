import streamlit as st
from mail_utils import initialize_mails, send_email, parse_email_date, get_gmail_categories, fetch_all_categorized_emails
from gpt_utils import summarize_emails, generate_reply
from auth_utils import login_form, logout, is_authenticated
from database_utils import (
    save_email_to_supabase, 
    get_user_emails_from_supabase,
    get_user_emails_by_category,
    get_category_statistics,
    save_email_summary,
    get_email_summary,
    save_email_reply,
    get_user_preferences,
    save_user_preference,
    get_user_statistics,
    mark_email_as_processed
)
from datetime import datetime, date, timezone

st.set_page_config(page_title="Assistant Mail", layout="wide")

# Vérifier l'authentification
if not is_authenticated():
    login_form()
    st.stop()

# Interface principale pour les utilisateurs connectés
user_id = st.session_state.get('user_id')
user_email = st.session_state.get('user_email')

col1, col2 = st.columns([3, 1])

with col1:
    st.title("📬 Assistant Mail – Résumé et Réponses par Catégorie")

with col2:
    st.markdown(f"**👤 Connecté:** {user_email}")
    if st.button("🚪 Déconnexion"):
        logout()

# Charger les préférences utilisateur
user_preferences = get_user_preferences(user_id)
default_date = user_preferences.get("default_filter_date", date.today().isoformat())

# Configuration de l'interface
st.markdown("### ⚙️ Configuration")

col1, col2 = st.columns([2, 1])

with col1:
    # Choix de la date avec un datepicker Streamlit
    selected_date = st.date_input(
        "📅 Filtrer les mails depuis cette date :", 
        value=date.fromisoformat(default_date) if default_date else date.today()
    )

with col2:
    # Sélection des catégories à afficher
    available_categories = list(get_gmail_categories().keys())
    selected_categories = st.multiselect(
        "📂 Catégories à afficher :",
        available_categories,
        default=user_preferences.get("selected_categories", available_categories)
    )

# Sauvegarder les préférences
if selected_date.isoformat() != default_date:
    save_user_preference(user_id, "default_filter_date", selected_date.isoformat())

if selected_categories != user_preferences.get("selected_categories", available_categories):
    save_user_preference(user_id, "selected_categories", selected_categories)

# Options de chargement
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    use_cache = st.checkbox("🗄️ Utiliser les données en cache Supabase", value=True)
with col2:
    force_reload = st.button("🔄 Recharger depuis Gmail")
with col3:
    show_stats = st.checkbox("📊 Afficher les statistiques", value=True)

# Initialisation des mails par catégorie
if 'categorized_mails' not in st.session_state or force_reload or not use_cache:
    with st.spinner("🔄 Chargement des mails par catégorie..."):
        try:
            if use_cache and not force_reload:
                # Charger depuis Supabase
                st.info("📥 Chargement des emails depuis la base de données...")
                cached_mails = get_user_emails_by_category(user_id, selected_date, selected_categories, limit_per_category=50)
                
                if cached_mails and any(len(emails) > 0 for emails in cached_mails.values()):
                    # Convertir le format Supabase vers le format attendu
                    st.session_state.categorized_mails = {}
                    for category, emails in cached_mails.items():
                        st.session_state.categorized_mails[category] = []
                        for mail in emails:
                            processed_mail = {
                                'db_id': mail['id'],
                                'subject': mail['subject'],
                                'from': mail['sender'],
                                'to': mail['recipient'],
                                'body': mail['body'],
                                'date': mail['date_received'],
                                'category': mail.get('category', category),
                                'is_processed': mail['is_processed']
                            }
                            st.session_state.categorized_mails[category].append(processed_mail)
                    
                    total_emails = sum(len(emails) for emails in st.session_state.categorized_mails.values())
                    st.success(f"✅ {total_emails} emails chargés depuis la base de données")
                else:
                    st.info("📭 Aucun email en cache, chargement depuis Gmail...")
                    # Charger depuis Gmail
                    categorized_mails = fetch_all_categorized_emails(selected_date, limit_per_category=50)
                    
                    # Convertir au format attendu et synchroniser
                    st.session_state.categorized_mails = {}
                    for category, emails in categorized_mails.items():
                        if category in selected_categories:
                            converted_emails = []
                            for email in emails:
                                email['category'] = category
                                # Synchroniser avec la base
                                from database_utils import sync_emails_with_imap
                                sync_emails_with_imap(user_id, [email])
                                
                                converted_emails.append({
                                    'db_id': None,  # Sera mis à jour après sync
                                    'subject': email['subject'],
                                    'from': email['from'],
                                    'to': email['to'],
                                    'body': email['body'],
                                    'date': email['date'],
                                    'category': category,
                                    'is_processed': False
                                })
                            st.session_state.categorized_mails[category] = converted_emails
            else:
                # Forcer le chargement depuis Gmail
                st.info("📧 Chargement des emails depuis Gmail...")
                categorized_mails = fetch_all_categorized_emails(selected_date, limit_per_category=50)
                
                # Convertir et synchroniser
                st.session_state.categorized_mails = {}
                for category, emails in categorized_mails.items():
                    if category in selected_categories:
                        converted_emails = []
                        for email in emails:
                            email['category'] = category
                            # Synchroniser avec la base
                            from database_utils import sync_emails_with_imap
                            sync_emails_with_imap(user_id, [email])
                            
                            converted_emails.append({
                                'db_id': None,
                                'subject': email['subject'],
                                'from': email['from'],
                                'to': email['to'],
                                'body': email['body'],
                                'date': email['date'],
                                'category': category,
                                'is_processed': False
                            })
                        st.session_state.categorized_mails[category] = converted_emails
                
        except Exception as e:
            st.error(f"❌ Erreur lors du chargement des mails: {str(e)}")
            st.session_state.categorized_mails = {}

categorized_mails = st.session_state.categorized_mails

# Affichage des statistiques
if show_stats:
    st.markdown("### 📊 Statistiques par catégorie")
    
    # Statistiques globales
    stats = get_user_statistics(user_id)
    category_stats = get_category_statistics(user_id)
    
    # Affichage des métriques
    cols = st.columns(len(selected_categories) + 1)
    
    with cols[0]:
        total_filtered = sum(len(emails) for emails in categorized_mails.values())
        st.metric("📧 Total filtré", total_filtered)
    
    for idx, category in enumerate(selected_categories):
        with cols[idx + 1]:
            count = len(categorized_mails.get(category, []))
            total_in_db = category_stats.get(category, 0)
            st.metric(f"📂 {category}", f"{count}/{total_in_db}")

# Interface principale avec onglets par catégorie
if not categorized_mails or not any(len(emails) > 0 for emails in categorized_mails.values()):
    st.warning("Aucun mail trouvé dans les catégories sélectionnées. Essayez de :")
    st.markdown("- Vérifier votre connexion Gmail")
    st.markdown("- Sélectionner d'autres catégories")
    st.markdown("- Cliquer sur 'Recharger depuis Gmail'")
    st.markdown("- Vérifier que vous avez bien des emails dans vos catégories Gmail")
    st.stop()

# Créer des onglets pour chaque catégorie
tabs = st.tabs([f"📂 {cat} ({len(categorized_mails.get(cat, []))})" for cat in selected_categories if categorized_mails.get(cat)])

for tab_idx, category in enumerate([cat for cat in selected_categories if categorized_mails.get(cat)]):
    with tabs[tab_idx]:
        emails_in_category = categorized_mails[category]
        
        if not emails_in_category:
            st.info(f"Aucun email dans la catégorie '{category}' depuis le {selected_date.strftime('%d %b %Y')}")
            continue
        
        st.markdown(f"### 📨 Emails de '{category}' ({len(emails_in_category)} trouvés)")
        
        # Sélection du mail dans cette catégorie
        mail_options = [f"{i+1}. {mail['subject']} – {mail['from']}" for i, mail in enumerate(emails_in_category)]
        selected_index = st.selectbox(
            f"✉️ Choisissez un mail de '{category}' :", 
            range(len(mail_options)), 
            format_func=lambda i: mail_options[i],
            key=f"select_{category}"
        )
        selected_mail = emails_in_category[selected_index]
        
        # Affichage des détails du mail sélectionné
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("#### 📌 Résumé du mail")
            
            # Vérifier s'il y a déjà un résumé en cache
            cached_summary = None
            if selected_mail.get('db_id'):
                cached_summary = get_email_summary(user_id, selected_mail['db_id'])
            
            if cached_summary and cached_summary.get('summary_text') and not cached_summary['summary_text'].startswith('Erreur'):
                st.info(f"📋 Résumé : {cached_summary['summary_text']}")
                st.caption(f"Généré le {cached_summary.get('created_at', 'Date inconnue')}")
            else:
                with st.spinner("🤖 Génération du résumé..."):
                    summary = summarize_emails([selected_mail])
                    
                    if summary and not summary.startswith('Erreur'):
                        # Sauvegarder le résumé dans Supabase
                        if selected_mail.get('db_id'):
                            save_email_summary(user_id, selected_mail['db_id'], summary)
                        st.info(summary)
                    else:
                        st.error(f"❌ Échec de la génération du résumé : {summary}")
        
        with col2:
            st.markdown("#### 📄 Détails")
            st.markdown(f"**De:** {selected_mail['from']}")
            st.markdown(f"**À:** {selected_mail.get('to', 'N/A')}")
            st.markdown(f"**Date:** {selected_mail['date']}")
            st.markdown(f"**Statut:** {'✅ Traité' if selected_mail.get('is_processed') else '⏳ En attente'}")
        
        # Affichage du contenu complet
        with st.expander("📄 Afficher le contenu complet du mail"):
            st.markdown(f"**Sujet:** {selected_mail['subject']}")
            st.markdown("**Corps du message:**")
            st.text(selected_mail['body'])
        
        # Génération et envoi de réponse
        st.markdown("#### 🤖 Générer et envoyer une réponse")
        
        with st.form(f"reply_form_{category}"):
            user_prompt = st.text_input(
                "💭 Expliquez ce que vous voulez répondre", 
                placeholder="ex: 'Refuser poliment', 'Demander plus d'infos', 'Accepter la proposition'...",
                key=f"prompt_{category}"
            )

            generated_reply = st.text_area(
                "✍️ Réponse générée (modifiable avant envoi)",
                value=st.session_state.get(f"generated_reply_{category}", ""),
                height=200,
                placeholder="La réponse générée apparaîtra ici...",
                key=f"reply_{category}"
            )

            col1, col2 = st.columns(2)
            with col1:
                generate = st.form_submit_button("💬 Générer une réponse", use_container_width=True)
            with col2:
                send = st.form_submit_button("📤 Envoyer la réponse", use_container_width=True)

            if generate and user_prompt:
                with st.spinner("🤖 GPT rédige une réponse..."):
                    reply = generate_reply(selected_mail["body"], user_prompt, selected_mail.get('db_id'))
                    st.session_state[f"generated_reply_{category}"] = reply
                    # Sauvegarder la réponse générée dans Supabase
                    if selected_mail.get('db_id'):
                        save_email_reply(user_id, selected_mail['db_id'], user_prompt, reply, reply, False)
                    st.rerun()

            if send and st.session_state.get(f"generated_reply_{category}"):
                with st.spinner("📤 Envoi de la réponse..."):
                    final_reply = st.session_state[f"generated_reply_{category}"]
                    success = send_email(
                        to=selected_mail["from"],
                        subject="Re: " + selected_mail["subject"],
                        body=final_reply
                    )
                    if success:
                        # Sauvegarder la réponse envoyée dans Supabase
                        if selected_mail.get('db_id'):
                            save_email_reply(user_id, selected_mail['db_id'], user_prompt, st.session_state[f"generated_reply_{category}"], final_reply, True)
                            # Marquer l'email comme traité
                            mark_email_as_processed(selected_mail['db_id'])
                        st.success("✅ Réponse envoyée avec succès !")
                        del st.session_state[f"generated_reply_{category}"]
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de l'envoi de la réponse")

# Statistiques globales en bas
st.markdown("---")
st.markdown("### 📊 Statistiques globales")

stats = get_user_statistics(user_id)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📧 Total emails en base", stats["total_emails"])
with col2:
    total_filtered = sum(len(emails) for emails in categorized_mails.values())
    st.metric("🔍 Emails filtrés", total_filtered)
with col3:
    st.metric("📋 Résumés générés", stats["summaries_generated"])
with col4:
    st.metric("📤 Réponses envoyées", stats["replies_sent"])

# Préférences et historique
with st.expander("⚙️ Préférences et paramètres"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Préférences actuelles:**")
        for key, value in user_preferences.items():
            if isinstance(value, list):
                st.write(f"• {key}: {', '.join(value)}")
            else:
                st.write(f"• {key}: {value}")
    
    with col2:
        st.markdown("**Actions:**")
        if st.button("🔄 Réinitialiser toutes les préférences"):
            # Logique pour réinitialiser
            st.success("Préférences réinitialisées")
        
        if st.button("🗑️ Vider le cache de l'application"):
            # Vider le cache Streamlit
            for key in list(st.session_state.keys()):
                if key.startswith(('categorized_mails', 'generated_reply')):
                    del st.session_state[key]
            st.success("Cache vidé")
            st.rerun()