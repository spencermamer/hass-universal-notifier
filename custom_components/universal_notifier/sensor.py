"""Sensor platform for Universal Notifier."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info: Optional[dict] = None,
) -> None:
    """Set up the Universal Notifier sensor platform."""
    if DOMAIN not in hass.data:
        return

    store = hass.data[DOMAIN].get("store")
    if not store:
        return

    async_add_entities([NotificationHistorySensor(hass, store)], True)


class NotificationHistorySensor(SensorEntity):
    """Sensor to display notification history."""

    def __init__(self, hass: HomeAssistant, store) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._store = store
        self._attr_name = "Universal Notifier History"
        self._attr_unique_id = "universal_notifier_history"
        self._attr_icon = "mdi:bell-ring"

    @property
    def native_value(self) -> int:
        """Return the number of stored notifications."""
        return self._store.count

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        # Get the most recent 10 notifications for attributes
        notifications = self._hass.loop.run_in_executor(
            None, self._store.async_get_notifications, 10
        )
        
        return {
            "total_count": self._store.count,
            "recent_notifications": self._store._notifications[:10] if self._store._notifications else [],
        }

    async def async_update(self) -> None:
        """Update the sensor."""
        # The store is updated in real-time, no need to fetch
        pass
