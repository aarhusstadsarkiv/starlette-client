"""
Bookmark sendpoints.
"""

from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse
from stadsarkiv_client.core.templates import templates
from stadsarkiv_client.core.context import get_context
from stadsarkiv_client.core.auth import is_authenticated, is_authenticated_json
from stadsarkiv_client.core import flash
from stadsarkiv_client.core.translate import translate
from stadsarkiv_client.core.user_data import UserData
from stadsarkiv_client.core.logging import get_log
from stadsarkiv_client.core.api import OpenAwsException
from stadsarkiv_client.core import api
from stadsarkiv_client.records.meta_data_record import get_record_meta_data
from stadsarkiv_client.records import normalize_dates


log = get_log()


async def bookmarks(request: Request):
    """User bookmarks page."""

    await is_authenticated(request)
    try:
        me = await api.me_get(request)
        user_data = UserData(me)
        bookmarks = user_data.get_bookmarks_list()

        records = await api.proxies_resolve(request, bookmarks)

        bookmarks_data = []

        for record in records:

            record = normalize_dates.normalize_dates(record)
            meta_data = get_record_meta_data(request, record)

            record_id = meta_data["id"]
            record_link = f"/records/{record_id}"
            title = meta_data.get("title")
            date_normalized = record.get("date_normalized")
            collection_label = record.get("collection", {}).get("label", "")
            content_types_label = meta_data.get("content_types_label")

            bookmark_data = {
                "record_id": record_id,
                "record_link": record_link,
                "title": title,
                "date_normalized": date_normalized,
                "collection_label": collection_label,
                "content_types": content_types_label,
            }

            bookmarks_data.append(bookmark_data)

        context_values = {"title": translate("Your bookmarks"), "me": me, "bookmarks_data": bookmarks_data}
        context = await get_context(request, context_values=context_values)

        return templates.TemplateResponse(request, "auth/bookmarks.html", context)
    except OpenAwsException as e:
        flash.set_message(request, str(e), type="error")
    except Exception as e:
        log.exception(e)
        flash.set_message(request, str(e), type="error")
        return RedirectResponse(url="/auth/login", status_code=302)


async def bookmarks_json(request: Request):
    """Get user bookmarks as JSON"""
    try:
        me = await api.me_get(request)
        user_data = UserData(me)
        bookmarks = user_data.get_bookmarks()
        return JSONResponse(bookmarks, status_code=200)
    except OpenAwsException as e:
        log.exception(e)
        json_data = {"message": str(e), "error": True}
        return JSONResponse(json_data, status_code=400)


async def bookmarks_post(request: Request):
    """
    POST request to bookmark a record.
    """

    message = translate("You need to be logged in as user in order to bookmark a record.")
    await is_authenticated_json(request, ["user"], message=message)

    try:

        me = await api.users_me_get(request)
        json_data = await request.json()

        user_data = UserData(me)
        if json_data["action"] == "remove":
            user_data.remove_bookmark(json_data["record_id"])
        else:
            user_data.append_bookmark(json_data["record_id"])

        data = user_data.get_data()
        await api.users_data_post(request, data)

    except OpenAwsException as e:
        log.exception(e)
        json_data = {"message": str(e), "error": True}
        return JSONResponse(json_data, status_code=400)

    except Exception as e:
        log.exception(e)
        json_data = {"message": str(e), "error": True}
        return JSONResponse(json_data, status_code=400)

    if json_data["action"] == "add":
        message = translate("Bookmark has been added.")
    else:
        message = translate("Bookmark has been removed.")

    json_data = {"message": message, "user_data": json_data, "error": False}
    return JSONResponse(json_data, status_code=200)
