import time
from pathlib import Path

from iiot.alerts import AlertEngine, DEFAULT_RULES
from iiot.config import Config
from iiot.gateway import decode, encode, make_client
from iiot.security import NonceCache, backoff_delays, sign, verify


def main():
    cfg = Config()
    engine = AlertEngine(DEFAULT_RULES)
    cache = NonceCache()
    telemetry_topic = f"plant/{cfg.site}/{cfg.line}/+/telemetry"

    client = make_client(
        "alert-service",
        username=cfg.mqtt_user,
        password=cfg.mqtt_password,
    )
    client.reconnect_delay_set(min_delay=1, max_delay=60)

    health_file = Path(cfg.health_file)
    health_file.parent.mkdir(parents=True, exist_ok=True)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(telemetry_topic, qos=1)
            print(f"Сервіс сповіщень підключено: {telemetry_topic}", flush=True)
        else:
            print(f"Брокер відхилив підключення: {reason_code}", flush=True)

    def on_message(client, userdata, message):
        try:
            if cfg.signing_key is None:
                telemetry = decode(message.payload)
            else:
                telemetry = verify(
                    cfg.signing_key,
                    message.topic,
                    message.payload,
                    now=time.time(),
                    cache=cache,
                )

            events = engine.process(telemetry)
        except Exception as error:
            print(f"Телеметрію пропущено: {type(error).__name__}", flush=True)
            return

        alerts_topic = message.topic.rsplit("/", 1)[0] + "/alerts"
        for event in events:
            if cfg.signing_key is None:
                payload = encode(event)
            else:
                payload = sign(cfg.signing_key, alerts_topic, event)

            client.publish(alerts_topic, payload, qos=1)
            print(f"{alerts_topic} {event['rule']} {event['state']}", flush=True)

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        for delay in backoff_delays():
            try:
                client.connect(cfg.mqtt_host, cfg.mqtt_port)
                break
            except OSError as error:
                print(f"Брокер недоступний: {error}. Повтор через {delay} с.", flush=True)
                time.sleep(delay)

        client.loop_start()
        while True:
            health_file.touch()
            time.sleep(1)

    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()