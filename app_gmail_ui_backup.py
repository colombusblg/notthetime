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
    page_title="Gmail - Assistant Mail", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Gmail authentique basé sur votre capture d'écran
st.markdown("""
<style>
    /* Reset et variables */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    :root {
        --gmail-primary: #1a73e8;
        --gmail-red: #d93025;
        --gmail-yellow: #f9ab00;
        --gmail-green: #137333;
        --gmail-gray-50: #f8f9fa;
        --gmail-gray-100: #f1f3f4;
        --gmail-gray-200: #e8eaed;
        --gmail-gray-300: #dadce0;
        --gmail-gray-400: #bdc1c6;
        --gmail-gray-500: #9aa0a6;
        --gmail-gray-600: #80868b;
        --gmail-gray-700: #5f6368;
        --gmail-gray-800: #3c4043;
        --gmail-gray-900: #202124;
        --gmail-white: #ffffff;
    }
    
    /* Masquer les éléments Streamlit */
    .stApp > header {display: none;}
    .stDeployButton {display: none;}
    .stDecoration {display: none;}
    #MainMenu {display: none;}
    footer {display: none;}
    .stAppViewContainer > .main > div {padding: 0;}
    .stMarkdown {margin: 0;}
    
    /* Container principal */
    .gmail-container {
        display: flex;
        height: 100vh;
        font-family: 'Google Sans', Roboto, Arial, sans-serif;
        background: var(--gmail-white);
    }
    
    /* Sidebar gauche */
    .gmail-sidebar {
        width: 256px;
        background: var(--gmail-white);
        border-right: 1px solid var(--gmail-gray-200);
        display: flex;
        flex-direction: column;
        padding: 8px 0;
    }
    
    .gmail-logo {
        padding: 16px 24px;
        font-size: 22px;
        font-weight: 400;
        color: var(--gmail-gray-700);
        border-bottom: 1px solid var(--gmail-gray-200);
        margin-bottom: 8px;
    }
    
    .gmail-compose-btn {
        margin: 8px 16px 24px 16px;
        background: var(--gmail-primary);
        color: white;
        border: none;
        border-radius: 24px;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        box-shadow: 0 1px 3px rgba(60,64,67,0.3);
        transition: all 0.2s;
    }
    
    .gmail-compose-btn:hover {
        box-shadow: 0 2px 8px rgba(60,64,67,0.4);
    }
    
    .gmail-nav-item {
        padding: 8px 12px 8px 24px;
        margin: 1px 8px;
        border-radius: 0 16px 16px 0;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 16px;
        font-size: 14px;
        color: var(--gmail-gray-700);
        transition: background-color 0.2s;
        height: 32px;
    }
    
    .gmail-nav-item:hover {
        background: var(--gmail-gray-100);
    }
    
    .gmail-nav-item.active {
        background: #fce8e6;
        color: var(--gmail-red);
        font-weight: 500;
    }
    
    .gmail-nav-item .icon {
        width: 20px;
        display: flex;
        justify-content: center;
    }
    
    .gmail-nav-item .count {
        margin-left: auto;
        font-size: 13px;
        color: var(--gmail-gray-600);
    }
    
    .gmail-nav-item.active .count {
        color: var(--gmail-red);
        font-weight: 500;
    }
    
    /* Zone principale */
    .gmail-main {
        flex: 1;
        display: flex;
        flex-direction: column;
        background: var(--gmail-white);
    }
    
    /* Header avec recherche */
    .gmail-header {
        height: 64px;
        border-bottom: 1px solid var(--gmail-gray-200);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 24px;
        background: var(--gmail-white);
    }
    
    .gmail-search-container {
        flex: 1;
        max-width: 720px;
        margin: 0 48px;
    }
    
    .gmail-search {
        width: 100%;
        background: var(--gmail-gray-100);
        border: 1px solid var(--gmail-gray-300);
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 16px;
        color: var(--gmail-gray-800);
        outline: none;
        transition: all 0.2s;
    }
    
    .gmail-search:focus {
        background: var(--gmail-white);
        box-shadow: 0 2px 8px rgba(60,64,67,0.15);
    }
    
    .gmail-user-info {
        display: flex;
        align-items: center;
        gap: 16px;
        color: var(--gmail-gray-700);
        font-size: 14px;
    }
    
    /* Onglets */
    .gmail-tabs {
        display: flex;
        border-bottom: 1px solid var(--gmail-gray-200);
        background: var(--gmail-white);
        padding: 0 16px;
    }
    
    .gmail-tab {
        padding: 16px 24px;
        border-bottom: 3px solid transparent;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        color: var(--gmail-gray-600);
        transition: all 0.2s;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .gmail-tab:hover {
        background: var(--gmail-gray-50);
    }
    
    .gmail-tab.active {
        color: var(--gmail-primary);
        border-bottom-color: var(--gmail-primary);
    }
    
    /* Toolbar */
    .gmail-toolbar {
        height: 48px;
        background: var(--gmail-white);
        border-bottom: 1px solid var(--gmail-gray-200);
        display: flex;
        align-items: center;
        padding: 0 16px;
        gap: 8px;
    }
    
    .gmail-toolbar-btn {
        padding: 8px;
        border: none;
        background: transparent;
        border-radius: 4px;
        cursor: pointer;
        color: var(--gmail-gray-600);
        transition: background-color 0.2s;
        font-size: 18px;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .gmail-toolbar-btn:hover {
        background: var(--gmail-gray-100);
    }
    
    .gmail-toolbar-separator {
        width: 1px;
        height: 24px;
        background: var(--gmail-gray-200);
        margin: 0 8px;
    }
    
    /* Liste des emails */
    .gmail-email-list {
        flex: 1;
        overflow-y: auto;
        background: var(--gmail-white);
    }
    
    .gmail-email-item {
        border-bottom: 1px solid var(--gmail-gray-200);
        padding: 0 16px;
        height: 54px;
        display: flex;
        align-items: center;
        cursor: pointer;
        transition: background-color 0.1s;
        position: relative;
    }
    
    .gmail-email-item:hover {
        box-shadow: inset 1px 0 0 var(--gmail-gray-300), inset -1px 0 0 var(--gmail-gray-300), 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
        z-index: 1;
    }
    
    .gmail-email-item.unread {
        background: var(--gmail-white);
        font-weight: 700;
    }
    
    .gmail-email-item.read {
        background: var(--gmail-white);
        font-weight: 400;
    }
    
    .gmail-email-checkbox {
        width: 20px;
        height: 20px;
        margin-right: 12px;
        cursor: pointer;
    }
    
    .gmail-email-star {
        width: 24px;
        height: 24px;
        margin-right: 12px;
        cursor: pointer;
        color: var(--gmail-gray-400);
        font-size: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .gmail-email-star.starred {
        color: var(--gmail-yellow);
    }
    
    .gmail-email-sender {
        width: 200px;
        font-size: 14px;
        color: var(--gmail-gray-900);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-right: 16px;
    }
    
    .gmail-email-content {
        flex: 1;
        font-size: 14px;
        color: var(--gmail-gray-900);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-right: 16px;
    }
    
    .gmail-email-subject {
        font-weight: inherit;
    }
    
    .gmail-email-snippet {
        color: var(--gmail-gray-600);
        margin-left: 4px;
    }
    
    .gmail-email-date {
        width: 80px;
        text-align: right;
        font-size: 12px;
        color: var(--gmail-gray-600);
        white-space: nowrap;
    }
    
    /* Page de détail email */
    .gmail-detail-page {
        display: flex;
        flex-direction: column;
        height: 100%;
        background: var(--gmail-white);
    }
    
    .gmail-detail-header {
        height: 64px;
        border-bottom: 1px solid var(--gmail-gray-200);
        display: flex;
        align-items: center;
        padding: 0 24px;
        gap: 16px;
    }
    
    .gmail-back-btn {
        padding: 8px;
        border: none;
        background: transparent;
        border-radius: 20px;
        cursor: pointer;
        color: var(--gmail-gray-600);
        font-size: 18px;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background-color 0.2s;
    }
    
    .gmail-back-btn:hover {
        background: var(--gmail-gray-100);
    }
    
    .gmail-detail-title {
        font-size: 20px;
        font-weight: 400;
        color: var(--gmail-gray-800);
        flex: 1;
    }
    
    .gmail-detail-content {
        flex: 1;
        overflow-y: auto;
        padding: 24px;
    }
    
    /* Carte email */
    .gmail-email-card {
        background: var(--gmail-white);
        border: 1px solid var(--gmail-gray-200);
        border-radius: 8px;
        margin-bottom: 24px;
        overflow: hidden;
    }
    
    .gmail-email-card-header {
        padding: 20px 24px;
        border-bottom: 1px solid var(--gmail-gray-200);
    }
    
    .gmail-email-card-subject {
        font-size: 20px;
        font-weight: 400;
        color: var(--gmail-gray-800);
        margin-bottom: 12px;
    }
    
    .gmail-email-card-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: var(--gmail-gray-600);
        font-size: 14px;
    }
    
    .gmail-email-card-body {
        padding: 24px;
        color: var(--gmail-gray-800);
        line-height: 1.6;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    
    /* Section résumé */
    .gmail-summary-section {
        background: #e8f0fe;
        border: 1px solid #d2e3fc;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 24px;
    }
    
    .gmail-summary-title {
        font-size: 16px;
        font-weight: 500;
        color: var(--gmail-primary);
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .gmail-summary-content {
        color: var(--gmail-gray-800);
        line-height: 1.5;
    }
    
    /* Section réponse */
    .gmail-reply-section {
        background: var(--gmail-white);
        border: 1px solid var(--gmail-gray-200);
        border-radius: 8px;
        padding: 20px;
        margin-top: 24px;
    }
    
    .gmail-reply-title {
        font-size: 16px;
        font-weight: 500;
        color: var(--gmail-gray-800);
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .gmail-form-group {
        margin-bottom: 16px;
    }
    
    .gmail-form-label {
        display: block;
        font-size: 14px;
        font-weight: 500;
        color: var(--gmail-gray-700);
        margin-bottom: 8px;
    }
    
    .gmail-form-input, .gmail-form-textarea {
        width: 100%;
        border: 1px solid var(--gmail-gray-300);
        border-radius: 4px;
        padding: 12px 16px;
        font-size: 14px;
        color: var(--gmail-gray-800);
        outline: none;
        transition: border-color 0.2s;
        font-family: inherit;
    }
    
    .gmail-form-input:focus, .gmail-form-textarea:focus {
        border-color: var(--gmail-primary);
    }
    
    .gmail-form-textarea {
        resize: vertical;
        min-height: 120px;
    }
    
    .gmail-form-actions {
        display: flex;
        gap: 12px;
    }
    
    .gmail-btn {
        padding: 8px 24px;
        border: 1px solid var(--gmail-gray-300);
        border-radius: 4px;
        background: var(--gmail-white);
        color: var(--gmail-gray-700);
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.2s;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .gmail-btn:hover {
        background: var(--gmail-gray-50);
        box-shadow: 0 1px 3px rgba(60,64,67,0.3);
    }
    
    .gmail-btn.primary {
        background: var(--gmail-primary);
        color: white;
        border-color: var(--gmail-primary);
    }
    
    .gmail-btn.primary:hover {
        background: #1557b0;
        border-color: #1557b0;
    }
    
    /* États et animations */
    .loading {
        opacity: 0.6;
        pointer-events: none;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(4px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .gmail-email-item {
        animation: fadeIn 0.2s ease-out;
    }
    
    /* Scrollbar personnalisée */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--gmail-gray-50);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--gmail-gray-300);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--gmail-gray-400);
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .gmail-sidebar {
            width: 200px;
        }
        
        .gmail-email-sender {
            width: 120px;
        }
        
        .gmail-search-container {
            margin: 0 16px;
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
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'inbox'
if 'selected_email' not in st.session_state:
    st.session_state.selected_email = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 'Principale'
if 'active_nav' not in st.session_state:
    st.session_state.active_nav = 'Boîte de réception'

# Charger les préférences utilisateur
user_preferences = get_user_preferences(user_id)
default_date = user_preferences.get("default_filter_date", date.today().isoformat())

def render_sidebar():
    """Rendu de la sidebar"""
    # Statistiques pour les compteurs
    stats = get_user_statistics(user_id)
    category_stats = get_category_statistics(user_id)
    
    nav_items = [
        ("📥", "Boîte de réception", category_stats.get("Boîte de réception", 0)),
        ("⭐", "Messages suivis", 0),
        ("🕐", "En attente", 0),
        ("📤", "Messages envoyés", 0),
        ("➕", "Plus", 0)
    ]
    
    sidebar_html = """
    <div class="gmail-sidebar">
        <div class="gmail-logo">📧 Assistant Mail</div>
        <div class="gmail-compose-btn">✏️ Nouveau message</div>
    """
    
    for icon, label, count in nav_items:
        active_class = "active" if st.session_state.active_nav == label else ""
        count_display = f'<span class="count">{count}</span>' if count > 0 else ""
        sidebar_html += f"""
        <div class="gmail-nav-item {active_class}" onclick="selectNav('{label}')">
            <span class="icon">{icon}</span>
            <span>{label}</span>
            {count_display}
        </div>
        """
    
    sidebar_html += "</div>"
    return sidebar_html

def render_header():
    """Rendu du header"""
    return f"""
    <div class="gmail-header">
        <div class="gmail-search-container">
            <input type="text" class="gmail-search" placeholder="Rechercher dans la messagerie">
        </div>
        <div class="gmail-user-info">
            <span>{user_email}</span>
            <button class="gmail-btn" onclick="logout()">🚪 Déconnexion</button>
        </div>
    </div>
    """

def render_tabs():
    """Rendu des onglets"""
    tabs = [
        ("📧", "Principale"),
        ("🏷️", "Promotions"),
        ("👥", "Réseaux sociaux"),
        ("🔔", "Notifications")
    ]
    
    tabs_html = '<div class="gmail-tabs">'
    
    for icon, label in tabs:
        active_class = "active" if st.session_state.active_tab == label else ""
        tabs_html += f"""
        <div class="gmail-tab {active_class}" onclick="selectTab('{label}')">
            <span>{icon}</span>
            <span>{label}</span>
        </div>
        """
    
    tabs_html += "</div>"
    return tabs_html

def render_toolbar():
    """Rendu de la toolbar"""
    return """
    <div class="gmail-toolbar">
        <div class="gmail-toolbar-btn">☑️</div>
        <div class="gmail-toolbar-btn">🗃️</div>
        <div class="gmail-toolbar-btn">🗑️</div>
        <div class="gmail-toolbar-separator"></div>
        <div class="gmail-toolbar-btn">📧</div>
        <div class="gmail-toolbar-btn">⏰</div>
        <div class="gmail-toolbar-btn">➕</div>
        <div class="gmail-toolbar-separator"></div>
        <div class="gmail-toolbar-btn">🔄</div>
        <div class="gmail-toolbar-btn">⋮</div>
    </div>
    """

def render_email_list(emails):
    """Rendu de la liste des emails"""
    if not emails:
        return """
        <div class="gmail-email-list">
            <div style="text-align: center; padding: 40px; color: #5f6368;">
                <h3>📭 Aucun email</h3>
                <p>Aucun email trouvé dans cette catégorie.</p>
            </div>
        </div>
        """
    
    list_html = '<div class="gmail-email-list">'
    
    for idx, email in enumerate(emails):
        is_unread = not email.get('is_processed', False)
        unread_class = "unread" if is_unread else "read"
        
        # Tronquer le contenu
        sender = email.get('from', 'Expéditeur inconnu')[:25] + ('...' if len(email.get('from', '')) > 25 else '')
        subject = email.get('subject', 'Pas de sujet')
        body_snippet = email.get('body', '')[:50].replace('\n', ' ').replace('\r', ' ')
        
        # Formater la date
        try:
            email_date = parse_email_date(email.get('date', ''))
            if email_date.date() == date.today():
                date_str = email_date.strftime('%H:%M')
            else:
                date_str = email_date.strftime('%d %b')
        except:
            date_str = 'Date inconnue'
        
        star_class = "starred" if is_unread else ""
        
        list_html += f"""
        <div class="gmail-email-item {unread_class}" onclick="selectEmail({idx})">
            <input type="checkbox" class="gmail-email-checkbox">
            <div class="gmail-email-star {star_class}">☆</div>
            <div class="gmail-email-sender">{sender}</div>
            <div class="gmail-email-content">
                <span class="gmail-email-subject">{subject}</span>
                <span class="gmail-email-snippet"> - {body_snippet}</span>
            </div>
            <div class="gmail-email-date">{date_str}</div>
        </div>
        """
    
    list_html += '</div>'
    return list_html

def render_email_detail(email):
    """Rendu de la page de détail d'un email"""
    # Vérifier s'il y a un résumé en cache
    cached_summary = None
    if email.get('db_id'):
        cached_summary = get_email_summary(user_id, email['db_id'])
    
    # Formater la date
    try:
        email_date = parse_email_date(email.get('date', ''))
        formatted_date = email_date.strftime('%d %b %Y à %H:%M')
    except:
        formatted_date = 'Date inconnue'
    
    detail_html = f"""
    <div class="gmail-detail-page">
        <div class="gmail-detail-header">
            <button class="gmail-back-btn" onclick="goBack()">←</button>
            <div class="gmail-detail-title">{email.get('subject', 'Pas de sujet')}</div>
        </div>
        
        <div class="gmail-detail-content">
            <!-- Section résumé IA -->
            <div class="gmail-summary-section">
                <div class="gmail-summary-title">
                    🤖 Résumé intelligent
                </div>
                <div class="gmail-summary-content" id="summary-content">
    """
    
    if cached_summary and cached_summary.get('summary_text'):
        detail_html += f"{cached_summary['summary_text']}"
    else:
        detail_html += """
                    <button class="gmail-btn primary" onclick="generateSummary()">Générer un résumé</button>
        """
    
    detail_html += """
                </div>
            </div>
            
            <!-- Email principal -->
            <div class="gmail-email-card">
                <div class="gmail-email-card-header">
                    <div class="gmail-email-card-subject">{subject}</div>
                    <div class="gmail-email-card-meta">
                        <div>
                            <strong>De:</strong> {sender}<br>
                            <strong>À:</strong> {recipient}<br>
                            <strong>Date:</strong> {date}
                        </div>
                        <div>
                            {status}
                        </div>
                    </div>
                </div>
                
                <div class="gmail-email-card-body" id="email-body">
                    {body_preview}
                    <br><br>
                    <button class="gmail-btn" onclick="toggleFullContent()">Afficher le contenu complet</button>
                </div>
                
                <div class="gmail-email-card-body" id="full-email-body" style="display: none;">
                    {full_body}
                    <br><br>
                    <button class="gmail-btn" onclick="toggleFullContent()">Masquer le contenu complet</button>
                </div>
            </div>
            
            <!-- Section réponse -->
            <div class="gmail-reply-section">
                <div class="gmail-reply-title">
                    ✍️ Répondre
                </div>
                
                <div class="gmail-form-group">
                    <label class="gmail-form-label">Instructions pour l'IA</label>
                    <input type="text" class="gmail-form-input" id="user-prompt" 
                           placeholder="Ex: 'Refuser poliment', 'Demander plus d'informations', 'Accepter la proposition'...">
                </div>
                
                <div class="gmail-form-group">
                    <label class="gmail-form-label">Réponse générée (modifiable)</label>
                    <textarea class="gmail-form-textarea" id="generated-reply" 
                              placeholder="La réponse générée apparaîtra ici..."></textarea>
                </div>
                
                <div class="gmail-form-actions">
                    <button class="gmail-btn" onclick="generateReply()">🤖 Générer</button>
                    <button class="gmail-btn primary" onclick="sendReply()">📤 Envoyer</button>
                    <button class="gmail-btn" onclick="saveDraft()">💾 Brouillon</button>
                </div>
            </div>
        </div>
    </div>
    """.format(
        subject=email.get('subject', 'Pas de sujet'),
        sender=email.get('from', 'Expéditeur inconnu'),
        recipient=email.get('to', 'Destinataire inconnu'),
        date=formatted_date,
        status='✅ Traité' if email.get('is_processed') else '⏳ En attente',
        body_preview=email.get('body', 'Pas de contenu')[:200] + ('...' if len(email.get('body', '')) > 200 else ''),
        full_body=email.get('body', 'Pas de contenu')
    )
    
    return detail_html

# JavaScript pour l'interactivité
def render_javascript():
    """JavaScript pour les interactions"""
    return """
    <script>
        function selectNav(navItem) {
            // Cette fonction sera gérée par Streamlit
            console.log('Navigation:', navItem);
        }
        
        function selectTab(tabName) {
            // Cette fonction sera gérée par Streamlit
            console.log('Tab:', tabName);
        }
        
        function selectEmail(emailIndex) {
            // Cette fonction sera gérée par Streamlit
            console.log('Email selected:', emailIndex);
        }
        
        function goBack() {
            // Cette fonction sera gérée par Streamlit
            console.log('Go back');
        }
        
        function toggleFullContent() {
            const preview = document.getElementById('email-body');
            const full = document.getElementById('full-email-body');
            
            if (full.style.display === 'none') {
                preview.style.display = 'none';
                full.style.display = 'block';
            } else {
                preview.style.display = 'block';
                full.style.display = 'none';
            }
        }
        
        function generateSummary() {
            const summaryContent = document.getElementById('summary-content');
            summaryContent.innerHTML = '<div style="padding: 20px; text-align: center;">🤖 Génération du résumé en cours...</div>';
            // Cette fonction sera gérée par Streamlit
        }
        
        function generateReply() {
            const prompt = document.getElementById('user-prompt').value;
            if (!prompt) {
                alert('Veuillez saisir des instructions pour l\'IA');
                return;
            }
            
            const replyArea = document.getElementById('generated-reply');
            replyArea.value = '🤖 Génération de la réponse en cours...';
            // Cette fonction sera gérée par Streamlit
        }
        
        function sendReply() {
            const reply = document.getElementById('generated-reply').value;
            if (!reply) {
                alert('Veuillez d\'abord générer une réponse');
                return;
            }
            // Cette fonction sera gérée par Streamlit
        }
        
        function saveDraft() {
            const reply = document.getElementById('generated-reply').value;
            if (reply) {
                alert('✅ Brouillon sauvegardé');
            }
        }
        
        function logout() {
            // Cette fonction sera gérée par Streamlit
            console.log('Logout');
        }
    </script>
    """

# Fonction principale pour charger les emails
def load_emails_for_category(category, since_date):
    """Charge les emails pour une catégorie donnée"""
    try:
        # Mapping des catégories d'onglets vers les catégories Gmail
        category_mapping = {
            "Principale": "Boîte de réception",
            "Promotions": "Promotions", 
            "Réseaux sociaux": "Réseaux sociaux",
            "Notifications": "Notifications"
        }
        
        gmail_category = category_mapping.get(category, "Boîte de réception")
        
        # Charger depuis la base de données d'abord
        cached_emails = get_user_emails_by_category(
            user_id, 
            since_date, 
            [gmail_category], 
            limit_per_category=100
        )
        
        if cached_emails and cached_emails.get(gmail_category):
            # Convertir le format Supabase vers le format attendu
            emails = []
            for mail in cached_emails[gmail_category]:
                emails.append({
                    'db_id': mail.get('id'),
                    'subject': mail.get('subject', ''),
                    'from': mail.get('sender', ''),
                    'to': mail.get('recipient', ''),
                    'body': mail.get('body', ''),
                    'date': mail.get('date_received', ''),
                    'category': mail.get('category', gmail_category),
                    'is_processed': mail.get('is_processed', False)
                })
            return emails
        else:
            # Charger depuis Gmail si pas de cache
            categorized_mails = fetch_all_categorized_emails(since_date, limit_per_category=50)
            return categorized_mails.get(gmail_category, [])
            
    except Exception as e:
        st.error(f"Erreur lors du chargement : {str(e)}")
        return []

# Interface principale
st.markdown('<div class="gmail-container">', unsafe_allow_html=True)

# Gestion des boutons avec des colonnes invisibles pour capturer les clics
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 8])

