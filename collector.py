import json
import logging
import os
import time

import paho.mqtt.client as mqtt
from fusion_solar_py.client import FusionSolarClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

# --- Config from environment ---
FS_USER = os.environ["FUSIONSOLAR_USER"]
FS_PASSWORD = os.environ["FUSIONSOLAR_PASSWORD"]
FS_SUBDOMAIN = os.environ.get("FUSIONSOLAR_SUBDOMAIN", "uni005eu5")

MQTT_HOST = os.environ["MQTT_HOST"]
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_USER = os.environ.get("MQTT_USER")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD")
MQTT_DISCOVERY_PREFIX = os.environ.get("MQTT_DISCOVERY_PREFIX", "homeassistant")
MQTT_STATE_TOPIC = os.environ.get("MQTT_STATE_TOPIC", "fusionsolar/state")

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", 300))

DEVICE_INFO = {
    "identifiers": ["fusionsolar"],
    "name": "FusionSolar",
    "manufacturer": "Huawei",
    "model": "SmartPVMS",
}

# --- Sensor definitions for HA auto-discovery ---
SENSORS = [
    {
        "id": "current_power",
        "name": "Solar Current Power",
        "unit": "kW",
        "device_class": "power",
        "state_class": "measurement",
        "value_key": "current_power_kw",
        "icon": "mdi:solar-power",
    },
    {
        "id": "energy_today",
        "name": "Solar Energy Today",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "value_key": "energy_today_kwh",
        "icon": "mdi:solar-power",
    },
    {
        "id": "energy_total",
        "name": "Solar Energy Total",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "value_key": "energy_total_kwh",
        "icon": "mdi:solar-power",
    },
    {
        "id": "energy_month",
        "name": "Solar Energy This Month",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "value_key": "energy_month_kwh",
        "icon": "mdi:solar-power",
    },
    {
        "id": "energy_year",
        "name": "Solar Energy This Year",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "value_key": "energy_year_kwh",
        "icon": "mdi:solar-power",
    },
]

BINARY_SENSORS = [
    {
        "id": "plant_online",
        "name": "Solar Plant Online",
        "device_class": "connectivity",
        "value_key": "plant_online",
    },
]


def build_mqtt_client() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="fusionsolar-collector")
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()
    return client


def publish_discovery(client: mqtt.Client) -> None:
    for sensor in SENSORS:
        topic = f"{MQTT_DISCOVERY_PREFIX}/sensor/fusionsolar/{sensor['id']}/config"
        payload = {
            "name": sensor["name"],
            "unique_id": f"fusionsolar_{sensor['id']}",
            "state_topic": MQTT_STATE_TOPIC,
            "value_template": "{{{{ value_json.{} }}}}".format(sensor["value_key"]),
            "unit_of_measurement": sensor["unit"],
            "device_class": sensor["device_class"],
            "state_class": sensor["state_class"],
            "icon": sensor["icon"],
            "device": DEVICE_INFO,
        }
        client.publish(topic, json.dumps(payload), retain=True)
        log.info("Published discovery for sensor %s", sensor["id"])

    for sensor in BINARY_SENSORS:
        topic = f"{MQTT_DISCOVERY_PREFIX}/binary_sensor/fusionsolar/{sensor['id']}/config"
        payload = {
            "name": sensor["name"],
            "unique_id": f"fusionsolar_{sensor['id']}",
            "state_topic": MQTT_STATE_TOPIC,
            "value_template": "{{% if value_json.{} %}}ON{{% else %}}OFF{{% endif %}}".format(sensor["value_key"]),
            "device_class": sensor["device_class"],
            "device": DEVICE_INFO,
        }
        client.publish(topic, json.dumps(payload), retain=True)
        log.info("Published discovery for binary_sensor %s", sensor["id"])


def fetch_data(fs_client: FusionSolarClient) -> dict:
    status = fs_client.get_power_status()
    stations = fs_client.get_station_list()

    # Station list returns a list; grab the first (and typically only) station
    station = stations[0] if stations else {}

    month_energy = float(station.get("monthEnergy", 0) or 0)
    year_energy = float(station.get("yearEnergy", 0) or 0)
    plant_status = station.get("plantStatus", "")

    return {
        "current_power_kw": round(status.current_power_kw, 3),
        "energy_today_kwh": round(status.energy_today_kwh, 3),
        "energy_total_kwh": round(status.energy_kwh, 3),
        "energy_month_kwh": round(month_energy, 3),
        "energy_year_kwh": round(year_energy, 3),
        "plant_online": plant_status == "connected",
    }


def main() -> None:
    log.info("Connecting to MQTT broker %s:%s", MQTT_HOST, MQTT_PORT)
    mqtt_client = build_mqtt_client()

    log.info("Publishing HA auto-discovery messages")
    publish_discovery(mqtt_client)

    log.info("Connecting to FusionSolar (%s.fusionsolar.huawei.com)", FS_SUBDOMAIN)
    fs_client = FusionSolarClient(FS_USER, FS_PASSWORD, huawei_subdomain=FS_SUBDOMAIN)

    while True:
        try:
            data = fetch_data(fs_client)
            mqtt_client.publish(MQTT_STATE_TOPIC, json.dumps(data))
            log.info("Published: %s", data)
        except Exception as exc:
            log.error("Failed to fetch/publish data: %s", exc)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
