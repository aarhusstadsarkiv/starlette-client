"""
A collection of functions for performing CRUD operations on orders.
"""

from stadsarkiv_client.core.dynamic_settings import settings
from stadsarkiv_client.database.crud import CRUD
from stadsarkiv_client.database import utils_orders
from stadsarkiv_client.database.utils import DatabaseConnection
from stadsarkiv_client.core.logging import get_log
import json


log = get_log()

try:
    orders_url = settings["sqlite3"]["orders"]
except KeyError:
    orders_url = ""

STATUSES_ORDER = utils_orders.STATUSES_LOCATION


async def is_record_active_by_user(user_id: str, record_id: str):
    row = await _get_active_order(user_id, record_id)
    return row is not None


async def is_owner_of_order(user_id: str, order_id: int):

    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        filters = {"order_id": order_id, "user_id": user_id}
        is_owner = await crud.exists(
            table="orders",
            filters=filters,
        )

    return is_owner


async def insert_order(meta_data: dict, me: dict):

    # Check if user is already active on this record
    is_active_by_user = await is_record_active_by_user(me["id"], meta_data["id"])
    if is_active_by_user:
        # This may happen is user has already ordered the record
        # In reality it will only happen if the user has two tabs open and POST the same order twice
        raise Exception("User is already active on this record")

    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)

        """
        Check if there are other active users on this record that are orderable
        If so, set status to QUEUED, otherwise set status to ORDERED
        """

        # insert or update user
        user_insert_update_values = utils_orders.get_insert_user_data(me)
        await crud.replace("users", user_insert_update_values, {"user_id": me["id"]})

        # insert or update record
        record_insert_update_values = utils_orders.get_insert_record_data(meta_data)
        await crud.replace("records", record_insert_update_values, {"record_id": meta_data["id"]})

        # Check if active order exists on record.
        # If so, set status to QUEUED, otherwise set status to ORDERED
        num_active_orders = await _count_active_users(crud, meta_data["id"])
        if num_active_orders > 0:
            user_status = utils_orders.STATUSES_USER.QUEUED
        else:
            user_status = utils_orders.STATUSES_USER.ORDERED

        await crud.insert(
            "orders",
            utils_orders.get_order_data(user_insert_update_values["user_id"], record_insert_update_values["record_id"], user_status),
        )

        last_order_id = await crud.last_insert_id()
        order_data = await crud.select_one("orders", filters={"order_id": last_order_id})

        # Send message to user
        utils_orders.send_order_message("Order created", order_data)

        # Insert log message
        await _insert_log_message(
            crud,
            order_id=order_data["order_id"],
            location=record_insert_update_values["location"],
            user_status=order_data["user_status"],
            changed_by=me["id"],
        )


async def get_orders_user(user_id: str, completed=0):
    """
    Get all orders for a user. Exclude orders with specific statuses.
    """
    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)

        if completed:
            query = f"""
            SELECT * FROM orders o
            LEFT JOIN records r ON o.record_id = r.record_id
            WHERE o.user_id = :user_id
            AND o.user_status IN ({utils_orders.STATUSES_USER.COMPLETED}, {utils_orders.STATUSES_USER.DELETED})
            """
        else:
            query = f"""
            SELECT * FROM orders o
            LEFT JOIN records r ON o.record_id = r.record_id
            WHERE o.user_id = :user_id
            AND o.user_status NOT IN ({utils_orders.STATUSES_USER.COMPLETED}, {utils_orders.STATUSES_USER.DELETED})
            """

        filters = {"user_id": user_id}

        orders = await crud.query(query, filters)
        for order in orders:
            order["resources"] = json.loads(order["resources"])
            order = utils_orders.format_order_display(order)

        return orders


async def update_order(location: int, update_values: dict, filters: dict, user_id: str):
    """
    Update order by order_id. Allow to set any values in the order and location of the record.
    """

    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)

        await crud.update(
            table="orders",
            update_values=update_values,
            filters=filters,
        )

        updated_joined_order = await _get_joined_order(crud, filters["order_id"])
        if location:
            await crud.update(
                table="records",
                update_values={"location": location},
                filters={"record_id": updated_joined_order["record_id"]},
            )

        # TODO: If location AVAILABLE_IN_READING_ROOM. Send message to user

        # Send message to user
        utils_orders.send_order_message("Order updated", updated_joined_order)

        # Insert log message
        await _insert_log_message(
            crud,
            order_id=updated_joined_order["order_id"],
            location=updated_joined_order["location"],
            user_status=updated_joined_order["user_status"],
            changed_by=user_id,
        )


