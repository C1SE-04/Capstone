# services/email_service.py
# US 8.1 - Task T8.7: Service gửi email thông báo & cảnh báo cho Phụ huynh

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# Bộ nhớ tạm in-memory lưu danh sách email đã gửi (phục vụ test tự động và kiểm tra nhanh)
SENT_EMAILS_LOG: List[Dict[str, Any]] = []

def get_sent_emails() -> List[Dict[str, Any]]:
    """Lấy danh sách các email đã được gửi trong phiên chạy hiện tại."""
    return SENT_EMAILS_LOG.copy()

def clear_sent_emails():
    """Xóa danh sách email đã lưu (dùng trong teardown test)."""
    SENT_EMAILS_LOG.clear()

def send_email(
    to_email: str,
    subject: str,
    text_content: str,
    html_content: Optional[str] = None,
    category: str = "GENERAL_ALERT"
) -> bool:
    """
    Gửi email đến phụ huynh học sinh.
    - Nếu cấu hình SMTP_HOST / SMTP_USER trong môi trường: thực hiện gửi email thật qua SMTP.
    - Nếu không có cấu hình SMTP (môi trường dev/test): ghi log vào SENT_EMAILS_LOG và trả về True.
    """
    if not to_email or not to_email.strip():
        print("[EmailService] ⚠️ Bỏ qua gửi email: to_email rỗng.")
        return False

    to_email = to_email.strip()
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user or "no-reply@socratickid.edu.vn")

    timestamp = datetime.now(timezone.utc).isoformat()
    record = {
        "timestamp": timestamp,
        "to_email": to_email,
        "subject": subject,
        "text_content": text_content,
        "html_content": html_content,
        "category": category,
        "status": "SENT"
    }

    if smtp_pass:
        smtp_pass = smtp_pass.replace(" ", "").strip()

    # 1. Ưu tiên gửi qua Brevo API (Cổng 443 HTTPS - Hoạt động trên Render và Cloud không bị chặn cổng)
    brevo_api_key = os.getenv("BREVO_API_KEY")
    if brevo_api_key and brevo_api_key.strip():
        try:
            import requests
            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "accept": "application/json",
                "api-key": brevo_api_key.strip(),
                "content-type": "application/json",
            }
            sender_name = os.getenv("BREVO_SENDER_NAME", "SocraticKid AI")
            sender_email = os.getenv("BREVO_SENDER_EMAIL", from_email or "socratickid@gmail.com")
            payload = {
                "sender": {"name": sender_name, "email": sender_email},
                "to": [{"email": to_email}],
                "subject": subject,
                "textContent": text_content,
            }
            if html_content:
                payload["htmlContent"] = html_content

            res = requests.post(url, json=payload, headers=headers, timeout=10)
            if res.status_code in [200, 201, 202]:
                record["delivery_method"] = "BREVO_API"
                record["status"] = "SENT"
                SENT_EMAILS_LOG.append(record)
                print(f"[EmailService] [OK] Da gui email qua Brevo API thanh cong toi {to_email}: '{subject}'")
                return True
            else:
                print(f"[EmailService] [WARN] Loi Brevo API ({res.status_code}): {res.text}. Fallback sang SMTP...")
        except Exception as e:
            print(f"[EmailService] [WARN] Exception khi goi Brevo API: {e}. Fallback sang SMTP...")

    # 2. Gửi qua SMTP truyền thống (Dùng khi test local hoặc server mở cổng 587)
    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to_email

            part_text = MIMEText(text_content, "plain", "utf-8")
            msg.attach(part_text)

            if html_content:
                part_html = MIMEText(html_content, "html", "utf-8")
                msg.attach(part_html)

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, [to_email], msg.as_string())

            record["delivery_method"] = "SMTP"
            SENT_EMAILS_LOG.append(record)
            print(f"[EmailService] [OK] Da gui email SMTP thanh cong toi {to_email}: '{subject}'")
            return True
        except Exception as e:
            record["status"] = "FAILED"
            record["error"] = str(e)
            SENT_EMAILS_LOG.append(record)
            print(f"[EmailService] [ERROR] Loi khi gui SMTP toi {to_email}: {e}")
            return False
    else:
        # Chế độ Mock / Dev log
        record["delivery_method"] = "MOCK_LOG"
        SENT_EMAILS_LOG.append(record)
        print(f"[EmailService] [DEV MODE - DA GUI EMAIL GIA LAP] Toi: {to_email} | Tieu de: '{subject}'")
        return True