# Navigation sidebar
with col1:
    if st.button("📥", key="nav_inbox", help="Boîte de réception"):
        st.session_state.active_nav = "Boîte de réception"
        st.session_state.current_page = 'inbox'
        st.rerun()

with col2:
    if st.button("📤", key="nav_sent", help="Messages envoyés"):
        st.session_state.active_nav = "Messages envoyés"
        st.session_state.current_page = 'sent'
        st.rerun()

with col3:
    if st.button("🗑️", key="nav_trash", help="Supprimés"):
        st.session_state.active_nav = "Supprimés"
        st.session_state.current_page = 'trash'
        st.rerun()

with col4:
    if st.button("🚪", key="logout_btn", help="Déconnexion"):
        logout()

# Navigation par onglets
tab_col1, tab_col2, tab_col3, tab_col4, tab_col5 = st.columns([1, 1, 1, 1, 8])

with tab_col1:
    if st.button("📧 Principale", key="tab_principale"):
        st.session_state.active_tab = "Principale"
        st.session_state.current_page = 'inbox'
        st.rerun()

with tab_col2:
    if st.button("🏷️ Promotions", key="tab_promotions"):
        st.session_state.active_tab = "Promotions"
        st.session_state.current_page = 'inbox'
        st.rerun()

with tab_col3:
    if st.button("👥 Réseaux sociaux", key="tab_social"):
        st.session_state.active_tab = "Réseaux sociaux"
        st.session_state.current_page = 'inbox'
        st.rerun()

