import logging
from flask import Flask, request, jsonify, render_template
from config import Config
from services.graph_service import GraphService
from services.teams_bot_service import TeamsBotService
from services.teams_activity_service import TeamsActivityService
from services.email_service import EmailService
from services.webhook_service import WebhookService


# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/")
def index():
    """Serve the Web Dashboard."""
    return render_template("index.html")

@app.route("/api/config", methods=["GET"])
def get_config_status():
    """Return configured status (masking credentials for safety)."""
    try:
        Config.validate()
        status = "Configured"
    except Exception as e:
        status = f"Error: {str(e)}"
        
    return jsonify({
        "status": status,
        "tenant_id": Config.AZURE_TENANT_ID,
        "client_id": Config.AZURE_CLIENT_ID,
        "bot_id": Config.TEAMS_BOT_ID,
        "default_sender": Config.DEFAULT_SENDER_EMAIL or "Not Configured"
    })

@app.route("/api/user/<username>", methods=["GET"])
def find_user(username):
    """API endpoint to search for a user in Entra ID (Azure AD)."""
    try:
        user = GraphService.find_user(username)
        if not user:
            return jsonify({"error": f"User '{username}' not found in Microsoft Directory."}), 404
        return jsonify(user)
    except Exception as e:
        logger.error(f"Error looking up user: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/api/send", methods=["POST"])
def send_notification():
    """API endpoint to send a notification to a specific user."""
    data = request.get_json() or {}
    
    username = data.get("username")
    message = data.get("message")
    channel = data.get("channel", "teams_bot") # teams_bot, email, teams_activity, webhook
    
    if not message:
        return jsonify({"error": "Missing required field: 'message'"}), 400
    if channel != "webhook" and not username:
        return jsonify({"error": "Missing required field: 'username' for this channel."}), 400
        
    try:
        result = {}
        recipient_info = None

        # 1. If not a generic webhook, look up the user
        if channel != "webhook":
            logger.info(f"Looking up user: {username}")
            user = GraphService.find_user(username)
            if not user:
                return jsonify({
                    "success": False,
                    "error": f"User '{username}' was not found in Microsoft Entra ID. Please ensure the user exists."
                }), 404
                
            user_id = user.get("id")
            user_upn = user.get("userPrincipalName")
            user_email = user.get("mail") or user_upn
            display_name = user.get("displayName", username)
            
            recipient_info = {
                "username": username,
                "displayName": display_name,
                "userPrincipalName": user_upn,
                "email": user_email,
                "id": user_id
            }
            logger.info(f"Found user: {display_name} (UPN: {user_upn}, ID: {user_id})")
        
        # 2. Route message to selected channel
        if channel == "teams_bot":
            logger.info(f"Sending Teams Bot message to: {user_upn}")
            bot_result = TeamsBotService.send_proactive_message(
                tenant_id=Config.AZURE_TENANT_ID,
                user_aad_id=user_id,
                message_text=message
            )
            result = {
                "channel": "teams_bot",
                "details": bot_result,
                "status": "Message sent successfully"
            }
            
        elif channel == "teams_activity":
            logger.info(f"Sending Teams Activity Feed notification to: {user_upn}")
            activity_result = TeamsActivityService.send_activity_notification(
                user_id=user_id,
                message_text=message
            )
            result = {
                "channel": "teams_activity",
                "details": activity_result,
                "status": "Activity Feed notification sent successfully"
            }
            
        elif channel == "email":
            logger.info(f"Sending email notification to: {user_email}")
            subject = data.get("subject", "New Notification from System")
            sender = data.get("sender_email") # Optional custom sender override
            email_result = EmailService.send_email(
                recipient_email=user_email,
                subject=subject,
                body_content=f"<div style='font-family: sans-serif; padding: 20px; border: 1px solid #eaeaea; border-radius: 5px;'>"
                             f"<h2>New System Notification</h2>"
                             f"<p>{message}</p>"
                             f"</div>",
                sender_email=sender
            )
            result = {
                "channel": "email",
                "details": email_result,
                "status": "Email sent successfully"
            }
            
        elif channel == "webhook":
            logger.info("Sending message via Teams Webhook")
            webhook_url = data.get("webhook_url")
            import os
            if not webhook_url:
                webhook_url = os.getenv("TEAMS_WEBHOOK_URL")
            if not webhook_url:
                return jsonify({
                    "success": False,
                    "error": "No Webhook URL provided. Please supply 'webhook_url' in request payload or configure TEAMS_WEBHOOK_URL."
                }), 400
                
            webhook_result = WebhookService.send_webhook_message(webhook_url, message)
            result = {
                "channel": "webhook",
                "details": webhook_result,
                "status": "Webhook message sent successfully"
            }
            recipient_info = {
                "username": "Teams Channel Webhook",
                "displayName": "Teams Channel",
                "email": "N/A",
                "id": "N/A"
            }
        else:
            return jsonify({"error": f"Unknown notification channel '{channel}'"}), 400
            
        return jsonify({
            "success": True,
            "recipient": recipient_info,
            "delivery": result
        })
        
    except Exception as e:
        logger.error(f"Failed to send notification via {channel}: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "troubleshooting": (
                "Please double-check Azure AD App Registration permissions in the Azure Portal. "
                "Ensure required permissions (e.g., User.Read.All, TeamsActivity.Send, Mail.Send) "
                "are consented by an Admin."
            )
        }), 500

