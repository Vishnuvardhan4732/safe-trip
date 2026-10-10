import os
import sqlite3
import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from functools import wraps

import requests
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, abort
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "safetrip.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SAFETRIP_SECRET_KEY") or "local-demo-change-this-secret-key"

EMERGENCY_NUMBER = "112"
WEATHER_TIMEOUT = 6

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000)
    return salt, digest.hex()

def verify_password(password, salt, stored_hash):
    _, candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, stored_hash)

def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            title TEXT NOT NULL,
            severity TEXT NOT NULL,
            details TEXT NOT NULL,
            instructions TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            source TEXT NOT NULL DEFAULT 'Demonstration data',
            created_at TEXT NOT NULL
        )
    """)
    count = conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
    if count == 0:
        username = os.environ.get("SAFETRIP_ADMIN_USER", "admin")
        password = os.environ.get("SAFETRIP_ADMIN_PASSWORD", "SafeTrip@123")
        salt, pw_hash = hash_password(password)
        conn.execute(
            "INSERT INTO admins (username, salt, password_hash) VALUES (?, ?, ?)",
            (username, salt, pw_hash)
        )
    alert_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    if alert_count == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        samples = [
            ("Chennai (demo)", "Sample heavy-rain preparedness notice", "Medium",
             "This is example content for demonstration, not a live weather warning.",
             "Check official weather bulletins, avoid flooded roads, and follow local authorities.", "Active", "Demonstration data", now),
            ("Ooty (demo)", "Sample hill-travel caution", "Low",
             "This example reminds visitors to check road and weather conditions before travel.",
             "Carry suitable clothing and confirm road conditions with official sources.", "Active", "Demonstration data", now),
        ]
        conn.executemany("""
            INSERT INTO alerts
            (location, title, severity, details, instructions, status, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, samples)
    conn.commit()
    conn.close()

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Please sign in as an administrator.", "warning")
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper

def get_active_alerts(limit=10):
    conn = db()
    rows = conn.execute(
        "SELECT * FROM alerts WHERE status='Active' ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return rows

def fetch_weather(place):
    """Fetch weather from Open-Meteo without an API key; return explicit source status."""
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": place, "count": 1, "language": "en", "format": "json"},
            timeout=WEATHER_TIMEOUT
        )
        geo.raise_for_status()
        results = geo.json().get("results", [])
        if not results:
            return {"ok": False, "message": "No matching destination was found. Try a larger city name."}
        loc = results[0]
        weather = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m",
                "timezone": "auto"
            },
            timeout=WEATHER_TIMEOUT
        )
        weather.raise_for_status()
        current = weather.json().get("current", {})
        code = current.get("weather_code")
        descriptions = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle",
            53: "Moderate drizzle", 55: "Dense drizzle", 61: "Slight rain",
            63: "Moderate rain", 65: "Heavy rain", 71: "Slight snow",
            73: "Moderate snow", 75: "Heavy snow", 80: "Rain showers",
            81: "Moderate rain showers", 82: "Violent rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail"
        }
        return {
            "ok": True,
            "place": ", ".join(x for x in [loc.get("name"), loc.get("admin1"), loc.get("country")] if x),
            "temperature": current.get("temperature_2m", "—"),
            "feels_like": current.get("apparent_temperature", "—"),
            "humidity": current.get("relative_humidity_2m", "—"),
            "wind": current.get("wind_speed_10m", "—"),
            "description": descriptions.get(code, "Weather conditions available"),
            "time": current.get("time", "Time unavailable"),
            "source": "Live Open-Meteo data",
            "latitude": loc["latitude"],
            "longitude": loc["longitude"]
        }
    except (requests.RequestException, ValueError, KeyError) as exc:
        return {"ok": False, "message": "Live weather could not be loaded right now. Please check an official weather source. The app is still usable in demonstration mode."}

@app.context_processor
def shared_context():
    return {
        "emergency_number": EMERGENCY_NUMBER,
        "current_year": datetime.now().year
    }

@app.route("/")
def home():
    alerts = get_active_alerts(4)
    return render_template("index.html", alerts=alerts)

