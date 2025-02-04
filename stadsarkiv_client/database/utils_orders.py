from stadsarkiv_client.core.logging import get_log
import json
import dataclasses
from stadsarkiv_client.core import date_format
import arrow
from stadsarkiv_client.core import utils_core
from stadsarkiv_client.core import api
from stadsarkiv_client.core.mail import get_template_content
from stadsarkiv_client.core.dynamic_settings import settings


log = get_log()


@dataclasses.dataclass
class StatusesLocation:
    """
    Possible admin statuses for an order
    """

    IN_STORAGE: int = 1
    PACKED_STORAGE: int = 2
    # IN_STORAGE_DOKK1: int = 3
    READING_ROOM: int = 4
    RETURN_TO_STORAGE: int = 5


STATUSES_LOCATION = StatusesLocation()
STATUSES_LOCATION_HUMAN = {
    1: "På magasin",  # Initial status
    2: "Pakket til læsesal",
    # 3: "Depotrum på dokk1",
    4: "På læsesalen",
    5: "Pakket til magasin",
    # 6: "Tilbage på magasin",
}


@dataclasses.dataclass
class StatusesUser:
    """
    Possible user statuses for an order
    NOTICE: In /static/js/orders.js the statuses are copied from here
    """

    ORDERED: int = 1
    COMPLETED: int = 2
    QUEUED: int = 3
    DELETED: int = 4


STATUSES_USER = StatusesUser()
STATUSES_USER_HUMAN = {
    1: "Bestilt",
    2: "Afsluttet",
    3: "I kø",
    4: "Slettet",
}

# TEST
DATELINE_DAYS = 1


def get_insert_user_data(me: dict) -> dict:
    """
    Get user data for inserting into users table
    """
    return {
        "user_id": me["id"],
        "user_email": me["email"],
        "user_display_name": me["display_name"],
    }


def get_insert_record_data(meta_data: dict, record_and_types: dict, location: int = 0) -> dict:
    """
    Get material data for inserting into records table
    """
    if not location:
        location = STATUSES_LOCATION.IN_STORAGE

    data = {
        "record_id": meta_data["id"],
        "label": meta_data["meta_title"],
        "meta_data": json.dumps(meta_data),
        "record_and_types": json.dumps(record_and_types),
        "location": location,
    }

    return data


def get_order_data(user_id: str, record_id: str, user_status: int) -> dict:
    return {
        "user_id": user_id,
        "record_id": record_id,
        "user_status": user_status,
        "created_at": get_current_date_time(),
        "updated_at": get_current_date_time(),
    }


def format_order_display(order: dict):
    """
    Format dates in order for display. Change from UTC to Europe/Copenhagen
    """
    try:
        order["created_at"] = date_format.timezone_alter(order["created_at"])
        order["updated_at"] = date_format.timezone_alter(order["updated_at"])

        # log.debug(f"Order: {order['record_and_types']}")
        # Load json data
        order["record_and_types"] = json.loads(order["record_and_types"])
        order["meta_data_dict"] = json.loads(order["meta_data"])

        # Convert record_and_types to string
        record_and_types = order["record_and_types"]
        resources = order["meta_data_dict"]["resources"]

        used_keys = ["date_normalized", "series", "collection", "collectors"]
        record_and_types_strings = utils_core.get_record_and_types_as_strings(record_and_types, used_keys)
        record_and_types_strings.update(resources)

        order["collectors"] = record_and_types_strings.get("collectors", "")

        # Convert deadline to date string
        if order["deadline"]:
            deadline = date_format.timezone_alter(order["deadline"])
            deadline = arrow.get(deadline).format("YYYY-MM-DD")
            order["deadline"] = deadline

        # Convert statuses to human readable
        order["user_status_human"] = STATUSES_USER_HUMAN.get(order["user_status"])

        # Check if queued
        if order["user_status"] == STATUSES_USER.QUEUED:
            order["queued"] = True

        order["location_human"] = STATUSES_LOCATION_HUMAN.get(order["location"])
    except (json.JSONDecodeError, TypeError) as e:
        log.debug(f"Error: {e}")
        log.debug(f"{type(order['record_and_types'])}")

    return order


def format_log_display(log: dict):
    """
    Format dates in log for display. Change from UTC to Europe/Copenhagen
    """
    updated_location = STATUSES_LOCATION_HUMAN.get(log["updated_location"], "")
    update_user_status = STATUSES_USER_HUMAN.get(log["updated_user_status"], "")
    log["updated_location"] = updated_location
    log["updated_user_status"] = update_user_status

    # convert created_at to danish timezone
    log["updated_at"] = format_order_display(log)["updated_at"]

    return log


def get_deadline_date() -> str:

    utc_now = arrow.utcnow()
    deadline = utc_now.shift(days=DATELINE_DAYS)

    # Return deadline as datetime string (suitable for sqlite)
    return deadline.format("YYYY-MM-DD HH:mm:ss")


def get_current_date_time() -> str:
    return arrow.utcnow().format("YYYY-MM-DD HH:mm:ss")


async def send_order_message(message: str, order: dict):

    title = "Din bestilling er klar til gennemsyn"
    template_values = {
        "title": title,
        "order": order,
        "client_domain_url": settings["client_url"],
        "client_name": settings["client_name"],
    }

    html_content = await get_template_content("mails/order_mail.html", template_values)
    mail_dict = {
        "data": {
            "user_id": order["user_id"],
            "subject": title,
            "sender": {"email": settings["client_email"], "name": settings["client_name"]},
            "reply_to": {"email": settings["client_email"], "name": settings["client_name"]},
            "html_content": html_content,
            "text_content": html_content,
        }
    }

    await api.mail_post(mail_dict)
    log.info(f"Send mail message: {message} Order: {order['order_id']}")
