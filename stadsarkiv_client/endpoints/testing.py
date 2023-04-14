from starlette.requests import Request
from stadsarkiv_client.core.templates import templates
from stadsarkiv_client.core.context import get_context
from stadsarkiv_client.core import dynamic_settings
import json
from stadsarkiv_client.core.logging import get_log

log = get_log()


async def test(request: Request):

    settings = dynamic_settings.settings
    settings_json = json.dumps(settings, indent=4, ensure_ascii=False)
    context_variables = {'settings': settings_json, 'title': 'Test'}
    context = await get_context(request, context_variables)
    return templates.TemplateResponse("testing/test.html", context)
