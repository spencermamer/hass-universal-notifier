"""Notification data store for Universal Notifier."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "universal_notifier.notifications"


class NotificationStore:
    """Class to manage notification history storage."""

    def __init__(self, hass: HomeAssistant, max_notifications: int = 100):
        """Initialize the notification store.
        
        Args:
            hass: Home Assistant instance
            max_notifications: Maximum number of notifications to store
        """
        self._hass = hass
        self._max_notifications = max_notifications
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._notifications: List[Dict[str, Any]] = []
        self._loaded = False

    async def async_load(self) -> None:
        """Load stored notifications from disk."""
        if self._loaded:
            return

        try:
            data = await self._store.async_load()
            if data:
                self._notifications = data.get("notifications", [])
                _LOGGER.debug(
                    "Loaded %d notifications from storage", len(self._notifications)
                )
            else:
                self._notifications = []
            self._loaded = True
        except Exception as err:
            _LOGGER.error("Error loading notification history: %s", err)
            self._notifications = []
            self._loaded = True

    async def async_save(self) -> None:
        """Save notifications to disk."""
        try:
            await self._store.async_save({"notifications": self._notifications})
        except Exception as err:
            _LOGGER.error("Error saving notification history: %s", err)

    async def async_add_notification(
        self,
        message: str,
        targets: List[str],
        title: Optional[str] = None,
        priority: bool = False,
        **kwargs: Any,
    ) -> None:
        """Add a notification to the store.
        
        Args:
            message: Notification message
            targets: List of target channels
            title: Optional notification title
            priority: Whether this is a priority notification
            **kwargs: Additional notification data
        """
        if not self._loaded:
            await self.async_load()

        notification = {
            "timestamp": dt_util.now().isoformat(),
            "message": message,
            "targets": targets,
            "title": title,
            "priority": priority,
        }
        
        # Add any additional data
        for key, value in kwargs.items():
            if key not in notification:
                notification[key] = value

        self._notifications.insert(0, notification)

        # Trim to max notifications
        if len(self._notifications) > self._max_notifications:
            self._notifications = self._notifications[: self._max_notifications]

        await self.async_save()
        _LOGGER.debug("Added notification to store: %s", notification)

    async def async_get_notifications(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get stored notifications.
        
        Args:
            limit: Optional limit on number of notifications to return
            
        Returns:
            List of notifications
        """
        if not self._loaded:
            await self.async_load()

        if limit:
            return self._notifications[:limit]
        return self._notifications

    async def async_clear_notifications(self) -> None:
        """Clear all stored notifications."""
        self._notifications = []
        await self.async_save()
        _LOGGER.debug("Cleared notification history")

    @property
    def count(self) -> int:
        """Return the number of stored notifications."""
        return len(self._notifications)
