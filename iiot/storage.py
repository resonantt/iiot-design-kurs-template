import sqlite3
from math import isfinite
from threading import RLock

def init_db(path=":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS telemetry (
            ts REAL,
            device_id TEXT,
            metric TEXT,
            value REAL
        );

        CREATE INDEX IF NOT EXISTS idx_telemetry_device_metric_ts
        ON telemetry (device_id, metric, ts);

        CREATE TABLE IF NOT EXISTS telemetry_1m (
            bucket INTEGER,
            device_id TEXT,
            metric TEXT,
            avg REAL,
            min REAL,
            max REAL,
            n INTEGER,
            PRIMARY KEY (bucket, device_id, metric)
        );
    """)

    return conn

def insert_batch(conn, msgs):
    rows = []
    for msg in msgs:
        for metric, value in msg["metrics"].items():
            rows.append((msg["ts"], msg["device_id"], metric, value))

    with conn:
        conn.executemany(
            "INSERT INTO telemetry (ts, device_id, metric, value) VALUES (?, ?, ?, ?)",
            rows,
        )

    return len(rows)

def last_n(conn, device_id, metric, n):
    if n <= 0:
        return []

    rows = conn.execute(
        """
        SELECT ts, value
        FROM telemetry
        WHERE device_id = ? AND metric = ?
        ORDER BY ts DESC, rowid DESC
        LIMIT ?
        """,
        (device_id, metric, n),
    ).fetchall()

    rows.reverse()
    return rows

def downsample_1m(conn, before_ts):
    with conn:
        conn.execute(
            """
            INSERT INTO telemetry_1m
                (bucket, device_id, metric, avg, min, max, n)
            SELECT
                CAST(ts / 60 AS INTEGER) * 60 AS bucket,
                device_id, metric,
                AVG(value), MIN(value), MAX(value), COUNT(*)
            FROM telemetry
            WHERE ts < ?
            GROUP BY bucket, device_id, metric
            ON CONFLICT(bucket, device_id, metric) DO UPDATE SET
                avg = excluded.avg,
                min = excluded.min,
                max = excluded.max,
                n = excluded.n
            """,
            (before_ts,),
        )
        return conn.execute("SELECT COUNT(*) FROM telemetry_1m").fetchone()[0]

def purge_older_than(conn, ts):
    with conn:
        cursor = conn.execute("DELETE FROM telemetry WHERE ts < ?", (ts,))
        return cursor.rowcount

class Ingestor:
    def __init__(self, conn, decoder, batch_size=20):
        self.conn = conn
        self.decoder = decoder
        self.batch_size = batch_size
        self.batch = []
        self.lock = RLock()

    def on_message(self, client, userdata, message):
        try:
            data = self.decoder(message.payload, message.topic)
            device_id = data["device_id"]
            ts = data["ts"]
            metrics = data["metrics"]

            if not isinstance(device_id, str) or not device_id:
                return
            if not isinstance(metrics, dict) or not metrics:
                return

            values = [ts, *metrics.values()]
            if not all(type(v) in (int, float) and isfinite(v) for v in values):
                return
        except (ValueError, TypeError, KeyError, OverflowError):
            return

        with self.lock:
            self.batch.append(data)
            if len(self.batch) >= self.batch_size:
                self.flush()

    def flush(self):
        with self.lock:
            if not self.batch:
                return 0

            rows_written = insert_batch(self.conn, self.batch)
            self.batch.clear()
            return rows_written