"""Sensor platform for Polish Shipment Tracking."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, INTEGRATION_VERSION, CONF_PHONE, CONF_EMAIL
from .coordinator import ShipmentCoordinator
from .helpers import (
    get_parcel_id,
    get_raw_status,
    is_delivered,
    normalize_status,
)

_LOGGER = logging.getLogger(__name__)

ACTIVE_SHIPMENTS_UNIQUE_ID = f"{DOMAIN}_active_shipments"

<<<<<<< HEAD
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up the sensor platform."""
    coordinator: ShipmentCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Handle global active shipments sensor
    if "_active_shipments_sensor" not in hass.data[DOMAIN]:
        global_sensor = ActiveShipmentsSensor(hass)
        hass.data[DOMAIN]["_active_shipments_sensor"] = global_sensor
        async_add_entities([global_sensor])
    
    global_sensor = hass.data[DOMAIN]["_active_shipments_sensor"]
    global_sensor.attach_coordinator(coordinator)
    entry.async_on_unload(lambda: global_sensor.detach_coordinator(coordinator))
=======
_LABEL_TRANSLATIONS = {
    "parcel": {
        "pl": "Paczka",
        "en": "Parcel",
    },
    "active_shipments": {
        "pl": "Aktywne przesyłki",
        "en": "Active shipments",
    },
}

