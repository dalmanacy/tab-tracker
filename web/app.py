import json
import os

from flask import Flask, redirect, render_template, request, url_for

from moveon import MoveOn, MoveOnAPIError, MoveOnAuthError

app = Flask(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), ".moveon_config.json")


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(instance: str, username: str, password: str) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump({"instance": instance, "username": username, "password": password}, f)


def build_base_url(instance: str) -> str:
    return f"https://{instance}.restapi.moveonfr.com/api/v1/"


@app.route("/", methods=["GET"])
def index():
    cfg = load_config()
    return render_template("config.html", config=cfg, status=None, error=None)


@app.route("/connect", methods=["POST"])
def connect():
    instance = request.form.get("instance", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not instance or not username or not password:
        cfg = {"instance": instance, "username": username, "password": ""}
        return render_template("config.html", config=cfg, status=None, error="All fields are required.")

    base_url = build_base_url(instance)
    try:
        client = MoveOn(base_url, username, password)
        # Trigger a lightweight call to validate credentials
        client.academic_years.list(limit=1)
        save_config(instance, username, password)
        cfg = {"instance": instance, "username": username, "password": ""}
        return render_template("config.html", config=cfg, status="connected", error=None)
    except MoveOnAuthError:
        cfg = {"instance": instance, "username": username, "password": ""}
        return render_template("config.html", config=cfg, status=None, error="Invalid username or password.")
    except MoveOnAPIError as e:
        cfg = {"instance": instance, "username": username, "password": ""}
        return render_template("config.html", config=cfg, status=None, error=f"API error: {e.message}")
    except Exception as e:
        cfg = {"instance": instance, "username": username, "password": ""}
        return render_template("config.html", config=cfg, status=None, error=f"Could not reach instance: {e}")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
