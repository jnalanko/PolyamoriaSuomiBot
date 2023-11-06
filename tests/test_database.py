import os
import unittest

from mysql.connector.pooling import MySQLConnectionPool

from database import create_db_if_needed


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.pool = MySQLConnectionPool(pool_name="mypool",
                                        pool_size=1,
                                        host="127.0.0.1",
                                        user="root",
                                        password=os.getenv("TEST_MARIADB_ROOT_PASSWORD"))
        self.test_db_name = "test_polyamoria_suomi_bot_unique_d83k19tv5lg8"

    def test_create_db_if_needed_when_no_db(self):
        # Make sure the test db doesn't exist
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DROP DATABASE IF EXISTS {self.test_db_name}")

        create_db_if_needed(pool=self.pool, db_name=self.test_db_name)

        db_names = self._get_databases()
        self.assertTrue(self.test_db_name in db_names)

    def test_create_db_if_needed_when_already_exists(self):
        # Create the test db
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.test_db_name}")

        create_db_if_needed(pool=self.pool, db_name=self.test_db_name)

        db_names = self._get_databases()
        self.assertTrue(self.test_db_name in db_names)

    def tearDown(self):
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DROP DATABASE IF EXISTS {self.test_db_name}")

    def _get_databases(self) -> list[str]:
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")

            # List of database names
            databases = cursor.fetchall()
            db_names = [db[0] for db in databases]
        return db_names


if __name__ == '__main__':
    unittest.main()
