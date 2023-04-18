from starlette.requests import Request
from starlette.exceptions import HTTPException
from stadsarkiv_client.core.templates import templates
from stadsarkiv_client.core.context import get_context
from stadsarkiv_client.core.translate import translate
from stadsarkiv_client.core.logging import get_log
from stadsarkiv_client.core import api
import json
from stadsarkiv_client.core.alter_records import alter_record
from stadsarkiv_client.core.openaws import (
    SchemaRead,
    EntityRead,
    RecordsIdGet,
)


log = get_log()


async def get_records_search(request: Request):
    try:
        context_values = {"title": translate("Search")}
        context = await get_context(request, context_values=context_values)
        return templates.TemplateResponse("records/search.html", context)

    except Exception as e:
        # for sure this is a 404
        raise HTTPException(404, detail=str(e), headers=None)


async def get_records_search_results(request: Request):
    try:
        context_values = {"title": translate("Search results")}
        context = await get_context(request, context_values=context_values)
        return templates.TemplateResponse("records/search.html", context)

    except Exception as e:
        # for sure this is a 404
        raise HTTPException(404, detail=str(e), headers=None)


async def get_record_view(request: Request):
    try:
        record: RecordsIdGet = await api.record_read(request)
        record_dict = record.to_dict()
        record_dict = alter_record(record_dict)

        record_json = json.dumps(record_dict, indent=4, ensure_ascii=False)
        context_values = {
            "title": translate("Entity"),
            "record_dict": record_dict,
            "record_json": record_json,
        }

        context = await get_context(request, context_values=context_values)
        return templates.TemplateResponse("records/record.html", context)

    except Exception as e:
        # for sure this is a 404
        log.exception(e)
        raise HTTPException(404, detail=str(e), headers=None)