async def get_orders_admin(completed: int = 0):
    """
    Get all orders for a user. Allow to set status and finished.
    """
    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)

        statuses_hidden = [utils_orders.STATUSES_USER.COMPLETED, utils_orders.STATUSES_USER.DELETED]
        completed_statuses_str = utils_orders.get_sql_in_str(statuses_hidden)

        statuses_hidden_with_queued = [
            utils_orders.STATUSES_USER.COMPLETED,
            utils_orders.STATUSES_USER.DELETED,
            utils_orders.STATUSES_USER.QUEUED,
        ]
        completed_statuses_str_with_queued = utils_orders.get_sql_in_str(statuses_hidden_with_queued)

        if completed:
            query = f"""
            SELECT * FROM orders o
            LEFT JOIN records r ON o.record_id = r.record_id
            LEFT JOIN users u ON o.user_id = u.user_id
            WHERE o.user_status IN ({completed_statuses_str})
            """
        else:
            # in admin view do not show orders that are queued
            query = f"""
            SELECT * FROM orders o
            LEFT JOIN records r ON o.record_id = r.record_id
            LEFT JOIN users u ON o.user_id = u.user_id
            WHERE o.user_status NOT IN ({completed_statuses_str_with_queued})
            """

        query += " ORDER BY o.order_id ASC"

        orders = await crud.query(query, {})
        for order in orders:
            order["resources"] = json.loads(order["resources"])
            order = utils_orders.format_order_display(order)
            order["count"] = await _count_active_users(crud, order["record_id"])

        return orders


async def _get_joined_order(crud: "CRUD", order_id: int):
    """
    Get joined order data by order_id
    """

    query = """
    SELECT * FROM orders o
    LEFT JOIN records r ON o.record_id = r.record_id
    LEFT JOIN users u ON o.user_id = u.user_id
    WHERE o.order_id = :order_id
    """
    order = await crud.query_one(query, {"order_id": order_id})
    order = dict(order)
    order["resources"] = json.loads(order["resources"])
    order = utils_orders.format_order_display(order)
    return order


async def get_order(order_id):
    """
    Get joined order data by order_id
    """
    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        return await _get_joined_order(CRUD(connection), order_id)


async def _get_active_order(user_id: str, record_id: str, statuses=None):
    database_connection = DatabaseConnection(orders_url)
    async with database_connection.transaction_scope_async() as connection:
        crud = CRUD(connection)
        query = f"""
        SELECT *
        FROM orders o
        LEFT JOIN records r ON o.record_id = r.record_id
        WHERE r.record_id = :record_id
        AND o.user_id = :user_id
        AND o.user_status NOT IN ({utils_orders.STATUSES_USER.COMPLETED}, {utils_orders.STATUSES_USER.DELETED});
        """
        order = await crud.query_one(query, {"user_id": user_id, "record_id": record_id})
        return order


async def _get_active_orders_by_record_id(crud: "CRUD", record_id: str):
    """
    Get all active orders connected to a record
    """
    query = f"""
    SELECT *
    FROM orders o
    LEFT JOIN records r ON o.record_id = r.record_id
    WHERE r.record_id = :record_id
    AND o.user_status NOT IN ({utils_orders.STATUSES_USER.COMPLETED}, {utils_orders.STATUSES_USER.DELETED})
    ORDER BY o.created_at ASC
    """
    orders = await crud.query(query, {"record_id": record_id})
    return orders


async def _count_active_users(crud: "CRUD", record_id: str):
    """
    Get count of active users on a record
    """
    rows = await _get_active_orders_by_record_id(crud, record_id)
    num_rows = len(rows)
    return num_rows


async def _insert_log_message(crud: "CRUD", order_id, location, user_status, changed_by):
    log_message = {
        "order_id": order_id,
        "location": location,
        "user_status": user_status,
        "changed_by": changed_by,
    }

    await crud.insert("orders_log", log_message)
