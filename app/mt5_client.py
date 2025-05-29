# app/mt5_client.py

import os
from datetime import datetime, date, time, timedelta
from dotenv import load_dotenv
import MetaTrader5 as mt5
import pandas as pd

# ----------------------------------------------------------------------
# Carga .env
load_dotenv()

_MT5_PATH = os.getenv("MT5_PATH")
_LOGIN    = int(os.getenv("MT5_LOGIN", 0))
_PASSWORD = os.getenv("MT5_PASSWORD", "")
_SERVER   = os.getenv("MT5_SERVER", "")

_initialized = False
_server_offset: timedelta = None  # offset desde UTC que usa MT5 (en segundos)

def initialize_mt5():
    """
    Inicializa MT5 una sola vez y lee el offset horario del terminal.
    """
    global _initialized, _server_offset

    if _initialized:
        return

    if not mt5.initialize(path=_MT5_PATH or None,
                          login=_LOGIN,
                          password=_PASSWORD,
                          server=_SERVER):
        err = mt5.last_error()
        raise RuntimeError(f"MT5 initialize() falló: {err}")

    # terminal_info().timezone suele ser la diferencia en segundos respecto a UTC
    info = mt5.terminal_info()
    tz_secs = getattr(info, "timezone", 0)
    _server_offset = timedelta(seconds=tz_secs)
    _initialized = True

def shutdown_mt5():
    """
    Cierra la sesión de MT5 si está inicializada.
    """
    global _initialized
    if _initialized:
        mt5.shutdown()
        _initialized = False

def fetch_ohlc(symbol: str,
               timeframe: str,
               start_date: date,
               end_date: date) -> pd.DataFrame:
    """
    Descarga un OHLC DataFrame desde 00:00 del start_date hasta
    justo antes de 00:00 del end_date+1, usando el mismo timezone
    que el terminal MT5.

    Args:
      symbol     – "EURUSD", etc.
      timeframe  – "M1","M2",...,"H12","D1","W1","MN1"
      start_date – fecha inicial (incluye 00:00)
      end_date   – fecha final   (excluye 00:00 de este día)

    Returns:
      pd.DataFrame con columnas ['time','open','high','low','close','tick_volume']
    """
    initialize_mt5()

    # 1) Mapear timeframe
    tf_map = {
        "M1":  mt5.TIMEFRAME_M1,  "M2":  mt5.TIMEFRAME_M2,  "M3":  mt5.TIMEFRAME_M3,
        "M4":  mt5.TIMEFRAME_M4,  "M5":  mt5.TIMEFRAME_M5,  "M6":  mt5.TIMEFRAME_M6,
        "M10": mt5.TIMEFRAME_M10, "M12": mt5.TIMEFRAME_M12, "M15": mt5.TIMEFRAME_M15,
        "M20": mt5.TIMEFRAME_M20, "M30": mt5.TIMEFRAME_M30,
        "H1":  mt5.TIMEFRAME_H1,  "H2":  mt5.TIMEFRAME_H2,  "H3":  mt5.TIMEFRAME_H3,
        "H4":  mt5.TIMEFRAME_H4,  "H6":  mt5.TIMEFRAME_H6,  "H8":  mt5.TIMEFRAME_H8,
        "H12": mt5.TIMEFRAME_H12,
        "D1":  mt5.TIMEFRAME_D1,
        "W1":  mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
    if timeframe not in tf_map:
        raise ValueError(f"Timeframe desconocido: {timeframe}")
    mt5_tf = tf_map[timeframe]

    # 2) Calcular ventana UTC según offset del servidor
    #    start_local = YYYY-MM-DD 00:00:00
    #    end_local_excl = (YYYY-MM-DD + 1) 00:00:00
    naive_start = datetime.combine(start_date, time.min)
    naive_end_excl = datetime.combine(end_date + timedelta(days=1), time.min)

    # Para pedir al terminal sus 00:00 locales, restamos el offset:
    start_utc = naive_start - _server_offset
    end_utc   = naive_end_excl - _server_offset

    # 3) Seleccionar símbolo
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"No se pudo seleccionar el símbolo {symbol}")

    # 4) Copiar rates en UTC
    rates = mt5.copy_rates_range(symbol, mt5_tf, start_utc, end_utc)
    if rates is None:
        err = mt5.last_error()
        raise RuntimeError(f"copy_rates_range() falló: {err}")

    # 5) DataFrame y conversión a local
    df = pd.DataFrame(rates)
    # 'time' es UNIX UTC
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    # Convertimos a timezone del servidor sumando el offset
    df['time'] = df['time'] + _server_offset
    # y lo hacemos naive (sin tzinfo)
    df['time'] = df['time'].dt.tz_localize(None)

    # 6) Filtrar estrictamente [start_date 00:00, end_date+1 00:00)
    df = df[(df['time'] >= naive_start) & (df['time'] < naive_end_excl)]

    # 7) Seleccionar columnas finales
    return df[['time','open','high','low','close','tick_volume']]
