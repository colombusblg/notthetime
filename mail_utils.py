import imaplib
import email
import smtplib
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import streamlit as st
from auth_utils import get_current_user_credentials

def parse_email_date(date_str):
    """Parse une date d'email en objet datetime"""
    try:
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
        
        # Si aucun format ne fonctionne, retourner None
        return None
    except Exception:
        return None

def initialize_mails():
    """Initialise et récupère les emails via IMAP"""
    try:
        # Récupérer les identifiants de l'utilisateur connecté
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
        
        # Rechercher les emails
        status, messages = mail.search(None, "ALL")
        if status != "OK":
            st.error("❌ Erreur lors de la recherche des emails")
            return []
        
        email_ids = messages[0].split()
        
        emails = []
        # Prendre les 50 derniers emails (ou ajuster selon vos besoins)
        for email_id in email_ids[-50:]:
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue
                
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Extraire les informations
                subject = decode_header(msg["Subject"])[0][0] if msg["Subject"] else "Pas de sujet"
                if isinstance(subject, bytes):
                    subject = subject.decode()
                    
                from_email = msg.get("From", "Expéditeur inconnu")
                date = msg.get("Date", "Date inconnue")
                
                # Extraire le corps
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode()
                                break
                            except:
                                continue
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()
                    except:
                        body = "Impossible de décoder le contenu"
                
                emails.append({
                    "from": from_email,
                    "subject": subject,
                    "date": date,
                    "body": body
                })
            except Exception as e:
                st.warning(f"⚠️ Erreur lors du traitement d'un email : {str(e)}")
                continue
        
        mail.close()
        mail.logout()
        return emails
        
    except Exception as e:
        st.error(f"❌ Erreur IMAP : {str(e)}")
        return []

def send_email(to, subject, body):
    """Envoie un email via SMTP"""
    try:
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