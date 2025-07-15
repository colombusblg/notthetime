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
import json

# Configuration de la page
st.set_page_config(
    page_title="📧 Assistant Mail", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS moderne qui fonctionne avec Streamlit
st.markdown("""
<style>
    /* Variables de couleur Gmail */
    :root {
        --gmail-blue: #1a73e8;
        --gmail-red: #d93025;
        --gmail-yellow: #f9ab00;
        --gmail-green: #137333;
        --gmail-gray-50: #f8f9fa;
        --gmail-gray-100: #f1f3f4;
        --gmail-gray-600: #5f6368;
        --gmail-gray-800: #3c4043;
    }
    
    /* Style global */
    .main .block-container {
        padding-top: 1rem;
        max-width: none;
    }
    
    /* Header moderne */
    .header-container {
        background: linear-gradient(135deg, var(--gmail-blue), #4285f4);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(26, 115, 232, 0.15);
    }
    
    .header-title {
        font-size: 2rem;
        font-weight: 600;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .header-subtitle {
        opacity: 0.9;
        margin-top: 0.5rem;
        font-size: 1.1rem;
    }
    
    /* Cards modernes */
    .email-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .email-card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        transform: translateY(-2px);
        border-color: var(--gmail-blue);
    }
    
    .email-card.unread {
        border-left: 4px solid var(--gmail-blue);
        background: #f8f9ff;
    }
    
    .email-card.read {
        opacity: 0.8;
    }
    
    .email-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1rem;
    }
    
    .email-sender {
        font-weight: 600;
        color: var(--gmail-gray-800);
        font-size: 1.1rem;
    }
    
    .email-date {
        color: var(--gmail-gray-600);
        font-size: 0.9rem;
    }
    
    .email-subject {
        font-size: 1.2rem;
        font-weight: 500;
        color: var(--gmail-gray-800);
        margin-bottom: 0.5rem;
    }
    
    .email-snippet {
        color: var(--gmail-gray-600);
        line-height: 1.5;
    }
    
    .email-status {
        display: inline-block;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        margin-top: 0.5rem;
    }
    
    .status-unread {
        background: #e3f2fd;
        color: var(--gmail-blue);
    }
    
    .status-read {
        background: #f1f3f4;
        color: var(--gmail-gray-600);
    }
    
    /* Onglets modernes */
    .tab-container {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 2rem;
        border-bottom: 2px solid #f1f3f4;
    }
    
    .tab-item {
        padding: 1rem 1.5rem;
        border-radius: 8px 8px 0 0;
        background: #f8f9fa;
        border: none;
        cursor: pointer;
        font-weight: 500;
        color: var(--gmail-gray-600);
        transition: all 0.2s;
    }
    
    .tab-item.active {
        background: var(--gmail-blue);
        color: white;
        transform: translateY(-2px);
    }
    
    /* Stats cards */
    .stats-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }
    
    .stat-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: var(--gmail-blue);
        margin-bottom: 0.5rem;
    }
    
    .stat-label {
        color: var(--gmail-gray-600);
        font-weight: 500;
    }
    
    /* Section résumé */
    .summary-section {
        background: linear-gradient(135deg, #e3f2fd, #f3e5f5);
        border: 1px solid #bbdefb;
        border-radius: 12px;
        padding: 2rem;
        margin: 2rem 0;
    }
    
    .summary-title {
        color: var(--gmail-blue);
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .summary-content {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid var(--gmail-blue);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Section réponse */
    .reply-section {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 2rem;
        margin-top: 2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .reply-title {
        color: var(--gmail-gray-800);
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Boutons modernes */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        border: none;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Messages de statut */
    .success-message {
        background: #e8f5e8;
        border: 1px solid #4caf50;
        border-radius: 8px;
        padding: 1rem;
        color: #2e7d32;
        margin: 1rem 0;
    }
    
    .error-message {
        background: #ffebee;
        border: 1px solid #f44336;
        border-radius: 8px;
        padding: 1rem;
        color: #c62828;
        margin: 1rem 0;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .header-container {
            padding: 1rem;
        }
        
        .header-title {
            font-size: 1.5rem;
        }
        
        .email-card {
            padding: 1rem;
        }
        
        .stats-container {
            grid-template-columns: 1fr;
        }
    }
</style>
""", unsafe_allow_html=True)

# Vérifier l'authentification
if not is_authenticated():
    login_form()
    st.stop()

# Variables de session
user_id = st.session_state.get('user_id')
user_email = st.session_state.get('user_email')

# Initialiser l'état de navigation
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'list'
if 'selected_email' not in st.session_state:
    st.session_state.selected_email = None
if 'active_category' not in st.session_state:
    st.session_state.active_category = 'Boîte de réception'

# Header moderne
st.markdown(f"""
<div class="header-container">
    <div class="header-title">📧 Assistant Mail</div>
    <div class="header-subtitle">Connecté en tant que {user_email}</div>
</div>
""", unsafe_allow_html=True)

# Sidebar avec navigation
with st.sidebar:
    st.markdown("### 🗂️ Navigation")
    
    # Bouton déconnexion
    if st.button("🚪 Déconnexion", use_container_width=True):
        logout()
    
    st.markdown("---")
    
    # Sélection de catégorie
    categories = list(get_gmail_categories().keys())
    selected_category = st.selectbox(
        "📂 Catégorie",
        categories,
        index=categories.index(st.session_state.active_category) if st.session_state.active_category in categories else 0
    )
    
    if selected_category != st.session_state.active_category:
        st.session_state.active_category = selected_category
        st.session_state.current_view = 'list'
        st.rerun()
    
    # Filtre par date
    user_preferences = get_user_preferences(user_id)
    default_date = user_preferences.get("default_filter_date", date.today().isoformat())
    
    since_date = st.date_input(
        "📅 Depuis",
        value=date.fromisoformat(default_date) if default_date else date.today()
    )
    
    # Options
    use_cache = st.checkbox("🗄️ Utiliser le cache", value=True)
    
    if st.button("🔄 Recharger", use_container_width=True):
        st.session_state.force_reload = True
        st.rerun()
    
    # Statistiques
    st.markdown("---")
    st.markdown("### 📊 Statistiques")
    
    stats = get_user_statistics(user_id)
    category_stats = get_category_statistics(user_id)
    
    st.metric("📧 Total emails", stats["total_emails"])
    st.metric("📋 Résumés", stats["summaries_generated"])
    st.metric("📤 Réponses", stats["replies_sent"])
    st.metric(f"📂 {selected_category}", category_stats.get(selected_category, 0))

# Fonction pour charger les emails
@st.cache_data(ttl=300)  # Cache 5 minutes
def load_emails_cached(category, since_date_str, use_cache_param):
    """Charge les emails avec cache"""
    try:
        since_date_obj = date.fromisoformat(since_date_str)
        
        if use_cache_param:
            # Charger depuis Supabase
            cached_emails = get_user_emails_by_category(
                user_id, 
                since_date_obj, 
                [category], 
                limit_per_category=100
            )
            
            if cached_emails and cached_emails.get(category):
                emails = []
                for mail in cached_emails[category]:
                    emails.append({
                        'db_id': mail.get('id'),
                        'subject': mail.get('subject', ''),
                        'from': mail.get('sender', ''),
                        'to': mail.get('recipient', ''),
                        'body': mail.get('body', ''),
                        'date': mail.get('date_received', ''),
                        'category': mail.get('category', category),
                        'is_processed': mail.get('is_processed', False)
                    })
                return emails
        
        # Charger depuis Gmail
        categorized_mails = fetch_all_categorized_emails(since_date_obj, limit_per_category=50)
        return categorized_mails.get(category, [])
        
    except Exception as e:
        st.error(f"Erreur lors du chargement : {str(e)}")
        return []

# Interface principale
if st.session_state.current_view == 'list':
    # Vue liste des emails
    
    # Charger les emails
    with st.spinner("📧 Chargement des emails..."):
        current_emails = load_emails_cached(
            st.session_state.active_category,
            since_date.isoformat(),
            use_cache
        )
    
    # Affichage des statistiques rapides
    total_emails = len(current_emails)
    unread_count = sum(1 for email in current_emails if not email.get('is_processed', False))
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📧 Total", total_emails)
    with col2:
        st.metric("📬 Non lus", unread_count)
    with col3:
        st.metric("📂 Catégorie", st.session_state.active_category)
    with col4:
        st.metric("📅 Depuis", since_date.strftime('%d/%m'))
    
    st.markdown("---")
    
    if not current_emails:
        st.info(f"📭 Aucun email trouvé dans '{st.session_state.active_category}' depuis le {since_date.strftime('%d %b %Y')}")
    else:
        st.markdown(f"### 📨 Emails de '{st.session_state.active_category}' ({len(current_emails)} trouvés)")
        
        # Liste des emails avec design moderne
        for idx, email in enumerate(current_emails):
            is_unread = not email.get('is_processed', False)
            
            # Formater la date
            try:
                email_date = parse_email_date(email.get('date', ''))
                if email_date.date() == date.today():
                    date_str = email_date.strftime('%H:%M')
                else:
                    date_str = email_date.strftime('%d %b')
            except:
                date_str = 'Date inconnue'
            
            # Créer la carte email
            card_class = "unread" if is_unread else "read"
            status_class = "status-unread" if is_unread else "status-read"
            status_text = "🔵 Non lu" if is_unread else "✅ Lu"
            
            # Snippet du contenu
            snippet = email.get('body', '')[:150].replace('\n', ' ').replace('\r', ' ')
            if len(snippet) > 150:
                snippet += "..."
            
            st.markdown(f"""
            <div class="email-card {card_class}">
                <div class="email-header">
                    <div class="email-sender">{email.get('from', 'Expéditeur inconnu')}</div>
                    <div class="email-date">{date_str}</div>
                </div>
                <div class="email-subject">{email.get('subject', 'Pas de sujet')}</div>
                <div class="email-snippet">{snippet}</div>
                <div class="email-status {status_class}">{status_text}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Bouton pour ouvrir l'email
            if st.button(f"📖 Ouvrir cet email", key=f"open_email_{idx}", use_container_width=True):
                st.session_state.selected_email = email
                st.session_state.current_view = 'detail'
                st.rerun()

elif st.session_state.current_view == 'detail':
    # Vue détail d'un email
    
    if st.session_state.selected_email:
        email = st.session_state.selected_email
        
        # Bouton retour
        if st.button("← Retour à la liste", key="back_to_list"):
            st.session_state.current_view = 'list'
            st.session_state.selected_email = None
            st.rerun()
        
        # Affichage de l'email
        st.markdown(f"## 📧 {email.get('subject', 'Pas de sujet')}")
        
        # Métadonnées
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**De:** {email.get('from', 'Expéditeur inconnu')}")
            st.markdown(f"**À:** {email.get('to', 'Destinataire inconnu')}")
            
            try:
                email_date = parse_email_date(email.get('date', ''))
                formatted_date = email_date.strftime('%d %b %Y à %H:%M')
            except:
                formatted_date = 'Date inconnue'
            st.markdown(f"**Date:** {formatted_date}")
        
        with col2:
            status = '✅ Traité' if email.get('is_processed') else '⏳ En attente'
            st.markdown(f"**Statut:** {status}")
        
        # Section résumé IA
        st.markdown("""
        <div class="summary-section">
            <div class="summary-title">🤖 Résumé intelligent</div>
            <div class="summary-content" id="summary-content">
        """, unsafe_allow_html=True)
        
        # Vérifier s'il y a un résumé en cache
        cached_summary = None
        if email.get('db_id'):
            cached_summary = get_email_summary(user_id, email['db_id'])
        
        if cached_summary and cached_summary.get('summary_text'):
            st.markdown(cached_summary['summary_text'])
        else:
            if st.button("🤖 Générer un résumé", key="generate_summary_detail"):
                with st.spinner("Génération du résumé..."):
                    summary = summarize_emails([email])
                    if summary and not summary.startswith('Erreur'):
                        if email.get('db_id'):
                            save_email_summary(user_id, email['db_id'], summary)
                        st.success("✅ Résumé généré!")
                        st.rerun()
        
        st.markdown("</div></div>", unsafe_allow_html=True)
        
        # Contenu de l'email
        with st.expander("📄 Contenu complet de l'email", expanded=False):
            st.text(email.get('body', 'Pas de contenu'))
        
        # Section réponse
        st.markdown("""
        <div class="reply-section">
            <div class="reply-title">✍️ Répondre à cet email</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("reply_form_detail"):
            st.markdown(f"**Répondre à:** {email.get('from', 'Expéditeur inconnu')}")
            st.markdown(f"**Sujet:** Re: {email.get('subject', 'Pas de sujet')}")
            
            user_prompt = st.text_input(
                "💭 Instructions pour l'IA",
                placeholder="Ex: 'Refuser poliment', 'Demander plus d'informations', 'Accepter la proposition'..."
            )
            
            generated_reply = st.text_area(
                "✍️ Réponse (modifiable)",
                value=st.session_state.get('current_reply_detail', ''),
                height=150,
                placeholder="La réponse générée apparaîtra ici..."
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                generate_btn = st.form_submit_button("🤖 Générer", use_container_width=True)
            
            with col2:
                send_btn = st.form_submit_button("📤 Envoyer", use_container_width=True)
            
            with col3:
                save_draft_btn = st.form_submit_button("💾 Brouillon", use_container_width=True)
            
            if generate_btn and user_prompt:
                with st.spinner("🤖 Génération de la réponse..."):
                    reply = generate_reply(
                        email.get('body', ''), 
                        user_prompt, 
                        email.get('db_id')
                    )
                    st.session_state.current_reply_detail = reply
                    st.success("✅ Réponse générée!")
                    st.rerun()
            
            if send_btn and generated_reply:
                with st.spinner("📤 Envoi de la réponse..."):
                    success = send_email(
                        to=email.get('from', ''),
                        subject=f"Re: {email.get('subject', '')}",
                        body=generated_reply
                    )
                    if success:
                        # Sauvegarder dans la base
                        if email.get('db_id'):
                            save_email_reply(
                                user_id, 
                                email['db_id'], 
                                user_prompt, 
                                generated_reply, 
                                generated_reply, 
                                True
                            )
                            mark_email_as_processed(email['db_id'])
                        
                        st.success("✅ Réponse envoyée avec succès!")
                        st.session_state.current_reply_detail = ''
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de l'envoi")
            
            if save_draft_btn and generated_reply:
                st.success("✅ Brouillon sauvegardé!")
    
    else:
        st.error("Aucun email sélectionné")
        if st.button("← Retour à la liste"):
            st.session_state.current_view = 'list'
            st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    📧 Assistant Mail - Développé avec ❤️ et IA
</div>
""", unsafe_allow_html=True)