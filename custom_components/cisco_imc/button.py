"""Button platform for Cisco IMC."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, POWER_ACTIONS

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class CiscoImcButtonEntityDescription(ButtonEntityDescription):
    """Describe a Cisco IMC button."""

    power_action: str


BUTTON_TYPES: tuple[CiscoImcButtonEntityDescription, ...] = (
    CiscoImcButtonEntityDescription(
        key="start",
        name="Start",
        icon="mdi:power",
        power_action=POWER_ACTIONS["start"],
    ),
    CiscoImcButtonEntityDescription(
        key="stop",
        name="Force Power Off",
        icon="mdi:power-off",
        power_action=POWER_ACTIONS["stop"],
    ),
    CiscoImcButtonEntityDescription(
        key="shutdown",
        name="Shutdown",
        icon="mdi:power-standby",
        power_action=POWER_ACTIONS["shutdown"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cisco IMC buttons."""

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        CiscoImcPowerButton(entry, coordinator, description)
        for description in BUTTON_TYPES
    )


class CiscoImcPowerButton(CoordinatorEntity, ButtonEntity):
    """Cisco IMC power control button."""

    entity_description: CiscoImcButtonEntityDescription

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator,
        description: CiscoImcButtonEntityDescription,
    ) -> None:
        """Initialize the button."""

        super().__init__(coordinator)

        self.entity_description = description
        self.imc = entry.data.get(CONF_IP_ADDRESS)[0]

        self._attr_name = f"{NAME} {self.imc} {description.name}"
        self._attr_unique_id = (
            f"{DOMAIN}_{self.imc.lower().replace('.', '_')}_{description.key}"
        )

    async def async_press(self) -> None:
        """Execute the selected power action."""

        desired_state = self.entity_description.power_action

        _LOGGER.warning(
            "Executing Cisco IMC power action %s on %s",
            desired_state,
            self.imc,
        )

        await self.hass.async_add_executor_job(
            self._set_admin_power,
            desired_state,
        )

        await self.coordinator.async_request_refresh()

    def _set_admin_power(self, desired_state: str) -> None:
        """Set the server administrative power state."""

        rack_unit = self.coordinator.client.query_dn("sys/rack-unit-1")

        if rack_unit is None:
            raise RuntimeError(
                f"Unable to retrieve rack unit from Cisco IMC {self.imc}"
            )

        rack_unit.admin_power = desired_state
        self.coordinator.client.set_mo(rack_unit)