_STATUS_MAP = {
    "inpost": {
        "CREATED": "created",
        "CONFIRMED": "created",
        "OFFER_SELECTED": "created",
        "OFFERS_PREPARED": "created",
        "DISPATCHED_BY_SENDER": "in_transport",
        "DISPATCHED_BY_SENDER_TO_POK": "in_transport",
        "TAKEN_BY_COURIER": "in_transport",
        "TAKEN_BY_COURIER_FROM_POK": "in_transport",
        "COLLECTED_FROM_SENDER": "in_transport",
        "ADOPTED_AT_SOURCE_BRANCH": "in_transport",
        "ADOPTED_AT_SORTING_CENTER": "in_transport",
        "SENT_FROM_SOURCE_BRANCH": "in_transport",
        "SENT_FROM_SORTING_CENTER": "in_transport",
        "ADOPTED_AT_TARGET_BRANCH": "in_transport",
        "READDRESSED": "in_transport",
        "REDIRECT_TO_BOX": "in_transport",
        "PERMANENTLY_REDIRECTED_TO_BOX_MACHINE": "in_transport",
        "PERMANENTLY_REDIRECTED_TO_CUSTOMER_SERVICE_POINT": "in_transport",
        "UNSTACK_FROM_BOX_MACHINE": "in_transport",
        "AVIZO": "in_transport",
        "OUT_FOR_DELIVERY": "handed_out_for_delivery",
        "OUT_FOR_DELIVERY_TO_ADDRESS": "handed_out_for_delivery",
        "UNSTACK_FROM_CUSTOMER_SERVICE_POINT": "handed_out_for_delivery",
        "PICKUP_REMINDER_SENT_ADDRESS": "handed_out_for_delivery",
        "READY_TO_PICKUP": "waiting_for_pickup",
        "READY_FOR_COLLECTION": "waiting_for_pickup",
        "READY_TO_PICKUP_FROM_BRANCH": "waiting_for_pickup",
        "READY_TO_PICKUP_FROM_POK": "waiting_for_pickup",
        "READY_TO_PICKUP_FROM_POK_REGISTERED": "waiting_for_pickup",
        "PICKUP_REMINDER_SENT": "waiting_for_pickup",
        "STACK_IN_BOX_MACHINE": "waiting_for_pickup",
        "STACK_IN_CUSTOMER_SERVICE_POINT": "waiting_for_pickup",
        "AVIZO_COMPLETED": "waiting_for_pickup",
        "DELIVERED": "delivered",
        "COLLECTED_BY_CUSTOMER": "delivered",
        "RETURNED_TO_SENDER": "returned",
        "RETURN_PICKUP_CONFIRMATION_TO_SENDER": "returned",
        "NOT_COLLECTED": "returned",
        "PICKUP_TIME_EXPIRED": "returned",
        "STACK_PARCEL_PICKUP_TIME_EXPIRED": "returned",
        "STACK_PARCEL_IN_BOX_MACHINE_PICKUP_TIME_EXPIRED": "returned",
        "CANCELED": "cancelled",
        "CANCELLED": "cancelled",
        "CANCELED_REDIRECT_TO_BOX": "cancelled",
        "DELAY_IN_DELIVERY": "exception",
        "DELIVERY_ATTEMPT_FAILED": "exception",
        "UNDELIVERED": "exception",
        "UNDELIVERED_COD_CASH_RECEIVER": "exception",
        "UNDELIVERED_INCOMPLETE_ADDRESS": "exception",
        "UNDELIVERED_LACK_OF_ACCESS_LETTERBOX": "exception",
        "UNDELIVERED_NO_MAILBOX": "exception",
        "UNDELIVERED_NOT_LIVE_ADDRESS": "exception",
        "UNDELIVERED_UNKNOWN_RECEIVER": "exception",
        "UNDELIVERED_WRONG_ADDRESS": "exception",
        "REJECTED_BY_RECEIVER": "exception",
        "MISSING": "exception",
        "OVERSIZED": "exception",
        "CLAIMED": "exception",
        "COD_REJECTED": "exception",
        "C2X_REJECTED": "exception",
        "AVIZO_REJECTED": "exception",
        "COD_COMPLETED": "in_transport",
        "C2X_COMPLETED": "in_transport",
        "OTHER": "unknown",
    },
    "dpd": {
        "READY_TO_SEND": "created",
        "RECEIVED_FROM_SENDER": "in_transport",
        "SENT": "in_transport",
        "IN_TRANSPORT": "in_transport",
        "RECEIVED_IN_DEPOT": "in_transport",
        "REDIRECTED": "in_transport",
        "RESCHEDULED": "in_transport",
        "HANDED_OVER_FOR_DELIVERY": "handed_out_for_delivery",
        "READY_TO_PICK_UP": "waiting_for_pickup",
        "SELF_PICKUP": "waiting_for_pickup",
        "HARD_RESERVED": "waiting_for_pickup",
        "DELIVERED": "delivered",
        "PICKED_UP": "delivered",
        "RETURNED_TO_SENDER": "returned",
        "EXPIRED_PICKUP": "returned",
        "UNSUCCESSFUL_DELIVERY": "exception",
    },
    "dhl": {
        "NONE": "created",
        "SHIPMENTINPREPARATION": "created",
        "INPREPARATION": "created",
        "WAITINGFORCOURIERPICKUP": "created",
        "POSTED": "in_transport",
        "SENT": "in_transport",
        "POSTEDATPOINT": "in_transport",
        "PICKEDUPBYCOURIER": "in_transport",
        "ROUTE": "in_transport",
        "REDIRECTED": "in_transport",
        "REDIRECTEDTOPOINT": "in_transport",
        "DELIVERY": "handed_out_for_delivery",
        "FOR_DELIVERY": "handed_out_for_delivery",
        "DELIVERYTOPOINT": "handed_out_for_delivery",
        "DELIVERYTOLOCKER": "handed_out_for_delivery",
        "READY": "waiting_for_pickup",
        "DELIVEREDTOPOINT": "waiting_for_pickup",
        "DELIVEREDTOLOCKER": "waiting_for_pickup",
        "DELIVEREDTOPARCELLOCKER": "waiting_for_pickup",
        "DELIVEREDTOPICKUPPOINT": "waiting_for_pickup",
        "RETRIEVEDFROMPOINT": "delivered",
        "RETRIEVEDFROMLOCKER": "delivered",
        "DELIVERED": "delivered",
        "ROUTETOSENDER": "returned",
        "PARCELRETURNSTOSENDER": "returned",
        "PARCELRETURNEDTOSENDER": "returned",
        "RETURN": "returned",
        "RESIGNATED": "cancelled",
        "ERROR": "exception",
        "DELIVERYDELAY": "exception",
        "DELIVERYPROBLEM": "exception",
        "UNSUCCESSFULATTEMPTATDELIVERY": "exception",
        "SECONDUNSUCCESSFULATTEMPTATDELIVERY": "exception",
        "REFUSAL": "exception",
        "LOST": "exception",
        "DISPOSED": "exception",
    },
    "pocztex": {
        "PRZYGOTOWANA": "created",
        "NADANA": "in_transport",
        "W TRANSPORCIE": "in_transport",
        "W DORĘCZENIU": "handed_out_for_delivery",
        "W DORECZENIU": "handed_out_for_delivery",
        "AWIZOWANA": "waiting_for_pickup",
        "P_KWD": "waiting_for_pickup",
        "ODEBRANA W PUNKCIE": "delivered",
        "P_OWU": "delivered",
    },
}

