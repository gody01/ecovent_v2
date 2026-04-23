"""Frontend registration for the EcoVent schedule dialog."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_FRONTEND_URL_BASE = f"/api/{DOMAIN}/frontend"
_DIALOG_JS = "ecovent-schedule-dialog.js"
_REGISTERED_KEY = f"{DOMAIN}_frontend_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Expose and register the schedule dialog frontend once."""
    if hass.data.get(_REGISTERED_KEY):
        return

    frontend_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                f"{_FRONTEND_URL_BASE}/{_DIALOG_JS}",
                str(frontend_dir / _DIALOG_JS),
                cache_headers=False,
            )
        ]
    )
    add_extra_js_url(hass, f"{_FRONTEND_URL_BASE}/{_DIALOG_JS}")
    hass.data[_REGISTERED_KEY] = True
