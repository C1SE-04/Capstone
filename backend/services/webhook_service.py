"""
========================================================================================
File: backend/services/webhook_service.py
Sprint 11 - US 11.5: Feedback & Contact Hub
========================================================================================
Dịch vụ gửi thông báo Webhook tự động tới Discord / Telegram của nhóm phát triển:
  - Tự động phân loại:
      + Báo lỗi (BUG): Gắn tag Dev (@DevTeam / #Dev)
      + Góp ý tính năng (FEATURE/FEEDBACK): Gắn tag PM (@ProductManager / #PM)
      + Thắc mắc sư phạm / Hợp tác: Gắn tag Support (#Support)
  - Hỗ trợ Discord Webhook (Rich Embed format)
  - Hỗ trợ Telegram Bot (HTML format)
  - Chế độ Fail-Safe: Gặp lỗi mạng hoặc chưa cấu hình webhook URL không bao giờ làm sập API.
  - Lưu in-memory log SENT_WEBHOOKS_LOG phục vụ kiểm thử tự động (Unit Tests).
========================================================================================
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import httpx

import models

logger = logging.getLogger("webhook_service")

# Log bộ nhớ phục vụ kiểm thử tự động (Unit Test / Dev mode)
SENT_WEBHOOKS_LOG: List[Dict[str, Any]] = []


def get_sent_webhooks() -> List[Dict[str, Any]]:
    """Lấy danh sách các thông báo webhook đã bắn trong phiên hiện tại."""
    return list(SENT_WEBHOOKS_LOG)


def clear_sent_webhooks() -> None:
    """Xóa nhật ký webhook (dùng trong test fixtures)."""
    SENT_WEBHOOKS_LOG.clear()


def resolve_team_tag(topic: str) -> Dict[str, Any]:
    """
    Phân loại tag thông báo đội ngũ dựa trên chủ đề:
    - BUG / Báo lỗi -> Dev
    - FEATURE / Góp ý tính năng -> PM
    - PEDAGOGY / COOPERATION / Khác -> Support
    """
    normalized = (topic or "").upper().strip()
    if any(k in normalized for k in ["BUG", "LỖI", "ERROR", "CRASH"]):
        return {
            "team": "DEV",
            "tag_discord": "<@&DevTeam> 🚨 **[BUG ALERT]**",
            "tag_telegram": "<b>#Dev #BugAlert 🚨</b>",
            "color_discord": 0xE74C3C,  # Đỏ
            "prefix": "🚨 [BÁO LỖI]",
        }
    elif any(k in normalized for k in ["FEATURE", "TÍNH NĂNG", "FEEDBACK", "GÓP Ý"]):
        return {
            "team": "PM",
            "tag_discord": "<@&ProductManager> 💡 **[FEATURE / FEEDBACK]**",
            "tag_telegram": "<b>#PM #FeatureRequest 💡</b>",
            "color_discord": 0x2ECC71,  # Xanh lá
            "prefix": "💡 [GÓP Ý TÍNH NĂNG]",
        }
    else:
        return {
            "team": "SUPPORT",
            "tag_discord": "🎓 **[LIÊN HỆ / SƯ PHẠM]**",
            "tag_telegram": "<b>#Support #GeneralContact 🎓</b>",
            "color_discord": 0x3498DB,  # Xanh dương
            "prefix": "📬 [LIÊN HỆ MỚI]",
        }


async def send_discord_webhook(
    webhook_url: str,
    contact: models.ContactRequest,
    meta: Dict[str, Any],
) -> bool:
    """Gửi Rich Embed thông báo đến Discord Webhook."""
    attachments_text = "\n".join(contact.attachment_urls) if contact.attachment_urls else "Không có"
    score_text = f"{float(contact.recaptcha_score):.2f}" if contact.recaptcha_score is not None else "N/A"

    embed = {
        "title": f"{meta['prefix']} {contact.full_name}",
        "description": contact.content[:1000],
        "color": meta["color_discord"],
        "fields": [
            {"name": "👤 Người gửi", "value": f"{contact.full_name} ({contact.email})", "inline": True},
            {"name": "🎓 Vai trò", "value": contact.role or "GUEST", "inline": True},
            {"name": "🏷️ Chủ đề", "value": contact.topic or "FEEDBACK", "inline": True},
            {"name": "🤖 reCAPTCHA Score", "value": score_text, "inline": True},
            {"name": "📎 Ảnh đính kèm", "value": attachments_text, "inline": False},
        ],
        "footer": {
            "text": f"SocraticKid Contact Hub • ID: {contact.id}",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Nếu có ảnh đính kèm đầu tiên, hiển thị thumbnail trong embed
    if contact.attachment_urls and len(contact.attachment_urls) > 0:
        embed["thumbnail"] = {"url": contact.attachment_urls[0]}

    payload = {
        "content": meta["tag_discord"],
        "embeds": [embed],
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code in [200, 204]:
                logger.info(f"[Webhook] Đã gửi Discord Webhook thành công cho contact {contact.id}")
                return True
            else:
                logger.warning(f"[Webhook] Discord Webhook trả về HTTP {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.warning(f"[Webhook] Không thể gửi Discord Webhook ({e})")
        return False


async def send_telegram_webhook(
    bot_token: str,
    chat_id: str,
    contact: models.ContactRequest,
    meta: Dict[str, Any],
) -> bool:
    """Gửi tin nhắn định dạng HTML đến Telegram Group/Channel."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    attachments_text = ", ".join(contact.attachment_urls) if contact.attachment_urls else "Không"
    score_text = f"{float(contact.recaptcha_score):.2f}" if contact.recaptcha_score is not None else "N/A"

    text = (
        f"{meta['tag_telegram']}\n"
        f"<b>{meta['prefix']} từ:</b> {contact.full_name}\n"
        f"<b>Email:</b> {contact.email}\n"
        f"<b>Vai trò:</b> {contact.role}\n"
        f"<b>Chủ đề:</b> {contact.topic}\n"
        f"<b>reCAPTCHA Score:</b> {score_text}\n"
        f"<b>Ảnh đính kèm:</b> {attachments_text}\n\n"
        f"<b>Nội dung:</b>\n<i>{contact.content}</i>\n\n"
        f"<code>ID: {contact.id}</code>"
    )

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info(f"[Webhook] Đã gửi Telegram Webhook thành công cho contact {contact.id}")
                return True
            else:
                logger.warning(f"[Webhook] Telegram Webhook trả về HTTP {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.warning(f"[Webhook] Không thể gửi Telegram Webhook ({e})")
        return False


async def dispatch_contact_webhook(contact: models.ContactRequest) -> Dict[str, Any]:
    """
    Hàm điều phối bắn thông báo Webhook tự động:
    1. Phân loại tag Dev vs PM.
    2. Ghi nhận log in-memory cho môi trường dev/test.
    3. Gửi thật qua Discord / Telegram nếu đã cấu hình biến môi trường.
    """
    meta = resolve_team_tag(contact.topic)

    # Ghi nhận vào log bộ nhớ
    record = {
        "contact_id": contact.id,
        "full_name": contact.full_name,
        "email": contact.email,
        "role": contact.role,
        "topic": contact.topic,
        "content": contact.content,
        "team": meta["team"],
        "tag_discord": meta["tag_discord"],
        "tag_telegram": meta["tag_telegram"],
        "attachment_urls": contact.attachment_urls or [],
        "recaptcha_score": float(contact.recaptcha_score) if contact.recaptcha_score is not None else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    SENT_WEBHOOKS_LOG.append(record)

    discord_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    tele_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    tele_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    discord_sent = False
    telegram_sent = False

    if discord_url:
        discord_sent = await send_discord_webhook(discord_url, contact, meta)
    if tele_token and tele_chat_id:
        telegram_sent = await send_telegram_webhook(tele_token, tele_chat_id, contact, meta)

    return {
        "dispatched": True,
        "team": meta["team"],
        "discord_sent": discord_sent,
        "telegram_sent": telegram_sent,
    }

