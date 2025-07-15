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
            return datetime.now(timezone.utc)  # Retourner la date actuelle avec timezone UTC
            
        # Utiliser email.utils.parsedate_to_datetime pour une meilleure gestion des timezones
        try:
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            # Si la date n'a pas de timezone, ajouter UTC
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            return parsed_date
        except:
            pass
        
        # Fallback avec les formats manuels
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
                # Si pas de timezone dans le format, ajouter UTC
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
            except ValueError:
                continue
        
        # Si aucun format ne fonctionne, retourner la date actuelle avec UTC
        return datetime.now(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def fetch_emails_from_imap(since_date=None):
    """Récupère les emails depuis IMAP avec filtre de date optionnel"""
    try:
        # Récupérer les identifiants de l'utilisateur connecté
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
        mail.select("inbox")
        
        # Construire la requête de recherche
        search_criteria = "ALL"
        if since_date:
            # Convertir la date en format IMAP (DD-MMM-YYYY)
            if hasattr(since_date, 'strftime'):
                date_str = since_date.strftime('%d-%b-%Y')
                search_criteria = f'(SINCE {date_str})'
            else:
                # Si c'est déjà une string, l'utiliser directement
                search_criteria = f'(SINCE {since_date})'
        
        # Rechercher les emails
        status, messages = mail.search(None, search_criteria)
        if status != "OK":
            st.error(f"❌ Erreur lors de la recherche des emails avec critère : {search_criteria}")
            return []
        
        email_ids = messages[0].split()
        
        emails = []
        # Prendre les derniers emails (maximum 100)
        for email_id in email_ids[-100:]:
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
                    # Convertir since_date en datetime avec timezone pour comparaison
                    if hasattr(since_date, 'tzinfo'):
                        since_datetime = since_date
                    else:
                        since_datetime = datetime.combine(since_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                    
                    # Comparer les dates (pas les heures)
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
                email_unique_id = f"{from_email}_{subject}_{date}"
                
                emails.append({
                    "email_id": email_unique_id,
                    "from": from_email,
                    "to": to_email,
                    "subject": subject,
                    "date": date,
                    "body": body
                })
                
            except Exception as e:
                st.warning(f"⚠️ Erreur lors du traitement d'un email : {str(e)}")
                continue
        
        mail.close()
        mail.logout()
        
        # Trier les emails par date (plus récents en premier)
        emails.sort(key=lambda x: parse_email_date(x.get('date', '')), reverse=True)
        
        return emails
        
    except Exception as e:
        st.error(f"❌ Erreur IMAP : {str(e)}")
        return []

def initialize_mails(force_sync=False, since_date=None):
    """Initialise les emails - priorité à la DB, sync IMAP si nécessaire"""
    try:
        # Import local pour éviter les imports circulaires
        from database_utils import sync_emails_with_imap, get_user_emails
        
        user_id = st.session_state.get('user_id')
        if not user_id:
            st.error("❌ Utilisateur non authentifié")
            return []
        
        # Récupérer les emails depuis la base de données
        db_emails = get_user_emails(user_id, since_date, limit=100)
        
        # Si pas d'emails en DB ou synchronisation forcée
        if not db_emails or force_sync:
            st.info("🔄 Synchronisation avec Gmail...")
            
            # Récupérer depuis IMAP avec le filtre de date
            imap_emails = fetch_emails_from_imap(since_date)
            
            if imap_emails:
                # Synchroniser avec la base de données
                synced_count = sync_emails_with_imap(user_id, imap_emails)
                st.success(f"✅ {synced_count} emails synchronisés")
                
                # Récupérer les emails mis à jour depuis la DB
                db_emails = get_user_emails(user_id, since_date, limit=100)
        
        # Convertir le format DB vers le format attendu par l'app
        emails = []
        for db_email in db_emails:
            emails.append({
                "db_id": db_email.get("id"),  # ID de la base de données
                "from": db_email.get("sender", ""),
                "to": db_email.get("recipient", ""),
                "subject": db_email.get("subject", ""),
                "date": db_email.get("date_received", ""),
                "body": db_email.get("body", ""),
                "is_processed": db_email.get("is_processed", False)
            })
        
        return emails
        
    except Exception as e:
        st.error(f"❌ Erreur lors de l'initialisation : {str(e)}")
        return []

def send_email(to, subject, body):
    """Envoie un email via SMTP"""
    try:
        # Import local pour éviter les imports circulaires
        from auth_utils import get_current_user_credentials
        
        # Récupérer les identifiants de l'utilisateur connecté
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