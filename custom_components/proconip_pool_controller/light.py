"""Light platform for proconip — DMX-channel lights."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DMX_LIGHTS, DOMAIN, LOGGER
from .coordinator import ProconipPoolControllerDataUpdateCoordinator
from .entity import ProconipPoolControllerEntity

LIGHT_TYPE_CHANNEL_COUNT = {"dimmer": 1, "rgb": 3, "rgbw": 4}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the light platform."""
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    lights_config = entry.options.get(CONF_DMX_LIGHTS, [])
    entities: list[ProconipPoolControllerEntity] = []
    for light in lights_config:
        cls = _entity_class_for_type(light["type"])
        if cls is None:
            LOGGER.warning(
                "Unknown DMX light type %r — skipping %r",
                light["type"],
                light.get("name"),
            )
            continue
        entities.append(
            cls(
                coordinator=coordinator,
                instance_id=entry.entry_id,
                slug=light["slug"],
                name=light["name"],
                start_channel=light["start_channel"],
            )
        )
    async_add_devices(entities)


def _entity_class_for_type(light_type: str) -> type[ProconipDmxLightEntityBase] | None:
    return {
        "dimmer": ProconipDmxDimmerLight,
        "rgb": ProconipDmxRgbLight,
        "rgbw": ProconipDmxRgbwLight,
    }.get(light_type)


class ProconipDmxLightEntityBase(ProconipPoolControllerEntity, LightEntity):
    """Shared base for DMX light entities."""

    _channel_count: int = 1
    _attr_translation_key = "dmx_light"

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        instance_id: str,
        slug: str,
        name: str,
        start_channel: int,
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._slug = slug
        self._start_channel = start_channel
        self._attr_translation_placeholders = {"device_name": name}
        self._attr_unique_id = f"dmx_light_{slug}_{instance_id}"

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self.coordinator.dmx_shadow is not None

    def _read_channels(self) -> list[int]:
        shadow = self.coordinator.dmx_shadow
        if shadow is None:
            return [0] * self._channel_count
        start_idx = self._start_channel - 1
        return [int(shadow[start_idx + i].value) for i in range(self._channel_count)]

    def _write_channels(self, values: list[int]) -> None:
        shadow = self.coordinator.dmx_shadow
        if shadow is None:
            return
        start_idx = self._start_channel - 1
        for i, v in enumerate(values):
            shadow.set(start_idx + i, max(0, min(255, int(v))))
        self.coordinator.schedule_dmx_flush()

    @property
    def is_on(self) -> bool:
        return any(v > 0 for v in self._read_channels())


class ProconipDmxDimmerLight(ProconipDmxLightEntityBase):
    _channel_count = 1
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def brightness(self) -> int | None:
        return self._read_channels()[0]

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        self._write_channels([brightness])
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._write_channels([0])
        await self.coordinator.async_request_refresh()


class ProconipDmxRgbLight(ProconipDmxLightEntityBase):
    _channel_count = 3
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        r, g, b = self._read_channels()
        return r, g, b

    @property
    def brightness(self) -> int | None:
        return max(self._read_channels())

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
        elif self.is_on:
            r, g, b = self.rgb_color
        else:
            r, g, b = 255, 255, 255
        if ATTR_BRIGHTNESS in kwargs:
            # Scale so the brightest channel equals the requested brightness;
            # naive `value * brightness / 255` would silently dim the colour
            # on every slider change because the max channel is rarely 255.
            current_max = max(r, g, b)
            if current_max > 0:
                scale = kwargs[ATTR_BRIGHTNESS] / current_max
                r, g, b = (
                    int(round(r * scale)),
                    int(round(g * scale)),
                    int(round(b * scale)),
                )
        self._write_channels([r, g, b])
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._write_channels([0, 0, 0])
        await self.coordinator.async_request_refresh()


class ProconipDmxRgbwLight(ProconipDmxLightEntityBase):
    _channel_count = 4
    _attr_color_mode = ColorMode.RGBW
    _attr_supported_color_modes = {ColorMode.RGBW}

    @property
    def rgbw_color(self) -> tuple[int, int, int, int]:
        r, g, b, w = self._read_channels()
        return r, g, b, w

    @property
    def brightness(self) -> int | None:
        return max(self._read_channels())

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_RGBW_COLOR in kwargs:
            r, g, b, w = kwargs[ATTR_RGBW_COLOR]
        elif self.is_on:
            r, g, b, w = self.rgbw_color
        else:
            r, g, b, w = 0, 0, 0, 255
        if ATTR_BRIGHTNESS in kwargs:
            # Scale so the brightest channel equals the requested brightness;
            # see ProconipDmxRgbLight.async_turn_on for the same fix.
            current_max = max(r, g, b, w)
            if current_max > 0:
                scale = kwargs[ATTR_BRIGHTNESS] / current_max
                r, g, b, w = (
                    int(round(r * scale)),
                    int(round(g * scale)),
                    int(round(b * scale)),
                    int(round(w * scale)),
                )
        self._write_channels([r, g, b, w])
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._write_channels([0, 0, 0, 0])
        await self.coordinator.async_request_refresh()