_FINAL_STATUS_KEYS = {"delivered", "returned", "cancelled"}
ACTIVE_SHIPMENTS_OBJECT_ID = f"{DOMAIN}_active_shipments"
ACTIVE_SHIPMENTS_UNIQUE_ID = ACTIVE_SHIPMENTS_OBJECT_ID

_SHARED_STATUS_FALLBACK = {
    "pl": {
        "created": "Utworzona",
        "in_transport": "W transporcie",
        "handed_out_for_delivery": "Wydana do doręczenia",
        "waiting_for_pickup": "Gotowa do odbioru",
        "delivered": "Doręczona",
        "returned": "Zwrócona do nadawcy",
        "cancelled": "Anulowana",
        "exception": "Problem z doręczeniem",
        "unknown": "Nieznany status",
    },
    "en": {
        "created": "Created",
        "in_transport": "In transit",
        "handed_out_for_delivery": "Out for delivery",
        "waiting_for_pickup": "Ready for pickup",
        "delivered": "Delivered",
        "returned": "Returned to sender",
        "cancelled": "Cancelled",
        "exception": "Delivery issue",
        "unknown": "Unknown status",
    },
}


def _normalize_language(language):
    if not language:
        return "en"
    return str(language).replace("_", "-").split("-")[0].lower()


def _get_hass_language(hass):
    if not hass:
        return None
    lang = getattr(hass.config, "language", None)
    if lang:
        return lang
    locale = getattr(hass.config, "locale", None)
    if locale and getattr(locale, "language", None):
        return locale.language
    return None


def _translate_label(key, language):
    lang = _normalize_language(language)
    labels = _LABEL_TRANSLATIONS.get(key, {})
    return labels.get(lang) or labels.get("en") or key


def _get_translation_dirs(language):
    lang = _normalize_language(language)
    if lang in _TRANSLATION_DIRS:
        return _TRANSLATION_DIRS[lang]

    base = Path(__file__).resolve()
    root = base.parents[2] / "translations"
    candidates = []

    if lang == "pl":
        lang_dir = root / "pl"
        if lang_dir.exists():
            candidates.append(lang_dir)
        if root.exists():
            candidates.append(root)
    else:
        lang_dir = root / lang
        if lang_dir.exists():
            candidates.append(lang_dir)

    _TRANSLATION_DIRS[lang] = candidates
    return candidates


def _load_translation_map(filename, language):
    for base in _get_translation_dirs(language):
        path = base / filename
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            return {str(key).upper(): str(value) for key, value in data.items()}
        except Exception as err:
            _LOGGER.warning("Failed to load translation file %s: %s", path, err)
            return {}
    return {}


def _get_shared_translations(language):
    lang = _normalize_language(language)
    if lang in _SHARED_TRANSLATION_CACHE:
        return _SHARED_TRANSLATION_CACHE[lang]

    shared = _load_translation_map("shared.json", lang)
    if not shared:
        fallback = _SHARED_STATUS_FALLBACK.get(lang, _SHARED_STATUS_FALLBACK["en"])
        shared = {key.upper(): value for key, value in fallback.items()}
    _SHARED_TRANSLATION_CACHE[lang] = shared
    return shared


def _get_courier_translations(courier, language):
    lang = _normalize_language(language)
    cache_key = (lang, courier)
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]
    translations = _load_translation_map(f"{courier}.json", lang)
    _TRANSLATION_CACHE[cache_key] = translations
    return translations