with tab_col4:
    if st.button("🔔 Notifications", key="tab_notifications"):
        st.session_state.active_tab = "Notifications"
        st.session_state.current_page = 'inbox'
        st.rerun()

# Interface principale selon la page active
if st.session_state.current_page == 'inbox':
    # Page principale avec liste des emails
    
    # Sidebar
    st.markdown(render_sidebar(), unsafe_allow_html=True)
    
    # Header
    st.markdown(render_header(), unsafe_allow_html=True)
    
    # Onglets
    st.markdown(render_tabs(), unsafe_allow_html=True)
    
    # Toolbar
    st.markdown(render_toolbar(), unsafe_allow_html=True)
    
    # Charger les emails pour l'onglet actif
    with st.spinner("📧 Chargement des emails..."):
        current_emails = load_emails_for_category(
            st.session_state.active_tab, 
            date.fromisoformat(default_date) if default_date else date.today()
        )
    
    # Stocker les emails dans la session
    st.session_state.current_emails = current_emails
    
    # Liste des emails
    st.markdown(render_email_list(current_emails), unsafe_allow_html=True)
    
    # Gestion de la sélection d'email avec boutons invisibles
    if current_emails:
        email_cols = st.columns(len(current_emails))
        for idx, email in enumerate(current_emails):
            with email_cols[idx % len(email_cols)]:
                if st.button(f"Email {idx}", key=f"select_email_{idx}", 
                           label_visibility="hidden", alpha=0):
                    st.session_state.selected_email = email
                    st.session_state.current_page = 'detail'
                    st.rerun()

