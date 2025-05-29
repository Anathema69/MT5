# app/routes.py

from flask import Flask, render_template, request, send_file, abort
from app.mt5_client import fetch_ohlc_chunked
from io import StringIO, BytesIO
from datetime import datetime, date, time
import pandas as pd

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

# Intervalos disponibles
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
    today = date.today().isoformat()
    return render_template(
        "index.html",
        intervals=intervals,
        default_start=today,
        default_end=today
    )

@app.route("/download", methods=["POST"])
def download():
    # Símbolo
    symbol = request.form.get("symbol")
    if symbol == "other":
        symbol = request.form.get("symbol_other", "").strip()
    if not symbol:
        abort(400, "Símbolo inválido")

    # Intervalo
    interval = request.form.get("interval")

    # Fechas
    try:
        start_date = date.fromisoformat(request.form.get("start_date"))
        end_date   = date.fromisoformat(request.form.get("end_date"))
    except:
        abort(400, "Fecha inválida")


    # Fetch OHLC
    start = datetime.combine(start_date, time.min)
    end = datetime.combine(end_date, time.min)


    try:
        df = fetch_ohlc_chunked(symbol, interval, start, end)
    except Exception as e:
        abort(500, f"Error al descargar datos: {e}")

    # Genera CSV en memoria
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
