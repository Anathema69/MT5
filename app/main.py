# app/main.py

import threading
import socket
import webbrowser
from app.routes import app as flask_app

from app.mt5_client import initialize_mt5, shutdown_mt5

def find_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def start_server(port):
    flask_app.run(host='127.0.0.1', port=port, debug=False)

if __name__ == "__main__":
    # Inicializa MT5
    try:
        initialize_mt5()
    except Exception as e:
        print(f"❌ Error inicializando MT5: {e}")
        exit(1)

    # Encuentra un puerto libre
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    # Arranca Flask en background
    server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
    server_thread.start()
    print(f"🖥️  Servidor Flask arrancado en {url}")

    # Abre el navegador por defecto
    webbrowser.open(url)

    # Espera al hilo (Ctrl+C para salir)
    try:
        server_thread.join()
    except KeyboardInterrupt:
        print("\n🚪 Deteniendo aplicación.")
    finally:
        shutdown_mt5()
