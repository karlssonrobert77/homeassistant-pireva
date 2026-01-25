"""Constants for the component."""

from pathlib import Path
import json

# Component domain, used to store component data in hass data.
DOMAIN = "pireva"


def _load_manifest_version() -> str:
	"""Read version from manifest.json to keep single source of truth."""
	try:
		manifest_path = Path(__file__).parent / "manifest.json"
		with manifest_path.open("r", encoding="utf-8") as f:
			manifest = json.load(f)
		return str(manifest.get("version", "0.0.0"))
	except Exception:
		return "0.0.0"


VERSION = _load_manifest_version()
DEVICE_VERSION = VERSION

SENSOR_NAME = "Pireva Garbage Pickup"

DEVICE_NAME = "Pireva Garbage Collection"
DEVICE_AUTHOR = "Robert Karlsson"

CONF_ADDRESS = "address"            # Address format: "street-number" (e.g. vag-nr)

SENSOR_ATTRIB = "Data from Pireva (https://www.pireva.se)"

