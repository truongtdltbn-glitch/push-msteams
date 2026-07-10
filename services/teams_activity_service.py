import requests
import logging
from services.graph_service import GraphService
from config import Config

logger = logging.getLogger(__name__)

class TeamsActivityService:
    @classmethod
    def send_activity_notification(cls, user_id, message_text):
        """
        Send a message to a Teams user via 1:1 chat using service account credentials.
        This method uses username + password (Resource Owner Password Credentials flow).
        Requires MFA to be DISABLED for the service account.
        Requires 'Chat.Create' and 'Chat.ReadWrite' permissions.
        """
        logger.info(f"[DEBUG] Sending Teams Chat message to user {user_id}")
        
        try:
            # Get access token using service account credentials
            # Use .default scope to get all consented permissions
            access_token = GraphService.get_access_token_with_credentials(
                username=Config.SERVICE_ACCOUNT_EMAIL,
                password=Config.SERVICE_ACCOUNT_PASSWORD,
                scopes=["https://graph.microsoft.com/.default"]
            )
            logger.info(f"[DEBUG] ✅ Access token acquired for {Config.SERVICE_ACCOUNT_EMAIL}")
        except Exception as e:
            error_msg = f"Failed to get access token: {str(e)}"
            logger.error(f"[DEBUG] ❌ {error_msg}")
            raise Exception(error_msg)
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Step 0: Get service account ID
        logger.info(f"[DEBUG] Step 0: Getting service account ID")
        try:
            service_user = GraphService.find_user(Config.SERVICE_ACCOUNT_EMAIL.split("@")[0])
            if not service_user:
                raise Exception(f"Could not find service account user: {Config.SERVICE_ACCOUNT_EMAIL}")
            service_account_id = service_user.get("id")
            logger.info(f"[DEBUG] Service account ID: {service_account_id}")
        except Exception as e:
            error_msg = f"Failed to find service account: {str(e)}"
            logger.error(f"[DEBUG] ❌ {error_msg}")
            raise Exception(error_msg)
        
        # Step 1: Create a 1:1 chat with service account and target user
        logger.info(f"[DEBUG] Step 1: Creating 1:1 chat with service account and user {user_id}")
        
        create_chat_url = "https://graph.microsoft.com/v1.0/chats"
        chat_payload = {
            "chatType": "oneOnOne",
            "members": [
                {
                    "@odata.type": "#microsoft.graph.aadUserConversationMember",
                    "roles": ["owner"],
                    "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{service_account_id}"
                },
                {
                    "@odata.type": "#microsoft.graph.aadUserConversationMember",
                    "roles": ["owner"],
                    "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{user_id}"
                }
            ]
        }
        
        logger.info(f"[DEBUG] Create chat payload: {chat_payload}")
        
        response = requests.post(create_chat_url, json=chat_payload, headers=headers)
        logger.info(f"[DEBUG] Create chat response status: {response.status_code}")
        logger.info(f"[DEBUG] Create chat response: {response.text}")
        
        if response.status_code not in (201, 200):
            error_msg = f"Failed to create 1:1 chat. Status: {response.status_code}, Error: {response.text}"
            logger.error(f"[DEBUG] ❌ {error_msg}")
            raise Exception(error_msg)
        
        chat_id = response.json().get("id")
        logger.info(f"[DEBUG] ✅ Chat created. ID: {chat_id}")
        
        # Step 2: Send message to the chat
        logger.info(f"[DEBUG] Step 2: Sending message to chat {chat_id}")
        
        send_message_url = f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages"
        message_payload = {
            "body": {
                "content": message_text,
                "contentType": "html"
            }
        }
        
        logger.info(f"[DEBUG] Send message payload: {message_payload}")
        
        response = requests.post(send_message_url, json=message_payload, headers=headers)
        logger.info(f"[DEBUG] Send message response status: {response.status_code}")
        logger.info(f"[DEBUG] Send message response: {response.text}")
        
        if response.status_code not in (201, 200):
            error_msg = f"Failed to send message. Status: {response.status_code}, Error: {response.text}"
            logger.error(f"[DEBUG] ❌ {error_msg}")
            raise Exception(error_msg)
        
        logger.info(f"[DEBUG] ✅ Message sent successfully!")
        return {"status": "success", "message": f"Message sent to user {user_id} in chat {chat_id}"}
