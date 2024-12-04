import sqlite3
from stadsarkiv_client.core.logging import get_log
from stadsarkiv_client.database.sql_builder import SQLBuilder

log = get_log()


class CRUD:
    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize CRUD with database URL.
        """
        self.connection = connection

    async def last_insert_id(self) -> int:
        """
        Get the last inserted row ID.
        """
        cursor = self.connection.execute("SELECT last_insert_rowid() as last_insert_id")
        row = cursor.fetchone()
        return row["last_insert_id"]

    async def insert(self, table: str, insert_values: dict):
        """
        Insert a single row into the table.
        """
        sql_builder = SQLBuilder(table)
        query = sql_builder.build_insert(insert_values)
        self.connection.execute(query, insert_values)

    async def insert_many(self, table: str, insert_values_many: list[dict]):
        """
        Insert multiple rows into the table.
        """
        for single_data in insert_values_many:
            await self.insert(table, single_data)

    async def select(
        self,
        table: str,
        columns: list = [],
        filters: dict = {},
        order_by: list = [],
        limit_offset: tuple = (),
    ) -> list:
        """
        Select rows from the table.
        """
        sql_builder = SQLBuilder(table)
        query = sql_builder.build_select(
            columns=columns,
            filters=filters,
            order_by=order_by,
            limit_offset=limit_offset,
        )
        result = self.connection.execute(query, filters)
        rows = result.fetchall()
        rows = [dict(row) for row in rows]
        return rows

    async def select_one(self, table: str, columns: list = [], filters: dict = {}) -> dict:
        """
        Select a single row from the table.
        """
        rows = await self.select(table=table, columns=columns, filters=filters, limit_offset=(1, 0))
        if rows:
            return dict(rows[0])
        return {}

    async def update(self, table: str, update_values: dict, filters: dict):
        """
        Update rows in the table.
        """
        sql_builder = SQLBuilder(table)
        query = sql_builder.build_update(update_values, filters)
        self.connection.execute(query, sql_builder.get_execute_values())

    async def delete(self, table: str, filters: dict):
        """
        Delete rows from the table.
        """
        sql_builder = SQLBuilder(table)
        query = sql_builder.build_delete(filters)
        self.connection.execute(query, filters)

    async def exists(self, table: str, filters: dict) -> bool:
        """
        Check if any row exists matching the filters.
        """
        row = await self.select_one(table=table, filters=filters)
        return bool(row)

    async def count(self, table: str, filters: dict, column: str = "*") -> int:
        """
        Count rows in the table matching the filters.
        """
        sql_builder = SQLBuilder(table)
        query = sql_builder.build_select(columns=[f"COUNT({column}) as num_rows"], filters=filters)
        result = self.connection.execute(query, filters)
        row = result.fetchone()
        return row["num_rows"]

    async def query(self, query: str, values: dict):
        """
        Execute a custom query and return the rows.
        """
        cursor = self.connection.execute(query, values)
        rows = cursor.fetchall()
        rows = [dict(row) for row in rows]
        return rows

    async def query_one(self, query: str, values: dict):
        """
        Execute a custom query and return a single row.
        """
        cursor = self.connection.execute(query, values)
        row = cursor.fetchone()
        return row
