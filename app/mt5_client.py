# app/mt5_client.py

import os
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

# ——— Credenciales DEMO hardcodeadas para FOREX ———
_MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
_LOGIN    = 680557
_PASSWORD = "-nSsId0a"
_SERVER   = "TenTrade-Server"
# ——————————————————————————————————————————————

_initialized = False
_server_offset: timedelta = None  # offset local del broker


# Timeframe -> segundos por barra
_BAR_SECONDS = {
    "M1": 60, "M2": 120, "M3": 180, "M4": 240, "M5": 300,
    "M6": 360, "M10": 600, "M12": 720, "M15": 900, "M20": 1200,
    "M30": 1800,
    "H1": 3600, "H2": 7200, "H3": 10800, "H4": 14400,
    "H6": 21600, "H8": 28800, "H12": 43200,
    "D1": 86400,
    "W1": 604800,
    "MN1": 2592000
}


_CHUNK_BARS = 70000  # barras por chunk recomendado


def initialize_mt5():
    """
    Inicializa MT5 una sola vez y lee el offset horario del terminal.
    """
    global _initialized, _server_offset

    if _initialized:
        return

    # DEBUG: vemos qué rutas y credenciales estamos usando
    logger.debug(f"MT5_PATH hardcodeado: {_MT5_PATH!r}")
    logger.debug(f"LOGIN hardcodeado:   {_LOGIN!r}")
    logger.debug(f"SERVER hardcodeado:  {_SERVER!r}")

    # Llamamos a mt5.initialize con parámetros fijos
    success = mt5.initialize(
        path=_MT5_PATH,
        login=_LOGIN,
        password=_PASSWORD,
        server=_SERVER
    )

    if not success:
        err = mt5.last_error()
        raise RuntimeError(f"MT5 initialize() falló: {err}")

    # terminal_info().timezone suele ser la diferencia en segundos respecto a UTC
    info = mt5.terminal_info()
    tz_secs = getattr(info, "timezone", 0)
    _server_offset = timedelta(seconds=tz_secs)
    _initialized = True


def shutdown_mt5():
    global _initialized
    if _initialized:
        mt5.shutdown()
        _initialized = False


def fetch_ohlc(symbol: str,
               timeframe: str,
               start: datetime,
               end: datetime) -> pd.DataFrame:
    """
    start/end son datetime naïve en hora LOCAL del broker, p.ej.
    2025-05-01 00:00   hasta   2025-05-06 00:00
    """

    initialize_mt5()

    # 1) Mapa de timeframes
    tf_map = {
        "M1": mt5.TIMEFRAME_M1, "M2": mt5.TIMEFRAME_M2, "M3": mt5.TIMEFRAME_M3,
        "M4": mt5.TIMEFRAME_M4, "M5": mt5.TIMEFRAME_M5, "M6": mt5.TIMEFRAME_M6,
        "M10": mt5.TIMEFRAME_M10, "M12": mt5.TIMEFRAME_M12, "M15": mt5.TIMEFRAME_M15,
        "M20": mt5.TIMEFRAME_M20, "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "H2": mt5.TIMEFRAME_H2, "H3": mt5.TIMEFRAME_H3,
        "H4": mt5.TIMEFRAME_H4, "H6": mt5.TIMEFRAME_H6, "H8": mt5.TIMEFRAME_H8,
        "H12": mt5.TIMEFRAME_H12,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
    if timeframe not in tf_map:
        raise ValueError(f"Timeframe desconocido: {timeframe}")
    mt5_tf = tf_map[timeframe]

    # 2) Selección del símbolo
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"No se pudo seleccionar {symbol}")

    # 3) Creamos objetos “aware” con la zona del broker
    local_tz = timezone(_server_offset)
    start_aware = start.replace(tzinfo=local_tz)
    end_aware = end.replace(tzinfo=local_tz)

    # 4) Pedimos las barras entre esos datetimes aware

    rates = mt5.copy_rates_range(symbol, mt5_tf, start_aware, end_aware)
    if rates is None:
        err = mt5.last_error()
        raise RuntimeError(f"copy_rates_range() falló: {err}")

    # 5) A DataFrame y convertimos el campo `time` (viene en UTC)
    df = pd.DataFrame(rates)

    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    # y lo llevamos de UTC → zona local del broker, luego lo hacemos naïve:
    df['time'] = (
        df['time']
        .dt.tz_convert(local_tz)
        .dt.tz_localize(None)
    )

    # 6) Filtramos exactamente entre start y end (inclusive si quieres)
    df = df[(df['time'] >= start) & (df['time'] <= end)]

    # 7) Columnas de salida
    return df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]

def _get_chunks(start: datetime, end: datetime, bar_seconds: int) -> list[tuple[datetime, datetime]]:
    """
    Devuelve lista de pares (chunk_start, chunk_end) para no exceder _CHUNK_BARS.
    """
    max_delta = timedelta(seconds=_CHUNK_BARS * bar_seconds)
    chunks = []
    curr = start
    while curr < end:
        chunk_end = min(end, curr + max_delta)
        chunks.append((curr, chunk_end))
        curr = chunk_end
    return chunks

def fetch_ohlc_chunked(symbol: str,
                       timeframe: str,
                       start: datetime,
                       end: datetime) -> pd.DataFrame:
    """
    Igual a fetch_ohlc, pero en chunks de _CHUNK_BARS.
    """
    # calcular tamaño en segundos por barra
    if timeframe not in _BAR_SECONDS:
        raise ValueError(f"Timeframe desconocido: {timeframe}")
    secs = _BAR_SECONDS[timeframe]
    chunks = _get_chunks(start, end, secs)

    dfs = []
    for s, e in chunks:
        df_chunk = fetch_ohlc(symbol, timeframe, s, e)
        dfs.append(df_chunk)

    full = pd.concat(dfs, ignore_index=True)
    full = full.drop_duplicates(subset=['time'])
    full = full.sort_values('time').reset_index(drop=True)
    return full