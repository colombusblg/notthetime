import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone
import uuid
import hashlib
from config import SUPABASE_URL, SUPABASE_KEY
import email.utils

def parse_email_date(date_str):
    """Parse une date d'email en objet datetime avec gestion des timezones"""
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

# Client Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_email_id(email_data):
    """Génère un ID unique pour un email basé sur son contenu"""
    try:
        content = f"{email_data.get('from', '')}{email_data.get('subject', '')}{email_data.get('date', '')}{email_data.get('body', '')[:100]}"
        return hashlib.md5(content.encode()).hexdigest()
    except Exception:
        return str(uuid.uuid4())

def save_email_to_supabase(user_id, email_data, email_id=None):
    """Sauvegarde un email dans la base de données Supabase avec catégorie"""
    try:
        date_received = parse_email_date(email_data.get('date', ''))
        
        if date_received is None:
            date_received = datetime.now(timezone.utc)
        elif date_received.tzinfo is None:
            date_received = date_received.replace(tzinfo=timezone.utc)
        
        if not email_id:
            email_id = generate_email_id(email_data)
        
        email_record = {
            'user_id': user_id,
            'email_id': email_id,
            'subject': email_data.get('subject', ''),
            'sender': email_data.get('from', ''),
            'recipient': email_data.get('to', ''),
            'body': email_data.get('body', ''),
            'date_received': date_received.isoformat(),
            'category': email_data.get('category', 'Boîte de réception'),  # Nouvelle colonne catégorie
            'is_processed': False,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
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
    """Récupère les emails d'un utilisateur depuis Supabase avec gestion correcte des dates"""
    try:
        query = supabase.table('user_emails').select('*').eq('user_id', user_id).order('date_received', desc=True)
        
        if since_date:
            if hasattr(since_date, 'date'):
                if since_date.tzinfo is None:
                    since_datetime = since_date.replace(tzinfo=timezone.utc)
                else:
                    since_datetime = since_date
                since_date_str = since_datetime.isoformat()
            elif hasattr(since_date, 'isoformat'):
                since_datetime = datetime.combine(since_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                since_date_str = since_datetime.isoformat()
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

def get_user_emails_by_category(user_id, since_date=None, categories=None, limit_per_category=50):
    """Récupère les emails d'un utilisateur organisés par catégorie"""
    try:
        # Construire la requête de base
        query = supabase.table('user_emails').select('*').eq('user_id', user_id)
        
        # Filtrer par date si spécifiée
        if since_date:
            if hasattr(since_date, 'date'):
                if since_date.tzinfo is None:
                    since_datetime = since_date.replace(tzinfo=timezone.utc)
                else:
                    since_datetime = since_date
                since_date_str = since_datetime.isoformat()
            elif hasattr(since_date, 'isoformat'):
                since_datetime = datetime.combine(since_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                since_date_str = since_datetime.isoformat()
            else:
                since_date_str = since_date
            
            query = query.gte('date_received', since_date_str)
        
        # Filtrer par catégories si spécifiées
        if categories:
            query = query.in_('category', categories)
        
        # Ordonner par date
        query = query.order('date_received', desc=True)
        
        # Récupérer tous les emails (on limitera par catégorie après)
        result = query.execute()
        
        # Organiser par catégorie
        emails_by_category = {}
        for email in result.data:
            category = email.get('category', 'Boîte de réception')
            if category not in emails_by_category:
                emails_by_category[category] = []
            
            # Limiter le nombre d'emails par catégorie
            if len(emails_by_category[category]) < limit_per_category:
                emails_by_category[category].append(email)
        
        return emails_by_category
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération des emails par catégorie : {str(e)}")
        return {}

def get_user_emails(user_id, since_date=None, limit=50):
    """Alias pour get_user_emails_from_supabase pour compatibilité"""
    return get_user_emails_from_supabase(user_id, since_date, limit)

def get_category_statistics(user_id):
    """Récupère les statistiques par catégorie"""
    try:
        # Compter les emails par catégorie
        result = supabase.table('user_emails').select('category').eq('user_id', user_id).execute()
        
        category_counts = {}
        for email in result.data:
            category = email.get('category', 'Boîte de réception')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return category_counts
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération des statistiques par catégorie : {str(e)}")
        return {}

def save_email_summary(user_id, email_id, summary_text):
    """Sauvegarde un résumé dans la base de données"""
    try:
        summary_record = {
            'user_id': user_id,
            'email_id': email_id,
            'summary_text': summary_text,
            'created_at': datetime.now(timezone.utc).isoformat()
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

def get_email_reply(email_id):
    """Récupère une réponse d'email depuis la base de données"""
    try:
        result = supabase.table('email_replies').select('*').eq('email_id', email_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        return None

def save_email_reply(user_id, email_id, user_prompt, generated_reply, final_reply, was_sent=False):
    """Sauvegarde une réponse dans la base de données"""
    try:
        current_time = datetime.now(timezone.utc).isoformat()
        
        reply_record = {
            'user_id': user_id,
            'email_id': email_id,
            'user_prompt': user_prompt,
            'generated_reply': generated_reply,
            'final_reply': final_reply,
            'was_sent': was_sent,
            'sent_at': current_time if was_sent else None,
            'created_at': current_time
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
            'sent_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', reply_id).execute()
        
        return result.data[0] if result.data else None
        
    except Exception as e:
        st.error(f"Erreur lors de la mise à jour du statut : {str(e)}")
        return None

def get_user_preferences(user_id):
    """Récupère les préférences d'un utilisateur"""
    try:
        result = supabase.table('user_preferences').select('*').eq('user_id', user_id).execute()
        
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
        current_time = datetime.now(timezone.utc).isoformat()
        
        preference_record = {
            'user_id': user_id,
            'preference_key': preference_key,
            'preference_value': preference_value,
            'created_at': current_time,
            'updated_at': current_time
        }
        
        existing = supabase.table('user_preferences').select('id').eq('user_id', user_id).eq('preference_key', preference_key).execute()
        
        if existing.data:
            result = supabase.table('user_preferences').update({
                'preference_value': preference_value,
                'updated_at': current_time
            }).eq('id', existing.data[0]['id']).execute()
            return existing.data[0]['id']
        else:
            result = supabase.table('user_preferences').insert(preference_record).execute()
            return result.data[0]['id'] if result.data else None
        
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde de la préférence : {str(e)}")
        return None

def get_user_statistics(user_id):
    """Récupère les statistiques d'un utilisateur"""
    try:
        emails_count = supabase.table('user_emails').select('id', count='exact').eq('user_id', user_id).execute()
        summaries_count = supabase.table('email_summaries').select('id', count='exact').eq('user_id', user_id).execute()
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
            'updated_at': datetime.now(timezone.utc).isoformat()
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
            email_unique_id = email_data.get('email_id') or generate_email_id(email_data)
            
            saved_id = save_email_to_supabase(user_id, email_data, email_unique_id)
            if saved_id:
                synced_count += 1
        
        return synced_count
        
    except Exception as e:
        st.error(f"Erreur lors de la synchronisation : {str(e)}")
        return 0