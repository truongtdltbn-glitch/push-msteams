import requests
from config import Config

class TeamsBotService:
    @classmethod
    def get_bot_token(cls):
        """
        Get an access token from the Bot Framework token service.
        Supports both Single-Tenant and Multi-Tenant bots.
        """
        errors = []
        tenant = Config.AZURE_TENANT_ID
        
        # 1. Try tenant-specific endpoint (required for Single-Tenant Bots)
        if tenant:
            url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
            data = {
                "client_id": Config.AZURE_CLIENT_ID,
                "client_secret": Config.AZURE_CLIENT_SECRET,
                "grant_type": "client_credentials",
                "scope": "https://api.botframework.com/.default"
            }
            try:
                response = requests.post(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
                if response.status_code == 200:
                    return response.json().get("access_token")
                errors.append(f"Tenant-specific endpoint failed: {response.status_code} - {response.text}")
            except Exception as e:
                errors.append(f"Tenant-specific endpoint connection error: {str(e)}")
                
        # 2. Fallback to multi-tenant Bot Framework directory endpoint
        url = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
        data = {
            "client_id": Config.AZURE_CLIENT_ID,
            "client_secret": Config.AZURE_CLIENT_SECRET,
            "grant_type": "client_credentials",
            "scope": "https://api.botframework.com/.default"
        }
        try:
            response = requests.post(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
            if response.status_code == 200:
                return response.json().get("access_token")
            errors.append(f"Multi-tenant botframework.com endpoint failed: {response.status_code} - {response.text}")
        except Exception as e:
            errors.append(f"Multi-tenant connection error: {str(e)}")
            
        raise Exception(f"Failed to get Bot Framework token:\n" + "\n".join(errors))

    @classmethod
    def send_proactive_message(cls, tenant_id, user_aad_id, message_text):
        """
        Send a proactive 1:1 message to a Teams user using their AAD Object ID.
        """
        # 1. Get Bot Framework Token
        bot_token = cls.get_bot_token()
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json"
        }
        
        # We use the standard MS Teams Bot Framework connector service URL
        service_url = "https://smba.trafficmanager.net/apis"
        
        # 2. Create a 1:1 conversation with the user
        # Note: This will succeed if the user has installed/interacted with the Bot.
        # Otherwise, it might return a 403 Forbidden or 400 bad request.
        create_conv_url = f"{service_url}/v3/conversations"
        bot_account_id = f"28:{Config.TEAMS_BOT_ID}"
        recipient_account_id = f"29:{user_aad_id}"
        
        conv_payload = {
            "bot": {
                "id": bot_account_id
            },
            "members": [
                {
                    "id": recipient_account_id
                }
            ],
            "channelData": {
                "tenant": {
                    "id": tenant_id
                }
            },
            "isGroup": False
        }
        
        response = requests.post(create_conv_url, json=conv_payload, headers=headers)
        if response.status_code not in (200, 201):
            raise Exception(
                f"Failed to create conversation. The user may not have installed the bot. "
                f"Status: {response.status_code}, Error: {response.text}"
            )
            
        conversation_id = response.json().get("id")
        
        # 3. Post the message activity to the conversation
        send_activity_url = f"{service_url}/v3/conversations/{conversation_id}/activities"
        activity_payload = {
            "type": "message",
            "text": message_text
        }
        
        response = requests.post(send_activity_url, json=activity_payload, headers=headers)
        if response.status_code not in (200, 201, 202):
            raise Exception(f"Failed to send message activity. Status: {response.status_code}, Error: {response.text}")
            
        return response.json()
