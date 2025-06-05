# app/routes.py

import sys, os
from flask import Flask, render_template, request, send_file, abort
from io import StringIO, BytesIO
from datetime import datetime, date, time, timedelta
import pandas as pd
import zipfile

from app.mt5_client import fetch_ohlc_chunked, fetch_ticks_chunked, set_mode

# Detección de la carpeta de plantillas y estáticos
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
    """
    Renderiza la página principal. Pasa como default:
      - default_start = hoy - 7 días
      - default_end   = hoy
    """
    today = date.today()
    seven_days_ago = today - timedelta(days=7)

    return render_template(
        "index.html",
        intervals=intervals,
        default_start=seven_days_ago.isoformat(),
        default_end=today.isoformat()
    )

@app.route("/download", methods=["POST"])
def download():
    """
    Procesa el formulario al darle click en “Descargar CSV”:
      1) Lee asset_type ("forex" o "synthetic") → set_mode(asset_type)
      2) Lee símbolo, intervalo y fechas.
      3) Llama a fetch_ohlc_chunked(...) para descargar OHLCV.
      4) Si es "synthetic" y el usuario marcó "download_ticks",
         también llama a fetch_ticks_chunked(...) y genera un ZIP con:
            - CSV de OHLCV
            - CSV de Ticks
      5) Si no descarga ticks, envía un único CSV de OHLCV.
    """
    # 1) Tipo de activo y establecer credenciales
    asset_type = request.form.get("asset_type", "synthetic")
    try:
        set_mode(asset_type)
    except Exception as e:
        abort(400, f"Modo inválido: {e}")

    # 2) Símbolo
    symbol = request.form.get("symbol")
    if symbol == "other":
        symbol = request.form.get("symbol_other", "").strip()
    if not symbol:
        abort(400, "Símbolo inválido")

    # 3) Intervalo
    interval = request.form.get("interval")

    # 4) Fechas
    try:
        start_date = date.fromisoformat(request.form.get("start_date"))
        end_date   = date.fromisoformat(request.form.get("end_date"))
    except:
        abort(400, "Fecha inválida")

    start = datetime.combine(start_date, time.min)
    end   = datetime.combine(end_date, time.min)

    # 5) Descarga OHLCV chunked
    try:
        df_ohlc = fetch_ohlc_chunked(symbol, interval, start, end)
    except Exception as e:
        abort(500, f"Error al descargar OHLCV: {e}")

    # Preparamos CSV de OHLCV en memoria
    csv_buffer_ohlc = StringIO()
    df_ohlc.to_csv(csv_buffer_ohlc, index=False)
    csv_bytes_ohlc = csv_buffer_ohlc.getvalue().encode('utf-8')
    filename_ohlc = f"{symbol}_{interval}_{start_date}_{end_date}_OHLCV.csv"

    # 6) ¿Descargar ticks? (solo si es synthetic Y el usuario marcó el checkbox)
    download_ticks = request.form.get("download_ticks") == "on"
    if asset_type == "synthetic" and download_ticks:
        try:
            df_ticks = fetch_ticks_chunked(symbol, start, end)
        except Exception as e:
            abort(500, f"Error al descargar Ticks: {e}")

        # Creamos CSV de ticks
        csv_buffer_ticks = StringIO()
        df_ticks.to_csv(csv_buffer_ticks, index=False)
        csv_bytes_ticks = csv_buffer_ticks.getvalue().encode('utf-8')
        filename_ticks = f"{symbol}_{start_date}_{end_date}_Ticks.csv"

        # 7) Empaquetamos ambos CSV en un ZIP
        mem_zip = BytesIO()
        with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr(filename_ohlc, csv_bytes_ohlc)
            z.writestr(filename_ticks, csv_bytes_ticks)
        mem_zip.seek(0)

        zip_name = f"{symbol}_{interval}_{start_date}_{end_date}.zip"
        return send_file(
            mem_zip,
            as_attachment=True,
            download_name=zip_name,
            mimetype="application/zip"
        )

    # 8) Si no descargamos ticks, devolvemos solo OHLCV
    return send_file(
        BytesIO(csv_bytes_ohlc),
        as_attachment=True,
        download_name=filename_ohlc,
        mimetype="text/csv"
    )
