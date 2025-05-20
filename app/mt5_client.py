# app/mt5_client.py

import os
from datetime import datetime
from dotenv import load_dotenv
import MetaTrader5 as mt5
import pandas as pd

# Carga variables de entorno
load_dotenv()  # busca .env en la raíz del proyecto

# Parámetros de conexión
_MT5_PATH = os.getenv("MT5_PATH")        # Ruta al terminal MT5 (opcional)
_LOGIN     = int(os.getenv("MT5_LOGIN", 0))
_PASSWORD  = os.getenv("MT5_PASSWORD", "")
_SERVER    = os.getenv("MT5_SERVER", "")

_initialized = False

def initialize_mt5():
    """
    Inicializa la conexión con MetaTrader5.
    Llama mt5.initialize() solo una vez.
    """
    global _initialized
    if _initialized:
        return True

    # Si quieres lanzar MT5 desde aquí, pasa path=_MT5_PATH
    success = mt5.initialize(
        path=_MT5_PATH or None,
        login=_LOGIN,
        password=_PASSWORD,
        server=_SERVER
    )
    if not success:
        err = mt5.last_error()
        raise RuntimeError(f"MT5 initialize() falló: {err}")
    _initialized = True
    return True

def shutdown_mt5():
    """
    Cierra la conexión con MetaTrader5.
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
    Descarga datos OHLC para un símbolo dado, en el rango de fechas y timeframe indicado.

    Args:
        symbol (str): nombre del símbolo (p.ej. "EURUSD").
        timeframe (str): uno de ["1s", "1m", "1h", "1d"].
        start (datetime): fecha/hora de inicio.
        end (datetime): fecha/hora de fin.

    Returns:
        pd.DataFrame: DataFrame con columnas ['time', 'open', 'high', 'low', 'close', 'tick_volume'].
    """
    # Asegura que MT5 esté inicializado
    initialize_mt5()

    # Mapea string a timeframe de MT5
    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M2": mt5.TIMEFRAME_M2,
        "M3": mt5.TIMEFRAME_M3,
        "M4": mt5.TIMEFRAME_M4,
        "M5": mt5.TIMEFRAME_M5,
        "M6": mt5.TIMEFRAME_M6,
        "M10": mt5.TIMEFRAME_M10,
        "M12": mt5.TIMEFRAME_M12,
        "M15": mt5.TIMEFRAME_M15,
        "M20": mt5.TIMEFRAME_M20,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H2": mt5.TIMEFRAME_H2,
        "H3": mt5.TIMEFRAME_H3,
        "H4": mt5.TIMEFRAME_H4,
        "H6": mt5.TIMEFRAME_H6,
        "H8": mt5.TIMEFRAME_H8,
        "H12": mt5.TIMEFRAME_H12,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
    if timeframe not in tf_map:
        raise ValueError(f"Timeframe desconocido: {timeframe}")

    mt5_tf = tf_map[timeframe]

    # Asegúrate de que el símbolo esté disponible
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"No se pudo seleccionar el símbolo {symbol}")

    # Copia los rates en el rango
    rates = mt5.copy_rates_range(symbol, mt5_tf, start, end)
    if rates is None:
        err = mt5.last_error()
        raise RuntimeError(f"copy_rates_range fallo: {err}")

    # Convierte a DataFrame y formatea la columna time
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    # Selecciona y renombra columnas
    df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
    return df
