import smtplib
from email.message import EmailMessage
from flask import current_app


def is_smtp_configured():
    required = [
        current_app.config.get("SMTP_HOST"),
        current_app.config.get("SMTP_USERNAME"),
        current_app.config.get("SMTP_PASSWORD"),
        current_app.config.get("MAIL_FROM"),
    ]

    return all(required)


def send_email(to_email, subject, body):
    host = current_app.config.get("SMTP_HOST")
    port = int(current_app.config.get("SMTP_PORT", 587))
    username = current_app.config.get("SMTP_USERNAME")
    password = current_app.config.get("SMTP_PASSWORD")
    use_tls = current_app.config.get("SMTP_USE_TLS", True)
    mail_from = current_app.config.get("MAIL_FROM")
    log_body_enabled = bool(current_app.config.get("EMAIL_LOG_BODY_ENABLED", False))

    if not is_smtp_configured():
        print("\n--- AMBITIONZ EMAIL FALLBACK ---")
        print("Reason: SMTP not fully configured.")
        print("SMTP_HOST:", bool(host))
        print("SMTP_USERNAME:", bool(username))
        print("SMTP_PASSWORD:", bool(password))
        print("MAIL_FROM:", bool(mail_from))
        print("To:", to_email)
        print("Subject:", subject)
        if log_body_enabled:
            print(body)
        else:
            print("Body omitted. Set EMAIL_LOG_BODY_ENABLED=true only in local development if needed.")
        print("--------------------------------\n")
        return False

    msg = EmailMessage()
    msg["From"] = mail_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            if use_tls:
                server.starttls()

            server.login(username, password)
            server.send_message(msg)

        print("\n--- AMBITIONZ EMAIL SENT ---")
        print("To:", to_email)
        print("Subject:", subject)
        print("----------------------------\n")
        return True

    except Exception as error:
        print("\n--- AMBITIONZ SMTP ERROR ---")
        print("Error type:", type(error).__name__)
        print("Error:", error)
        print("SMTP_HOST:", host)
        print("SMTP_PORT:", port)
        print("SMTP_USERNAME:", username)
        print("MAIL_FROM:", mail_from)
        print("To:", to_email)
        print("Subject:", subject)
        if log_body_enabled:
            print(body)
        else:
            print("Body omitted. Set EMAIL_LOG_BODY_ENABLED=true only in local development if needed.")
        print("-----------------------------\n")
        return False


def send_smtp_test_email(to_email):
    subject = "Ambitionz SMTP Test"

    body = """Ambitionz SMTP test successful.

If you received this message, the production email system is working.

Ambitionz
Risk. Elements. Ambition.
"""

    return send_email(to_email, subject, body)


def send_verification_email(user, verification_url):
    subject = "Confirm your Ambitionz account"

    body = f"""Welcome to Ambitionz, {user.username}.

Your account was created successfully.

Confirm your account using the secure link below:

{verification_url}

This link expires for security reasons.

After confirming, return to Ambitionz and log in normally.

Ambitionz
Risk. Elements. Ambition.
"""

    return send_email(user.email, subject, body)


def send_password_reset_email(user, reset_url):
    subject = "Reset your Ambitionz password"

    body = f"""Hi {user.username}.

We received a request to reset your Ambitionz password.

Use the secure link below to create a new password:

{reset_url}

If you did not request this, ignore this email.

Ambitionz
"""

    return send_email(user.email, subject, body)
