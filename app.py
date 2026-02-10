import threading
import time

import webview  # pywebview

from downloader.server import app as flask_app


def run_flask():
    """
    Sobe o servidor Flask em uma thread separada.
    use_reloader=False é importante para não criar processos extras.
    """
    flask_app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    # Inicia o Flask em segundo plano
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Dá um tempinho para o servidor subir
    time.sleep(1)

    # Abre uma janela nativa carregando o front servido pelo Flask
    window = webview.create_window("AuroraYt", "http://127.0.0.1:5000/")
    webview.start()

