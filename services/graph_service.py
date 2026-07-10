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
        # Always acquire fresh token (don't use cache)
        result = app.acquire_token_for_client(scopes=scopes)
        
        if "access_token" in result:
            return result["access_token"]
        else:
            error_desc = result.get("error_description", "Unknown error")
            raise Exception(f"Failed to acquire Microsoft Graph token: {error_desc}")

    @classmethod
    def get_access_token_with_credentials(cls, username, password, scopes=None):
        """
        Retrieve access token using Resource Owner Password Credentials flow.
        Used for service account (bot) authentication.
        NOTE: Requires MFA to be disabled for the user account.
        """
        if scopes is None:
            scopes = ["https://graph.microsoft.com/.default"]
        
        token_url = f"https://login.microsoftonline.com/{Config.AZURE_TENANT_ID}/oauth2/v2.0/token"
        
        payload = {
            'client_id': Config.AZURE_CLIENT_ID,
            'client_secret': Config.AZURE_CLIENT_SECRET,
            'grant_type': 'password',
            'scope': ' '.join(scopes),
            'username': username,
            'password': password,
        }
        
        response = requests.post(token_url, data=payload)
        response_json = response.json()
        
        if 'access_token' in response_json:
            return response_json['access_token']
        else:
            error_desc = response_json.get('error_description', 'Unknown error')
            raise Exception(f"Failed to acquire token with credentials: {error_desc}")

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
