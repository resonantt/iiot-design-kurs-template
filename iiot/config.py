import os


class Config:
    def __init__(self):
        self.mqtt_host = os.getenv("MQTT_HOST") or "localhost"
        self.mqtt_port = int(os.getenv("MQTT_PORT") or "1883")
        self.mqtt_user = os.getenv("MQTT_USER") or None
        self.mqtt_password = os.getenv("MQTT_PASSWORD") or None

        self.site = os.getenv("SITE") or "kyiv"
        self.line = os.getenv("LINE") or "line1"
        self.device_id = os.getenv("DEVICE_ID") or "pump-01"
        self.interval = float(os.getenv("INTERVAL") or "1.0")

        signing_key = os.getenv("SIGNING_KEY")
        self.signing_key = signing_key.encode("utf-8") if signing_key else None

        self.db_path = os.getenv("DB_PATH") or "iiot.db"
        self.health_file = os.getenv("HEALTH_FILE") or "/tmp/healthy"

        fault_after = os.getenv("FAULT_AFTER")
        self.fault_after = float(fault_after) if fault_after else None