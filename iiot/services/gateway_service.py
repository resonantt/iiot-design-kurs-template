import time
from pathlib import Path

from iiot.config import Config
from iiot.gateway import Gateway, make_client
from iiot.security import backoff_delays, sign
from iiot.sim import PumpSimulator


def main():
    cfg = Config()
    sim = PumpSimulator(device_id=cfg.device_id, seed=42)
    client = make_client(
        f"{cfg.device_id}-gateway",
        username=cfg.mqtt_user,
        password=cfg.mqtt_password,
    )
    gw = Gateway(client, cfg.site, cfg.line, cfg.device_id)

    client.on_connect = gw.on_connect
    client.on_disconnect = gw.on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=60)

    health_file = Path(cfg.health_file)
    health_file.parent.mkdir(parents=True, exist_ok=True)

    for delay in backoff_delays():
        try:
            client.connect(cfg.mqtt_host, cfg.mqtt_port)
            break
        except OSError as error:
            print(f"Брокер недоступний: {error}. Повтор через {delay} с.", flush=True)
            time.sleep(delay)

    client.loop_start()
    started = time.monotonic()
    fault_injected = False

    try:
        while True:
            elapsed = time.monotonic() - started
            if (
                cfg.fault_after is not None
                and not fault_injected
                and elapsed >= cfg.fault_after
            ):
                sim.inject_fault("bearing")
                fault_injected = True
                print(f"{cfg.device_id}: несправність підшипника", flush=True)

            msg = sim.step()
            if cfg.signing_key is not None:
                payload = sign(cfg.signing_key, gw.telemetry_topic, msg)
                if isinstance(payload, str):
                    payload = payload.encode("utf-8")
                gw.publish(payload)
            else:
                gw.publish(msg)

            health_file.touch()
            time.sleep(cfg.interval)

    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()