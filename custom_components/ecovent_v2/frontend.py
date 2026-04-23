"""Frontend registration for the EcoVent schedule panel."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_FRONTEND_URL_BASE = f"/api/{DOMAIN}/frontend"
_PANEL_URL_PATH = "ecovent-v2"
_PANEL_MODULE_NAME = "ecovent-schedule-panel"
_PANEL_JS = "ecovent-schedule-panel.js"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Expose and register the schedule panel once."""
    if DOMAIN in hass.data.get("frontend_panels", {}):
        return

    frontend_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                f"{_FRONTEND_URL_BASE}/{_PANEL_JS}",
                str(frontend_dir / _PANEL_JS),
                cache_headers=False,
            )
        ]
    )

    async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title="Ventilation",
        sidebar_icon="mdi:fan",
        frontend_url_path=_PANEL_URL_PATH,
        config={
            "_panel_custom": {
                "name": _PANEL_MODULE_NAME,
                "embed_iframe": True,
                "trust_external": False,
                "js_url": f"{_FRONTEND_URL_BASE}/{_PANEL_JS}",
            }
        },
        require_admin=False,
    )
