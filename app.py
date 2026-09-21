from flask import Flask, request, jsonify
import requests
import logging
from services.graph_service import GraphService
from services.teams_activity_service import TeamsActivityService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ===== Webhook mapping =====
WEBHOOKS = {
    "noc": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/e799a13acca74916b316035bd6081fa5/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=w8ao_4_u_rJpBkItqGYsmUnSazrwD14fRC4SyRKxH44",
    "t24-chat": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/e799a13acca74916b316035bd6081fa5/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=w8ao_4_u_rJpBkItqGYsmUnSazrwD14fRC4SyRKxH44",
    "eod": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/852181e9134549ba912a03acd561f564/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=4nmyujfyyiaYAgmFIZNcGZQ2IB8_xa-zUaR9oOW5HlE",
    "t24-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/61f7d33940e0498bad5bce03166942d9/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=CDhhVrK7jeWvlGro3cTEslZcyaHPwX3MHjztQ_SWsEg",
    "test": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/730f00b50bfe41fdbb8ef9db83526329/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=oFLs3ebEWQrx7Dju_4bSEF4jNuu8Y15cvfLe8LQsZ5A",
    "ibft-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/ed44689d54fa4657b440785676dca043/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=EpuuhlwVRzevRXpWv8xsMb041lNd3dTxxyEphNORNq0",
    "card-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/8d6cba3b25c64e9d91410179f00d7e10/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=sllGlnF1dlI8-QXjCdNR0SQ2SPiBYk73hN3ocy709Wg",
    "windows-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/d3f82e1553d14464aded6200006df1ed/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=Ari9l7Sy2z9oCCq4p_vjoBSqD2Qbb1C3rQH3d_-kohk",
    "grafana-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/78321822916845bb9017b1abf4aed664/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=tMvvsGjENx2jVUkEMT_IpSSdqRoYYvqroBIapniM_PI",
    "report-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/f2681ab8c71642c195041d632ee764fc/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=ISPdPrik0YHUk012TTU8Ya8UHP4Lc72JNS2_CLp8lGY",
    "activemq-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/e84873f06c9f44be9f83ee9b00ce9d74/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=UIt6HpEfSpGGhBxNVTrCZ-g0ej-uxJQ4VVUQAk15RIE",
    "il4-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/695b3ffb166f445490ce2ae0e5147f2a/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=2rU6YL1tTWxFRMM1gOCJTTMhiqCkxV1xlgkqVPfDv8k",
    "database-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/747dfb95ff0748a28fa4081c1fd2b948/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=z2L_CpEahgm963qn8gEBvbJHUTERGSfr0HfvVOe0yk4",
    "uat-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/39e82da36dda406eab6fd83c26f6a9c5/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=zVM9oZ5MU5PhLAOdVWmVhPxFAXfmP7kF6epbZLrTc6I",
    "retail-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/c2959d9da3d54fdfb3a8307e644fd995/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=3H6Kvu3DiLEtcVh5BGhI-dNZaZQkMvEV8O7fgIibmnk",
    "corp-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/f97a462cbeb6492eb1a54a7630c5d0e8/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=zw_vtbCRGd3NYPgILPiOu96mDL48Y4899ikv4lQ5D0k",
    "aix-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/8b5b991f1a9f4b20b45347a3a8df195d/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=43MjPRU64FrVxmmGaqZ3k8UJjQx6plJzC9VH_bwHsD8",
    "ott-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/0603c6034f384881be15811889ae6cb8/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=JOsGwSuNJcM8BkEmjgkN5kHgj3rwGgVNJR_MJ6nh6ms",
    "camera-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/fc22163d4e3a44cdbc642aad1f252efe/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=KES9O4sJ9JQ7UFmYoR5cTldvuosGP3WjoLXgjBUwcN4",
    "mobile-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/9b2bde6a6d33497fac1739ceee0951d1/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=d4usD1LlHcMI7mKk1ObK_OtWEL_nQVeEdsL7Nl-3Alg",
    "api-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/045e656da3c24b80bc96b6d931786148/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=NhNmNjibGiRjGUMjTyXSiBSzk7I409bXJo2M7LjnRMY",
    "retail-chat": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/dde6210556764ad189a2fa41d007543b/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=Qt0tvPIToITWNRk54uN91dp0j4b18X6Scjk5XIaAY3M",
    "kondor-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/e6ef9b8da9d84afc9e378b48ebce0067/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=M8am_rYMXnH2vg4_VDJR5D7n-bcdlDSaJcAWpdat-Ls",
    "kubelet-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/cf3e384e35854fee9068eb100fe8230b/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=_m-NiI94RaUTucVGzF41tF__bGWwi_4BCDMs2zUWPbE",
    "vnpay-chat": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/dde6210556764ad189a2fa41d007543b/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=Qt0tvPIToITWNRk54uN91dp0j4b18X6Scjk5XIaAY3M",
    "esb-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/19/workflows/a8b05568223541de8ffa5bdb5f677dd8/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=1lhOSwxUaE5A8LjOWdOMBd4jbJOrhYyIwqQQeE0wl7k",
    "mcc-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/06/workflows/80e45273d7e24161ac2310bf6b4acaac/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=-Emw2jJlp4tlsdtNEXiMHCq2gJ_-6DXD8XrbkrduZV8",
    "linux-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/78321822916845bb9017b1abf4aed664/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=tMvvsGjENx2jVUkEMT_IpSSdqRoYYvqroBIapniM_PI",
    "esign-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/26/workflows/91e7c2b8702246fe8c81be9b68bf491b/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=AWGNq51NHm5Gh3gA7YfL1LceRW6Eaparxc7PgZZr3CI",
    "ocp-channel": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/cf3e384e35854fee9068eb100fe8230b/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=_m-NiI94RaUTucVGzF41tF__bGWwi_4BCDMs2zUWPbE",
    "dwh-chat": "https://defaultc756d8b934af408bb1e49f084cbcc0.23.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/08/workflows/adb772994d6c468d9eccf572641aaf2a/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=Qemu2MYBMofBASIoDWs_DzH60p2LeSS5FAjiulujDds"
}

