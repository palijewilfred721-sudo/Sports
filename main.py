"""Android entry point (python-for-android 'webview' bootstrap).

The bootstrap opens a WebView on http://localhost:5000, so this file only
has to run the Flask server on that port and keep running.
"""
from app import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
