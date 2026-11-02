"""Android launcher (Buildozer): Flask in a background thread, shown in a WebView."""
import socket
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.label import Label
from werkzeug.serving import make_server

from app import app as flask_app


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class FootballApp(App):
    def build(self):
        self.webview = None
        self.port = free_port()
        self.server = make_server("127.0.0.1", self.port, flask_app, threaded=True)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        Window.bind(on_keyboard=self.on_keyboard)
        Clock.schedule_once(self.open_webview, 1)
        return Label(text="Starting Football Manager...")

    def open_webview(self, _dt):
        from android.runnable import run_on_ui_thread
        from jnius import autoclass

        WebView = autoclass("android.webkit.WebView")
        WebViewClient = autoclass("android.webkit.WebViewClient")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        url = f"http://127.0.0.1:{self.port}/"

        @run_on_ui_thread
        def create():
            view = WebView(activity)
            settings = view.getSettings()
            settings.setJavaScriptEnabled(True)
            settings.setDomStorageEnabled(True)
            view.setWebViewClient(WebViewClient())
            activity.setContentView(view)
            view.loadUrl(url)
            self.webview = view

        create()

    def on_keyboard(self, _window, key, *_args):
        if key == 27 and self.webview is not None:  # Android back button
            from android.runnable import run_on_ui_thread

            @run_on_ui_thread
            def back():
                if self.webview.canGoBack():
                    self.webview.goBack()

            back()
            return True
        return False

    def on_pause(self):
        return True

    def on_stop(self):
        self.server.shutdown()


if __name__ == "__main__":
    FootballApp().run()