# ===== Alert / Job level config =====
LEVEL_MAP = {
    "WARNING":   {"icon": "⚠️", "label": "WARNING",   "color": "warning"},
    "CRITICAL":  {"icon": "🚨", "label": "CRITICAL",  "color": "attention"},
    "RESOLVED":  {"icon": "✅", "label": "RESOLVED",  "color": "good"},
    "RUNNING":   {"icon": "🔄", "label": "RUNNING",   "color": "accent"},
    "COMPLETED": {"icon": "🏁", "label": "COMPLETED", "color": "good"},
    "FAILED":    {"icon": "❌", "label": "FAILED",    "color": "attention"}
}

# ===== Build Adaptive Card =====
def build_card(p):
    type_key = p.get("type", "").upper()
    meta = LEVEL_MAP.get(type_key, {"icon": "ℹ️", "label": type_key, "color": "default"})

    # Normalize detail -> list
    detail_raw = p.get("detail", [])
    if isinstance(detail_raw, str):
        detail_lines = [detail_raw]
    elif isinstance(detail_raw, list):
        detail_lines = [str(x) for x in detail_raw if x]
    else:
        detail_lines = [str(detail_raw)]

    # Build detail facts or text blocks
    # We'll use a simple list of text blocks for details to maintain flexibility
    detail_blocks = []
    for line in detail_lines:
        detail_blocks.append({
            "type": "TextBlock",
            "text": f"- {line}",
            "wrap": True,
            "isSubtle": True,
            "size": "Small",
            "spacing": "None"
        })

    return {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "msteams": {"width": "Full"},
                "body": [
                    {
                        "type": "Container",
                        "style": meta["color"],
                        "bleed": True,
                        "items": [
                            {
                                "type": "ColumnSet",
                                "columns": [
                                    {
                                        "type": "Column",
                                        "width": "auto",
                                        "verticalContentAlignment": "Center",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": meta["icon"],
                                                "size": "ExtraLarge"
                                            }
                                        ]
                                    },
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": p.get("name", "Notification"),
                                                "weight": "Bolder",
                                                "size": "Large",
                                                "wrap": True
                                            },
                                            {
                                                "type": "TextBlock",
                                                "spacing": "None",
                                                "text": meta["label"],
                                                "isSubtle": True,
                                                "weight": "Bolder"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "type": "Container",
                        "spacing": "Medium",
                        "items": [
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "⏰ Thời gian:", "value": p.get("time", "N/A")},
                                    {"title": "🚦 Trạng thái:", "value": f"{meta['icon']} {meta['label']}"}
                                ]
                            },
                            {
                                "type": "TextBlock",
                                "text": f"❌ **Mô tả lỗi:**\n{p.get('error', 'N/A')}",
                                "wrap": True,
                                "spacing": "Medium"
                            },
                            {
                                "type": "Container",
                                "spacing": "Medium",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "📋 **Chi tiết hệ thống:**",
                                        "weight": "Bolder",
                                        "wrap": True
                                    },
                                    *detail_blocks
                                ]
                            },
                            {
                                "type": "TextBlock",
                                "text": f"🛠 **Hành động đề xuất:** {p.get('action', 'N/A')}",
                                "wrap": True,
                                "weight": "Bolder",
                                "color": "Accent",
                                "spacing": "Large"
                            }
                        ]
                    }
                ],
                "actions": [
                    {
                        "type": "Action.OpenUrl",
                        "title": "📊 Xem trên Grafana",
                        "url": p.get("grafana", "#"),
                        "style": "positive"
                    }
                ]
            }
        }]
    }

