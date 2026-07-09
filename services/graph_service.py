import requests
import msal
from config import Config

class GraphService:
    _msal_app = None

    @classmethod
    def _get_msal_app(cls):
        if not cls._msal_app:
            Config.validate()
            authority = f"https://login.microsoftonline.com/{Config.AZURE_TENANT_ID}"
            cls._msal_app = msal.ConfidentialClientApplication(
                client_id=Config.AZURE_CLIENT_ID,
                client_credential=Config.AZURE_CLIENT_SECRET,
                authority=authority
            )
        return cls._msal_app

    @classmethod
    def get_access_token(cls, scopes=None):
        """Retrieve access token for Graph API."""
        if scopes is None:
            scopes = ["https://graph.microsoft.com/.default"]
        
        app = cls._get_msal_app()
        # Acquire token from cache if valid, otherwise request new one
        result = app.acquire_token_silent(scopes=scopes, account=None)
        if not result:
            result = app.acquire_token_for_client(scopes=scopes)
        
        if "access_token" in result:
            return result["access_token"]
        else:
            error_desc = result.get("error_description", "Unknown error")
            raise Exception(f"Failed to acquire Microsoft Graph token: {error_desc}")

    @classmethod
    def get_headers(cls):
        token = cls.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    @classmethod
    def find_user(cls, username):
        """
        Find user details (ID, userPrincipalName, displayName, mail) by username.
        Accepts: exact UPN, email, or username prefix (e.g., 'truongtd3').
        """
        headers = cls.get_headers()
        
        # 1. Clean username input
        username = username.strip()
        
        # 2. Build filters to find user
        # We search by userPrincipalName, mail, mailNickname, or displayName
        filters = []
        if "@" in username:
            filters.append(f"userPrincipalName eq '{username}'")
            filters.append(f"mail eq '{username}'")
        else:
            filters.append(f"mailNickname eq '{username}'")
            filters.append(f"startsWith(userPrincipalName, '{username}')")
            filters.append(f"displayName eq '{username}'")
            
        filter_str = " or ".join(filters)
        url = f"https://graph.microsoft.com/v1.0/users?$filter={filter_str}&$select=id,userPrincipalName,displayName,mail,mailNickname"
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Graph API Error: {response.status_code} - {response.text}")
            
        users = response.json().get("value", [])
        if not users:
            return None
            
        # Return first matching user
        return users[0]
