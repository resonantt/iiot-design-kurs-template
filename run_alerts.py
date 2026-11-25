from iiot.alerts import AlertEngine, DEFAULT_RULES
from iiot.gateway import decode, encode, make_client


def main():
    engine = AlertEngine(DEFAULT_RULES)
    client = make_client("lab4-alerts")

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe("plant/+/+/+/telemetry", qos=1)
            print("Підключено до брокера. Очікую телеметрію.")

    def on_message(client, userdata, message):
        data = decode(message.payload)
        events = engine.process(data)
        alerts_topic = message.topic.rsplit("/", 1)[0] + "/alerts"

        for event in events:
            client.publish(alerts_topic, encode(event), qos=1)
            print(alerts_topic, event["rule"], event["state"], event["value"])

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("localhost", 1883)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()