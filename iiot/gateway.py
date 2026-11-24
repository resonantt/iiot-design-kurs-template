import json
from collections import deque
from threading import Lock
import paho.mqtt.client as mqtt

def build_topic(site, line, device, kind="telemetry"):
    return f"plant/{site}/{line}/{device}/{kind}"


def encode(msg):
    return json.dumps(msg, separators=(",", ":"), sort_keys=True).encode("utf-8")


def decode(raw):
    return json.loads(raw.decode("utf-8"))

class OfflineBuffer:
    def __init__(self, maxlen):
        self.items = deque(maxlen=maxlen)
        self.dropped = 0

    def push(self, item):
        if len(self.items) == self.items.maxlen:
            self.dropped += 1
        self.items.append(item)

    def drain(self):
        messages = list(self.items)
        self.items.clear()
        return messages

    def __len__(self):
        return len(self.items)

class Gateway:
    def __init__(self, client, site, line, device_id, buffer_size=1000):
        self.client = client
        self.connected = False
        self.lock = Lock()
        self.buffer = OfflineBuffer(buffer_size)
        self.telemetry_topic = build_topic(site, line, device_id)
        self.status_topic = build_topic(site, line, device_id, "status")

        self.client.will_set(
            self.status_topic,
            encode({"state": "offline"}),
            qos=1,
            retain=True,
        )

    def on_connect(self, client=None, userdata=None, flags=None,
                   reason_code=0, properties=None):
        if reason_code != 0:
            return

        with self.lock:
            self.connected = True
            self.client.publish(
                self.status_topic,
                encode({"state": "online"}),
                qos=1,
                retain=True,
            )
            for payload in self.buffer.drain():
                self.client.publish(self.telemetry_topic, payload, qos=1)

    def on_disconnect(self, *args, **kwargs):
        with self.lock:
            self.connected = False

    def publish(self, msg):
        payload = msg if isinstance(msg, bytes) else encode(msg)

        with self.lock:
            if self.connected:
                self.client.publish(self.telemetry_topic, payload, qos=1)
            else:
                self.buffer.push(payload)

def make_client(client_id, username=None, password=None):
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
    )
    if username is not None:
        client.username_pw_set(username, password)
    return client