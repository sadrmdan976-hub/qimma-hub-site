import os
import socket
import sys
import threading
import webbrowser
from urllib.request import urlopen

os.chdir(os.path.dirname(os.path.abspath(__file__)))

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def port_in_use():
    s = socket.socket()
    s.settimeout(0.4)
    try:
        return s.connect_ex((HOST, PORT)) == 0
    finally:
        s.close()


def site_is_up():
    try:
        with urlopen(URL + "/healthz", timeout=1) as r:
            return b'"ok"' in r.read()
    except Exception:
        return False


def main():
    if port_in_use():
        if site_is_up():
            print("QIMMA HUB is already running. Opening:", URL)
            webbrowser.open(URL)
            return
        print(f"Port {PORT} is used by another program. Close it and try again.")
        sys.exit(1)

    threading.Timer(2.0, lambda: webbrowser.open(URL)).start()
    print("Starting QIMMA HUB on", URL)
    print("Keep this window open while using the site. Press Ctrl+C to stop.")
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
