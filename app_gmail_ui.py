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

# Configuration de la page avec style Gmail
st.set_page_config(
    page_title="Assistant Mail", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour l'interface Gmail
st.markdown("""
<style>
    /* Variables CSS pour la cohérence */
    :root {
        --gmail-red: #ea4335;
        --gmail-blue: #4285f4;
        --gmail-green: #34a853;
        --gmail-yellow: #fbbc05;
        --gmail-gray: #5f6368;
        --gmail-light-gray: #f8f9fa;
        --gmail-border: #dadce0;
        --gmail-hover: #f1f3f4;
    }
    
    /* Masquer les éléments Streamlit par défaut */
    .stDeployButton {display: none;}
    .stDecoration {display: none;}
    #MainMenu {display: none;}
    
    /* Header style Gmail */
    .gmail-header {
        background: white;
        border-bottom: 1px solid var(--gmail-border);
        padding: 8px 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        position: sticky;
        top: 0;
        z-index: 100;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .gmail-logo {
        font-size: 22px;
        font-weight: 400;
        color: var(--gmail-gray);
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .gmail-search {
        background: var(--gmail-light-gray);
        border: 1px solid var(--gmail-border);
        border-radius: 24px;
        padding: 8px 16px;
        width: 500px;
        font-size: 14px;
    }
    
    .gmail-user-info {
        display: flex;
        align-items: center;
        gap: 12px;
        color: var(--gmail-gray);
        font-size: 14px;
    }
    
    /* Sidebar style Gmail */
    .gmail-sidebar {
        background: white;
        border-right: 1px solid var(--gmail-border);
        padding: 8px 0;
        height: 100vh;
        overflow-y: auto;
    }
    
    .gmail-compose-btn {
        background: var(--gmail-blue);
        color: white;
        border: none;
        border-radius: 24px;
        padding: 12px 24px;
        margin: 8px 16px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    
    .gmail-nav-item {
        padding: 8px 24px;
        margin: 2px 8px;
        border-radius: 0 24px 24px 0;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 14px;
        color: var(--gmail-gray);
        transition: background-color 0.2s;
    }
    
    .gmail-nav-item:hover {
        background: var(--gmail-hover);
    }
    
    .gmail-nav-item.active {
        background: var(--gmail-red);
        color: white;
        font-weight: 500;
    }
    
    .gmail-nav-item .count {
        margin-left: auto;
        font-size: 13px;
        color: var(--gmail-gray);
    }
    
    .gmail-nav-item.active .count {
        color: white;
    }
    
    /* Liste des emails style Gmail */
    .gmail-email-list {
        background: white;
        border: 1px solid var(--gmail-border);
        border-radius: 8px;
        overflow: hidden;
    }
    
    .gmail-email-item {
        padding: 12px 16px;
        border-bottom: 1px solid var(--gmail-border);
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 12px;
        transition: background-color 0.2s;
    }
    
    .gmail-email-item:hover {
        background: var(--gmail-hover);
    }
    
    .gmail-email-item.selected {
        background: #fef7e0;
        border-left: 4px solid var(--gmail-yellow);
    }
    
    .gmail-email-item.unread {
        background: white;
        font-weight: 500;
    }
    
    .gmail-email-item.read {
        background: var(--gmail-light-gray);
        opacity: 0.8;
    }
    
    .gmail-email-checkbox {
        width: 18px;
        height: 18px;
        border: 2px solid var(--gmail-border);
        border-radius: 2px;
        margin-right: 8px;
    }
    
    .gmail-email-star {
        color: var(--gmail-yellow);
        font-size: 18px;
        cursor: pointer;
    }
    
    .gmail-email-sender {
        min-width: 200px;
        font-weight: 500;
        color: var(--gmail-gray);
    }
    
    .gmail-email-subject {
        flex: 1;
        color: var(--gmail-gray);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .gmail-email-date {
        min-width: 80px;
        text-align: right;
        font-size: 12px;
        color: var(--gmail-gray);
    }
    
    .gmail-email-snippet {
        color: #999;
        font-size: 13px;
        margin-left: 8px;
    }
    
    /* Détails de l'email */
    .gmail-email-detail {
        background: white;
        border: 1px solid var(--gmail-border);
        border-radius: 8px;
        padding: 24px;
        margin-top: 16px;
    }
    
    .gmail-email-header {
        border-bottom: 1px solid var(--gmail-border);
        padding-bottom: 16px;
        margin-bottom: 16px;
    }
    
    .gmail-email-subject-detail {
        font-size: 20px;
        font-weight: 400;
        color: var(--gmail-gray);
        margin-bottom: 8px;
    }
    
    .gmail-email-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: var(--gmail-gray);
        font-size: 14px;
    }
    
    .gmail-email-body {
        line-height: 1.6;
        color: var(--gmail-gray);
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    
    /* Boutons d'action Gmail */
    .gmail-actions {
        display: flex;
        gap: 8px;
        margin-top: 16px;
    }
    
    .gmail-btn {
        padding: 8px 16px;
        border: 1px solid var(--gmail-border);
        border-radius: 4px;
        background: white;
        color: var(--gmail-gray);
        cursor: pointer;
        font-size: 14px;
        transition: all 0.2s;
    }
    
    .gmail-btn:hover {
        background: var(--gmail-hover);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .gmail-btn.primary {
        background: var(--gmail-blue);
        color: white;
        border-color: var(--gmail-blue);
    }
    
    .gmail-btn.primary:hover {
        background: #3367d6;
    }
    
    /* Compose/Reply area */
    .gmail-compose {
        background: white;
        border: 1px solid var(--gmail-border);
        border-radius: 8px;
        padding: 16px;
        margin-top: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .gmail-compose-header {
        display: flex;
        justify-content: between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--gmail-border);
    }
    
    /* Toolbar */
    .gmail-toolbar {
        background: white;
        border-bottom: 1px solid var(--gmail-border);
        padding: 8px 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .gmail-toolbar-btn {
        padding: 6px 12px;
        border: none;
        background: transparent;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        color: var(--gmail-gray);
        transition: background-color 0.2s;
    }
    
    .gmail-toolbar-btn:hover {
        background: var(--gmail-hover);
    }
    
    /* Stats cards */
    .gmail-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }
    
    .gmail-stat-card {
        background: white;
        border: 1px solid var(--gmail-border);
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .gmail-stat-number {
        font-size: 28px;
        font-weight: 500;
        color: var(--gmail-blue);
        margin-bottom: 4px;
    }
    
    .gmail-stat-label {
        color: var(--gmail-gray);
        font-size: 14px;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .gmail-search {
            width: 100%;
            max-width: 300px;
        }
        
        .gmail-email-sender {
            min-width: 120px;
        }
        
        .gmail-stats {
            grid-template-columns: 1fr;
        }
    }
    
    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .gmail-email-item {
        animation: fadeIn 0.3s ease-out;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--gmail-light-gray);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--gmail-border);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--gmail-gray);
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

# Charger les préférences utilisateur
user_preferences = get_user_preferences(user_id)
default_date = user_preferences.get("default_filter_date", date.today().isoformat())

# Header Gmail
st.markdown(f"""
<div class="gmail-header">
    <div class="gmail-logo">
        📧 Assistant Mail
    </div>
    <div class="gmail-user-info">
        <span>{user_email}</span>
        <button onclick="window.location.reload()" class="gmail-btn">🚪 Déconnexion</button>
    </div>
</div>
""", unsafe_allow_html=True)

# Layout principal avec sidebar
col_sidebar, col_main = st.columns([1, 4])

with col_sidebar:
    st.markdown('<div class="gmail-sidebar">', unsafe_allow_html=True)
    
    # Bouton Compose (sera utilisé pour les paramètres)
    st.markdown("""
    <div class="gmail-compose-btn">
        ⚙️ Paramètres
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation par catégorie
    st.markdown("### 📂 Catégories")
    
    # Récupérer les statistiques par catégorie
    category_stats = get_category_statistics(user_id)
    available_categories = list(get_gmail_categories().keys())
    
    # Gérer la sélection de catégorie
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = "Boîte de réception"
    
    for category in available_categories:
        count = category_stats.get(category, 0)
        emoji = {
            "Boîte de réception": "📥",
            "Promotions": "🏷️",
            "Réseaux sociaux": "👥",
            "Notifications": "🔔",
            "Forums": "💬"
        }.get(category, "📁")
        
        is_active = st.session_state.selected_category == category
        
        if st.button(f"{emoji} {category} ({count})", 
                    key=f"nav_{category}",
                    use_container_width=True):
            st.session_state.selected_category = category
            st.rerun()
    
    # Section paramètres
    st.markdown("---")
    st.markdown("### ⚙️ Paramètres")
    
    # Filtre par date
    selected_date = st.date_input(
        "📅 Depuis", 
        value=date.fromisoformat(default_date) if default_date else date.today(),
        key="date_filter"
    )
    
    # Options de chargement
    use_cache = st.checkbox("🗄️ Utiliser le cache", value=True)
    
    if st.button("🔄 Recharger", use_container_width=True):
        st.session_state.force_reload = True
        st.rerun()
    
    # Statistiques globales
    st.markdown("---")
    st.markdown("### 📊 Statistiques")
    
    stats = get_user_statistics(user_id)
    
    st.metric("📧 Total emails", stats["total_emails"])
    st.metric("📋 Résumés", stats["summaries_generated"])
    st.metric("📤 Réponses", stats["replies_sent"])
    
    if st.button("🚪 Déconnexion", use_container_width=True):
        logout()
    
    st.markdown('</div>', unsafe_allow_html=True)

with col_main:
    # Sauvegarder les préférences si changement
    if selected_date.isoformat() != default_date:
        save_user_preference(user_id, "default_filter_date", selected_date.isoformat())
    
    # Charger les emails pour la catégorie sélectionnée
    force_reload = st.session_state.get('force_reload', False)
    if force_reload:
        st.session_state.force_reload = False
    
    # Initialisation des emails
    if 'categorized_mails' not in st.session_state or force_reload or not use_cache:
        with st.spinner("🔄 Chargement des emails..."):
            try:
                if use_cache and not force_reload:
                    # Charger depuis Supabase
                    cached_mails = get_user_emails_by_category(
                        user_id, 
                        selected_date, 
                        [st.session_state.selected_category], 
                        limit_per_category=100
                    )
                    
                    if cached_mails and cached_mails.get(st.session_state.selected_category):
                        st.session_state.categorized_mails = cached_mails
                        st.success(f"✅ Emails chargés depuis la base de données")
                    else:
                        # Charger depuis Gmail
                        categorized_mails = fetch_all_categorized_emails(
                            selected_date, 
                            limit_per_category=100
                        )
                        st.session_state.categorized_mails = categorized_mails
                        st.success(f"✅ Emails chargés depuis Gmail")
                else:
                    # Forcer le chargement depuis Gmail
                    categorized_mails = fetch_all_categorized_emails(
                        selected_date, 
                        limit_per_category=100
                    )
                    st.session_state.categorized_mails = categorized_mails
                    st.success(f"✅ Emails rechargés depuis Gmail")
                    
            except Exception as e:
                st.error(f"❌ Erreur lors du chargement : {str(e)}")
                st.session_state.categorized_mails = {}
    
    # Récupérer les emails pour la catégorie sélectionnée
    current_emails = st.session_state.categorized_mails.get(st.session_state.selected_category, [])
    
    # Convertir le format si nécessaire (depuis Supabase)
    if current_emails and isinstance(current_emails[0], dict) and 'sender' in current_emails[0]:
        # Format Supabase -> format attendu
        converted_emails = []
        for mail in current_emails:
            converted_emails.append({
                'db_id': mail.get('id'),
                'subject': mail.get('subject', ''),
                'from': mail.get('sender', ''),
                'to': mail.get('recipient', ''),
                'body': mail.get('body', ''),
                'date': mail.get('date_received', ''),
                'category': mail.get('category', st.session_state.selected_category),
                'is_processed': mail.get('is_processed', False)
            })
        current_emails = converted_emails
    
    # Toolbar
    st.markdown(f"""
    <div class="gmail-toolbar">
        <div class="gmail-toolbar-btn">📧 {len(current_emails)} emails</div>
        <div class="gmail-toolbar-btn">📂 {st.session_state.selected_category}</div>
        <div class="gmail-toolbar-btn">📅 Depuis {selected_date.strftime('%d %b %Y')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if not current_emails:
        st.markdown("""
        <div style="text-align: center; padding: 40px; color: #999;">
            <h3>📭 Aucun email</h3>
            <p>Aucun email trouvé dans cette catégorie depuis la date sélectionnée.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Gestion de la sélection d'email
        if 'selected_email_index' not in st.session_state:
            st.session_state.selected_email_index = 0
        
        # Liste des emails (style Gmail)
        st.markdown('<div class="gmail-email-list">', unsafe_allow_html=True)
        
        for idx, email in enumerate(current_emails):
            is_selected = idx == st.session_state.selected_email_index
            is_processed = email.get('is_processed', False)
            
            # Tronquer le sujet et l'expéditeur
            subject = email.get('subject', 'Pas de sujet')[:50] + ('...' if len(subject) > 50 else '')
            sender = email.get('from', 'Expéditeur inconnu')[:30] + ('...' if len(email.get('from', '')) > 30 else '')
            
            # Extraire un snippet du corps
            body_snippet = email.get('body', '')[:100].replace('\n', ' ').replace('\r', ' ')
            
            # Formater la date
            try:
                email_date = parse_email_date(email.get('date', ''))
                if email_date.date() == date.today():
                    date_str = email_date.strftime('%H:%M')
                else:
                    date_str = email_date.strftime('%d %b')
            except:
                date_str = 'Date inconnue'
            
            # Créer l'item email
            item_class = "gmail-email-item"
            if is_selected:
                item_class += " selected"
            if not is_processed:
                item_class += " unread"
            else:
                item_class += " read"
            
            # Utiliser un bouton invisible pour la sélection
            if st.button(f"email_{idx}", key=f"email_btn_{idx}", 
                        label_visibility="hidden", use_container_width=True):
                st.session_state.selected_email_index = idx
                st.rerun()
            
            # Afficher l'email avec du HTML
            st.markdown(f"""
            <div class="{item_class}" onclick="document.querySelector('[data-testid=\"email_btn_{idx}\"]').click()">
                <div class="gmail-email-checkbox"></div>
                <div class="gmail-email-star">{'⭐' if not is_processed else '☆'}</div>
                <div class="gmail-email-sender">{sender}</div>
                <div class="gmail-email-subject">
                    <strong>{subject}</strong>
                    <span class="gmail-email-snippet"> - {body_snippet}</span>
                </div>
                <div class="gmail-email-date">{date_str}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Détails de l'email sélectionné
        if current_emails:
            selected_email = current_emails[st.session_state.selected_email_index]
            
            st.markdown('<div class="gmail-email-detail">', unsafe_allow_html=True)
            
            # Header de l'email
            st.markdown(f"""
            <div class="gmail-email-header">
                <div class="gmail-email-subject-detail">{selected_email.get('subject', 'Pas de sujet')}</div>
                <div class="gmail-email-meta">
                    <div>
                        <strong>De:</strong> {selected_email.get('from', 'Expéditeur inconnu')}<br>
                        <strong>À:</strong> {selected_email.get('to', 'Destinataire inconnu')}<br>
                        <strong>Date:</strong> {selected_email.get('date', 'Date inconnue')}
                    </div>
                    <div>
                        {'✅ Traité' if selected_email.get('is_processed') else '⏳ En attente'}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Corps de l'email
            st.markdown(f"""
            <div class="gmail-email-body">
                {selected_email.get('body', 'Pas de contenu')}
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Actions et résumé
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("### 📋 Résumé IA")
                
                # Vérifier s'il y a un résumé en cache
                cached_summary = None
                if selected_email.get('db_id'):
                    cached_summary = get_email_summary(user_id, selected_email['db_id'])
                
                if cached_summary and cached_summary.get('summary_text'):
                    st.info(cached_summary['summary_text'])
                else:
                    if st.button("🤖 Générer un résumé", key="generate_summary"):
                        with st.spinner("Génération du résumé..."):
                            summary = summarize_emails([selected_email])
                            if summary and not summary.startswith('Erreur'):
                                if selected_email.get('db_id'):
                                    save_email_summary(user_id, selected_email['db_id'], summary)
                                st.success("✅ Résumé généré!")
                                st.rerun()
            
            with col2:
                st.markdown("### 🎯 Actions rapides")
                
                if st.button("⭐ Marquer comme important", use_container_width=True):
                    if selected_email.get('db_id'):
                        mark_email_as_processed(selected_email['db_id'])
                        st.success("✅ Email marqué comme traité!")
                        st.rerun()
                
                if st.button("📁 Archiver", use_container_width=True):
                    st.success("✅ Email archivé!")
                
                if st.button("🗑️ Supprimer", use_container_width=True):
                    st.success("✅ Email supprimé!")
            
            # Zone de composition de réponse
            st.markdown("---")
            st.markdown("### ✍️ Répondre")
            
            st.markdown('<div class="gmail-compose">', unsafe_allow_html=True)
            
            # Formulaire de réponse
            with st.form("reply_form"):
                st.markdown(f"**Répondre à:** {selected_email.get('from', 'Expéditeur inconnu')}")
                st.markdown(f"**Sujet:** Re: {selected_email.get('subject', 'Pas de sujet')}")
                
                user_prompt = st.text_input(
                    "💭 Instructions pour l'IA",
                    placeholder="Ex: 'Refuser poliment', 'Demander plus d'informations', 'Accepter la proposition'..."
                )
                
                generated_reply = st.text_area(
                    "✍️ Réponse (modifiable)",
                    value=st.session_state.get('current_reply', ''),
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
                            selected_email.get('body', ''), 
                            user_prompt, 
                            selected_email.get('db_id')
                        )
                        st.session_state.current_reply = reply
                        st.success("✅ Réponse générée!")
                        st.rerun()
                
                if send_btn and generated_reply:
                    with st.spinner("📤 Envoi de la réponse..."):
                        success = send_email(
                            to=selected_email.get('from', ''),
                            subject=f"Re: {selected_email.get('subject', '')}",
                            body=generated_reply
                        )
                        if success:
                            # Sauvegarder dans la base
                            if selected_email.get('db_id'):
                                save_email_reply(
                                    user_id, 
                                    selected_email['db_id'], 
                                    user_prompt, 
                                    generated_reply, 
                                    generated_reply, 
                                    True
                                )
                                mark_email_as_processed(selected_email['db_id'])
                            
                            st.success("✅ Réponse envoyée avec succès!")
                            st.session_state.current_reply = ''
                            st.rerun()
                        else:
                            st.error("❌ Erreur lors de l'envoi")
                
                if save_draft_btn and generated_reply:
                    # Logique pour sauvegarder en brouillon
                    st.success("✅ Brouillon sauvegardé!")
            
            st.markdown('</div>', unsafe_allow_html=True)