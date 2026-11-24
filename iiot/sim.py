import random
import time

class PumpSimulator:
    def __init__(self, device_id="pump-01", seed=None, wear_rate=0.0):
        self.device_id = device_id
        self.running = True
        self.wear = 0.0
        self.wear_rate = wear_rate
        self.clogged = False
        self.temperature_c = 55.0
        self.rng = random.Random(seed)

    def inject_fault(self, kind):
        if kind == "bearing":
            self.wear = max(self.wear, 0.7)
        elif kind == "clog":
            self.clogged = True
        else:
            raise ValueError(f"Невідомий тип несправності: {kind}")

    def step(self, dt=1.0, now=None):
        self.wear = min(1.0, max(0.0, self.wear + self.wear_rate))

        if self.running:
            vibration = 1.8 + 6.0 * self.wear + self.rng.gauss(0, 0.15)
            self.temperature_c = 55.0 + 25.0 * self.wear + self.rng.gauss(0, 0.4)
            pressure = 4.2 + self.rng.gauss(0, 0.05)
            current = 12.0 + 3.0 * self.wear + self.rng.gauss(0, 0.15)

            if self.clogged:
                pressure -= 1.2
                current += 2.0
        else:
            vibration = 0.0
            pressure = 0.0
            current = 0.0
            self.temperature_c = 25.0 + (self.temperature_c - 25.0) * 0.95 ** dt

        return {
            "device_id": self.device_id,
            "ts": time.time() if now is None else now,
            "running": self.running,
            "metrics": {
                "vibration_mm_s": round(vibration, 3),
                "temperature_c": round(self.temperature_c, 3),
                "pressure_bar": round(pressure, 3),
                "current_a": round(current, 3),
            },
        }