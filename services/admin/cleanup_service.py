from sqlalchemy import text

from services.database.schema_tools import delete_table_if_exists, get_table_names


GAMEPLAY_TABLES = [
    "user_missions",
    "system_logs",
    "feedback_reports",
    "feedback_report",
    "booster_history",
    "booster_histories",
    "match_history",
    "match_histories",
    "card_stats",
    "beta_invites",
]


def clear_gameplay_data(db):
    cleared = []

    with db.engine.begin() as connection:
        for table in GAMEPLAY_TABLES:
            if delete_table_if_exists(db, connection, table):
                cleared.append(table)

    return {
        "cleared_tables": cleared,
        "cleared_count": len(cleared),
    }


def delete_non_admin_users(db):
    result = clear_gameplay_data(db)
    deleted_users = 0

    with db.engine.begin() as connection:
        tables = get_table_names(db)

        if "users" in tables:
            delete_result = connection.execute(
                text('DELETE FROM "users" WHERE COALESCE(is_admin, false) = false')
            )
            deleted_users = delete_result.rowcount or 0

    result["deleted_users"] = deleted_users

    return result
