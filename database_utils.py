import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import uuid
from config import SUPABASE_URL, SUPABASE_KEY

def parse_email_date(date_str):
    """Parse une date d'email en objet datetime"""
    try:
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
        
        return None
    except Exception:
        return None

# Client Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_email_to_db(user_id, email_data, email_id=None):
    """Sauvegarde un email dans la base de données"""
    try:
        # Parser la date
        date_received = parse_email_date(email_data.get('date', ''))
        
        email_record = {
            'user_id': user_id,
            'email_id': email_id or str(uuid.uuid4()),
            'from_email': email_data.get('from', ''),
            'subject': email_data.get('subject', ''),
            'date_received': date_received.isoformat() if date_received else None,
            'body': email_data.get('body', ''),
            'is_read': False,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Vérifier si l'email existe déjà
        existing = supabase.table('emails').select('id').eq('user_id', user_id).eq('email_id', email_record['email_id']).execute()
        
        if existing.data:
            # Mettre à jour l'email existant
            result = supabase.table('emails').update(email_record).eq('id', existing.data[0]['id']).execute()
            return existing.data[0]['id']
        else:
            # Insérer un nouveau email
            result = supabase.table('emails').insert(email_record).execute()
            return result.data[0]['id'] if result.data else None
            
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde de l'email : {str(e)}")
        return None

def get_user_emails(user_id, limit=50, since_date=None):
    """Récupère les emails d'un utilisateur depuis la base de données"""
    try:
        query = supabase.table('emails').select('*').eq('user_id', user_id).order('date_received', desc=True)
        
        if since_date:
            query = query.gte('date_received', since_date.isoformat())
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération des emails : {str(e)}")
        return []

def save_summary_to_db(user_id, email_id, summary):
    """Sauvegarde un résumé dans la base de données"""
    try:
        summary_record = {
            'user_id': user_id,
            'email_id': email_id,
            'summary': summary,
            'created_at': datetime.now().isoformat()
        }
        
        result = supabase.table('summaries').insert(summary_record).execute()
        return result.data[0]['id'] if result.data else None
        
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde du résumé : {str(e)}")
        return None

def get_email_summary(email_id):
    """Récupère le résumé d'un email"""
    try:
        result = supabase.table('summaries').select('summary').eq('email_id', email_id).execute()
        return result.data[0]['summary'] if result.data else None
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération du résumé : {str(e)}")
        return None

def save_reply_to_db(user_id, email_id, user_prompt, generated_reply, is_sent=False):
    """Sauvegarde une réponse dans la base de données"""
    try:
        reply_record = {
            'user_id': user_id,
            'email_id': email_id,
            'user_prompt': user_prompt,
            'generated_reply': generated_reply,
            'is_sent': is_sent,
            'sent_at': datetime.now().isoformat() if is_sent else None,
            'created_at': datetime.now().isoformat()
        }
        
        result = supabase.table('replies').insert(reply_record).execute()
        return result.data[0]['id'] if result.data else None
        
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde de la réponse : {str(e)}")
        return None

def update_reply_sent_status(reply_id):
    """Met à jour le statut d'envoi d'une réponse"""
    try:
        result = supabase.table('replies').update({
            'is_sent': True,
            'sent_at': datetime.now().isoformat()
        }).eq('id', reply_id).execute()
        
        return result.data[0] if result.data else None
        
    except Exception as e:
        st.error(f"Erreur lors de la mise à jour du statut : {str(e)}")
        return None

def get_user_statistics(user_id):
    """Récupère les statistiques d'un utilisateur"""
    try:
        # Nombre total d'emails
        emails_count = supabase.table('emails').select('id', count='exact').eq('user_id', user_id).execute()
        
        # Nombre de résumés générés
        summaries_count = supabase.table('summaries').select('id', count='exact').eq('user_id', user_id).execute()
        
        # Nombre de réponses envoyées
        replies_sent_count = supabase.table('replies').select('id', count='exact').eq('user_id', user_id).eq('is_sent', True).execute()
        
        return {
            'total_emails': emails_count.count,
            'summaries_generated': summaries_count.count,
            'replies_sent': replies_sent_count.count
        }
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération des statistiques : {str(e)}")
        return {'total_emails': 0, 'summaries_generated': 0, 'replies_sent': 0}

def sync_emails_with_imap(user_id, imap_emails):
    """Synchronise les emails IMAP avec la base de données"""
    try:
        synced_count = 0
        
        for email_data in imap_emails:
            # Créer un ID unique basé sur le contenu de l'email
            email_unique_id = f"{email_data.get('from', '')}_{email_data.get('subject', '')}_{email_data.get('date', '')}"
            
            saved_id = save_email_to_db(user_id, email_data, email_unique_id)
            if saved_id:
                synced_count += 1
        
        return synced_count
        
    except Exception as e:
        st.error(f"Erreur lors de la synchronisation : {str(e)}")
        return 0

def mark_email_as_read(email_id):
    """Marque un email comme lu"""
    try:
        result = supabase.table('emails').update({
            'is_read': True,
            'updated_at': datetime.now().isoformat()
        }).eq('id', email_id).execute()
        
        return result.data[0] if result.data else None
        
    except Exception as e:
        st.error(f"Erreur lors de la mise à jour : {str(e)}")
        return None