# ===== Build HTML (For User Chat) =====
def build_html(p):
    type_key = p.get("type", "").upper()
    meta = LEVEL_MAP.get(type_key, {"icon": "ℹ️", "label": type_key, "color": "default"})
    
    # Map adaptive card colors to HEX for HTML
    color_hex = {
        "warning": "#FFB900",    # Yellow
        "attention": "#E81123",  # Red
        "good": "#107C10",       # Green
        "accent": "#0078D4",     # Blue
        "default": "#000000"     # Black
    }.get(meta["color"], "#000000")

    # Normalize detail
    detail_raw = p.get("detail", [])
    if isinstance(detail_raw, str):
        detail_lines = [detail_raw]
    elif isinstance(detail_raw, list):
        detail_lines = [str(x) for x in detail_raw if x]
    else:
        detail_lines = [str(detail_raw)]
        
    li_html = "".join([f"<li>{line}</li>" for line in detail_lines])
    
    html = f"""
    <div style="font-family: sans-serif; font-size: 12px; line-height: 1.2; max-width: 350px;">
        <h3 style="margin: 0 0 2px 0; color: {color_hex}; font-size: 14px;">{meta['icon']} {p.get('name', 'Notification')}</h3>
        <p style="margin: 0 0 4px 0;"><strong>{meta['label']}</strong></p>
        <hr style="margin: 2px 0; border: 0; border-top: 1px solid #eee;">
        
        <p style="margin: 4px 0;"><strong>⏰ Thời gian:</strong> {p.get('time', 'N/A')}<br>
        <strong>🚦 Trạng thái:</strong> {meta['icon']} {meta['label']}</p>
        <p style="margin: 4px 0;">❌ <strong>Mô tả lỗi:</strong> {p.get('error', 'N/A')}</p>
        
        <p style="margin: 4px 0;">📋 <strong>Chi tiết hệ thống:</strong></p>
        <ul style="font-size: 11px; color: #605E5C; margin: 0 0 4px 0; padding-left: 20px;">{li_html}</ul>
        
        <p style="color: #0078D4; margin: 4px 0;">🛠 <strong>Hành động đề xuất:</strong> <b>{p.get('action', 'N/A')}</b></p>
        <hr style="margin: 2px 0; border: 0; border-top: 1px solid #eee;">
        <p style="margin: 4px 0;"><a href="{p.get('grafana', '#')}">📊 Xem trên Grafana</a></p>
    </div>
    """
    return html

# ===== Health check =====
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# ===== Push endpoint (Group + Cá nhân) =====
@app.route("/<target>", methods=["POST"])
def push(target):
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "invalid json"}), 400

    try:
        card = build_card(payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    # 1. Nếu là Group Channel
    if target in WEBHOOKS:
        r = requests.post(WEBHOOKS[target], json=card, timeout=10)
        if r.status_code >= 300:
            return jsonify({"error": "push failed", "detail": r.text}), 500
        return jsonify({"status": "ok"})
        
    # 2. Nếu không có trong Group -> Tự động tìm gửi Cá nhân
    else:
        try:
            html_content = build_html(payload)
            logger.info(f"Target '{target}' not in webhooks. Looking up as user.")
            
            user = GraphService.find_user(target)
            if not user:
                return jsonify({"error": f"Target '{target}' is not a valid channel and not found as a User in Directory."}), 404
                
            user_id = user.get("id")
            logger.info(f"Sending Teams notification to user_id: {user_id}")
            
            result = TeamsActivityService.send_activity_notification(
                user_id=user_id,
                message_text=html_content
            )
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error sending to user: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 400

# ===== Run =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
