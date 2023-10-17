import mysql.connector
import sys

db_password = "salasana" # Todo: config file
db_username = "polyamoria_suomi"
db_name = "polyamoria_suomi"

db_config = {
    "host": "localhost",
    "user": db_username,
    "password": db_password,
}

connection = mysql.connector.connect(**db_config)
cursor = connection.cursor()

cursor.execute("CREATE DATABASE IF NOT EXISTS {}".format(db_name))
cursor.execute("USE {}".format(db_name))

create_table_query = """
CREATE TABLE IF NOT EXISTS activity (
    username VARCHAR(255) PRIMARY KEY,
    last_message_date DATETIME
)
"""
cursor.execute(create_table_query)

# If username is not in table, insert it
cursor.execute("INSERT IGNORE INTO activity (username, last_message_date) VALUES (%s, NOW())", ["drai"])

# Update the date
cursor.execute("UPDATE activity SET last_message_date = NOW() WHERE username = %s", ["drai"])

# Commit
connection.commit()