#!/usr/bin/env python
# test_connection.py
# Prueba de conexión a MetaTrader 5

import os
from dotenv import load_dotenv
import MetaTrader5 as mt5

def main():
    # 1) Carga .env
    load_dotenv()  # lee .env en el mismo directorio

    login    = int(os.getenv("MT5_LOGIN", 0))
    password = os.getenv("MT5_PASSWORD", "")
    server   = os.getenv("MT5_SERVER", "")

    # 2) Inicializa MT5 (suponiendo MT5 ya abierto)
    if not mt5.initialize(login=login, password=password, server=server):
        print("❌ Falló initialize():", mt5.last_error())
        return

    # 3) Muestra info de la cuenta
    info = mt5.account_info()
    if info:
        print("✅ Conectado:")
        print(f"   Login:   {info.login}")
        print(f"   Balance: {info.balance}")
        print(f"   Server:  {info.server}")
    else:
        print("❌ No se obtuvo account_info():", mt5.last_error())

    # 4) Cierra MT5
    mt5.shutdown()

if __name__ == "__main__":
    main()
