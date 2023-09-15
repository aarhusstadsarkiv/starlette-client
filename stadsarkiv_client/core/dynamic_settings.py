"""
Override default settings with local settings.
Override default settings_facets with local settings_facets.
This is only run one time when the server starts.
"""

from stadsarkiv_client.settings import settings
from stadsarkiv_client.settings_facets import settings_facets as settings_facets_default
from stadsarkiv_client.core.logging import get_log

log = get_log()

log.debug("Loading dynamic settings")


settings_local: dict = {}


try:
    from settings import settings as settings_local  # type: ignore

    log.debug("Loaded local settings file: settings.py")
except ImportError:
    log.debug("Local settings file NOT loaded: settings.py")
    pass

settings.update(settings_local)


def get_setting(key):
    return settings.get(key, None)


settings_facets_local: dict = {}

try:
    from settings_facets import settings_facets as settings_facets_local  # type: ignore

    log.debug("Loaded local settings_facets.py file: settings_facets.py")

except ImportError:
    log.debug("Local settings_facets.py file NOT loaded: settings_facets.py")
    pass

if settings_facets_local:
    settings_facets = settings_facets_local
else:
    settings_facets = settings_facets_default
