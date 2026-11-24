import time

from iiot.gateway import Gateway, make_client
from iiot.sim import PumpSimulator


def main():
    sim = PumpSimulator(device_id="pump-01", seed=42)
    client = make_client("pump-01-gateway")
    gw = Gateway(client, "kyiv", "line1", sim.device_id)

    client.on_connect = gw.on_connect
    client.on_disconnect = gw.on_disconnect
    client.connect("localhost", 1883)
    client.loop_start()

    try:
        while True:
            msg = sim.step()
            gw.publish(msg)
            print(
                f"ts={msg['ts']:.1f}  "
                f"тиск={msg['metrics']['pressure_bar']:.3f} бар  "
                f"у буфері={len(gw.buffer)}  "
                f"відкинуто={gw.buffer.dropped}"
            )
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()