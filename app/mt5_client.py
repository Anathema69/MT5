# app/mt5_client.py

import os
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

# ——— Credenciales y rutas para cada modo ———
_FOREX = {
    "MT5_PATH": r"C:\Program Files\MetaTrader 5\terminal64.exe",
    "LOGIN":    5037099836,
    "PASSWORD": "Cm_1NbVj",
    "SERVER":   "MetaQuotes-Demo"
}
_SYNTHETIC = {
    "MT5_PATH": r"C:\Program Files\MT5 Weltrade\terminal64.exe",
    "LOGIN":    19299053,
    "PASSWORD": "]Zc2p7+B",
    "SERVER":   "Weltrade-Demo"
}

# Variables globales que se van a reconfigurar en runtime
_MT5_PATH = None
_LOGIN    = None
_PASSWORD = None
_SERVER   = None

_initialized = False
_server_offset: timedelta = None  # offset local del broker

# Timeframe → segundos por barra
_BAR_SECONDS = {
    "M1":   60,      "M2":   120,    "M3":   180,    "M4":   240,
    "M5":  300,      "M6":   360,    "M10":  600,    "M12":  720,
    "M15": 900,      "M20": 1200,    "M30": 1800,
    "H1":  3600,     "H2":  7200,    "H3": 10800,    "H4": 14400,
    "H6": 21600,     "H8": 28800,    "H12": 43200,
    "D1": 86400,     "W1": 604800,   "MN1":2592000
}

_CHUNK_BARS = 70000  # barras por chunk recomendado


def set_mode(mode: str):
    """
    Configura globalmente _MT5_PATH, _LOGIN, _PASSWORD y _SERVER según el modo:
      - "forex"    → usa credenciales de _FOREX
      - "synthetic" → usa credenciales de _SYNTHETIC

    Si ya había una instancia inicializada, se hace shutdown para forzar reconexión.
    """
    global _MT5_PATH, _LOGIN, _PASSWORD, _SERVER, _initialized

    # Si ya estaba inicializado con otro modo, cerramos para reconectar
    if _initialized:
        mt5.shutdown()
        _initialized = False

    if mode == "forex":
        creds = _FOREX
    elif mode == "synthetic":
        creds = _SYNTHETIC
    else:
        raise ValueError(f"Modo desconocido: {mode!r}")

    _MT5_PATH = creds["MT5_PATH"]
    _LOGIN    = creds["LOGIN"]
    _PASSWORD = creds["PASSWORD"]
    _SERVER   = creds["SERVER"]
    _initialized = False


def initialize_mt5():
    """
    Inicializa MT5 una sola vez usando las variables globales:
        _MT5_PATH, _LOGIN, _PASSWORD, _SERVER.

    Luego lee el offset horario del broker.
    """
    global _initialized, _server_offset

    if _initialized:
        return

    logger.debug(f"MT5_PATH configurado: {_MT5_PATH!r}")
    logger.debug(f"LOGIN configurado:    {_LOGIN!r}")
    logger.debug(f"SERVER configurado:   {_SERVER!r}")

    success = mt5.initialize(
        path=_MT5_PATH,
        login=_LOGIN,
        password=_PASSWORD,
        server=_SERVER
    )

    if not success:
        err = mt5.last_error()
        raise RuntimeError(f"MT5 initialize() falló: {err}")

    info = mt5.terminal_info()
    tz_secs = getattr(info, "timezone", 0)
    _server_offset = timedelta(seconds=tz_secs)
    _initialized = True


def shutdown_mt5():
    """
    Cierra MT5 si estaba inicializado.
    """
    global _initialized
    if _initialized:
        mt5.shutdown()
        _initialized = False


