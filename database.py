from mysql.connector.pooling import MySQLConnectionPool


def open_database(db_name: str, username: str, password: str) -> MySQLConnectionPool:
    """Connection pool handles reconnections automatically"""
    db_config = {
        "host": "localhost",
        "user": username,
        "password": password,
        "charset": "utf8mb4", # Need 4-byte unicode for emoji support
    }

    connection_pool = MySQLConnectionPool(
        pool_name=db_name,
        **db_config
    )

    create_db_if_needed(pool=connection_pool, db_name=db_name)

    # Add "database" to config after it's been created
    db_config["database"] = db_name
    connection_pool.set_config(**db_config)

    create_tables_if_needed(pool=connection_pool)

    return connection_pool


def create_db_if_needed(pool: MySQLConnectionPool, db_name: str):
    with pool.get_connection() as conn:
        cursor = conn.cursor()

        # cursor.execute does not support sanitized CREATE DATABASE queries.
        # So we just trust our own config and plug in the database name directly.
        cursor.execute("CREATE DATABASE IF NOT EXISTS {}".format(db_name))


def create_tables_if_needed(pool: MySQLConnectionPool):
    with pool.get_connection() as conn:
        cursor = conn.cursor()

        create_message_counts_table = """
        CREATE TABLE IF NOT EXISTS message_counts (
            user_id BIGINT UNSIGNED,
            date DATE,
            count INT,
            PRIMARY KEY (user_id, date)
        )
        """

        cursor.execute(create_message_counts_table)

        create_autodelete_table = """
        CREATE TABLE IF NOT EXISTS autodelete (
            channel_id BIGINT UNSIGNED PRIMARY KEY,
            callback_interval_minutes INT,
            delete_older_than_minutes INT
        )
        """

        cursor.execute(create_autodelete_table)

        # Midnight winners table.
        # The prize is an emoji in unicode.
        midnight_winners = """
        CREATE TABLE IF NOT EXISTS midnight_winners (
            date DATE PRIMARY KEY,
            user_id BIGINT UNSIGNED,
            prize CHAR(4) CHARACTER SET utf8mb4
        )
        """

        cursor.execute(midnight_winners)

        conn.commit()
