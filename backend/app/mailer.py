"""Minimal SMTP mailer (works with Gmail app passwords, Outlook, Brevo, SendGrid, Mailgun, ...)."""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from . import settings

log = logging.getLogger("matchpoint.mail")


def send_email(to: str, subject: str, text: str, html: str | None = None) -> bool:
    if not settings.EMAIL_CONFIGURED:
        if settings.IS_PRODUCTION:
            log.warning("Email is not configured (SMTP_HOST/SMTP_FROM); not sending '%s'.", subject)
        else:
            # Development convenience: show the message in the server console instead.
            print(f"\n[dev email - SMTP not configured]\nTo: {to}\nSubject: {subject}\n\n{text}\n", flush=True)
        return False

    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    try:
        ctx = ssl.create_default_context()
        if settings.SMTP_SECURITY == "ssl":
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=ctx, timeout=20)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20)
            if settings.SMTP_SECURITY == "starttls":
                server.starttls(context=ctx)
        with server:
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        log.error("Could not send email to %s: %s", to, exc)
        return False
