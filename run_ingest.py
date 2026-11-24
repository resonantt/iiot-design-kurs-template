import time

from iiot.gateway import decode, make_client
from iiot.storage import Ingestor, init_db


def main():
    conn = init_db("iiot.db")
    ingestor = Ingestor(conn, lambda raw, topic: decode(raw))
    client = make_client("lab3-ingestor")
    topic = "plant/+/+/+/telemetry"

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(topic, qos=1)
            print(f"Підключено до брокера. Тема: {topic}")

    client.on_connect = on_connect
    client.on_message = ingestor.on_message

    try:
        client.connect("localhost", 1883)
        client.loop_start()
        while True:
            time.sleep(1)
            rows = ingestor.flush()
            if rows:
                print(f"Записано рядків: {rows}")
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()
        ingestor.flush()
        conn.close()


if __name__ == "__main__":
    main()