@app.route("/destination", methods=["GET", "POST"])
def destination():
    place = ""
    weather = None
    if request.method == "POST":
        place = request.form.get("place", "").strip()[:100]
        if not place:
            flash("Enter a destination to search.", "warning")
        else:
            weather = fetch_weather(place)
    return render_template("destination.html", place=place, weather=weather)

@app.route("/map")
def safety_map():
    return render_template("map.html")

@app.route("/health")
def health():
    return render_template("health.html")

@app.route("/emergency")
def emergency():
    return render_template("emergency.html")

@app.route("/checklist")
def checklist():
    return render_template("checklist.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = db()
        admin = conn.execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone()
        conn.close()
        if admin and verify_password(password, admin["salt"], admin["password_hash"]):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            session.permanent = True
            flash("Signed in successfully.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("admin_login.html")

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = db()
    alerts = conn.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin_dashboard.html", alerts=alerts)

@app.route("/admin/alerts/add", methods=["GET", "POST"])
@admin_required
def add_alert():
    if request.method == "POST":
        values = [
            request.form.get("location", "").strip()[:100],
            request.form.get("title", "").strip()[:150],
            request.form.get("severity", "Low"),
            request.form.get("details", "").strip()[:1000],
            request.form.get("instructions", "").strip()[:1000],
            request.form.get("source", "Administrator-entered information").strip()[:200]
        ]
        if not all(values[:2]) or not values[3] or not values[4]:
            flash("Complete all required fields.", "warning")
            return render_template("alert_form.html", alert=None)
        if values[2] not in ["Low", "Medium", "High", "Critical"]:
            abort(400)
        conn = db()
        conn.execute("""
            INSERT INTO alerts (location, title, severity, details, instructions, status, source, created_at)
            VALUES (?, ?, ?, ?, ?, 'Active', ?, ?)
        """, (*values, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        flash("Safety alert added.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("alert_form.html", alert=None)

@app.route("/admin/alerts/<int:alert_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_alert(alert_id):
    conn = db()
    alert = conn.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()
    if not alert:
        conn.close()
        abort(404)
    if request.method == "POST":
        location = request.form.get("location", "").strip()[:100]
        title = request.form.get("title", "").strip()[:150]
        severity = request.form.get("severity", "Low")
        details = request.form.get("details", "").strip()[:1000]
        instructions = request.form.get("instructions", "").strip()[:1000]
        source = request.form.get("source", "").strip()[:200]
        if not all([location, title, details, instructions, source]) or severity not in ["Low", "Medium", "High", "Critical"]:
            flash("Please complete all fields with valid values.", "warning")
            conn.close()
            return render_template("alert_form.html", alert=alert)
        conn.execute("""
            UPDATE alerts SET location=?, title=?, severity=?, details=?, instructions=?, source=?
            WHERE id=?
        """, (location, title, severity, details, instructions, source, alert_id))
        conn.commit()
        conn.close()
        flash("Alert updated.", "success")
        return redirect(url_for("admin_dashboard"))
    conn.close()
    return render_template("alert_form.html", alert=alert)

@app.route("/admin/alerts/<int:alert_id>/resolve", methods=["POST"])
@admin_required
def resolve_alert(alert_id):
    conn = db()
    conn.execute("UPDATE alerts SET status='Resolved' WHERE id=?", (alert_id,))
    conn.commit()
    conn.close()
    flash("Alert marked as resolved.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/alerts/<int:alert_id>/delete", methods=["POST"])
@admin_required
def delete_alert(alert_id):
    conn = db()
    conn.execute("DELETE FROM alerts WHERE id=?", (alert_id,))
    conn.commit()
    conn.close()
    flash("Alert deleted.", "info")
    return redirect(url_for("admin_dashboard"))

@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The page or record was not found."), 404

@app.errorhandler(500)
def server_error(_error):
    return render_template("error.html", code=500, message="Something went wrong. Please return to the home page."), 500

init_db()

if __name__ == "__main__":
    # Set SAFETRIP_SECRET_KEY and SAFETRIP_ADMIN_PASSWORD before public deployment.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
