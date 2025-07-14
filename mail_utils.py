import os
import pickle
import base64
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
# Ajoutez ici vos imports pour Supabase
# from supabase import create_client, Client

# Configuration Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']

def get_gmail_credentials():
    """Obtient les credentials Gmail API"""
    creds = None
    
    # Le fichier token.pickle stocke les tokens d'accès et de rafraîchissement
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # Si il n'y a pas de credentials valides, demander à l'utilisateur de se connecter
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Sauvegarder les credentials pour la prochaine fois
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def extract_message_body(payload):
    """Extrait le corps du message depuis le payload Gmail"""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
            elif part['mimeType'] == 'text/html' and not body:
                # Fallback sur HTML si pas de texte plain
                if 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
    else:
        if payload['mimeType'] == 'text/plain':
            if 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        elif payload['mimeType'] == 'text/html':
            if 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    return body

def initialize_mails():
    """
    Initialise et retourne la liste des emails.
    Cette fonction remplace l'ancienne variable globale 'mails'.
    """
    try:
        mails = get_all_emails_with_local_history()
        
        if not mails:
            print("Aucun mail trouvé")
            return []
            
        return mails
    except Exception as e:
        print(f"Erreur lors du chargement des mails: {e}")
        return []

def get_all_emails_with_local_history():
    """
    Récupère tous les emails avec l'historique local via Gmail API.
    Retourne une liste de dictionnaires contenant les emails.
    """
    try:
        # Obtenir les credentials
        credentials = get_gmail_credentials()
        service = build('gmail', 'v1', credentials=credentials)
        
        # Récupérer la liste des messages
        results = service.users().messages().list(userId='me', maxResults=50).execute()
        messages = results.get('messages', [])
        
        emails = []
        for message in messages:
            # Récupérer le détail de chaque message
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            
            # Extraire les informations
            headers = msg['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            from_email = next((h['value'] for h in headers if h['name'] == 'From'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Extraire le corps du message
            body = extract_message_body(msg['payload'])
            
            emails.append({
                "from": from_email,
                "subject": subject,
                "date": date,
                "body": body,
                "id": message['id']  # Ajout de l'ID du message
            })
        
        print(f"Récupération de {len(emails)} emails réussie")
        return emails
        
    except Exception as e:
        print(f"Erreur lors de la récupération des emails: {e}")
        return []

def send_email(to, subject, body):
    """
    Envoie un email via Gmail API.
    Retourne True si succès, False sinon.
    """
    try:
        # Obtenir les credentials
        credentials = get_gmail_credentials()
        service = build('gmail', 'v1', credentials=credentials)
        
        # Créer le message
        message = create_message(to, subject, body)
        
        # Envoyer le message
        result = service.users().messages().send(userId='me', body=message).execute()
        
        if result:
            print(f"Email envoyé avec succès à {to}")
            print(f"ID du message: {result['id']}")
            
            # Sauvegarde en base si nécessaire
            email_data = {
                "to": to,
                "subject": subject,
                "body": body,
                "sent_at": datetime.now().isoformat(),
                "message_id": result['id']
            }
            save_email_to_supabase(email_data)
            
            return True
        else:
            print("Erreur lors de l'envoi de l'email")
            return False
        
    except Exception as e:
        print(f"Erreur lors de l'envoi: {e}")
        return False

def create_message(to, subject, body):
    """Crée un message au format Gmail API"""
    import email.mime.text
    import email.mime.multipart
    
    msg = email.mime.multipart.MIMEMultipart()
    msg['to'] = to
    msg['subject'] = subject
    
    msg.attach(email.mime.text.MIMEText(body, 'plain'))
    
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {'raw': raw}

def save_email_to_supabase(data):
    """
    Sauvegarde un email dans la base Supabase.
    """
    try:
        # VOUS DEVEZ CONFIGURER SUPABASE d'abord
        # Décommentez et configurez ces lignes :
        # supabase_url = "votre_supabase_url"
        # supabase_key = "votre_supabase_key"
        # supabase = create_client(supabase_url, supabase_key)
        
        # response = supabase.table("email_history").insert(data).execute()
        # if response.data:
        #     print("Email sauvegardé en base")
        # else:
        #     print(f"Erreur sauvegarde email : {response}")
        
        print(f"Email sauvegardé (placeholder): {data}")
        
    except Exception as e:
        print(f"Erreur lors de la sauvegarde : {e}")

def parse_email_date(date_str):
    """Convertit la date d'entête mail en objet datetime"""
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S",
        "%d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except Exception:
            continue
    return None

def get_email_by_id(email_id):
    """Récupère un email spécifique par son ID"""
    try:
        credentials = get_gmail_credentials()
        service = build('gmail', 'v1', credentials=credentials)
        
        msg = service.users().messages().get(userId='me', id=email_id).execute()
        
        headers = msg['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        from_email = next((h['value'] for h in headers if h['name'] == 'From'), '')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        body = extract_message_body(msg['payload'])
        
        return {
            "from": from_email,
            "subject": subject,
            "date": date,
            "body": body,
            "id": email_id
        }
        
    except Exception as e:
        print(f"Erreur lors de la récupération de l'email {email_id}: {e}")
        return None

def search_emails(query, max_results=10):
    """Recherche des emails avec une requête spécifique"""
    try:
        credentials = get_gmail_credentials()
        service = build('gmail', 'v1', credentials=credentials)
        
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        emails = []
        for message in messages:
            email_data = get_email_by_id(message['id'])
            if email_data:
                emails.append(email_data)
        
        return emails
        
    except Exception as e:
        print(f"Erreur lors de la recherche: {e}")
        return []

# Fonctions utilitaires supplémentaires
def mark_as_read(email_id):
    """Marque un email comme lu"""
    try:
        credentials = get_gmail_credentials()
        service = build('gmail', 'v1', credentials=credentials)
        
        service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        print(f"Email {email_id} marqué comme lu")
        return True
        
    except Exception as e:
        print(f"Erreur lors du marquage comme lu: {e}")
        return False

def get_unread_emails():
    """Récupère uniquement les emails non lus"""
    return search_emails("is:unread")

# Exemple d'utilisation
if __name__ == "__main__":
    # Test de récupération des emails
    print("Récupération des emails...")
    emails = initialize_mails()
    
    if emails:
        print(f"Nombre d'emails récupérés: {len(emails)}")
        print(f"Premier email: {emails[0]['subject']}")
    
    # Test d'envoi d'email
    # send_email("destinataire@example.com", "Test Subject", "Test Body")
    
    # Test de recherche
    # unread_emails = get_unread_emails()
    # print(f"Emails non lus: {len(unread_emails)}")