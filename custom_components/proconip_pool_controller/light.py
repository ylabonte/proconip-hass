"""Light platform for proconip."""

from __future__ import annotations

from homeassistant.components.light import (
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ProconipPoolControllerDataUpdateCoordinator
from .entity import ProconipPoolControllerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Set up the light platform."""
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    light_entities: list[ProconipPoolControllerEntity] = []
    if coordinator.data.is_dmx_enabled():
        # for i in range(16):
        light_entities.append(
            ProconipPoolControllerDmxLightEntity(
                coordinator=coordinator,
                name="Beispiel",
                dmx_channel_mapping={},
                instance_id=entry.entry_id,
            )
        )
    async_add_devices(light_entities)


class ProconipPoolControllerDmxLightEntity(ProconipPoolControllerEntity, LightEntity):
    """ProCon.IP Pool Controller helper class for dmx lights."""

    _attr_color_mode = ColorMode.RGBW
    _attr_rgbw_color = (255, 255, 255, 255)
    _attr_supported_color_modes = {ColorMode.RGBW}

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        name: str,
        dmx_channel_mapping: dict[str, int],
        instance_id: str,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator=coordinator)
        self._attr_name = f"DMX Light {name}"
        self._attr_unique_id = f"dmx_light_{name}_{instance_id}"
        self._attr_brightness = 0
