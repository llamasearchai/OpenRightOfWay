from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Iterable, Optional

from openrightofway.utils.logging import get_logger

logger = get_logger(__name__)


class Notifier:
    def __init__(self) -> None:
        # Twilio config via env
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_from = os.getenv("TWILIO_FROM")

        # SMTP config via env
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.email_from = os.getenv("EMAIL_FROM")

    def send_sms(self, to_numbers: Iterable[str], message: str) -> None:
        numbers = list(to_numbers)
        if not numbers:
            logger.info("SMS: no recipients provided; skipping")
            return
        if self.twilio_sid and self.twilio_token and self.twilio_from:
            try:
                from twilio.rest import Client

                client = Client(self.twilio_sid, self.twilio_token)
                for to in numbers:
                    client.messages.create(body=message, from_=self.twilio_from, to=to)
                logger.info("Sent SMS to %d recipients via Twilio", len(numbers))
            except Exception as e:  # pragma: no cover - network dependent
                logger.error("Failed to send SMS via Twilio: %s", e)
        else:
            # Fallback: log
            for to in numbers:
                logger.info("SMS to %s: %s", to, message)

    def send_email(
        self,
        to_emails: Iterable[str],
        subject: str,
        body: str,
        attachments: Optional[Iterable[str]] = None,
    ) -> None:
        emails = list(to_emails)
        if not emails:
            logger.info("Email: no recipients provided; skipping")
            return

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.email_from or "openrightofway@example.com"
        msg["To"] = ", ".join(emails)
        msg.set_content(body)

        for path in (attachments or []):
            try:
                with open(path, "rb") as f:
                    data = f.read()
                maintype = "application"
                subtype = "octet-stream"
                msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(path))
            except Exception as e:
                logger.error("Failed to attach %s: %s", path, e)

        if self.smtp_host and self.smtp_username and self.smtp_password:
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:  # pragma: no cover - network dependent
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
                logger.info("Sent email to %d recipients via SMTP", len(emails))
            except Exception as e:  # pragma: no cover
                logger.error("Failed to send email via SMTP: %s", e)
        else:
            # Fallback: log
            logger.info("Email to %s: %s\n%s", ", ".join(emails), subject, body)

