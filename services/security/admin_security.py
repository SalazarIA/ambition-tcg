def is_truthy(value):
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def is_dev_tools_enabled(app):
    return is_truthy(app.config.get("DEV_TOOLS_ENABLED", False))


def danger_confirmation_matches(app, received_value):
    expected = app.config.get("ADMIN_DANGER_CONFIRMATION", "RESET AMBITIONZ")
    return str(received_value or "").strip() == expected
