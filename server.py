"""
server.py — Serveur Flask local
Reçoit les données de l'ESP32 et les stocke dans SQLite.
Lance avec: python server.py
"""

from flask import Flask, request, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

DB_PATH = "iot_data.db"
SECURITY_KEY = "123456"  # Même clé que dans le code ESP32


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT    NOT NULL,
            temp      REAL,
            hum       REAL,
            volt      REAL,
            current_ma REAL
        )
    """)
    conn.commit()
    conn.close()


def get_sleep_seconds():
    """
    Retourne la durée de sommeil dynamique (en secondes).
    Tu peux adapter cette logique selon l'heure, la tension, etc.
    """
    hour = datetime.now().hour
    if 0 <= hour < 6:
        return 300   # Nuit : mesure toutes les 5 min
    elif 6 <= hour < 22:
        return 60    # Journée : toutes les 60 s
    else:
        return 120   # Soirée : toutes les 2 min


@app.route("/update", methods=["POST"])
def update():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    if data.get("key") != SECURITY_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO readings (timestamp, temp, hum, volt, current_ma) VALUES (?, ?, ?, ?, ?)",
        (
            datetime.now().isoformat(),
            data.get("temp"),
            data.get("hum"),
            data.get("volt"),
            data.get("mA"),
        ),
    )
    conn.commit()
    conn.close()

    sleep_s = get_sleep_seconds()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Reçu → "
          f"T={data.get('temp'):.1f}°C  H={data.get('hum'):.1f}%  "
          f"V={data.get('volt'):.2f}V  I={data.get('mA'):.1f}mA  "
          f"→ sleep={sleep_s}s")

    return jsonify({"status": "ok", "sleep_seconds": sleep_s})


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "running", "db": DB_PATH})


if __name__ == "__main__":
    init_db()
    print("Serveur IoT démarré sur http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
