"""ProconipPoolControllerEntity class."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME, VERSION
from .coordinator import ProconipPoolControllerDataUpdateCoordinator


class ProconipPoolControllerEntity(CoordinatorEntity[ProconipPoolControllerDataUpdateCoordinator]):
    """ProconipPoolControllerEntity class."""

    _attr_attribution = ATTRIBUTION
    # Modern HA pattern: entity name is composed from the device name plus
    # the platform/translation_key-driven entity name. Subclasses set
    # `_attr_translation_key` (and `_attr_translation_placeholders` for
    # dynamic templates); the labels live in `translations/<lang>.json`
    # under `entity.<platform>.<key>.name`.
    _attr_has_entity_name = True

    def __init__(self, coordinator: ProconipPoolControllerDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        if self._attr_unique_id is None:
            self._attr_unique_id = coordinator.config_entry_id
        else:
            self._attr_unique_id = f"{coordinator.config_entry_id}-{self._attr_unique_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry_id)},
            name=NAME,
            model=VERSION,
            manufacturer=NAME,
        )
