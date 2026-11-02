"""Android launcher (Buildozer): Flask in a background thread, shown in a WebView.

Any startup error is shown on screen (and written to error.log) instead of
silently closing the app.
"""
import socket
import threading
import traceback

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def error_view(text):
    label = Label(text=text, font_size="12sp", size_hint_y=None,
                  halign="left", valign="top")
    label.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
    label.bind(texture_size=lambda w, s: setattr(w, "height", s[1]))
    scroll = ScrollView()
    scroll.add_widget(label)
    return scroll


class FootballApp(App):
    def build(self):
        self.webview = None
        self.server = None
        try:
            from werkzeug.serving import make_server
            from app import app as flask_app  # creates DB tables on import

            self.port = free_port()
            self.server = make_server("127.0.0.1", self.port, flask_app, threaded=True)
            threading.Thread(target=self.server.serve_forever, daemon=True).start()
            Window.bind(on_keyboard=self.on_keyboard)
            Clock.schedule_once(self.open_webview, 1)
            return Label(text="Starting Football Manager...")
        except Exception:
            return self.show_error()

    def show_error(self):
        text = traceback.format_exc()
        try:
            with open(self.user_data_dir + "/error.log", "w") as f:
                f.write(text)
        except Exception:
            pass
        return error_view("STARTUP ERROR\n\n" + text)

    def open_webview(self, _dt):
        try:
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
        except Exception:
            self.root_window.add_widget(
                error_view("WEBVIEW ERROR\n\n" + traceback.format_exc()))

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
        if self.server:
            self.server.shutdown()


if __name__ == "__main__":
    FootballApp().run()
