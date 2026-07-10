import os
from dotenv import load_dotenv

# Load environmental variables from .env file
load_dotenv()

class Config:
    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
    
    SERVICE_ACCOUNT_EMAIL = os.getenv("SERVICE_ACCOUNT_EMAIL")
    SERVICE_ACCOUNT_PASSWORD = os.getenv("SERVICE_ACCOUNT_PASSWORD")
    
    # Admin credentials for web login
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "PGBank@2026devops")

    # API Key for curl / programmatic access (set via environment variable)
    API_KEY = os.getenv("API_KEY", "")
    
    TEAMS_BOT_ID = os.getenv("TEAMS_BOT_ID", AZURE_CLIENT_ID)
    DEFAULT_SENDER_EMAIL = os.getenv("DEFAULT_SENDER_EMAIL")
    
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    @classmethod
    def validate(cls):
        """Validate required configuration values."""
        missing = []
        if not cls.AZURE_TENANT_ID:
            missing.append("AZURE_TENANT_ID")
        if not cls.AZURE_CLIENT_ID:
            missing.append("AZURE_CLIENT_ID")
        if not cls.AZURE_CLIENT_SECRET:
            missing.append("AZURE_CLIENT_SECRET")
        
        if missing:
            raise ValueError(f"Missing required configuration variables: {', '.join(missing)}")
