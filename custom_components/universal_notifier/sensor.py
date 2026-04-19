"""Sensor platform for Universal Notifier."""

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

if TYPE_CHECKING:
    from .store import NotificationStore

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

    def __init__(self, hass: HomeAssistant, store: "NotificationStore") -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._store = store
        self._attr_name = "Universal Notifier History"
        self._attr_unique_id = "universal_notifier_history"
        self._attr_icon = "mdi:bell-ring"
        self._recent_notifications = []
        self._last_count = -1  # Initialize to -1 to ensure first update fetches data

    @property
    def native_value(self) -> int:
        """Return the number of stored notifications."""
        return self._store.count

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        return {
            "total_count": self._store.count,
            "recent_notifications": self._recent_notifications,
        }

    async def async_update(self) -> None:
        """Update the sensor."""
        # Only fetch notifications if the count has changed
        if self._store.count != self._last_count:
            self._recent_notifications = await self._store.async_get_notifications(10)
            self._last_count = self._store.count

