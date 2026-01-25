"""Pireva tömmnings schema"""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_ADDRESS, DOMAIN
from .woker import HttpWorker
from . import config_flow  # noqa: F401

_LOGGER = logging.getLogger(__name__)


PLATFORMS = ["sensor"]

async def async_setup(hass, config):
    """Set up HASL integration"""
    
    # SERVICE FUNCTIONS
    @callback
    async def fetch_data(crapdata):
        await hass.async_add_executor_job(hass.data[DOMAIN]._fetch)
        return True

    hass.services.async_register(DOMAIN, 'fetch_data', fetch_data)

    return True

async def async_migrate_entry(hass, config_entry: ConfigEntry):
    return True

async def reload_entry(hass, entry):
    """Reload HASL."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up component from a config entry, config_entry contains data from config entry database."""
    # store worker object
    if (DOMAIN in hass.data):
        worker = hass.data[DOMAIN]
    else:
        worker = hass.data.setdefault(DOMAIN, PirevaWorker(hass))

    # add pollen region to worker
    worker.add_entry(entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await worker._fetch()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        worker = hass.data[DOMAIN]
        worker.remove_entry(entry)
        if worker.is_idle():
            # also remove worker if not used by any entry any more
            del hass.data[DOMAIN]

    return unload_ok


class PirevaWorker:
    """worker object. Stored in hass.data."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the instance."""
        self._hass = hass
        self._worker = HttpWorker()
        self._fetch_callback_listener = None
        self._area_street = {}

    @property
    def worker(self):
        return self._worker

    @property
    def postalcodes(self):
        return self._area_street

    def add_entry(self, config_entry: ConfigEntry):
        """Add entry."""
        address = config_entry.data[CONF_ADDRESS].strip()
        self._hass.bus.fire(f"{DOMAIN}_changed", {"action": "add", "address": address})
        if self.is_idle():
           # This is the first entry, therefore start the timer
           self._fetch_callback_listener = async_track_time_interval(self._hass, self._fetch_callback, timedelta(days=1))

        self._area_street[address] = config_entry

    def remove_entry(self, config_entry: ConfigEntry):
        """Remove entry."""
        address = config_entry.data[CONF_ADDRESS]
        self._hass.bus.fire(f"{DOMAIN}_changed", {"action": "remove", "address": address})
        self._area_street.pop(address)

        if self.is_idle():
            # This was the last region, therefore stop the timer
            remove_listener = self._fetch_callback_listener
            if remove_listener is not None:
                remove_listener()

    def is_idle(self) -> bool:
        return not bool(self._area_street)

    async def _fetch_callback(self, *_):
        await self._fetch()

    async def _fetch(self, *_):
        for address in self._area_street:
            try:
                _LOGGER.error(address)
                # run blocking fetch in executor
                await self._hass.async_add_executor_job(self._worker.fetch, address)
                self._hass.bus.async_fire(
                    f"{DOMAIN}_changed",
                    {"action": "refresh", "address": address},
                )
            except Exception as error:
                _LOGGER.error(f"fetch data failed : {error}")
