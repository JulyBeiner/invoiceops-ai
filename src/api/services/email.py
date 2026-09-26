import os

import requests
from flask import current_app

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(to, subject, html):
    api_key = os.getenv("BREVO_API_KEY")
    sender = os.getenv("MAIL_FROM")

    if not api_key or not sender:
        current_app.logger.info(
            "EMAIL (not sent) to=%s subject=%s\n%s", to, subject, html)
        return False

    response = requests.post(
        BREVO_URL,
        headers={"api-key": api_key, "Content-Type": "application/json"},
        json={
            "sender": {"email": sender},
            "to": [{"email": to}],
            "subject": subject,
            "htmlContent": html,
        },
        timeout=10,
    )
    response.raise_for_status()
    return True
