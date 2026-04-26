import smtplib
from email.message import EmailMessage
from flask import current_app


def is_smtp_configured():
    return current_app.config.get("SMTP_HOST") and current_app.config.get("SMTP_USERNAME") and current_app.config.get("SMTP_PASSWORD")


def send_email(to_email, subject, body):
    if not is_smtp_configured():
        print("\n--- AMBITION EMAIL FALLBACK ---")
        print("To:", to_email)
        print("Subject:", subject)
        print(body)
        print("-------------------------------\n")
        return False

    msg = EmailMessage()
    msg["From"] = current_app.config.get("MAIL_FROM")
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    host = current_app.config.get("SMTP_HOST")
    port = int(current_app.config.get("SMTP_PORT", 587))
    username = current_app.config.get("SMTP_USERNAME")
    password = current_app.config.get("SMTP_PASSWORD")
    use_tls = current_app.config.get("SMTP_USE_TLS", True)

    with smtplib.SMTP(host, port, timeout=20) as server:
        if use_tls:
            server.starttls()

        server.login(username, password)
        server.send_message(msg)

    return True


def send_verification_email(user, verification_url):
    subject = "Confirm your Ambition TCG account"

    body = f"""Welcome to Ambition TCG, {user.username}.

Confirm your account using the link below:

{verification_url}

This link expires for security reasons.

Ambition TCG
Risk. Elements. Overreach.
"""

    return send_email(user.email, subject, body)


def send_password_reset_email(user, reset_url):
    subject = "Reset your Ambition TCG password"

    body = f"""Hi {user.username}.

Use the link below to reset your Ambition TCG password:

{reset_url}

If you did not request this, ignore this email.

Ambition TCG
"""

    return send_email(user.email, subject, body)
