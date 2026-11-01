"""Windows desktop launcher: runs Flask locally and shows it in a native window."""
import socket
import threading

from werkzeug.serving import make_server

from app import app


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    port = free_port()
    server = make_server("127.0.0.1", port, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    try:
        import webview
        webview.create_window("Football Manager", url, width=1100, height=760)
        webview.start()
    except Exception as error:  # e.g. WebView2 runtime missing
        try:
            import tkinter
            from tkinter import messagebox
            root = tkinter.Tk()
            root.withdraw()
            messagebox.showerror(
                "Football Manager",
                "Could not open the app window.\n"
                "Install the Microsoft Edge WebView2 Runtime and try again.\n\n"
                f"Details: {error}",
            )
        except Exception:
            pass
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