def fetch_ohlc(symbol: str,
               timeframe: str,
               start: datetime,
               end: datetime) -> pd.DataFrame:
    """
    Descarga OHLC entre start y end (datetime naïve en zona local del broker).
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
    df['time'] = df['time'].dt.tz_convert(local_tz).dt.tz_localize(None)

    # 6) Filtramos exactamente entre start y end (inclusive si quieres)
    df = df[(df['time'] >= start) & (df['time'] <= end)]

    return df


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


def fetch_ticks_chunked(symbol: str,
                        start: datetime,
                        end: datetime) -> pd.DataFrame:
    """
    Descarga TICKS entre start y end (datetime naïve en zona local del broker),
    en “chunks” de 1 día (86400 segundos) para no sobrecargar MT5 en rangos muy largos.
    """
    initialize_mt5()

    secs_per_day = 86400
    chunks = _get_chunks(start, end, secs_per_day)

    dfs = []
    for s, e in chunks:
        # copy_ticks_range devuelve un array de ticks
        ticks = mt5.copy_ticks_range(symbol, s, e, mt5.COPY_TICKS_ALL)
        if ticks is None:
            continue
        df_chunk = pd.DataFrame(ticks)
        # Convertimos la columna `time` (segundos UTC) a datetime naïve en local:
        df_chunk['time'] = pd.to_datetime(df_chunk['time'], unit='s', utc=True)
        df_chunk['time'] = df_chunk['time'].dt.tz_localize(None)
        dfs.append(df_chunk)

    if not dfs:
        # Si no hubo ticks, devolvemos un DataFrame vacío con columnas típicas
        return pd.DataFrame(columns=['date','time', 'bid', 'ask', 'last', 'volume', 'flags'])


    full = pd.concat(dfs, ignore_index=True)
    full = full.sort_values('time').reset_index(drop=True)
    full = full[['time', 'bid', 'ask', 'last', 'volume', 'flags']]

    #formateamos el df para la salida esperada
    full_formated = format_df(full)

    return full_formated



def format_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Toma un DataFrame cuyo primer columna es datetime (nombre 'time' o equivalente)
    y las columnas siguientes son numéricas. Devuelve un nuevo DataFrame donde:
      - Se separa la primera columna datetime en:
          * 'date' -> solo fecha en formato 'dd-mm-yy'
          * 'time' -> solo hora en formato 'HH:MM:SS'
      - Las columnas numéricas se convierten a float y se redondean a 5 decimales.
    Si ocurre cualquier error, se imprime en consola el mensaje de error junto con
    los nombres de columnas que lo provocaron, y se retorna el DataFrame original sin modificaciones.
    """
    try:
        # Hacemos copia para no modificar el original
        df2 = df.copy()

        # 1) Asegurarnos de que la primera columna sea datetime
        time_col = df2.columns[0]


        # 2) Extraer fecha y hora en dos columnas nuevas
        #    - 'date' en formato dd-mm-yy
        #    - 'time' en formato HH:MM:SS
        df2.insert(0, 'DATE', pd.to_datetime(df2[time_col].dt.date, format='%d/%m/%y'))

        # Esto crea una columna de objetos time (sin fecha):
        # Se usa 'TIME' para que al eliminar no se confunda con el 'time' original
        df2.insert(1, 'TIME', df2[time_col].dt.time)

        # 3) Eliminar la columna datetime original
        df2 = df2.drop(columns=[time_col])

        # 4) Identificar las columnas "numéricas" restantes (cualquier dtype numérico)
        #    y convertir a float + redondear a 5 decimales
        for col in df2.columns:
            if pd.api.types.is_numeric_dtype(df2[col]):
                df2[col] = df2[col].astype(float).round(5)

        #renombramos las columnass a mayusculas
        df2.columns = df2.columns.str.upper()

        return  df2

    except Exception as e:
        # Si algo falla, imprimimos a consola qué columnas provocaron el error
        print(f"format_df ERROR: {e}")
        print(f"Columnas en df original: {df.columns.tolist()}")
        return df




# ——— Al importar el módulo, establecemos “forex” como modo por defecto ———
set_mode("forex")
