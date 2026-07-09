import requests
from services.graph_service import GraphService

class TeamsActivityService:
    @classmethod
    def send_activity_notification(cls, user_id, message_text):
        """
        Send an Activity Feed notification to a Teams user.
        Requires 'TeamsActivity.Send' or 'TeamsActivity.Send.User' application permission.
        """
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}/teamwork/sendActivityNotification"
        headers = GraphService.get_headers()
        
        payload = {
            "topic": {
                "source": "entityUrl",
                "value": f"https://graph.microsoft.com/v1.0/users/{user_id}"
            },
            "activityType": "systemDefault",
            "previewText": {
                "content": "System Notification"
            },
            "templateParameters": [
                {
                    "name": "systemDefaultText",
                    "value": message_text
                }
            ],
            "recipient": {
                "@odata.type": "microsoft.graph.aadUserNotificationRecipient",
                "userId": user_id
            }
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        # A successful response is 204 No Content
        if response.status_code not in (202, 204):
            raise Exception(f"Failed to send Teams Activity notification. Status: {response.status_code}, Error: {response.text}")
            
        return {"status": "success", "message": f"Teams Activity Notification sent to user {user_id}"}