def _normalize_status(raw_status, courier):
    status_text = str(raw_status or "").strip()
    if not status_text:
        return "unknown"

    status_upper = status_text.upper()
    courier_map = _STATUS_MAP.get(courier, {})
    if status_upper in courier_map:
        return courier_map[status_upper]

    status_lower = status_text.lower()
    status_ascii = status_lower.translate(str.maketrans("ąćęłńóśżź", "acelnoszz"))
    if status_lower in {"ready"}:
        return "waiting_for_pickup"
    if (
        "delivered to locker" in status_lower
        or "delivered to point" in status_lower
        or "delivered to parcel locker" in status_lower
        or "delivered to pickup point" in status_lower
    ):
        return "waiting_for_pickup"
    if "picked up" in status_lower or "collected by" in status_lower or "collected" in status_lower:
        return "delivered"
    if "ready for collection" in status_lower or "ready to pick" in status_lower or "ready for pick" in status_lower:
        return "waiting_for_pickup"
    if "pickup" in status_lower or "collection" in status_lower or "locker" in status_lower:
        return "waiting_for_pickup"
    if "delivered" in status_lower:
        return "delivered"
    if "awizo" in status_ascii:
        return "waiting_for_pickup"
    if "odebr" in status_ascii or "wydan" in status_ascii or "odebrane" in status_ascii:
        return "delivered"
    if "dorecz" in status_ascii or "dostarcz" in status_ascii:
        return "delivered"
    if "zwrot" in status_ascii or "odesl" in status_ascii:
        return "returned"
    if "anul" in status_ascii or "rezygn" in status_ascii:
        return "cancelled"
    if "problem" in status_ascii or "niedorecz" in status_ascii or "odmow" in status_ascii:
        return "exception"
    if "out for delivery" in status_lower or "handed over for delivery" in status_lower:
        return "handed_out_for_delivery"
    if "return" in status_lower or "returned" in status_lower:
        return "returned"
    if "cancel" in status_lower or "canceled" in status_lower or "cancelled" in status_lower:
        return "cancelled"
    if (
        "fail" in status_lower
        or "failed" in status_lower
        or "delay" in status_lower
        or "exception" in status_lower
        or "undeliver" in status_lower
        or "missing" in status_lower
        or "rejected" in status_lower
    ):
        return "exception"
    if (
        "transit" in status_lower
        or "in transport" in status_lower
        or "departed" in status_lower
        or "arrived" in status_lower
        or "processed" in status_lower
        or "received" in status_lower
        or "adopted" in status_lower
    ):
        return "in_transport"
    if (
        "created" in status_lower
        or "pre-transit" in status_lower
        or "label" in status_lower
        or "confirmed" in status_lower
        or "info received" in status_lower
        or "ready to send" in status_lower
    ):
        return "created"

    return "unknown"

def _ensure_json_payload(payload):
    try:
        return json.dumps(payload, ensure_ascii=False)
    except (TypeError, ValueError):
        return json.dumps(payload, ensure_ascii=False, default=str)

def _is_active_status(raw_status, courier):
    return _normalize_status(raw_status, courier) not in _FINAL_STATUS_KEYS

def _count_active_parcels(parcels, courier):
    if not parcels:
        return 0
    count = 0
    for parcel in parcels:
        raw_status = _get_raw_status(parcel, courier)
        if _is_active_status(raw_status, courier):
            count += 1
    return count

def get_active_shipments_unique_id():
    return ACTIVE_SHIPMENTS_UNIQUE_ID


def _translate_status(raw_status, courier, language):
    status_text = str(raw_status or "").strip()
    if not status_text:
        fallback = _SHARED_STATUS_FALLBACK.get(_normalize_language(language), _SHARED_STATUS_FALLBACK["en"])
        return _get_shared_translations(language).get("UNKNOWN", fallback["unknown"])

    courier_translations = _get_courier_translations(courier, language)
    translated = courier_translations.get(status_text.upper())
    if translated:
        return translated

    normalized = _normalize_status(status_text, courier)
    if courier == "pocztex" and normalized == "unknown":
        return status_text
    shared_translations = _get_shared_translations(language)
    return shared_translations.get(normalized.upper(), status_text)


