def password_policy_errors(password, min_length=10, require_complexity=True):
    password = password or ""
    errors = []

    if len(password) < min_length:
        errors.append(f"Password must have at least {min_length} characters.")

    if require_complexity:
        if not any(char.islower() for char in password):
            errors.append("Password must include a lowercase letter.")

        if not any(char.isupper() for char in password):
            errors.append("Password must include an uppercase letter.")

        if not any(char.isdigit() for char in password):
            errors.append("Password must include a number.")

    return errors
