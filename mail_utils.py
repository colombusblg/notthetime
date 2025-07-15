import imaplib
import email
import smtplib
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
import streamlit as st
import email.utils

def parse_email_date(date_str):
    """Parse une date d'email en objet datetime avec gestion complète des timezones"""
    try:
        if not date_str or date_str.strip() == "":
            return datetime.now(timezone.utc)
            
        try:
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            return parsed_date
        except:
            pass
        
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%d %b %Y %H:%M:%S %Z",
            "%a, %d %b %Y %H:%M:%S",
            "%d %b %Y %H:%M:%S"
        ]
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
            except ValueError:
                continue
        
        return datetime.now(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def get_gmail_categories():
    """Retourne la liste des catégories Gmail avec leurs dossiers IMAP correspondants"""
    return {
        "Boîte de réception": "INBOX",
        "Promotions": "[Gmail]/Category Promotions",
        "Réseaux sociaux": "[Gmail]/Category Social", 
        "Notifications": "[Gmail]/Category Updates",
        "Forums": "[Gmail]/Category Forums"
    }

def fetch_emails_from_category(category_folder, since_date=None, limit=50):
    """Récupère les emails d'une catégorie spécifique"""
    try:
        from auth_utils import get_current_user_credentials
        credentials = get_current_user_credentials()
        if not credentials:
            st.error("❌ Impossible de récupérer les identifiants utilisateur")
            return []
        
        username = credentials["email"]
        password = credentials["password"]
        
        # Configuration IMAP
        imap_server = "imap.gmail.com"
        
        # Connexion
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(username, password)
        
        # Lister tous les dossiers disponibles pour debug
        # status, folders = mail.list()
        # st.write(f"Dossiers disponibles: {[f.decode() for f in folders]}")
        
        # Sélectionner le dossier de la catégorie
        try:
            status, count = mail.select(category_folder)
            if status != "OK":
                st.warning(f"⚠️ Impossible d'accéder à la catégorie '{category_folder}'")
                mail.logout()
                return []
        except Exception as e:
            st.warning(f"⚠️ Catégorie '{category_folder}' non disponible: {str(e)}")
            mail.logout()
            return []
        
        # Construire la requête de recherche
        search_criteria = "ALL"
        if since_date:
            if hasattr(since_date, 'strftime'):
                date_str = since_date.strftime('%d-%b-%Y')
                search_criteria = f'(SINCE {date_str})'
        
        # Rechercher les emails
        status, messages = mail.search(None, search_criteria)
        if status != "OK":
            mail.logout()
            return []
        
        email_ids = messages[0].split()
        
        emails = []
        # Prendre les derniers emails (limité)
        for email_id in email_ids[-limit:]:
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue
                
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Extraire les informations
                subject = ""
                if msg["Subject"]:
                    subject_parts = decode_header(msg["Subject"])
                    for part, encoding in subject_parts:
                        if isinstance(part, bytes):
                            subject += part.decode(encoding or 'utf-8', errors='ignore')
                        else:
                            subject += part
                
                if not subject:
                    subject = "Pas de sujet"
                    
                from_email = msg.get("From", "Expéditeur inconnu")
                to_email = msg.get("To", "")
                date = msg.get("Date", "")
                
                # Parser la date pour vérification
                email_datetime = parse_email_date(date)
                
                # Vérifier si l'email correspond au filtre de date
                if since_date and hasattr(since_date, 'date'):
                    if hasattr(since_date, 'tzinfo'):
                        since_datetime = since_date
                    else:
                        since_datetime = datetime.combine(since_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                    
                    if email_datetime.date() < since_datetime.date():
                        continue
                
                # Extraire le corps du message
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = payload.decode('utf-8', errors='ignore')
                                    break
                            except:
                                continue
                else:
                    try:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='ignore')
                    except:
                        body = "Impossible de décoder le contenu"
                
                # Créer un ID unique pour l'email
                email_unique_id = f"{category_folder}_{from_email}_{subject}_{date}"
                
                emails.append({
                    "email_id": email_unique_id,
                    "from": from_email,
                    "to": to_email,
                    "subject": subject,
                    "date": date,
                    "body": body,
                    "category": category_folder
                })
                
            except Exception as e:
                continue
        
        mail.close()
        mail.logout()
        
        # Trier les emails par date (plus récents en premier)
        emails.sort(key=lambda x: parse_email_date(x.get('date', '')), reverse=True)
        
        return emails
        
    except Exception as e:
        st.error(f"❌ Erreur IMAP pour catégorie '{category_folder}': {str(e)}")
        return []

def fetch_all_categorized_emails(since_date=None, limit_per_category=50):
    """Récupère les emails de toutes les catégories Gmail"""
    all_emails = {}
    categories = get_gmail_categories()
    
    total_emails = 0
    
    for category_name, folder_name in categories.items():
        with st.spinner(f"📥 Chargement de '{category_name}'..."):
            emails = fetch_emails_from_category(folder_name, since_date, limit_per_category)
            all_emails[category_name] = emails
            total_emails += len(emails)
            
            if emails:
                st.success(f"✅ {len(emails)} emails chargés depuis '{category_name}'")
            else:
                st.info(f"📭 Aucun email dans '{category_name}'")
    
    st.success(f"🎉 Total: {total_emails} emails chargés depuis toutes les catégories")
    return all_emails

def fetch_emails_from_imap(since_date=None):
    """Récupère les emails depuis IMAP (version simplifiée pour compatibilité)"""
    # Pour compatibilité avec l'ancien code, récupère seulement la boîte de réception
    return fetch_emails_from_category("INBOX", since_date, limit=100)

def initialize_mails(force_sync=False, since_date=None, selected_categories=None):
    """Initialise les emails par catégorie"""
    try:
        from database_utils import sync_emails_with_imap, get_user_emails_by_category
        
        user_id = st.session_state.get('user_id')
        if not user_id:
            st.error("❌ Utilisateur non authentifié")
            return {}
        
        # Si pas de catégories sélectionnées, prendre toutes
        if not selected_categories:
            selected_categories = list(get_gmail_categories().keys())
        
        all_emails = {}
        
        if force_sync:
            # Forcer la synchronisation depuis Gmail
            st.info("🔄 Synchronisation complète avec Gmail...")
            
            for category in selected_categories:
                folder_name = get_gmail_categories()[category]
                emails = fetch_emails_from_category(folder_name, since_date, limit=50)
                
                if emails:
                    # Ajouter la catégorie à chaque email
                    for email in emails:
                        email['category'] = category
                    
                    # Synchroniser avec la base de données
                    synced_count = sync_emails_with_imap(user_id, emails)
                    
                all_emails[category] = emails
        else:
            # Charger depuis la base de données d'abord
            try:
                cached_emails = get_user_emails_by_category(user_id, since_date, selected_categories)
                if cached_emails:
                    all_emails = cached_emails
                    st.success("✅ Emails chargés depuis la base de données")
                else:
                    # Pas de cache, charger depuis Gmail
                    st.info("📭 Aucun email en cache, chargement depuis Gmail...")
                    return initialize_mails(force_sync=True, since_date=since_date, selected_categories=selected_categories)
            except:
                # Fonction pas encore implémentée, charger depuis Gmail
                return initialize_mails(force_sync=True, since_date=since_date, selected_categories=selected_categories)
        
        return all_emails
        
    except Exception as e:
        st.error(f"❌ Erreur lors de l'initialisation par catégorie : {str(e)}")
        return {}

def send_email(to, subject, body):
    """Envoie un email via SMTP"""
    try:
        from auth_utils import get_current_user_credentials
        
        credentials = get_current_user_credentials()
        if not credentials:
            st.error("❌ Impossible de récupérer les identifiants utilisateur")
            return False
        
        from_email = credentials["email"]
        password = credentials["password"]
        
        # Configuration SMTP pour Gmail
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Création du message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to
        msg['Subject'] = subject
        
        # Ajout du corps du message
        msg.attach(MIMEText(body, 'plain'))
        
        # Connexion et envoi
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        
        return True
        
    except Exception as e:
        st.error(f"❌ Erreur lors de l'envoi : {str(e)}")
        return False

def get_emails_since(since_date=None):
    """Fonction helper pour récupérer les emails depuis une date donnée"""
    return fetch_emails_from_imap(since_date)