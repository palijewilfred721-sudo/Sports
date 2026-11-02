"""Windows desktop entry point: Flask in a thread + a native window."""
import socket
import threading
import time

import webview

from app import app

HOST, PORT = "127.0.0.1", 5000


def run_server():
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


def wait_for_server(timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            if s.connect_ex((HOST, PORT)) == 0:
                return True
        time.sleep(0.2)
    return False


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    wait_for_server()
    webview.create_window("Football Manager", f"http://{HOST}:{PORT}",
                          width=1200, height=800)
    webview.start()
