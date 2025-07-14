import os
from dotenv import load_dotenv

# Chargement des variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Configuration OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configuration Gmail
GMAIL_EMAIL = os.getenv("EMAIL_ADDRESS")
GMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Validation des variables d'environnement obligatoires
required_vars = ["SUPABASE_URL", "SUPABASE_KEY", "OPENAI_API_KEY", "EMAIL_ADDRESS", "EMAIL_PASSWORD"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    raise ValueError(f"Variables d'environnement manquantes : {', '.join(missing_vars)}")

