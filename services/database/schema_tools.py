import re

from sqlalchemy import inspect, text


SAFE_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def get_table_names(db):
    try:
        return set(inspect(db.engine).get_table_names())
    except Exception as error:
        print("Schema inspection failed:", type(error).__name__, error)
        return set()


def table_exists(db, table_name):
    return table_name in get_table_names(db)


def delete_table_if_exists(db, connection, table_name):
    if not SAFE_TABLE_NAME_RE.match(str(table_name)):
        print(f"Cleanup skipped, unsafe table name: {table_name}")
        return False

    if not table_exists(db, table_name):
        print(f"Cleanup skipped, missing table: {table_name}")
        return False

    try:
        connection.execute(text(f'DELETE FROM "{table_name}"'))  # nosec B608
        print(f"Cleanup OK: {table_name}")
        return True
    except Exception as error:
        print(f"Cleanup ERROR on {table_name}: {type(error).__name__}: {error}")
        return False


def get_user_columns(db):
    try:
        inspector = inspect(db.engine)
        if "users" not in inspector.get_table_names():
            return set()

        return {column["name"] for column in inspector.get_columns("users")}
    except Exception as error:
        print("User column inspection failed:", type(error).__name__, error)
        return set()
