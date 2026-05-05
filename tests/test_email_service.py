from services.email_service import send_email


def test_email_fallback_logs_do_not_expose_recipient_subject_or_body(flask_app, capsys):
    flask_app.config.update(
        SMTP_HOST=None,
        SMTP_USERNAME=None,
        SMTP_PASSWORD=None,
        MAIL_FROM=None,
        EMAIL_LOG_BODY_ENABLED=True,
    )

    sent = send_email(
        "player.secret@example.com",
        "Private reset subject",
        "reset-token-123 should never be logged",
    )

    output = capsys.readouterr().out

    assert sent is False
    assert "player.secret@example.com" not in output
    assert "Private reset subject" not in output
    assert "reset-token-123" not in output
    assert "pl***@example.com" in output
    assert "Subject present: True" in output
    assert "Body logging requested but suppressed for safety." in output


def test_smtp_error_logs_do_not_expose_credentials_or_server_details(flask_app, monkeypatch, capsys):
    class FailingSMTP:
        def __init__(self, host, port, timeout=30):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def starttls(self):
            return None

        def login(self, username, password):
            raise RuntimeError(f"login failed for {username} with {password}")

        def send_message(self, msg):
            return None

    flask_app.config.update(
        SMTP_HOST="smtp.secret.example.com",
        SMTP_PORT=2525,
        SMTP_USERNAME="smtp-user-secret",
        SMTP_PASSWORD="smtp-password-secret",
        MAIL_FROM="sender.secret@example.com",
        SMTP_USE_TLS=True,
        EMAIL_LOG_BODY_ENABLED=True,
    )
    monkeypatch.setattr("services.email_service.smtplib.SMTP", FailingSMTP)

    sent = send_email(
        "recipient.secret@example.com",
        "Sensitive failure subject",
        "sensitive body content",
    )

    output = capsys.readouterr().out

    assert sent is False
    assert "smtp.secret.example.com" not in output
    assert "smtp-user-secret" not in output
    assert "smtp-password-secret" not in output
    assert "sender.secret@example.com" not in output
    assert "recipient.secret@example.com" not in output
    assert "Sensitive failure subject" not in output
    assert "sensitive body content" not in output
    assert "Error message omitted" in output
    assert "re***@example.com" in output
