"""Notification data store for Universal Notifier."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "universal_notifier.notifications"
SAVE_DELAY = 1.0  # Delay in seconds before saving to disk


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
        self._save_task: Optional[asyncio.Task] = None

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

    async def _debounced_save(self) -> None:
        """Debounced save to reduce disk I/O operations."""
        await asyncio.sleep(SAVE_DELAY)
        await self.async_save()
        self._save_task = None

    def _schedule_save(self) -> None:
        """Schedule a debounced save operation."""
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
        self._save_task = self._hass.async_create_task(self._debounced_save())

    @staticmethod
    def _validate_json_serializable(data: Dict[str, Any], path: str = "") -> None:
        """Validate that data is JSON serializable using recursive type checking.
        
        Args:
            data: Dictionary to validate
            path: Current path in the data structure (for error messages)
            
        Raises:
            ValueError: If data contains non-serializable values
        """
        allowed_types = (str, int, float, bool, type(None))
        
        if isinstance(data, dict):
            for key, value in data.items():
                if not isinstance(key, str):
                    raise ValueError(f"Dictionary keys must be strings, got {type(key).__name__} at {path}.{key}")
                NotificationStore._validate_json_serializable(value, f"{path}.{key}" if path else key)
        elif isinstance(data, (list, tuple)):
            for idx, item in enumerate(data):
                NotificationStore._validate_json_serializable(item, f"{path}[{idx}]")
        elif not isinstance(data, allowed_types):
            raise ValueError(
                f"Value at {path} is not JSON serializable: {type(data).__name__}. "
                f"Only str, int, float, bool, None, list, and dict are allowed."
            )

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
            **kwargs: Additional notification data (e.g., skip_greeting, include_time, assistant_name)
                     All values must be JSON serializable.
            
        Raises:
            ValueError: If any kwargs contain non-JSON-serializable values
            
        Note:
            The notification is stored with the following structure:
            {
                "timestamp": ISO 8601 timestamp string,
                "message": str,
                "targets": List[str],
                "title": Optional[str],
                "priority": bool,
                **kwargs: Any additional fields passed to the function
            }
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
        
        # Add any additional data (skip_greeting, include_time, assistant_name, etc.)
        # Note: Base notification fields (timestamp, message, targets, title, priority)
        # cannot be overwritten by kwargs
        base_fields = {"timestamp", "message", "targets", "title", "priority"}
        for key, value in kwargs.items():
            if key not in base_fields:
                notification[key] = value

        # Validate that the notification is JSON serializable
        try:
            self._validate_json_serializable(notification)
        except ValueError as err:
            _LOGGER.error("Failed to add notification: %s", err)
            raise

        self._notifications.insert(0, notification)

        # Trim to max notifications
        if len(self._notifications) > self._max_notifications:
            self._notifications = self._notifications[: self._max_notifications]

        # Use debounced save to reduce disk I/O
        self._schedule_save()
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
        """Return the number of stored notifications.
        
        Note:
            This property does not trigger loading from disk. Ensure that
            ``await async_load()`` has been called before accessing this
            property to obtain an accurate count.
        """
        return len(self._notifications)
