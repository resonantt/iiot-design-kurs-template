import matplotlib.pyplot as plt
from iiot.analytics import ewma, detect_anomalies, estimate_rul
from iiot.sim import PumpSimulator


def main():
    sim = PumpSimulator(seed=42, wear_rate=0.001)
    steps = list(range(1, 601))
    vibration = []

    for step in steps:
        message = sim.step(now=step)
        vibration.append(message["metrics"]["vibration_mm_s"])

    limit = 4.5
    first_crossing = next(
        (step for step, value in zip(steps, vibration) if value >= limit),
        None,
    )

    print("Кількість вимірювань:", len(vibration))
    if first_crossing is None:
        print("За час експерименту вібрація не досягла межі.")
    else:
        print("Перший крок із вібрацією ≥ 4,5 мм/с:", first_crossing)


    smoothed = ewma(vibration, alpha=0.3)

    plt.figure(figsize=(10, 5))
    plt.plot(steps, vibration, color="gray", alpha=0.55, label="Вібрація")
    plt.plot(steps, smoothed, color="blue", label="EWMA (α = 0,3)")
    plt.axhline(limit, color="red", linestyle="--", label="Межа 4,5 мм/с")
    if first_crossing is not None:
        plt.scatter(first_crossing, vibration[steps.index(first_crossing)],
                    color="red", label=f"Перший перетин: крок {first_crossing}")

    plt.xlabel("Крок симуляції")
    plt.ylabel("Вібрація, мм/с")
    plt.title("Зміна вібрації насоса зі зростанням зносу")
    plt.legend()
    plt.tight_layout()
    plt.savefig("lab5_vibration.png", dpi=150)
    plt.close()

    original_anomalies = detect_anomalies(vibration)
    print("Аномалії початкового сигналу, кроки:",
          [steps[i] for i in original_anomalies])

    with_spikes = vibration.copy()
    with_spikes[199] += 2.0  # Крок 200: стрибок угору
    with_spikes[349] -= 2.0  # Крок 350: стрибок униз

    detected = detect_anomalies(with_spikes)
    detected_steps = [steps[i] for i in detected]
    print("Аномалії після додавання викидів, кроки:", detected_steps)
    print("Обидва штучні викиди виявлено:",
          200 in detected_steps and 350 in detected_steps)

    checkpoints = []
    predictions = []
    actual_rul = []

    for end in range(100, len(steps) + 1, 50):
        step = steps[end - 1]
        window_ts = steps[end - 100:end]
        window_values = vibration[end - 100:end]
        prediction = estimate_rul(window_ts, window_values, limit)

        checkpoints.append(step)
        predictions.append(prediction)

        actual = None if first_crossing is None else max(first_crossing - step, 0)
        actual_rul.append(actual)

        if step == 400:
            print("Крок 400. Прогноз RUL:", prediction)
            print("Крок 400. Фактично залишалося кроків:", actual)

    plt.figure(figsize=(10, 5))
    plt.plot(checkpoints, predictions, "o-", label="Прогноз за останніми 100 вимірами")
    if first_crossing is not None:
        plt.plot(steps, [max(first_crossing - s, 0) for s in steps],
                 "--", label="Фактично до першого перетину")
    if first_crossing is not None:
        plt.axvline(first_crossing, color="gray", linestyle=":",
                    label=f"Перший перетин: крок {first_crossing}")

    plt.xlabel("Крок симуляції")
    plt.ylabel("Залишковий ресурс, кроки")
    plt.title("Прогноз часу до досягнення вібрації 4,5 мм/с")
    plt.legend()
    plt.tight_layout()
    plt.savefig("lab5_rul.png", dpi=150)
    plt.close()

if __name__ == "__main__":
    main()