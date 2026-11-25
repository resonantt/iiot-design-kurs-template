from dataclasses import dataclass


@dataclass
class Rule:
    name: str
    metric: str
    high: float
    hysteresis: float = 0.0
    debounce: int = 3
    severity: str = "warning"

class AlertEngine:
    def __init__(self, rules):
        self.rules = list(rules)
        self.state = {}

    def process(self, msg):
        events = []
        device_id = msg["device_id"]
        metrics = msg["metrics"]

        for rule in self.rules:
            if rule.metric not in metrics:
                continue

            value = metrics[rule.metric]
            key = (device_id, rule.name)
            state = self.state.setdefault(key, {"count": 0, "active": False})

            if state["active"]:
                if value >= rule.high - rule.hysteresis:
                    continue
                state["active"] = False
                state["count"] = 0
                event_state = "cleared"
            else:
                if value <= rule.high:
                    state["count"] = 0
                    continue
                state["count"] += 1
                if state["count"] < rule.debounce:
                    continue
                state["active"] = True
                event_state = "raised"

            events.append({
                "rule": rule.name,
                "device_id": device_id,
                "metric": rule.metric,
                "state": event_state,
                "value": value,
                "ts": msg["ts"],
                "severity": rule.severity,
            })

        return events

DEFAULT_RULES = [
    Rule(
        name="high_vibration",
        metric="vibration_mm_s",
        high=4.5,
        hysteresis=0.5,
        debounce=3,
        severity="critical",
    ),
    Rule(
        name="high_temperature",
        metric="temperature_c",
        high=80.0,
        hysteresis=3.0,
        debounce=5,
        severity="warning",
    ),
]