def render_academic_alert_html(result_data: dict) -> str:
    """Tạo giao diện HTML tinh tế, ấm áp cho Email Cảnh Báo Học Tập Yếu."""
    student_name = result_data.get("student_name", "Học sinh")
    grade = result_data.get("grade", "")
    summary = result_data.get("summary", "")
    strengths = result_data.get("strengths_observed", "")
    learning_gap = result_data.get("learning_gap_analysis", "")
    advice_list = result_data.get("actionable_parent_advice", [])
    opener = result_data.get("suggested_conversation_opener", "")

    advice_items_html = "".join([f"<li style='margin-bottom: 8px;'>{item}</li>" for item in advice_list])

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #f1cca6; border-radius: 12px; background-color: #fdfaf6;">
        <div style="background-color: #8c4905; padding: 16px; border-radius: 8px; text-align: center; color: white;">
            <h2 style="margin: 0; font-size: 20px;">SocraticKid – Đồng Hành Cùng Con</h2>
            <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.9;">Báo cáo học tập môn Toán Lớp {grade}</p>
        </div>
        <div style="padding: 20px 0;">
            <p>Kính gửi Quý Phụ huynh em <strong>{student_name}</strong>,</p>
            <p>{summary}</p>
            
            <div style="background-color: #eaf8ee; border-left: 4px solid #28a745; padding: 12px; margin: 16px 0; border-radius: 4px;">
                <strong style="color: #1e7e34;">🌟 Điểm tích cực của con:</strong>
                <p style="margin: 4px 0 0 0;">{strengths}</p>
            </div>

            <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 16px 0; border-radius: 4px;">
                <strong style="color: #856404;">🔍 Khúc mắc tư duy con đang gặp:</strong>
                <p style="margin: 4px 0 0 0;">{learning_gap}</p>
            </div>

            <div style="background-color: #ffffff; padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px; margin: 16px 0;">
                <strong style="color: #8c4905;">💡 Lời khuyên đồng hành tại nhà cho cha mẹ:</strong>
                <ul style="margin: 8px 0 0 0; padding-left: 20px;">
                    {advice_items_html}
                </ul>
            </div>

            <div style="background-color: #eff6ff; border: 1px dashed #3b82f6; padding: 12px; border-radius: 8px; margin: 16px 0;">
                <strong style="color: #1d4ed8;">💬 Gợi ý câu mở lời ấm áp để cha mẹ trò chuyện cùng con:</strong>
                <p style="margin: 6px 0 0 0; font-style: italic; color: #1e40af;">"{opener}"</p>
            </div>
        </div>
        <div style="text-align: center; font-size: 12px; color: #999; border-top: 1px solid #eee; padding-top: 12px;">
            Hệ thống Trợ lý SocraticKid – Dạy bằng phương pháp gợi mở tư duy.
        </div>
    </body>
    </html>
    """


def render_safety_alert_html(result_data: dict) -> str:
    """Tạo giao diện HTML trang nhã, nghiêm túc cho Email Cảnh Báo Ngôn Từ."""
    student_name = result_data.get("student_name", "Học sinh")
    grade = result_data.get("grade", "")
    censored_snippet = result_data.get("censored_snippet", "")
    context_analysis = result_data.get("context_analysis", "")
    tone_guidance = result_data.get("tone_guidance_for_parent", "")
    advice_list = result_data.get("actionable_parent_advice", [])
    opener = result_data.get("suggested_conversation_opener", "")

    advice_items_html = "".join([f"<li style='margin-bottom: 8px;'>{item}</li>" for item in advice_list])

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #fecaca; border-radius: 12px; background-color: #fffafb;">
        <div style="background-color: #b91c1c; padding: 16px; border-radius: 8px; text-align: center; color: white;">
            <h2 style="margin: 0; font-size: 20px;">SocraticKid – Thông Báo Nhắc Nhở Ngôn Từ</h2>
            <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.9;">Ghi nhận phát ngôn trong giờ học môn Toán Lớp {grade}</p>
        </div>
        <div style="padding: 20px 0;">
            <p>Kính gửi Quý Phụ huynh em <strong>{student_name}</strong>,</p>
            <p>Trong phiên trao đổi học tập vừa qua, hệ thống an toàn ghi nhận em đã sử dụng từ ngữ chưa phù hợp:</p>
            
            <div style="background-color: #fee2e2; border-left: 4px solid #ef4444; padding: 12px; margin: 16px 0; border-radius: 4px;">
                <strong style="color: #991b1b;">⚠️ Trích đoạn phát ngôn đã được kiểm duyệt:</strong>
                <p style="margin: 6px 0 0 0; font-family: monospace; font-size: 15px; color: #7f1d1d;">"{censored_snippet}"</p>
            </div>

            <div style="background-color: #ffffff; padding: 14px; border: 1px solid #f1f5f9; border-radius: 8px; margin: 16px 0;">
                <strong style="color: #475569;">🔍 Góc nhìn tâm lý:</strong>
                <p style="margin: 4px 0 0 0;">{context_analysis}</p>
            </div>

            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 16px 0; border-radius: 4px;">
                <strong style="color: #92400e;">🤝 Định hướng thái độ cho cha mẹ:</strong>
                <p style="margin: 4px 0 0 0;">{tone_guidance}</p>
            </div>

            <div style="background-color: #ffffff; padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px; margin: 16px 0;">
                <strong style="color: #8c4905;">💡 Hướng dẫn chỉ dẫn con tại nhà:</strong>
                <ul style="margin: 8px 0 0 0; padding-left: 20px;">
                    {advice_items_html}
                </ul>
            </div>

            <div style="background-color: #eff6ff; border: 1px dashed #3b82f6; padding: 12px; border-radius: 8px; margin: 16px 0;">
                <strong style="color: #1d4ed8;">💬 Gợi ý câu mở lời nhẹ nhàng để trò chuyện cùng con:</strong>
                <p style="margin: 6px 0 0 0; font-style: italic; color: #1e40af;">"{opener}"</p>
            </div>
        </div>
        <div style="text-align: center; font-size: 12px; color: #999; border-top: 1px solid #eee; padding-top: 12px;">
            Hệ thống Trợ lý SocraticKid – Môi trường học tập an toàn & nhân văn.
        </div>
    </body>
    </html>
    """
