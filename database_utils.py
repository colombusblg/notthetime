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

def save_email_to_supabase(user_id, email_data, email_id=None):
    """Sauvegarde un email dans la base de données Supabase"""
    try:
        # Parser la date
        date_received = parse_email_date(email_data.get('date', ''))
        
        email_record = {
            'user_id': user_id,
            'email_id': email_id or str(uuid.uuid4()),
            'subject': email_data.get('subject', ''),
            'sender': email_data.get('from', ''),
            'recipient': email_data.get('to', ''),
            'body': email_data.get('body', ''),
            'date_received': date_received.isoformat() if date_received else None,
            'is_processed': False,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Vérifier si l'email existe déjà
        existing = supabase.table('user_emails').select('id').eq('user_id', user_id).eq('email_id', email_record['email_id']).execute()
        
        if existing.data:
            # Mettre à jour l'email existant
            result = supabase.table('user_emails').update(email_record).eq('id', existing.data[0]['id']).execute()
            return existing.data[0]['id']
        else:
            # Insérer un nouveau email
            result = supabase.table('user_emails').insert(email_record).execute()
            return result.data[0]['id'] if result.data else None
            
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde de l'email : {str(e)}")
        return None

def get_user_emails_from_supabase(user_id, since_date=None, limit=50):
    """Récupère les emails d'un utilisateur depuis Supabase"""
    try:
        query = supabase.table('user_emails').select('*').eq('user_id', user_id).order('date_received', desc=True)
        
        if since_date:
            # Convertir la date en datetime si c'est un objet date
            if hasattr(since_date, 'isoformat'):
                since_date_str = since_date.isoformat()
            else:
                since_date_str = since_date
            query = query.gte('date_received', since_date_str)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération des emails : {str(e)}")
        return []

# Alias pour la compatibilité
def get_user_emails(user_id, since_date=None, limit=50):
    """Alias pour get_user_emails_from_supabase pour compatibilité"""
    return get_user_emails_from_supabase(user_id, since_date, limit)

def save_email_summary(user_id, email_id, summary_text):
    """Sauvegarde un résumé dans la base de données"""
    try:
        summary_record = {
            'user_id': user_id,
            'email_id': email_id,
            'summary_text': summary_text,
            'created_at': datetime.now().isoformat()
        }
        
        result = supabase.table('email_summaries').insert(summary_record).execute()
        return result.data[0]['id'] if result.data else None
        
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde du résumé : {str(e)}")
        return None

def get_email_summary(user_id, email_id):
    """Récupère le résumé d'un email"""
    try:
        result = supabase.table('email_summaries').select('*').eq('user_id', user_id).eq('email_id', email_id).execute()
        return result.data[0] if result.data else None
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération du résumé : {str(e)}")
        return None

def save_email_reply(user_id, email_id, user_prompt, generated_reply, final_reply, was_sent=False):
    """Sauvegarde une réponse dans la base de données"""
    try:
        reply_record = {
            'user_id': user_id,
            'email_id': email_id,
            'user_prompt': user_prompt,
            'generated_reply': generated_reply,
            'final_reply': final_reply,
            'was_sent': was_sent,
            'sent_at': datetime.now().isoformat() if was_sent else None,
            'created_at': datetime.now().isoformat()
        }
        
        result = supabase.table('email_replies').insert(reply_record).execute()
        return result.data[0]['id'] if result.data else None
        
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde de la réponse : {str(e)}")
        return None

def update_reply_sent_status(reply_id):
    """Met à jour le statut d'envoi d'une réponse"""
    try:
        result = supabase.table('email_replies').update({
            'was_sent': True,
            'sent_at': datetime.now().isoformat()
        }).eq('id', reply_id).execute()
        
        return result.data[0] if result.data else None
        
    except Exception as e:
        st.error(f"Erreur lors de la mise à jour du statut : {str(e)}")
        return None

def get_user_preferences(user_id):
    """Récupère les préférences d'un utilisateur"""
    try:
        result = supabase.table('user_preferences').select('*').eq('user_id', user_id).execute()
        
        # Convertir en dictionnaire
        preferences = {}
        for pref in result.data:
            preferences[pref['preference_key']] = pref['preference_value']
        
        return preferences
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération des préférences : {str(e)}")
        return {}

def save_user_preference(user_id, preference_key, preference_value):
    """Sauvegarde une préférence utilisateur"""
    try:
        preference_record = {
            'user_id': user_id,
            'preference_key': preference_key,
            'preference_value': preference_value,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Vérifier si la préférence existe déjà
        existing = supabase.table('user_preferences').select('id').eq('user_id', user_id).eq('preference_key', preference_key).execute()
        
        if existing.data:
            # Mettre à jour la préférence existante
            result = supabase.table('user_preferences').update({
                'preference_value': preference_value,
                'updated_at': datetime.now().isoformat()
            }).eq('id', existing.data[0]['id']).execute()
            return existing.data[0]['id']
        else:
            # Insérer une nouvelle préférence
            result = supabase.table('user_preferences').insert(preference_record).execute()
            return result.data[0]['id'] if result.data else None
        
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde de la préférence : {str(e)}")
        return None

def get_user_statistics(user_id):
    """Récupère les statistiques d'un utilisateur"""
    try:
        # Nombre total d'emails
        emails_count = supabase.table('user_emails').select('id', count='exact').eq('user_id', user_id).execute()
        
        # Nombre de résumés générés
        summaries_count = supabase.table('email_summaries').select('id', count='exact').eq('user_id', user_id).execute()
        
        # Nombre de réponses envoyées
        replies_sent_count = supabase.table('email_replies').select('id', count='exact').eq('user_id', user_id).eq('was_sent', True).execute()
        
        return {
            'total_emails': emails_count.count or 0,
            'summaries_generated': summaries_count.count or 0,
            'replies_sent': replies_sent_count.count or 0
        }
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération des statistiques : {str(e)}")
        return {'total_emails': 0, 'summaries_generated': 0, 'replies_sent': 0}

def mark_email_as_processed(email_id):
    """Marque un email comme traité"""
    try:
        result = supabase.table('user_emails').update({
            'is_processed': True,
            'updated_at': datetime.now().isoformat()
        }).eq('id', email_id).execute()
        
        return result.data[0] if result.data else None
        
    except Exception as e:
        st.error(f"Erreur lors de la mise à jour : {str(e)}")
        return None

def sync_emails_with_imap(user_id, imap_emails):
    """Synchronise les emails IMAP avec la base de données"""
    try:
        synced_count = 0
        
        for email_data in imap_emails:
            # Créer un ID unique basé sur le contenu de l'email
            email_unique_id = f"{email_data.get('from', '')}_{email_data.get('subject', '')}_{email_data.get('date', '')}"
            
            saved_id = save_email_to_supabase(user_id, email_data, email_unique_id)
            if saved_id:
                synced_count += 1
        
        return synced_count
        
    except Exception as e:
        st.error(f"Erreur lors de la synchronisation : {str(e)}")
        return 0