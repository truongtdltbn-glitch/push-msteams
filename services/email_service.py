import requests
from services.graph_service import GraphService
from config import Config

class EmailService:
    @classmethod
    def send_email(cls, recipient_email, subject, body_content, sender_email=None):
        """
        Send an email to a user via MS Graph sendMail API.
        Requires 'Mail.Send' application permission.
        """
        # Determine sender: prioritize input, fallback to Config default, otherwise fallback to recipient themselves
        sender = sender_email or Config.DEFAULT_SENDER_EMAIL
        if not sender:
            # Fallback to sending to themselves (useful for tests if only one mailbox is known)
            sender = recipient_email
            
        url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
        headers = GraphService.get_headers()
        
        payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body_content
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": recipient_email
                        }
                    }
                ]
            },
            "saveToSentItems": "false"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 202:
            raise Exception(f"Failed to send email via MS Graph. Status: {response.status_code}, Error: {response.text}")
            
        return {"status": "success", "message": f"Email sent successfully from {sender} to {recipient_email}"}
