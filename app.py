import logging
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from functools import wraps
from config import Config
from services.graph_service import GraphService
from services.teams_activity_service import TeamsActivityService
import os


# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure session
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = False  # Allow HTTP in development
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JS access to session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = 5 * 60  # 5 minutes (300 seconds)

# Admin credentials from config
ADMIN_USERNAME = Config.ADMIN_USERNAME
ADMIN_PASSWORD = Config.ADMIN_PASSWORD

# Authentication decorator — session-based (web UI)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Authentication decorator — API key-based (curl / programmatic)
def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key", "").strip()
        configured_key = Config.API_KEY
        if not configured_key:
            return jsonify({"error": "API key authentication is not configured on this server."}), 503
        if not api_key:
            return jsonify({"error": "Missing X-API-Key header."}), 401
        if api_key != configured_key:
            logger.warning("Invalid API key used in request")
            return jsonify({"error": "Invalid API key."}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route("/login")
def login_page():
    """Serve the Login Page."""
    if 'user' in session:
        return redirect(url_for('index'))
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def login():
    """API endpoint for user login."""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({
            "success": False,
            "error": "Missing username or password"
        }), 400
    
    # Check credentials
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['user'] = username
        session.permanent = True
        logger.info(f"User {username} logged in successfully")
        return jsonify({
            "success": True,
            "message": f"Welcome, {username}!"
        }), 200
    else:
        logger.warning(f"Failed login attempt for user {username}")
        return jsonify({
            "success": False,
            "error": "Invalid username or password"
        }), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    """API endpoint for user logout."""
    username = session.get('user', 'Unknown')
    session.clear()
    logger.info(f"User {username} logged out")
    return jsonify({
        "success": True,
        "message": "Logged out successfully"
    }), 200

@app.route("/")
def index():
    """Serve the Web Dashboard."""
    if 'user' not in session:
        return redirect(url_for('login_page'))
    return render_template("index.html")

@app.route("/api/config", methods=["GET"])
@login_required
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
@login_required
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
    """Send a Teams notification. Accepts session auth (web UI) or username+password in body (legacy curl)."""
    data = request.get_json() or {}

    # --- Authentication ---
    if 'user' in session:
        # Web UI: already authenticated via session, no credentials needed
        pass
    else:
        # Legacy / curl: validate username + password in request body
        req_user = data.get("username", "").strip()
        req_pass = data.get("password", "")
        if not req_user or not req_pass:
            return jsonify({"error": "Missing username or password"}), 400
        if req_user != ADMIN_USERNAME or req_pass != ADMIN_PASSWORD:
            logger.warning("Failed send attempt with invalid credentials")
            return jsonify({"success": False, "error": "Invalid username or password"}), 401

    # target_user: field from web form or curl body
    target_user = data.get("target_user") or data.get("username", "").strip()
    message = data.get("message")

    if not target_user:
        return jsonify({"error": "Missing required field: 'target_user'"}), 400
    if not message:
        return jsonify({"error": "Missing required field: 'message'"}), 400

    try:
        logger.info(f"Looking up user: {target_user}")
        user = GraphService.find_user(target_user)
        if not user:
            return jsonify({
                "success": False,
                "error": f"User '{target_user}' was not found in Microsoft Entra ID."
            }), 404

        user_id = user.get("id")
        user_upn = user.get("userPrincipalName")
        display_name = user.get("displayName", target_user)

        recipient_info = {
            "username": target_user,
            "displayName": display_name,
            "userPrincipalName": user_upn,
            "id": user_id
        }
        logger.info(f"Found user: {display_name} (UPN: {user_upn}, ID: {user_id})")

        logger.info(f"Sending Teams notification to: {user_upn}")
        TeamsActivityService.send_activity_notification(
            user_id=user_id,
            message_text=message
        )

        return jsonify({
            "success": True,
            "recipient": recipient_info,
            "message": message,
            "status": "Notification sent successfully via Teams Activity API"
        })
        
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "troubleshooting": "Ensure the bot is installed in Teams and has proper Azure AD permissions."
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

# ---------------------------------------------------------------------------
# Public API v1 — API Key authentication (no session / no login required)
# Use header:  X-API-Key: <your_api_key>
# ---------------------------------------------------------------------------

@app.route("/api/v1/user/<username>", methods=["GET"])
@api_key_required
def api_v1_find_user(username):
    """Look up a user in Entra ID using API key authentication."""
    try:
        user = GraphService.find_user(username)
        if not user:
            return jsonify({"error": f"User '{username}' not found in Microsoft Directory."}), 404
        return jsonify(user)
    except Exception as e:
        logger.error(f"[API v1] Error looking up user: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/send", methods=["POST"])
@api_key_required
def api_v1_send_notification():
    """Send a private Teams notification using API key authentication."""
    data = request.get_json() or {}
    target_user = data.get("target_user")
    message = data.get("message")

    if not target_user:
        return jsonify({"error": "Missing required field: 'target_user'"}), 400
    if not message:
        return jsonify({"error": "Missing required field: 'message'"}), 400

    try:
        user = GraphService.find_user(target_user)
        if not user:
            return jsonify({
                "success": False,
                "error": f"User '{target_user}' was not found in Microsoft Entra ID."
            }), 404

        user_id = user.get("id")
        user_upn = user.get("userPrincipalName")
        display_name = user.get("displayName", target_user)

        logger.info(f"[API v1] Sending Teams notification to: {user_upn}")
        TeamsActivityService.send_activity_notification(
            user_id=user_id,
            message_text=message
        )

        return jsonify({
            "success": True,
            "recipient": {
                "username": target_user,
                "displayName": display_name,
                "userPrincipalName": user_upn,
                "id": user_id
            },
            "message": message,
            "status": "Notification sent successfully via Teams Activity API"
        })

    except Exception as e:
        logger.error(f"[API v1] Failed to send message: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "troubleshooting": "Ensure the bot is installed in Teams and has proper Azure AD permissions."
        }), 500


# ---------------------------------------------------------------------------
# API Documentation page — public, no authentication required
# ---------------------------------------------------------------------------

@app.route("/api-docs")
def api_docs():
    """Render the public API documentation page."""
    base_url = request.host_url.rstrip("/")
    return render_template("api_docs.html", base_url=base_url)


if __name__ == "__main__":
    logger.info(f"Starting Notification Service on port {Config.FLASK_PORT}...")
    app.run(host="0.0.0.0", port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)