def _get_raw_status(parcel_data, courier):
    if not parcel_data:
        return None
    if courier == "inpost":
        return parcel_data.get("status")
    if courier == "dpd":
        return (parcel_data.get("main_status") or {}).get("status")
    if courier == "dhl":
        return parcel_data.get("status")
    if courier == "pocztex":
        return _pick_pocztex_status(parcel_data)
    return None

def _pick_pocztex_id(parcel_data):
    if not parcel_data or not isinstance(parcel_data, dict):
        return None
    keys = [
        "trackingId",
        "trackingNumber",
        "trackingNo",
        "parcelNumber",
        "consignmentNumber",
        "shipmentNumber",
        "number",
        "id",
    ]
    for key in keys:
        if key in parcel_data and parcel_data[key] is not None:
            return str(parcel_data[key])
    return None

def _pick_pocztex_status(parcel_data):
    if not parcel_data or not isinstance(parcel_data, dict):
        return None
    status = parcel_data.get("status")
    if isinstance(status, str):
        return status
    state = parcel_data.get("state")
    if isinstance(state, str):
        return state
    state_code = parcel_data.get("stateCode")
    if state_code is not None:
        return str(state_code)
    if isinstance(status, dict):
        for key in ("name", "label", "description", "code"):
            if status.get(key) is not None:
                return str(status.get(key))
    for key in (
        "statusName",
        "statusText",
        "statusLabel",
        "statusDescription",
        "statusCode",
        "state",
        "stateCode",
    ):
        if parcel_data.get(key) is not None:
            return str(parcel_data.get(key))
    return None

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    coordinator.add_entities_callback = async_add_entities

    global_sensor = hass.data[DOMAIN].get("_active_shipments_sensor")
    if not global_sensor:
        global_sensor = ActiveShipmentsSensor(hass)
        hass.data[DOMAIN]["_active_shipments_sensor"] = global_sensor
        async_add_entities([global_sensor])
    global_sensor.attach_coordinator(coordinator)

    from .__init__ import _update_entities
    await _update_entities(hass, entry, coordinator)
>>>>>>> eab2013f176cb849baa1d59ca3db66b26f34f320

    @callback
    def async_update_parcels() -> None:
        """Add new sensors and remove old ones."""
        current_data = coordinator.data or []
        new_entities = []
        
        current_ids = set()
        for parcel in current_data:
            pid = get_parcel_id(parcel, coordinator.courier)
            if not pid or is_delivered(parcel, coordinator.courier):
                continue
            
            current_ids.add(pid)
            if pid not in coordinator.known_parcels:
                coordinator.known_parcels.add(pid)
                new_entities.append(ShipmentSensor(coordinator, parcel, pid))
        
        if new_entities:
            async_add_entities(new_entities)

        # Remove entities that are no longer present
        _async_remove_old_entities(hass, entry, coordinator, current_ids)
        
        # Keep track of active parcels for this coordinator
        coordinator.known_parcels.intersection_update(current_ids)

    entry.async_on_unload(coordinator.async_add_listener(async_update_parcels))
    async_update_parcels()

def _async_remove_old_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: ShipmentCoordinator,
    current_ids: set[str],
) -> None:
    """Remove entities that are no longer in the active parcels list."""
    registry = async_get_entity_registry(hass)
    current_unique_ids = {f"{coordinator.courier}_{pid}" for pid in current_ids}
    
    entities_to_remove = []
    for entity_entry in registry.entities.values():
        if (
            entity_entry.platform == DOMAIN
            and entity_entry.config_entry_id == entry.entry_id
            and entity_entry.unique_id != ACTIVE_SHIPMENTS_UNIQUE_ID
            and entity_entry.unique_id not in current_unique_ids
        ):
            entities_to_remove.append(entity_entry.entity_id)
            
    for entity_id in entities_to_remove:
        registry.async_remove(entity_id)

