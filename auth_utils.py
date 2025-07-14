import streamlit as st
import hashlib
import imaplib
from cryptography.fernet import Fernet
from supabase import create_client, Client
import json
import uuid
from datetime import datetime
from config import SUPABASE_URL, SUPABASE_KEY

# Client Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Clé de chiffrement fixe (en production, utilisez une clé d'environnement)
ENCRYPTION_KEY = b'P8kvq1bU8CE36_oks9Tfa9EFpWn1b-AvXfqFADB0LM8='  # Générez votre propre clé

def encrypt_credentials(email, password):
    """Chiffre les identifiants utilisateur"""
    f = Fernet(ENCRYPTION_KEY)
    credentials = json.dumps({"email": email, "password": password})
    encrypted_credentials = f.encrypt(credentials.encode())
    return encrypted_credentials.decode('utf-8')

def decrypt_credentials(encrypted_credentials):
    """Déchiffre les identifiants utilisateur"""
    f = Fernet(ENCRYPTION_KEY)
    try:
        decrypted = f.decrypt(encrypted_credentials.encode())
        return json.loads(decrypted.decode())
    except Exception as e:
        st.error(f"Erreur de déchiffrement : {str(e)}")
        return None

def test_gmail_connection(email, password):
    """Teste la connexion Gmail"""
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(email, password)
        imap.logout()
        return True
    except Exception as e:
        st.error(f"Erreur de connexion Gmail : {str(e)}")
        return False

def save_user_to_supabase(email, password):
    """Sauvegarde l'utilisateur dans Supabase"""
    try:
        # Chiffrer les identifiants
        encrypted_creds = encrypt_credentials(email, password)
        
        # Essayer d'insérer l'utilisateur
        user_data = {
            "id": str(uuid.uuid4()),
            "email": email,
            "encrypted_credentials": encrypted_creds,
            "last_login": datetime.now().isoformat()
        }
        
        # Vérifier si l'utilisateur existe déjà
        existing_user = supabase.table("users").select("*").eq("email", email).execute()
        
        if existing_user.data:
            # Mettre à jour l'utilisateur existant
            result = supabase.table("users").update({
                "encrypted_credentials": encrypted_creds,
                "last_login": datetime.now().isoformat()
            }).eq("email", email).execute()
            return existing_user.data[0]["id"]
        else:
            # Créer un nouvel utilisateur
            result = supabase.table("users").insert(user_data).execute()
            return result.data[0]["id"]
            
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde : {str(e)}")
        return None

def get_user_from_supabase(email):
    """Récupère l'utilisateur depuis Supabase"""
    try:
        result = supabase.table("users").select("*").eq("email", email).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        st.error(f"Erreur lors de la récupération : {str(e)}")
        return None

def authenticate_user(email, password):
    """Authentifie un utilisateur"""
    # Tester la connexion Gmail
    if not test_gmail_connection(email, password):
        return None
    
    # Sauvegarder dans Supabase
    user_id = save_user_to_supabase(email, password)
    return user_id

def login_form():
    """Affiche le formulaire de connexion"""
    st.title("🔐 Connexion à Assistant Mail")
    
    with st.form("login_form"):
        st.markdown("### Connectez-vous avec votre compte Gmail")
        email = st.text_input("📧 Adresse email Gmail", placeholder="votre.email@gmail.com")
        password = st.text_input("🔒 Mot de passe", type="password", placeholder="Votre mot de passe Gmail")
        
        st.markdown("---")
        st.markdown("**⚠️ Sécurité :**")
        st.markdown("- Vos identifiants sont chiffrés et stockés de manière sécurisée")
        st.markdown("- Utilisez un [mot de passe d'application](https://support.google.com/accounts/answer/185833) pour plus de sécurité")
        st.markdown("- Activez la [vérification en 2 étapes](https://support.google.com/accounts/answer/185839)")
        
        submit = st.form_submit_button("🚀 Se connecter")
        
        if submit:
            if email and password:
                with st.spinner("Connexion en cours..."):
                    user_id = authenticate_user(email, password)
                    if user_id:
                        st.session_state['authenticated'] = True
                        st.session_state['user_id'] = user_id
                        st.session_state['user_email'] = email
                        st.success("✅ Connexion réussie !")
                        st.rerun()
            else:
                st.error("Veuillez remplir tous les champs")

def logout():
    """Déconnecte l'utilisateur"""
    for key in ['authenticated', 'user_id', 'user_email']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def is_authenticated():
    """Vérifie si l'utilisateur est authentifié"""
    return st.session_state.get('authenticated', False)

def get_current_user_credentials():
    """Récupère les identifiants de l'utilisateur connecté"""
    if not is_authenticated():
        return None
    
    user_email = st.session_state.get('user_email')
    if user_email:
        user = get_user_from_supabase(user_email)
        if user:
            return decrypt_credentials(user['encrypted_credentials'])
    return None