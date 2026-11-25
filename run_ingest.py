import time
from getpass import getpass
from pathlib import Path

from iiot.gateway import make_client
from iiot.security import NonceCache, verify
from iiot.storage import Ingestor, init_db


def main():
    password = getpass("MQTT password for ingest: ")
    signing_key = getpass("Telemetry signing key: ").encode("utf-8")
    cache = NonceCache()
    topic = "plant/+/+/+/telemetry"

    def verify_message(raw, message_topic):
        try:
            return verify(
                signing_key,
                message_topic,
                raw,
                now=time.time(),
                cache=cache,
            )
        except Exception as error:
            print(f"Телеметрію відхилено: {type(error).__name__}")
            raise

    db_path = Path(__file__).with_name("iiot.db")
    conn = init_db(str(db_path))
    ingestor = Ingestor(conn, verify_message)
    client = make_client("lab3-ingestor", username="ingest", password=password)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(topic, qos=1)
            print(f"Підключено до брокера. Очікую телеметрію: {topic}")
        else:
            print(f"Брокер відхилив підключення: {reason_code}")

    def on_message(client, userdata, message):
        try:
            ingestor.on_message(client, userdata, message)
        except Exception as error:
            print(f"Повідомлення пропущено: {type(error).__name__}")

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect("localhost", 1883)
        client.loop_start()
        while True:
            time.sleep(1)
            rows = ingestor.flush()
            if rows:
                print(f"Записано рядків у SQLite: {rows}")
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()
        ingestor.flush()
        conn.close()


if __name__ == "__main__":
    main()