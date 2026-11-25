from collections import deque
from statistics import mean, pstdev

def ewma(values, alpha=0.3):
    smoothed = []
    for value in values:
        if smoothed:
            value = alpha * value + (1 - alpha) * smoothed[-1]
        smoothed.append(value)
    return smoothed

class RollingZ:
    def __init__(self, window=30, min_samples=10):
        self.history = deque(maxlen=window)
        self.min_samples = min_samples

    def update(self, x):
        score = None
        if len(self.history) >= self.min_samples:
            average = mean(self.history)
            deviation = max(pstdev(self.history), 1e-6)
            score = (x - average) / deviation

        self.history.append(x)
        return score

def detect_anomalies(values, window=30, threshold=3.5):
    detector = RollingZ(window=window)
    indices = []

    for index, value in enumerate(values):
        score = detector.update(value)
        if score is not None and abs(score) > threshold:
            indices.append(index)

    return indices

def linear_trend(ts, values):
    if len(ts) == 0 or len(ts) != len(values):
        raise ValueError("Потрібна одна часова мітка для кожного вимірювання")

    mean_t = mean(ts)
    mean_value = mean(values)
    sxx = sum((t - mean_t) ** 2 for t in ts)

    if sxx == 0:
        return 0.0, float(mean_value)

    sxy = sum((t - mean_t) * (value - mean_value)
              for t, value in zip(ts, values))
    slope = sxy / sxx
    intercept = mean_value - slope * mean_t
    return slope, intercept

def estimate_rul(ts, values, limit):
    if len(ts) == 0 or len(ts) != len(values):
        raise ValueError("Потрібна одна часова мітка для кожного вимірювання")

    if values[-1] >= limit:
        return 0.0

    slope, intercept = linear_trend(ts, values)
    if slope <= 1e-12:
        return None

    crossing_time = (limit - intercept) / slope
    return max(crossing_time - ts[-1], 0.0)