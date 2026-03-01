from __future__ import annotations

import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from .intake import format_schedule


def build_email_reminder(appointment: dict, clinic_name: str = "Life Chiropractic") -> dict:
    subject = f"Reminder: {appointment['type_label']} on {appointment['date_label']} at {appointment['time_label']}"
    lines = [
        f"Hi {appointment['patient_first_name']},",
        "",
        f"This is a reminder from {clinic_name} about your {appointment['type_label']}.",
        f"When: {appointment['starts_label']}",
    ]
    if appointment.get("clinician_name"):
        lines.append(f"Clinician: {appointment['clinician_name']}")
    if appointment.get("note"):
        lines.extend(["", "What to expect:", appointment["note"]])
    lines.extend(
        [
            "",
            "Please contact the clinic if you need to reschedule.",
            "",
            clinic_name,
        ]
    )
    return {
        "channel": "email",
        "recipient": appointment.get("patient_email", ""),
        "subject": subject,
        "message": "\n".join(lines),
    }


def build_sms_reminder(appointment: dict, clinic_name: str = "Life Chiropractic") -> dict:
    message = (
        f"{clinic_name}: reminder for your {appointment['type_label']} on "
        f"{appointment['date_label']} at {appointment['time_label']}."
    )
    if appointment.get("note"):
        message += f" {appointment['note']}"
    message += " Reply to the clinic if you need to reschedule."
    return {
        "channel": "sms",
        "recipient": appointment.get("patient_phone", ""),
        "subject": "",
        "message": message,
    }


def deliver_email(app_config: dict, payload: dict) -> tuple[str, str, str]:
    mode = (app_config.get("REMINDER_EMAIL_MODE") or "outbox").strip().lower()
    if mode == "smtp":
        host = app_config.get("SMTP_HOST", "").strip()
        from_email = app_config.get("REMINDER_EMAIL_FROM", "").strip()
        if not host or not from_email:
            raise RuntimeError("SMTP delivery requires SMTP_HOST and REMINDER_EMAIL_FROM.")

        message = EmailMessage()
        message["Subject"] = payload["subject"]
        message["From"] = from_email
        message["To"] = payload["recipient"]
        message.set_content(payload["message"])

        port = int(app_config.get("SMTP_PORT", 587))
        username = app_config.get("SMTP_USERNAME", "").strip()
        password = app_config.get("SMTP_PASSWORD", "")
        use_ssl = bool(app_config.get("SMTP_USE_SSL"))
        use_tls = bool(app_config.get("SMTP_USE_TLS"))

        if use_ssl:
            with smtplib.SMTP_SSL(host, port) as client:
                if username:
                    client.login(username, password)
                client.send_message(message)
        else:
            with smtplib.SMTP(host, port) as client:
                client.ehlo()
                if use_tls:
                    client.starttls()
                    client.ehlo()
                if username:
                    client.login(username, password)
                client.send_message(message)
        return "sent", mode, ""

    return "logged", mode or "outbox", ""


def deliver_sms(app_config: dict, payload: dict) -> tuple[str, str, str]:
    mode = (app_config.get("REMINDER_SMS_MODE") or "outbox").strip().lower()
    return "logged", mode or "outbox", ""


def deliver_reminder(app_config: dict, payload: dict) -> tuple[str, str, str]:
    if payload["channel"] == "email":
        return deliver_email(app_config, payload)
    if payload["channel"] == "sms":
        return deliver_sms(app_config, payload)
    raise ValueError(f"Unsupported reminder channel: {payload['channel']}")


def build_mailto_link(payload: dict) -> str:
    recipient = quote(payload.get("recipient", ""))
    subject = quote(payload.get("subject", ""))
    body = quote(payload.get("message", ""))
    return f"mailto:{recipient}?subject={subject}&body={body}"


def build_sms_link(payload: dict) -> str:
    recipient = quote(payload.get("recipient", ""))
    body = quote(payload.get("message", ""))
    return f"sms:{recipient}?body={body}"


def build_delivery_launch_link(payload: dict) -> str | None:
    if payload.get("channel") == "email" and payload.get("recipient"):
        return build_mailto_link(payload)
    if payload.get("channel") == "sms" and payload.get("recipient"):
        return build_sms_link(payload)
    return None


def reminder_preview_payload(appointment: dict, channel: str) -> dict:
    if channel == "email":
        return build_email_reminder(appointment)
    if channel == "sms":
        return build_sms_reminder(appointment)
    raise ValueError(f"Unsupported reminder channel: {channel}")


def appointment_schedule_label(starts_at: str) -> str:
    return format_schedule(starts_at) or starts_at
