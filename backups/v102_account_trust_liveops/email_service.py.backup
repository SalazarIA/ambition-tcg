import os
import smtplib
from email.message import EmailMessage


def email_configured():
    required = [
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "MAIL_FROM",
    ]

    return all(os.environ.get(key) for key in required)


def send_email(to_email, subject, body):
    if not email_configured():
        print("\n--- EMAIL SERVICE NOT CONFIGURED ---")
        print("To:", to_email)
        print("Subject:", subject)
        print(body)
        print("------------------------------------\n")
        return False

    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ["SMTP_PORT"])
    smtp_username = os.environ["SMTP_USERNAME"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    mail_from = os.environ["MAIL_FROM"]
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"

    message = EmailMessage()
    message["From"] = mail_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        if use_tls:
            server.starttls()

        server.login(smtp_username, smtp_password)
        server.send_message(message)

    return True


def send_verification_email(to_email, verification_url):
    subject = "Verify your Ambition TCG account"

    body = f"""Welcome to Ambition TCG.

Verify your account using the link below:

{verification_url}

If you did not create this account, ignore this message.
"""

    return send_email(to_email, subject, body)


def send_password_reset_email(to_email, reset_url):
    subject = "Reset your Ambition TCG password"

    body = f"""You requested a password reset for Ambition TCG.

Reset your password using the link below:

{reset_url}

This link expires soon. If you did not request this, ignore this message.
"""

    return send_email(to_email, subject, body)
