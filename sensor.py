import logging
import json

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (ATTR_IDENTIFIERS, ATTR_MANUFACTURER, ATTR_MODEL)
from homeassistant.helpers.device_registry import DeviceEntryType
from datetime import datetime

from .const import CONF_ADDRESS, DEVICE_AUTHOR, DEVICE_NAME, DOMAIN, DEVICE_VERSION, SENSOR_NAME, SENSOR_ATTRIB

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up platform for a new integration.   

    Called by the HA framework after async_setup_platforms has been called
    during initialization of a new integration.
    """
    worker = hass.data[DOMAIN]._worker
    entities = []

    entities.append(PirevaSensor(hass, worker, config_entry.data))

    async_add_entities(entities)


class PirevaSensor(SensorEntity):
    """Common functionality for all entities."""

    def __init__(self, hass, worker, config):
        self._worker = worker
        self._hass = hass
        # Use address directly as-is from config
        address = str(config[CONF_ADDRESS]).strip().lower().replace(" ", "")
        self._key = address
        self._address = address
        self._value = None

        self._update_sensor_listener = None

        # set HA instance attributes directly (don't use property)
        self._attr_unique_id = f"{DOMAIN}_{address}"
        self._attr_name = f"Sopor hämtning {config[CONF_ADDRESS]}"
        self._attr_icon = "mdi:trash-can"
        self._attr_device_info = {
            ATTR_IDENTIFIERS: {(DOMAIN, DEVICE_NAME)},
            ATTR_NAME: DEVICE_NAME,
            ATTR_MANUFACTURER: DEVICE_AUTHOR,
            ATTR_MODEL: "v"+DEVICE_VERSION,
            "entry_type": DeviceEntryType.SERVICE
        }

        #_LOGGER.info(self._worker.data)

        # Lyssna på pireva_changed events från __init__.py (async listener)
        self._unregister_listener = hass.bus.async_listen(
            f"{DOMAIN}_changed", self._on_pireva_changed
        )

    async def async_added_to_hass(self):
        """Run when entity is added to hass - trigger initial update."""
        await self.async_update()

    async def _on_pireva_changed(self, event):
        """Handle pireva_changed events and update sensor."""
        data = event.data
        action = data.get("action")
        address = data.get("address")
        
        _LOGGER.warning(f"Event mottaget: action={action}, address={address}, self._address={self._address}")
        
        if address == self._address and action in ("refresh", "add"):
            await self.async_update()
            self.async_write_ha_state()

    async def async_update(self):
        """Update the value of the entity."""
        _LOGGER.warning(f"PirevaSensor async_update körs för {self._address}")
        _LOGGER.warning(f"Worker data keys: {list(self._worker.data.keys())}")
        _LOGGER.warning(f"Looking for key: {self._key}")
        attributes = {}
        try:
            data_entry = self._worker.data.get(self._key)
            if not data_entry:
                _LOGGER.error(f"Ingen data för adressen {self._key}. Tillgängliga nycklar: {list(self._worker.data.keys())}")
                raise ValueError("ingen data för adressen")

            raw_json = data_entry.get('json', '')
            if isinstance(raw_json, str) and raw_json.startswith("Kunde inte hämta schemat"):
                raise ValueError(raw_json)

            j = json.loads(raw_json)
            next_list = j.get('nästa tömning', [])
            if not next_list:
                raise ValueError("nästa tömning saknas")
            nextEmptyDay = next_list[0]['datum']
            nextEmptyTyp = next_list[0]['typ']
            newDate = datetime.strptime(nextEmptyDay, "%Y-%m-%d")
            numDays = (newDate - datetime.now()).days+1

            attributes['last_update'] = data_entry.get('last_update')
            attributes['days_left'] = numDays
            attributes['address']  = data_entry.get('address')
            attributes['url']  = data_entry.get('url')
            attributes['next_day'] = nextEmptyDay
            attributes['next_typ'] = nextEmptyTyp
            attributes['schedule'] = j
            info_list = j.get('information', [])
            for idx, txt in enumerate(info_list, start=1):
                attributes[f"info{idx}"] = txt
            self._value = numDays
        except Exception as error:
            _LOGGER.error(
                "PirevaSensor update error for %s: %s | raw=%s",
                self._address,
                error,
                self._worker.data.get(self._key),
            )
            attributes['last_update'] = ''
            attributes['logo'] = ''
            attributes['days_left'] = ''
            attributes['address']  = ''
            attributes['next_day']  = '' 
            attributes['next_typ'] = ''
            attributes['schedule'] = {}     
            self._value = None

        self._attr_extra_state_attributes = attributes
        self._attr_attribution = SENSOR_ATTRIB

    @property
    def available(self):
        """Return true if value is valid."""
        return self._value is not None

    @property
    def native_value(self):
        """Return the value of the entity."""
        return self._value

    @property
    def device_class(self):
        """Return the class of this device."""
        return f"{DOMAIN}__providersensor"