"""
This module contains utility functions for working with SQLite databases.

The functions in this module are used to create a transaction scope to ensure that all operations are atomic.
If a query fails, the transaction is rolled back and an exception is raised. Otherwise, the transaction is committed.

Example usage:

```
from stadsarkiv_client.database.utils import DatabaseTransaction

database_url = settings["sqlite3"]["default"]
database_transation = DatabaseTransaction(database_url)
transaction_scope = database_transation.transaction_scope

async def delete_user(user_id: int):
    async with transaction_scope() as connection:
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        connection.execute("INSERT INTO deleted_user_log (user_id, message) VALUES (?, ?)", (user_id, "User deleted"))

async def get_user(user_id: int):
    async with transaction_scope() as connection:
        cursor = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return user
```
"""

import sqlite3
from contextlib import asynccontextmanager, contextmanager
from stadsarkiv_client.core.logging import get_log

log = get_log()


class DatabaseTransaction:
    def __init__(self, database_url):
        self.database_url = database_url

    def get_db_connection_sync(self) -> sqlite3.Connection:
        """
        Create a synchronous database connection.
        """
        connection = sqlite3.connect(self.database_url)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL;")
        return connection

    @contextmanager
    def transaction_scope_sync(self):
        """
        Synchronous transaction scope context manager.
        """
        connection = self.get_db_connection_sync()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except sqlite3.Error:
            connection.rollback()
            raise
        finally:
            connection.close()

    async def get_db_connection(self) -> sqlite3.Connection:
        """
        Create an asynchronous database connection.
        """
        connection = sqlite3.connect(self.database_url)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL;")
        return connection

    @asynccontextmanager
    async def transaction_scope(self):
        """
        Asynchronous transaction scope context manager.
        """
        connection = await self.get_db_connection()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except sqlite3.Error:
            connection.rollback()
            raise
        finally:
            connection.close()
