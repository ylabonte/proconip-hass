"""Button platform for proconip."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from proconip import DIGITAL_INPUT_COUNT

from .const import DOMAIN
from .coordinator import ProconipPoolControllerDataUpdateCoordinator
from .entity import ProconipPoolControllerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Set up the button platform."""
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        ProconipDigitalInputTriggerButton(
            coordinator=coordinator,
            digital_input_no=i + 1,
            instance_id=entry.entry_id,
        )
        for i in range(DIGITAL_INPUT_COUNT)
    )


class ProconipDigitalInputTriggerButton(ProconipPoolControllerEntity, ButtonEntity):
    """ProCon.IP digital input trigger button class.

    A stateless momentary control that pulses one digital input, mirroring the
    push buttons in the controller's native web UI. The read-only digital-input
    sensors report state; this triggers it.
    """

    _attr_icon = "mdi:gesture-tap-button"
    _attr_translation_key = "digital_input_trigger"

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        digital_input_no: int,
        instance_id: str,
    ) -> None:
        """Initialize the digital input trigger button."""
        super().__init__(coordinator=coordinator)
        self._digital_input_id = digital_input_no - 1
        self._digital_input = self.coordinator.data.digital_input_objects[self._digital_input_id]
        self._attr_entity_registry_visible_default = self._digital_input.name != "n.a."
        self._attr_translation_placeholders = {
            "sensor_no": str(digital_input_no),
            "device_name": self._digital_input.name,
        }
        self._attr_unique_id = f"digital_input_trigger_{digital_input_no}_{instance_id}"

    async def async_press(self) -> None:
        """Trigger the digital input with a momentary pulse."""
        await self.coordinator.client.async_trigger_digital_input(
            digital_input_id=self._digital_input_id,
        )
        await self.coordinator.async_request_refresh()