class ShipmentSensor(CoordinatorEntity[ShipmentCoordinator], SensorEntity):
    """Sensor for a single shipment."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:package-variant-closed"

    def __init__(
        self,
        coordinator: ShipmentCoordinator,
        parcel_data: dict,
        tracking_number: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._tracking_number = tracking_number
        self._courier = coordinator.courier
        
        # User requested including courier name in the entity name
        # We also add "Parcel" (Paczka) as in the example
        parcel_word = "Paczka" if coordinator.hass.config.language == "pl" else "Parcel"
        self._attr_name = f"{self._courier.title()} {parcel_word} {tracking_number}"
        self._attr_unique_id = f"{self._courier}_{tracking_number}"
        self._attr_translation_key = "shipment_status"
        self.parcel_data = parcel_data

        account_id = coordinator.entry.data.get(CONF_PHONE) or coordinator.entry.data.get(CONF_EMAIL)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=f"{self._courier.title()} ({account_id})",
            manufacturer="Polish Shipment Tracking",
            model=self._courier.title(),
            sw_version=INTEGRATION_VERSION,
        )

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        raw_status = get_raw_status(self.parcel_data, self._courier)
        return normalize_status(raw_status, self._courier)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {
            "courier": self._courier,
            "tracking_number": self._tracking_number,
        }
<<<<<<< HEAD
        
        raw_status = get_raw_status(self.parcel_data, self._courier)
=======
        if isinstance(self.parcel_data, dict) and "_raw_response" in self.parcel_data:
            raw_payload = self.parcel_data.get("_raw_response")
        else:
            raw_payload = self.parcel_data
        attrs["raw_response"] = _ensure_json_payload(raw_payload)
        raw_status = _get_raw_status(self.parcel_data, self._courier)
>>>>>>> eab2013f176cb849baa1d59ca3db66b26f34f320
        attrs["status_raw"] = raw_status
        
        # Include raw response for the custom card
        if "_raw_response" in self.parcel_data:
            attrs["raw_response"] = json.dumps(self.parcel_data["_raw_response"], ensure_ascii=False)
        else:
            attrs["raw_response"] = json.dumps(self.parcel_data, ensure_ascii=False)
            
        # Add courier specific attributes
        if self._courier == "inpost":
            self._add_inpost_attributes(attrs)
        elif self._courier == "dpd":
            self._add_dpd_attributes(attrs)
        elif self._courier == "pocztex":
            self._add_pocztex_attributes(attrs)
            
        return attrs

    def _add_inpost_attributes(self, attrs: dict) -> None:
        """Add InPost specific attributes."""
        sender = self.parcel_data.get("sender")
        if isinstance(sender, dict):
            attrs["sender"] = sender.get("name")
            
        pickup_point = self.parcel_data.get("pickUpPoint")
        if isinstance(pickup_point, dict):
            address = pickup_point.get("addressDetails") or {}
            street = address.get("street") or ""
            building = address.get("buildingNumber") or ""
            city = address.get("city") or ""
            parts = [p for p in [street, building, city] if p]
            attrs["location"] = ", ".join(parts)
            
        attrs["open_code"] = self.parcel_data.get("openCode")
        
        receiver = self.parcel_data.get("receiver")
        if isinstance(receiver, dict):
            phone = receiver.get("phoneNumber")
            if isinstance(phone, dict):
                attrs["phone_number"] = phone.get("value")

    def _add_dpd_attributes(self, attrs: dict) -> None:
        """Add DPD specific attributes."""
        sender = self.parcel_data.get("sender")
        if isinstance(sender, dict):
            attrs["sender"] = sender.get("name")

    def _add_pocztex_attributes(self, attrs: dict) -> None:
        """Add Pocztex specific attributes."""
        attrs["sender_name"] = self.parcel_data.get("senderName")
        attrs["recipient_name"] = self.parcel_data.get("recipientName")
        attrs["state_date"] = self.parcel_data.get("stateDate")
        attrs["direction"] = self.parcel_data.get("direction")
        attrs["pickup_date"] = self.parcel_data.get("pickupDate")
        history = self.parcel_data.get("history")
        if isinstance(history, list):
            attrs["history"] = history

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Find our parcel in the new data
        current_data = self.coordinator.data or []
        my_parcel = next(
            (p for p in current_data if get_parcel_id(p, self._courier) == self._tracking_number),
            None
        )
        
        if my_parcel:
            self.parcel_data = my_parcel
            self.async_write_ha_state()
        else:
            # If not found, it might be delivered or removed. 
            # The async_update_parcels listener will handle removal.
            pass

class ActiveShipmentsSensor(SensorEntity):
    """Sensor that counts active shipments across all accounts."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_icon = "mdi:package-variant"
    _attr_translation_key = "active_shipments"
    _attr_unique_id = ACTIVE_SHIPMENTS_UNIQUE_ID
    _attr_suggested_object_id = f"{DOMAIN}_active_shipments"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._coordinators: dict[ShipmentCoordinator, Any] = {}

    def attach_coordinator(self, coordinator: ShipmentCoordinator) -> None:
        """Attach a coordinator to this sensor."""
        if coordinator not in self._coordinators:
            self._coordinators[coordinator] = coordinator.async_add_listener(
                self.async_write_ha_state
            )

    def detach_coordinator(self, coordinator: ShipmentCoordinator) -> None:
        """Detach a coordinator from this sensor."""
        if coordinator in self._coordinators:
            unregister = self._coordinators.pop(coordinator)
            unregister()
            self.async_write_ha_state()

