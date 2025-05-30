# app/main.py

# app/main.py, arriba de todo:
import os, sys


if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))


import logging
import threading
import socket
import webbrowser
import sys
from app.routes import app as flask_app
from app.mt5_client import initialize_mt5, shutdown_mt5

# Configura logging:
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),           # consola
        logging.FileHandler("app_debug.log", encoding="utf-8")  # fichero
    ]
)
logger = logging.getLogger(__name__)

def find_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def start_server(port):
    logger.info(f"Arrancando Flask en 127.0.0.1:{port}")
    flask_app.run(host='127.0.0.1', port=port, debug=False)

if __name__ == "__main__":
    # Inicializa MT5
    try:
        logger.debug("Inicializando MT5…")
        initialize_mt5()
    except Exception as e:
        logger.exception("Error inicializando MT5")
        sys.exit(1)

    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    # Arranca Flask en background
    server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
    server_thread.start()
    logger.info(f"Servidor Flask arrancado en {url}")

    # Abre navegador
    webbrowser.open(url)

    try:
        server_thread.join()
    except KeyboardInterrupt:
        logger.info("🛑 Recibido Ctrl+C, deteniendo aplicación.")
    finally:
        logger.debug("Shutting down MT5…")
        shutdown_mt5()
        logger.info("MT5 cerrado, bye!")