elif st.session_state.current_page == 'detail':
    # Page de détail d'un email
    
    if st.session_state.selected_email:
        email = st.session_state.selected_email
        
        # Bouton retour en haut
        if st.button("← Retour à la boîte de réception", key="back_to_inbox"):
            st.session_state.current_page = 'inbox'
            st.session_state.selected_email = None
            st.rerun()
        
        # Afficher les détails de l'email
        st.markdown(render_email_detail(email), unsafe_allow_html=True)
        
        # Gestion des actions (résumé, réponse)
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            if st.button("🤖 Générer résumé", key="generate_summary_btn"):
                with st.spinner("Génération du résumé..."):
                    summary = summarize_emails([email])
                    if summary and not summary.startswith('Erreur'):
                        if email.get('db_id'):
                            save_email_summary(user_id, email['db_id'], summary)
                        st.success("✅ Résumé généré!")
                        st.rerun()
        
        # Section de réponse
        st.markdown("---")
        st.markdown("### ✍️ Répondre à cet email")
        
        with st.form("reply_form_detail"):
            st.markdown(f"**Répondre à:** {email.get('from', 'Expéditeur inconnu')}")
            st.markdown(f"**Sujet:** Re: {email.get('subject', 'Pas de sujet')}")
            
            user_prompt = st.text_input(
                "💭 Instructions pour l'IA",
                placeholder="Ex: 'Refuser poliment', 'Demander plus d'informations'..."
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
        if st.button("← Retour"):
            st.session_state.current_page = 'inbox'
            st.rerun()

# JavaScript pour l'interactivité
st.markdown(render_javascript(), unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Debugging info (à retirer en production)
if st.sidebar.button("🔧 Debug Info"):
    st.sidebar.write("Page actuelle:", st.session_state.current_page)
    st.sidebar.write("Onglet actif:", st.session_state.active_tab)
    st.sidebar.write("Navigation active:", st.session_state.active_nav)
    if st.session_state.selected_email:
        st.sidebar.write("Email sélectionné:", st.session_state.selected_email.get('subject', 'N/A'))