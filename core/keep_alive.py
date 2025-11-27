"""Enkel Flask-server for å holde botten i live (pingbar endpoint)."""

from threading import Thread
from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    """Returnerer en enkel statusmelding for helse/ping."""
    return "Bot is running!"


def run():
    """Starter Flask-serveren på 0.0.0.0:8080."""
    app.run(host="0.0.0.0", port=8080)


def keep_alive():
    """Starter serveren i egen tråd slik at botten kan holdes aktiv."""
    thread = Thread(target=run)
    thread.start()
