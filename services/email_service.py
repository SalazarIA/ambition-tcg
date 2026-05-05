import smtplib
from email.message import EmailMessage
from flask import current_app


def _mask_email(email):
    value = str(email or "").strip()

    if "@" not in value:
        return "<redacted>"

    local, domain = value.split("@", 1)
    safe_local = local[:2] + "***" if len(local) > 2 else "***"
    return f"{safe_local}@{domain}"


def _print_email_log_context(to_email, subject):
    print("Recipient:", _mask_email(to_email))
    print("Subject present:", bool(str(subject or "").strip()))


def _print_smtp_config_status(host, username, password, mail_from):
    print("SMTP configured flags:", {
        "host": bool(host),
        "username": bool(username),
        "password": bool(password),
        "mail_from": bool(mail_from),
    })


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
        _print_smtp_config_status(host, username, password, mail_from)
        _print_email_log_context(to_email, subject)
        if log_body_enabled:
            print("Body logging requested but suppressed for safety.")
        else:
            print("Body omitted.")
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
        _print_email_log_context(to_email, subject)
        print("----------------------------\n")
        return True

    except Exception as error:
        print("\n--- AMBITIONZ SMTP ERROR ---")
        print("Error type:", type(error).__name__)
        print("Error message omitted to avoid leaking SMTP or recipient details.")
        print("SMTP_PORT:", port)
        _print_smtp_config_status(host, username, password, mail_from)
        _print_email_log_context(to_email, subject)
        if log_body_enabled:
            print("Body logging requested but suppressed for safety.")
        else:
            print("Body omitted.")
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
