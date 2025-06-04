# app/routes.py

import sys, os
from flask import Flask, render_template, request, send_file, abort
from io import StringIO, BytesIO
from datetime import datetime, date, time, timedelta
import pandas as pd

from app.mt5_client import fetch_ohlc_chunked, set_mode

# --- mismo bloque de detección de base_path ---
if getattr(sys, "frozen", False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(base_path, "templates"),
    static_folder=os.path.join(base_path, "static"),
)

# Intervalos disponibles (sin cambios)
intervals = [
    ("M1",  "1 Minuto"),
    ("M2",  "2 Minutos"),
    ("M3",  "3 Minutos"),
    ("M4",  "4 Minutos"),
    ("M5",  "5 Minutos"),
    ("M6",  "6 Minutos"),
    ("M10", "10 Minutos"),
    ("M12", "12 Minutos"),
    ("M15", "15 Minutos"),
    ("M20", "20 Minutos"),
    ("M30", "30 Minutos"),
    ("H1",  "1 Hora"),
    ("H2",  "2 Horas"),
    ("H3",  "3 Horas"),
    ("H4",  "4 Horas"),
    ("H6",  "6 Horas"),
    ("H8",  "8 Horas"),
    ("H12", "12 Horas"),
    ("D1",  "Daily"),
    ("W1",  "Weekly"),
    ("MN1", "Monthly")
]

@app.route("/", methods=["GET"])
def index():
    today = date.today()
    seven_days_ago = today - timedelta(days=7)

    return render_template(
        "index.html",
        intervals=intervals,
        default_start=seven_days_ago.isoformat(),  # por ejemplo "2025-05-27"
        default_end=today.isoformat(),             # por ejemplo "2025-06-03"
    )

@app.route("/download", methods=["POST"])
def download():
    asset_type = request.form.get("asset_type", "synthetic")
    try:
        set_mode(asset_type)
    except Exception as e:
        abort(400, f"Modo inválido: {e}")

    symbol = request.form.get("symbol")
    if symbol == "other":
        symbol = request.form.get("symbol_other", "").strip()
    if not symbol:
        abort(400, "Símbolo inválido")

    interval = request.form.get("interval")

    try:
        start_date = date.fromisoformat(request.form.get("start_date"))
        end_date   = date.fromisoformat(request.form.get("end_date"))
    except:
        abort(400, "Fecha inválida")

    start = datetime.combine(start_date, time.min)
    end   = datetime.combine(end_date, time.min)

    try:
        df = fetch_ohlc_chunked(symbol, interval, start, end)
    except Exception as e:
        abort(500, f"Error al descargar datos: {e}")

    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue().encode('utf-8')
    filename = f"{symbol}_{interval}_{start_date}_{end_date}.csv"

    return send_file(
        BytesIO(csv_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="text/csv"
    )
