"""Notification channels: email (Gmail SMTP) and Telegram bot.

Credentials come from environment variables (set as GitHub Secrets in CI):

  EMAIL_USER            Gmail address used to send
  EMAIL_APP_PASSWORD    Gmail App Password (NOT your normal password)
  EMAIL_TO              where alerts are delivered (defaults to EMAIL_USER)
  TELEGRAM_BOT_TOKEN    bot token from @BotFather
  TELEGRAM_CHAT_ID      your chat id (see README)

Each configured channel is attempted independently; a failure in one is logged
and does not prevent the other from sending.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from .models import Job
from .providers.http import post_json

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _email_configured() -> bool:
    return bool(os.environ.get("EMAIL_USER") and os.environ.get("EMAIL_APP_PASSWORD"))


def _telegram_configured() -> bool:
    return bool(
        os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")
    )


def configured_channels() -> list[str]:
    channels = []
    if _email_configured():
        channels.append("email")
    if _telegram_configured():
        channels.append("telegram")
    return channels


# ---------- formatting ----------

def _job_line(job: Job) -> str:
    loc = f" · {job.location}" if job.location else ""
    return f"{job.company}: {job.title}{loc}\n{job.url}"


def format_body(jobs: list[Job]) -> str:
    return "\n\n".join(_job_line(j) for j in jobs)


def _subject(jobs: list[Job]) -> str:
    if len(jobs) == 1:
        return f"New internship: {jobs[0].company} — {jobs[0].title}"
    return f"{len(jobs)} new internship postings"


# ---------- channels ----------

def send_email(subject: str, body: str) -> None:
    user = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_APP_PASSWORD"]
    to = os.environ.get("EMAIL_TO") or user

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)


def send_telegram(text: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    post_json(
        TELEGRAM_API.format(token=token),
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        },
    )


# ---------- orchestration ----------

def notify_new_jobs(jobs: list[Job]) -> None:
    """Send one batched alert per channel for the given new jobs."""
    if not jobs:
        return
    subject = _subject(jobs)
    body = format_body(jobs)

    if _email_configured():
        try:
            send_email(subject, body)
            print(f"[notify] email sent ({len(jobs)} job(s))")
        except Exception as exc:  # noqa: BLE001 - channel isolation
            print(f"[notify] email FAILED: {exc}")

    if _telegram_configured():
        try:
            send_telegram(f"{subject}\n\n{body}")
            print(f"[notify] telegram sent ({len(jobs)} job(s))")
        except Exception as exc:  # noqa: BLE001 - channel isolation
            print(f"[notify] telegram FAILED: {exc}")


def send_test() -> None:
    """Send a 'hello' through every configured channel to verify credentials."""
    channels = configured_channels()
    if not channels:
        print("[notify] no channels configured; set EMAIL_* and/or TELEGRAM_* env vars")
        return
    text = "openings-bot test notification — if you can read this, alerts work."
    if "email" in channels:
        try:
            send_email("openings-bot test", text)
            print("[notify] test email sent")
        except Exception as exc:  # noqa: BLE001
            print(f"[notify] test email FAILED: {exc}")
    if "telegram" in channels:
        try:
            send_telegram(text)
            print("[notify] test telegram sent")
        except Exception as exc:  # noqa: BLE001
            print(f"[notify] test telegram FAILED: {exc}")
