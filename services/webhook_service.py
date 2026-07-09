import requests

class WebhookService:
    @classmethod
    def send_webhook_message(cls, webhook_url, message_text):
        """
        Send a notification to a Microsoft Teams Channel using an Incoming Webhook.
        Does not require any Azure AD / Graph API permissions.
        """
        if not webhook_url:
            raise ValueError("Teams Webhook URL is required for this channel.")
            
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "medium",
                                "weight": "bolder",
                                "text": "System Alert Notification"
                            },
                            {
                                "type": "TextBlock",
                                "text": message_text,
                                "wrap": True
                            }
                        ],
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "version": "1.4"
                    }
                }
            ]
        }
        
        response = requests.post(webhook_url, json=payload)
        if response.status_code != 200:
            # Fallback to simple text payload if Adaptive Card fails or is rejected
            simple_payload = {"text": message_text}
            response = requests.post(webhook_url, json=simple_payload)
            
        if response.status_code != 200:
            raise Exception(f"Failed to post to Teams Webhook. Status: {response.status_code}, Response: {response.text}")
            
        return {"status": "success", "message": "Notification sent successfully via Webhook."}
