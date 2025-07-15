import imaplib
import email
import smtplib
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import streamlit as st

def parse_email_date(date_str):
    """Parse une date d'email en objet datetime"""
    try:
        if not date_str or date_str.strip() == "":
            return datetime.now()  # Retourner la date actuelle si pas de date
            
        # Formats de date email courants
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
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Si aucun format ne fonctionne, retourner la date actuelle
        return datetime.now()
    except Exception:
        return datetime.now()

def fetch_emails_from_imap():
    """Récupère les emails depuis IMAP"""
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
        
        # Rechercher les emails récents (les 100 derniers)
        status, messages = mail.search(None, "ALL")
        if status != "OK":
            st.error("❌ Erreur lors de la recherche des emails")
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

def initialize_mails(force_sync=False):
    """Initialise les emails - priorité à la DB, sync IMAP si nécessaire"""
    try:
        # Import local pour éviter les imports circulaires
        from database_utils import sync_emails_with_imap, get_user_emails
        
        user_id = st.session_state.get('user_id')
        if not user_id:
            st.error("❌ Utilisateur non authentifié")
            return []
        
        # Récupérer les emails depuis la base de données
        db_emails = get_user_emails(user_id, limit=100)
        
        # Si pas d'emails en DB ou synchronisation forcée
        if not db_emails or force_sync:
            st.info("🔄 Synchronisation avec Gmail...")
            
            # Récupérer depuis IMAP
            imap_emails = fetch_emails_from_imap()
            
            if imap_emails:
                # Synchroniser avec la base de données
                synced_count = sync_emails_with_imap(user_id, imap_emails)
                st.success(f"✅ {synced_count} emails synchronisés")
                
                # Récupérer les emails mis à jour depuis la DB
                db_emails = get_user_emails(user_id, limit=100)
        
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