<<<<<<< HEAD
    @property
    def native_value(self) -> int:
        """Return the total count of active shipments."""
        total = 0
        for coordinator in self._coordinators:
            data = coordinator.data or []
            for parcel in data:
                if not is_delivered(parcel, coordinator.courier):
                    total += 1
        return total
=======

class ActiveShipmentsSensor(SensorEntity):
    _attr_should_poll = False

    def __init__(self, hass):
        self._hass = hass
        self._coordinators = {}
        self._attr_unique_id = get_active_shipments_unique_id()
        self._attr_suggested_object_id = ACTIVE_SHIPMENTS_OBJECT_ID
        self._attr_has_entity_name = True
        self._language = _normalize_language(_get_hass_language(hass))
        self._attr_name = _translate_label("active_shipments", self._language)
        self._attr_icon = "mdi:package-variant"

    async def async_added_to_hass(self):
        await self._async_ensure_entity_id()
        for coordinator in self._iter_coordinators():
            self.attach_coordinator(coordinator)

    @property
    def native_value(self):
        total = 0
        for coordinator in self._iter_coordinators():
            total += _count_active_parcels(coordinator.data or [], coordinator.courier)
        return total

    def attach_coordinator(self, coordinator):
        if coordinator in self._coordinators:
            return
        remove_listener = coordinator.async_add_listener(self._handle_coordinator_update)
        self._coordinators[coordinator] = remove_listener
        self._handle_coordinator_update()

    def detach_coordinator(self, coordinator):
        remove_listener = self._coordinators.pop(coordinator, None)
        if remove_listener:
            remove_listener()
        self._handle_coordinator_update()

    def _handle_coordinator_update(self):
        self.async_write_ha_state()

    def _iter_coordinators(self):
        if self._coordinators:
            for coordinator in list(self._coordinators.keys()):
                yield coordinator
            return
        data = self._hass.data.get(DOMAIN, {})
        for coordinator in data.values():
            if not getattr(coordinator, "courier", None):
                continue
            if not hasattr(coordinator, "data"):
                continue
            yield coordinator

    async def _async_ensure_entity_id(self):
        if not self.hass:
            return
        try:
            from homeassistant.helpers import entity_registry as er
        except Exception:
            return
        registry = er.async_get(self.hass)
        current_entity_id = registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            get_active_shipments_unique_id(),
        )
        if not current_entity_id:
            return
        desired_entity_id = f"sensor.{ACTIVE_SHIPMENTS_OBJECT_ID}"
        if current_entity_id == desired_entity_id:
            return
        if registry.async_get(desired_entity_id):
            return
        deleted = getattr(registry, "deleted_entities", None)
        if deleted and desired_entity_id in deleted:
            return
        try:
            registry.async_update_entity(current_entity_id, new_entity_id=desired_entity_id)
        except (ValueError, KeyError):
            return
>>>>>>> eab2013f176cb849baa1d59ca3db66b26f34f320
