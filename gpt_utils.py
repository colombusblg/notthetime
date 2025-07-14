import imaplib
import email
import smtplib
import openai
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
    """Récupère les emails depuis IMAP (fonction helper)"""
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
                date = msg.get("Date", "")  # Date vide au lieu de "Date inconnue"
                
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
                    "date": date,  # La date sera traitée par parse_email_date
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
        db_emails = get_user_emails(user_id)
        
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
                db_emails = get_user_emails(user_id)
        
        # Convertir le format DB vers le format attendu par l'app
        emails = []
        for db_email in db_emails:
            emails.append({
                "id": db_email.get("id"),  # ID de la base de données
                "from": db_email.get("sender", ""),
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

def summarize_emails(emails):
    """Génère un résumé des emails en utilisant OpenAI"""
    try:
        if not emails:
            return "Aucun email à résumer"
        
        # Préparer le contenu pour GPT
        email_content = ""
        for email in emails:
            email_content += f"De: {email.get('from', 'Expéditeur inconnu')}\n"
            email_content += f"Sujet: {email.get('subject', 'Pas de sujet')}\n"
            email_content += f"Date: {email.get('date', 'Date inconnue')}\n"
            email_content += f"Corps: {email.get('body', 'Pas de contenu')[:1000]}...\n\n"
        
        # Prompt pour le résumé
        prompt = f"""
        Veuillez résumer le(s) email(s) suivant(s) de manière concise et claire.
        Identifiez les points clés, les actions requises et l'urgence si applicable.
        Répondez en français et de manière professionnelle.
        
        Emails à résumer:
        {email_content}
        
        Résumé:
        """
        
        # Appel à l'API OpenAI
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Vous êtes un assistant qui résume les emails de manière concise et professionnelle en français."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la génération du résumé : {str(e)}")
        return "Erreur lors de la génération du résumé"

def generate_reply(email_body, user_prompt, email_db_id=None):
    """Génère une réponse à un email en utilisant OpenAI"""
    try:
        if not email_body or not user_prompt:
            return "Erreur: email ou prompt manquant"
        
        # Vérifier s'il y a une réponse en cache
        if email_db_id:
            try:
                from database_utils import get_email_reply
                cached_reply = get_email_reply(email_db_id)
                if cached_reply and cached_reply.get('user_prompt') == user_prompt:
                    return cached_reply.get('generated_reply', '')
            except:
                pass  # Continuer si pas de cache disponible
        
        # Limiter la longueur du corps de l'email pour éviter les limites de tokens
        truncated_body = email_body[:2000] if len(email_body) > 2000 else email_body
        
        # Prompt pour la génération de réponse
        prompt = f"""
        Vous devez générer une réponse professionnelle à l'email suivant.
        
        Email original:
        {truncated_body}
        
        Instructions de l'utilisateur:
        {user_prompt}
        
        Générez une réponse polie, professionnelle et appropriée en français.
        La réponse doit être directe, claire et respectueuse.
        N'incluez pas de formule de politesse d'ouverture comme "Cher..." car cela sera ajouté automatiquement.
        
        Réponse:
        """
        
        # Appel à l'API OpenAI
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Vous êtes un assistant qui génère des réponses professionnelles à des emails en français. Soyez concis et professionnel."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.5
        )
        
        generated_reply = response.choices[0].message.content.strip()
        
        # Sauvegarder la réponse générée si on a un ID d'email
        if email_db_id:
            try:
                from database_utils import save_email_reply
                user_id = st.session_state.get('user_id')
                if user_id:
                    save_email_reply(user_id, email_db_id, user_prompt, generated_reply, generated_reply, False)
            except:
                pass  # Continuer même si la sauvegarde échoue
        
        return generated_reply
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la génération de la réponse : {str(e)}")
        return "Erreur lors de la génération de la réponse"

def generate_smart_reply(email_body, email_subject, sender, user_context=""):
    """Génère une réponse intelligente basée sur le contexte"""
    try:
        system_prompt = """
        Vous êtes un assistant email intelligent qui génère des réponses professionnelles.
        Analysez le contexte de l'email et générez une réponse appropriée.
        Soyez concis, poli et professionnel.
        Répondez toujours en français.
        """
        
        user_prompt = f"""
        Analysez cet email et générez une réponse appropriée:
        
        Expéditeur: {sender}
        Sujet: {email_subject}
        
        Corps de l'email:
        {email_body[:1500]}
        
        Contexte utilisateur (si fourni): {user_context}
        
        Générez une réponse professionnelle et pertinente en français.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=600,
            temperature=0.4
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la génération de la réponse intelligente : {str(e)}")
        return "Erreur lors de la génération de la réponse"

def analyze_email_sentiment(email_body):
    """Analyse le sentiment d'un email"""
    try:
        prompt = f"""
        Analysez le sentiment de cet email et classifiez-le comme:
        - POSITIF
        - NEUTRE  
        - NÉGATIF
        - URGENT
        
        Email à analyser:
        {email_body[:1000]}
        
        Répondez avec seulement le sentiment principal suivi d'une brève explication (max 50 mots).
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Vous êtes un expert en analyse de sentiment d'emails professionnels."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.2
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        st.error(f"❌ Erreur lors de l'analyse de sentiment : {str(e)}")
        return "NEUTRE - Erreur d'analyse"

def extract_action_items(email_body):
    """Extrait les actions à effectuer d'un email"""
    try:
        prompt = f"""
        Extrayez les actions spécifiques à effectuer de cet email.
        Listez chaque action de manière claire et concise.
        Si aucune action n'est requise, répondez "Aucune action requise".
        
        Email à analyser:
        {email_body[:1500]}
        
        Actions à effectuer:
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Vous êtes un expert en extraction d'actions à effectuer depuis des emails professionnels."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        st.error(f"❌ Erreur lors de l'extraction des actions : {str(e)}")
        return "Erreur lors de l'extraction des actions"

def categorize_email(email_subject, email_body):
    """Catégorise un email automatiquement"""
    try:
        prompt = f"""
        Catégorisez cet email dans une des catégories suivantes:
        - TRAVAIL
        - PERSONNEL
        - COMMERCIAL
        - URGENT
        - INFORMATION
        - SPAM
        - AUTRE
        
        Sujet: {email_subject}
        Corps: {email_body[:800]}
        
        Répondez avec seulement la catégorie principale.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Vous êtes un expert en classification d'emails."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.1
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la catégorisation : {str(e)}")
        return "AUTRE"