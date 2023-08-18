"""BlueprintEntity class."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME, VERSION
from .coordinator import ProconipPoolControllerDataUpdateCoordinator


class ProconipPoolControllerEntity(CoordinatorEntity):
    """ProconipPoolControllerEntity class."""

    _attr_attribution = ATTRIBUTION

    coordinator: ProconipPoolControllerDataUpdateCoordinator

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        if self._attr_unique_id is None:
            self._attr_unique_id = coordinator.config_entry_id
        else:
            self._attr_unique_id = (
                f"{coordinator.config_entry_id}-{self._attr_unique_id}"
            )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry_id)},
            name=NAME,
            model=VERSION,
            manufacturer=NAME,
        )
