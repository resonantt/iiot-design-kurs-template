import time
from pathlib import Path

from iiot.config import Config
from iiot.gateway import decode, make_client
from iiot.security import NonceCache, backoff_delays, verify
from iiot.storage import Ingestor, init_db


def main():
    cfg = Config()
    cache = NonceCache()
    topic = f"plant/{cfg.site}/{cfg.line}/+/telemetry"

    def read_message(raw, message_topic):
        if cfg.signing_key is None:
            return decode(raw)

        return verify(
            cfg.signing_key,
            message_topic,
            raw,
            now=time.time(),
            cache=cache,
        )

    client = make_client(
        "ingest-service",
        username=cfg.mqtt_user,
        password=cfg.mqtt_password,
    )
    client.reconnect_delay_set(min_delay=1, max_delay=60)

    health_file = Path(cfg.health_file)
    health_file.parent.mkdir(parents=True, exist_ok=True)

    conn = init_db(cfg.db_path)
    ingestor = Ingestor(conn, read_message)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(topic, qos=1)
            print(f"Приймач підключено. Топік: {topic}", flush=True)
        else:
            print(f"Брокер відхилив підключення: {reason_code}", flush=True)

    def on_message(client, userdata, message):
        try:
            ingestor.on_message(client, userdata, message)
        except Exception as error:
            print(f"Повідомлення пропущено: {type(error).__name__}", flush=True)

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
            rows = ingestor.flush()
            if rows:
                print(f"Записано рядків у SQLite: {rows}", flush=True)
            health_file.touch()
            time.sleep(0.2)

    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()
        try:
            ingestor.flush()
        finally:
            conn.close()


if __name__ == "__main__":
    main()