# --- Dynamic Teams Manifest Generator ---
import io
import zipfile
import base64
import json
from flask import send_file

OUTLINE_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH"
    "5gcIERIZGzOnNAAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkQu4hAAAAdklEQVRYw+2W0QqAMAxD72D//8/dBx9E"
    "EJnOtTk3EDp5a1qbpEDwRyVSSnsiKgB1r5XWuB3E5p5M5oCI3oUeEZGv6EsEEX1d13Vd13Vd13Vd99/Xk5jZ+562Dpx52x4A8LzN6QHA"
    "83YnANy390vE2T2ZzAEAvtP6K/VvEfkD928v6t8eF/z2Ag161rG611bFAAAAAElFTkSuQmCC"
)

COLOR_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAAduf34AAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH"
    "5gcIERIZeM5aHAAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkQu4hAAABmklEQVR42u3VwQ3CQAwEQccJ6IAeqIEe"
    "oiE6IAt1QDfkhuMEiJAilpU8PTt692z+K/b+fBQA4KspQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIk"
    "QAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIk"
    "QAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIk"
    "QAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIk"
    "QAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIkQAIk"
    "QAIkQAIkQAIkQAJkhR8AAP//AwAn/WpWphz4AAAAAElFTkSuQmCC"
)

@app.route("/api/manifest/download", methods=["GET"])
def download_manifest():
    """Generate and return a Teams App Manifest zip file dynamically."""
    try:
        Config.validate()
        
        # Create manifest JSON contents
        manifest = {
            "$schema": "https://developer.microsoft.com/en-us/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
            "manifestVersion": "1.16",
            "version": "1.0.0",
            "id": Config.AZURE_CLIENT_ID,
            "packageName": "com.pushchat.notify",
            "developer": {
                "name": "PushChat Admin",
                "websiteUrl": "https://localhost:5000",
                "privacyUrl": "https://localhost:5000/privacy",
                "termsOfUseUrl": "https://localhost:5000/terms"
            },
            "icons": {
                "color": "color.png",
                "outline": "outline.png"
            },
            "name": {
                "short": "Push-Chat",
                "full": "Push-Chat Notification Bot"
            },
            "description": {
                "short": "Direct private notifications.",
                "full": "System bot that delivers direct notification alerts and messages to users."
            },
            "accentColor": "#6366F1",
            "bots": [
                {
                    "botId": Config.AZURE_CLIENT_ID,
                    "scopes": ["personal"],
                    "supportsFiles": False,
                    "isNotificationOnly": True
                }
            ],
            "permissions": ["identity", "messageTeamMembers"],
            "validDomains": [],
            "webApplicationInfo": {
                "id": Config.AZURE_CLIENT_ID,
                "resource": f"api://localhost:5000/{Config.AZURE_CLIENT_ID}"
            }
        }
        
        # Build Zip in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))
            zip_file.writestr("outline.png", base64.b64decode(OUTLINE_PNG_BASE64))
            zip_file.writestr("color.png", base64.b64decode(COLOR_PNG_BASE64))
            
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="teams_manifest.zip"
        )
    except Exception as e:
        logger.error(f"Failed to generate manifest: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to generate manifest: {str(e)}"}), 500

if __name__ == "__main__":
    logger.info(f"Starting Notification Service on port {Config.FLASK_PORT}...")
    app.run(host="0.0.0.0", port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)
