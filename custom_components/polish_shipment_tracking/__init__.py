from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, CoreState, EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import config_validation as cv
from homeassistant.components import websocket_api
import voluptuous as vol

from .const import DOMAIN, PLATFORMS, INTEGRATION_VERSION
from .frontend import JSModuleRegistration
from .coordinator import ShipmentCoordinator
from .sensor import ShipmentSensor, _pick_pocztex_id, _pick_pocztex_status, _normalize_status

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Shipment Tracking integration and register frontend resources."""
    hass.data.setdefault(DOMAIN, {})

    async def async_register_frontend(_event=None) -> None:
        """Register the JavaScript modules after Home Assistant startup."""
        module_register = JSModuleRegistration(hass)
        await module_register.async_register()

    # Websocket handler to expose the integration version to the frontend.
    @websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/version"})
    @websocket_api.async_response
    async def websocket_get_version(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Handle version requests from the frontend."""
        connection.send_result(msg["id"], {"version": INTEGRATION_VERSION})

    # Register the websocket command.
    websocket_api.async_register_command(hass, websocket_get_version)

    # Schedule frontend registration based on HA state.
    if hass.state == CoreState.running:
        await async_register_frontend()
    else:
        # Wait for Home Assistant to start before registering.
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, async_register_frontend)

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = ShipmentCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register the sensor platform, while managing entities manually.
    coordinator.add_entities_callback = None
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    entry.async_on_unload(
        coordinator.async_add_listener(
            lambda: hass.async_create_task(_update_entities(hass, entry, coordinator))
        )
    )
    
    return True

async def _update_entities(hass, entry, coordinator):
    """Check for new parcels and add sensors."""
    if not hasattr(coordinator, "known_parcels"):
        coordinator.known_parcels = set()
    
    new_entities = []
    current_data = coordinator.data or []
    current_ids = set()
    
    for parcel in current_data:
        pid = _get_parcel_id(parcel, coordinator.courier)
        
        if not pid:
            continue

        if _is_delivered(parcel, coordinator.courier):
            continue

        current_ids.add(pid)
        if pid not in coordinator.known_parcels:
            coordinator.known_parcels.add(pid)
            new_entities.append(ShipmentSensor(coordinator, parcel, coordinator.courier))
    
    if new_entities and coordinator.add_entities_callback:
        coordinator.add_entities_callback(new_entities)

    # Remove entities that are no longer present in the API response.
    current_unique_ids = {f"{coordinator.courier}_{pid}" for pid in current_ids}
    registry = er.async_get(hass)
    remove_entity_ids = []

    for entity_entry in registry.entities.values():
        if entity_entry.domain != "sensor":
            continue
        if entity_entry.platform != DOMAIN:
            continue
        if entity_entry.config_entry_id != entry.entry_id:
            continue
        if not entity_entry.unique_id:
            continue
        if entity_entry.unique_id not in current_unique_ids:
            remove_entity_ids.append(entity_entry.entity_id)

    if remove_entity_ids:
        for entity_id in remove_entity_ids:
            registry.async_remove(entity_id)

    # Keep in sync with the latest parcel list.
    coordinator.known_parcels.intersection_update(current_ids)

def _get_parcel_id(data, courier):
    if courier == "inpost": return data.get("shipmentNumber")
    if courier == "dpd": return data.get("waybill")
    if courier == "dhl": return data.get("shipmentNumber")
    if courier == "pocztex": return _pick_pocztex_id(data)
    return None

def _is_delivered(data, courier):
    status = ""
    if courier == "inpost":
        status = data.get("status") or ""
    elif courier == "dpd":
        status = (data.get("main_status") or {}).get("status") or ""
    elif courier == "dhl":
        status = data.get("status") or ""
    elif courier == "pocztex":
        status = _pick_pocztex_status(data) or ""

    status_norm = str(status).strip().lower()
    if not status_norm:
        return False

    delivered_markers = {
        "delivered",
        "delivered_to_pickup_point",
        "delivered_to_boxmachine",
        "delivered_to_address",
        "delivered_to_machine",
        "delivered_to_parcel_locker",
        "delivered_to_shop",
        "delivered_to_branch",
    }
    if status_norm in delivered_markers:
        return True

    if courier == "pocztex":
        return _normalize_status(status, courier) == "delivered"

    return "delivered" in status_norm

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if not hass.data.get(DOMAIN):
            await JSModuleRegistration(hass).async_unregister()
    return unload_ok
