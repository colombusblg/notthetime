import streamlit as st
import os
from dotenv import load_dotenv

# Chargement des variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration Supabase - Utiliser st.secrets pour Streamlit Cloud
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

# Configuration OpenAI
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

# Validation des variables d'environnement obligatoires
required_vars = {
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_KEY": SUPABASE_KEY,
    "OPENAI_API_KEY": OPENAI_API_KEY
}

missing_vars = [var for var, value in required_vars.items() if not value]

if missing_vars:
    raise ValueError(f"Variables d'environnement manquantes : {', '.join(missing_vars)}")

# Note: Les identifiants Gmail sont maintenant gérés par utilisateur via l'authentification
# et stockés de manière chiffrée dans Supabase