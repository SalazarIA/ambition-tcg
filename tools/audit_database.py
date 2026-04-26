from sqlalchemy import inspect


REQUIRED_USER_COLUMNS = [
    "id",
    "username",
    "email",
    "password_hash",
    "is_verified",
    "coins",
    "deck_json",
    "collection_json",
    "wins",
    "losses",
    "xp",
    "level",
    "is_admin",
    "account_status",
    "is_tester",
    "has_completed_onboarding",
]


def audit_database(app, db):
    errors = []

    with app.app_context():
        try:
            inspector = inspect(db.engine)
            tables = set(inspector.get_table_names())

            print("DATABASE TABLES:", sorted(tables))

            if "users" not in tables:
                errors.append("Missing users table")
                return errors

            user_columns = {column["name"] for column in inspector.get_columns("users")}

            for column in REQUIRED_USER_COLUMNS:
                if column not in user_columns:
                    errors.append(f"Missing users column: {column}")

            try:
                from models import User

                total_users = User.query.count()
                print("USERS TOTAL:", total_users)
            except Exception as error:
                errors.append(f"User query failed: {type(error).__name__}: {error}")

        except Exception as error:
            errors.append(f"Database audit failed: {type(error).__name__}: {error}")

    return errors
