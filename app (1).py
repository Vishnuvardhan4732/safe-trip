"""
SafeTrip — Tourist Safety, Health & Emergency Assistance Platform
Single-file Flask application for a hackathon prototype.

Run:
    py -m pip install flask
    py app.py
Then open http://127.0.0.1:5000

Optional production environment variables:
    SAFETRIP_SECRET_KEY
    SAFETRIP_ADMIN_USER
    SAFETRIP_ADMIN_PASSWORD

Data integrity notes:
- Weather is fetched from Open-Meteo when internet access is available.
- Map base layer is OpenStreetMap via Leaflet.
- Seeded alerts are DEMO examples, not live verified hazard reports.
- This prototype does not dispatch emergency services or verify nearby facilities.
"""

from flask import Flask, request, redirect, url_for, session, render_template_string, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timezone
from urllib.parse import urlencode
import sqlite3
import urllib.request
import json
import os
import secrets
import html

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SAFETRIP_SECRET_KEY") or secrets.token_hex(32)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "safetrip.db")
ADMIN_USER = os.environ.get("SAFETRIP_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("SAFETRIP_ADMIN_PASSWORD", "SafeTrip@123")
ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD)

LANGUAGES = {
    "en": "English", "ta": "தமிழ்", "te": "తెలుగు", "hi": "हिन्दी"
}

HEALTH_GUIDES = {
    "en": [
        ("Hydration", "Drink safe water regularly, especially in hot weather."),
        ("Medication", "Carry prescribed medicines in their original packaging."),
        ("Food safety", "Wash hands before eating and choose safely prepared food."),
        ("Heat and sun", "Use shade, suitable clothing and sun protection."),
        ("Urgent symptoms", "Seek professional medical help for severe symptoms.")
    ],
    "ta": [
        ("நீரேற்றம்", "வெப்பமான காலநிலையில் பாதுகாப்பான நீரை அடிக்கடி குடிக்கவும்."),
        ("மருந்துகள்", "மருத்துவர் பரிந்துரைத்த மருந்துகளை அசல் பொதியில் எடுத்துச் செல்லவும்."),
        ("உணவு பாதுகாப்பு", "உணவுக்கு முன் கைகளைக் கழுவி பாதுகாப்பான உணவைத் தேர்ந்தெடுக்கவும்."),
        ("வெயில் பாதுகாப்பு", "நிழலில் இருங்கள்; பொருத்தமான உடை மற்றும் சூரிய பாதுகாப்பைப் பயன்படுத்துங்கள்."),
        ("அவசர அறிகுறிகள்", "கடுமையான அறிகுறிகள் இருந்தால் மருத்துவ உதவியைப் பெறுங்கள்.")
    ],
    "te": [
        ("నీరు", "వేడి వాతావరణంలో సురక్షితమైన నీటిని తరచుగా తాగండి."),
        ("మందులు", "వైద్యుడు సూచించిన మందులను అసలు ప్యాకేజీలో తీసుకెళ్లండి."),
        ("ఆహార భద్రత", "తినే ముందు చేతులు కడుక్కొని సురక్షితమైన ఆహారాన్ని ఎంచుకోండి."),
        ("ఎండ నుంచి రక్షణ", "నీడలో ఉండండి; తగిన దుస్తులు, సూర్యరశ్మి రక్షణ ఉపయోగించండి."),
        ("తీవ్ర లక్షణాలు", "తీవ్రమైన లక్షణాలు ఉంటే వైద్య సహాయం పొందండి.")
    ],
    "hi": [
        ("पानी", "गर्म मौसम में सुरक्षित पानी नियमित रूप से पिएँ।"),
        ("दवाएँ", "डॉक्टर द्वारा बताई गई दवाएँ मूल पैकेजिंग में रखें।"),
        ("खाद्य सुरक्षा", "खाने से पहले हाथ धोएँ और सुरक्षित भोजन चुनें।"),
        ("धूप से बचाव", "छाया में रहें और उपयुक्त कपड़े व धूप से सुरक्षा अपनाएँ।"),
        ("गंभीर लक्षण", "गंभीर लक्षण होने पर चिकित्सा सहायता लें।")
    ]
}

BASE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#10243a">
<title>{{ title }} · SafeTrip</title>
<link rel="preconnect" href="https://unpkg.com">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
:root{--navy:#10243a;--blue:#176b87;--teal:#16a6a1;--bg:#f3f7fb;--ink:#172b3a;--muted:#5e7182;--line:#dce6ee;--white:#fff;--orange:#f59e0b;--red:#dc4545;--green:#16845b}
*{box-sizing:border-box}body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.55}
a{color:var(--blue)}header{background:linear-gradient(120deg,#10243a,#176b87);color:white;padding:18px max(18px,calc((100% - 1180px)/2));display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap}
.brand{display:flex;gap:12px;align-items:center}.logo{font-size:28px;background:#ffffff20;border-radius:12px;padding:8px}.brand h1{font-size:22px;margin:0}.brand p{margin:0;color:#d3e8f3;font-size:12px}
nav{background:#0c1d30;display:flex;justify-content:center;gap:4px;flex-wrap:wrap;padding:8px 12px}nav a{color:#e7f2fa;text-decoration:none;padding:9px 12px;border-radius:8px;font-size:14px}nav a:hover,nav a.active{background:#24445d;color:white}
main{max-width:1180px;margin:26px auto;padding:0 18px;min-height:65vh}.hero{padding:38px;border-radius:20px;color:white;background:linear-gradient(120deg,#12304b,#087e8b);position:relative;overflow:hidden}.hero h2{font-size:clamp(28px,4vw,44px);line-height:1.12;max-width:700px;margin:0 0 14px}.hero p{max-width:680px;color:#e0f4f6}.hero .btn{background:white;color:#12304b}
.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:16px;margin:18px 0}.col-3{grid-column:span 3}.col-4{grid-column:span 4}.col-5{grid-column:span 5}.col-6{grid-column:span 6}.col-7{grid-column:span 7}.col-8{grid-column:span 8}.col-12{grid-column:span 12}
.card{background:var(--white);border:1px solid var(--line);border-radius:15px;padding:21px;box-shadow:0 5px 18px #17324a08}.card h2,.card h3{margin-top:0}.muted{color:var(--muted)}.small{font-size:12px;color:var(--muted)}.eyebrow{text-transform:uppercase;letter-spacing:1.4px;font-size:11px;font-weight:800;color:var(--teal)}
.btn,button{display:inline-block;border:0;background:var(--blue);color:white;text-decoration:none;padding:10px 15px;border-radius:9px;font-weight:700;cursor:pointer;font-size:14px}.btn.secondary,button.secondary{background:#e8f1f6;color:#153b53}.btn.danger,button.danger{background:var(--red)}.btn.success{background:var(--green)}button:hover,.btn:hover{filter:brightness(.94)}
input,select,textarea{width:100%;border:1px solid #cbd8e2;border-radius:8px;padding:11px 12px;font:inherit;background:white;color:var(--ink)}label{font-size:13px;font-weight:700;display:block;margin:9px 0 5px}.form-row{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.form-actions{margin-top:16px;display:flex;gap:10px;flex-wrap:wrap}
.stat{font-size:30px;font-weight:800;line-height:1.2}.stat-label{font-size:13px;color:var(--muted)}.pill{display:inline-block;padding:4px 9px;border-radius:999px;background:#e8f4f7;color:#176b87;font-size:11px;font-weight:800}.pill.warning{background:#fff1d2;color:#875600}.pill.danger{background:#ffe7e7;color:#9e2424}.pill.good{background:#e2f7ed;color:#126847}
.notice{border-left:4px solid var(--orange);background:#fff8e8;padding:13px 15px;border-radius:7px;margin:14px 0}.success-msg{background:#e7f8ef;color:#126847;padding:11px;border-radius:8px;margin-bottom:12px}.error-msg{background:#ffeded;color:#8d2424;padding:11px;border-radius:8px;margin-bottom:12px}
table{width:100%;border-collapse:collapse;background:white}th,td{padding:11px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}th{background:#edf4f8;font-size:12px;text-transform:uppercase;letter-spacing:.5px}td{font-size:14px}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:10px}
#map{height:430px;border-radius:12px;border:1px solid var(--line);z-index:1}.checkrow{display:flex;align-items:flex-start;gap:10px;padding:11px 0;border-bottom:1px solid var(--line)}.checkrow input{width:auto;margin-top:5px}.checkrow span{flex:1}.checkrow.done span{text-decoration:line-through;color:var(--muted)}
footer{text-align:center;padding:24px;background:#0c1d30;color:#cbd9e4;font-size:12px;margin-top:35px}.empty{padding:24px;text-align:center;color:var(--muted)}.weather-big{font-size:40px;font-weight:800}.two-buttons{display:flex;gap:10px;flex-wrap:wrap}
@media(max-width:760px){.col-3,.col-4,.col-5,.col-6,.col-7,.col-8{grid-column:span 12}.hero{padding:25px}.form-row{grid-template-columns:1fr}header{padding:16px}main{margin:16px auto}nav a{padding:8px;font-size:12px}.stat{font-size:25px}}
</style>
</head>
<body>
<header><div class="brand"><div class="logo">🧭</div><div><h1>SafeTrip</h1><p>Tourist Safety · Health · Emergency Support</p></div></div>
<div><span class="pill">HACKATHON PROTOTYPE</span></div></header>
<nav>
<a href="{{ url_for('home') }}">Overview</a>
<a href="{{ url_for('destination') }}">Destination & Weather</a>
<a href="{{ url_for('map_page') }}">Safety Map</a>
<a href="{{ url_for('health') }}">Health Guide</a>
<a href="{{ url_for('checklist') }}">Checklist</a>
<a href="{{ url_for('alerts') }}">Safety Alerts</a>
<a href="{{ url_for('emergency') }}">Emergency</a>
<a href="{{ url_for('admin') }}">Admin</a>
</nav>
<main>
{% with messages = get_flashed_messages(with_categories=true) %}
{% for category, message in messages %}<div class="{{ 'success-msg' if category == 'success' else 'error-msg' }}">{{ message }}</div>{% endfor %}
{% endwith %}
{{ content|safe }}
</main>
<footer>SafeTrip · Responsible travel assistance · Verify urgent information with official local authorities.<br>Weather and map services require an internet connection.</footer>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
</body></html>
"""

def render_page(title, body, **context):
    content = render_template_string(body, **context)
    return render_template_string(BASE, title=title, content=content)

def db_connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db_connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            location TEXT NOT NULL,
            severity TEXT NOT NULL,
            details TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'Community/demo entry',
            created_at TEXT NOT NULL,
            is_demo INTEGER NOT NULL DEFAULT 1
        )""")
        if con.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            con.executemany("""INSERT INTO alerts(title,location,severity,details,source,created_at,is_demo)
            VALUES(?,?,?,?,?,?,1)""", [
                ("Sample heavy-rain travel caution", "Demo location", "Medium",
                 "Illustrative entry only. Check the official meteorological department for current warnings.",
                 "SafeTrip demo seed", now),
                ("Sample crowded-area reminder", "Demo location", "Low",
                 "Keep valuables secure and agree on a meeting point with your group.",
                 "SafeTrip demo seed", now)
            ])

def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(24)
    return session["_csrf"]

def csrf_field():
    return '<input type="hidden" name="_csrf" value="' + html.escape(csrf_token()) + '">'

@app.before_request
def csrf_guard():
    if request.method == "POST":
        sent = request.form.get("_csrf", "")
        expected = session.get("_csrf", "")
        if not expected or not secrets.compare_digest(sent, expected):
            return "Invalid or expired form token. Refresh the page and try again.", 400

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please sign in as an administrator first.", "error")
            return redirect(url_for("admin"))
        return fn(*args, **kwargs)
    return wrapper

def weather_lookup(city):
    """Fetch current weather through Open-Meteo; returns a result or readable error."""
    q = urlencode({"name": city, "count": 1, "language": "en", "format": "json"})
    req = urllib.request.Request(
        "https://geocoding-api.open-meteo.com/v1/search?" + q,
        headers={"User-Agent": "SafeTripHackathonPrototype/1.0"}
    )
    with urllib.request.urlopen(req, timeout=8) as response:
        places = json.loads(response.read().decode("utf-8")).get("results", [])
    if not places:
        return None, "We couldn't find that destination. Try a larger nearby city."
    place = places[0]
    wurl = "https://api.open-meteo.com/v1/forecast?" + urlencode({
        "latitude": place["latitude"], "longitude": place["longitude"],
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m",
        "timezone": "auto"
    })
    req = urllib.request.Request(wurl, headers={"User-Agent": "SafeTripHackathonPrototype/1.0"})
    with urllib.request.urlopen(req, timeout=8) as response:
        current = json.loads(response.read().decode("utf-8")).get("current", {})
    return {"place": place, "current": current}, None

@app.route("/")
def home():
    with db_connect() as con:
        count = con.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        high = con.execute("SELECT COUNT(*) FROM alerts WHERE lower(severity)='high'").fetchone()[0]
        latest = con.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 3").fetchall()
    body = r"""
    <section class="hero">
      <div class="eyebrow" style="color:#9de8e3">TRAVEL SMARTER. TRAVEL SAFER.</div>
      <h2>Your companion for safer journeys.</h2>
      <p>Check destination conditions, review travel health guidance, prepare a personal checklist and access emergency information from one responsive dashboard.</p>
      <div class="two-buttons"><a class="btn" href="{{ url_for('destination') }}">Check destination weather →</a><a class="btn secondary" href="{{ url_for('checklist') }}">Prepare my trip</a></div>
    </section>
    <div class="grid">
      <div class="card col-3"><div class="eyebrow">Safety notices</div><div class="stat">{{ count }}</div><div class="stat-label">Entries in the alert board</div></div>
      <div class="card col-3"><div class="eyebrow">High severity</div><div class="stat">{{ high }}</div><div class="stat-label">Entries marked high</div></div>
      <div class="card col-3"><div class="eyebrow">Languages</div><div class="stat">4</div><div class="stat-label">English, Tamil, Telugu, Hindi</div></div>
      <div class="card col-3"><div class="eyebrow">Emergency</div><div class="stat">112</div><div class="stat-label">India emergency number</div></div>
    </div>
    <div class="grid">
      <div class="card col-4"><h3>🌦️ Destination conditions</h3><p class="muted">Look up current weather for a destination using an external weather service.</p><a href="{{ url_for('destination') }}">Search weather →</a></div>
      <div class="card col-4"><h3>🗺️ Interactive map</h3><p class="muted">Explore a destination on an OpenStreetMap base layer.</p><a href="{{ url_for('map_page') }}">Open map →</a></div>
      <div class="card col-4"><h3>🩺 Health preparation</h3><p class="muted">Read general travel health reminders in your preferred language.</p><a href="{{ url_for('health') }}">View health guide →</a></div>
    </div>
    <div class="card"><h2>Latest safety board entries</h2>
      <div class="notice">Demo entries are clearly labelled. They are not verified live hazard reports or official government alerts.</div>
      {% for a in latest %}<div style="padding:12px 0;border-bottom:1px solid #dce6ee"><span class="pill {{ 'danger' if a['severity']=='High' else 'warning' if a['severity']=='Medium' else 'good' }}">{{ a['severity'] }}</span> <b>{{ a['title'] }}</b><div class="small">{{ a['location'] }} · {{ a['created_at'] }} · {{ a['source'] }}</div><p>{{ a['details'] }}</p></div>{% else %}<p class="empty">No alerts available.</p>{% endfor %}
      <p><a href="{{ url_for('alerts') }}">View all entries →</a></p>
    </div>
    <div class="notice"><b>Important:</b> SafeTrip is an informational prototype, not an emergency dispatch service. In immediate danger, contact local emergency services and follow official instructions.</div>
    """
    return render_page("Overview", body, count=count, high=high, latest=latest)

@app.route("/destination", methods=["GET", "POST"])
def destination():
    result, error, city = None, None, ""
    if request.method == "POST":
        city = request.form.get("city", "").strip()[:100]
        if not city:
            error = "Enter a destination name."
        else:
            try:
                result, error = weather_lookup(city)
            except Exception:
                error = "Live weather could not be loaded. Check your internet connection and try again."
    body = r"""
    <div class="card"><div class="eyebrow">Destination planner</div><h2>Weather lookup</h2>
    <p class="muted">Search for a city to retrieve current weather from Open-Meteo. Values are live only when the service responds successfully.</p>
    <form method="post">{{ csrf|safe }}<label for="city">Destination city</label><input id="city" name="city" value="{{ city }}" placeholder="e.g. Chennai, Ooty, Hyderabad" maxlength="100" required><div class="form-actions"><button>Check current weather</button></div></form>
    {% if error %}<div class="notice">{{ error }}</div>{% endif %}
    {% if result %}<div class="grid">
      <div class="card col-5"><div class="eyebrow">Destination</div><h2>{{ result.place.name }}{% if result.place.country %}, {{ result.place.country }}{% endif %}</h2><div class="weather-big">{{ result.current.get('temperature_2m','—') }}°C</div><p>Feels like {{ result.current.get('apparent_temperature','—') }}°C</p><span class="pill good">Live response received</span></div>
      <div class="card col-7"><h3>Current conditions</h3><div class="grid">
        <div class="col-6"><b>Humidity</b><div>{{ result.current.get('relative_humidity_2m','—') }}%</div></div>
        <div class="col-6"><b>Wind speed</b><div>{{ result.current.get('wind_speed_10m','—') }} km/h</div></div>
        <div class="col-6"><b>Precipitation</b><div>{{ result.current.get('precipitation','—') }} mm</div></div>
        <div class="col-6"><b>Coordinates</b><div>{{ '%.4f'|format(result.place.latitude) }}, {{ '%.4f'|format(result.place.longitude) }}</div></div>
      </div><p class="small">Weather is not a substitute for official severe-weather warnings.</p></div>
    </div>{% endif %}
    </div>
    """
    return render_page("Destination & Weather", body, result=result, error=error, city=city, csrf=csrf_field())

@app.route("/map")
def map_page():
    city = request.args.get("city", "Chennai").strip()[:100] or "Chennai"
    body = r"""
    <div class="card"><div class="eyebrow">Explore</div><h2>Interactive destination map</h2>
    <p class="muted">Map tiles are provided by OpenStreetMap. Search is geocoded by Nominatim. Respect the provider's usage policy.</p>
    <form id="mapForm"><label for="mapCity">Search a destination</label><input id="mapCity" value="{{ city }}" maxlength="100" required><div class="form-actions"><button type="submit">Find destination</button><button class="secondary" type="button" id="locate">Use my location</button></div></form>
    <div id="map"></div><p id="mapStatus" class="small">Loading map…</p>
    <div class="notice">This map is for orientation. It does not certify the location, availability or safety of hospitals, shelters, police stations or other facilities.</div></div>
    <script>
    const map=L.map('map').setView([13.0827,80.2707],11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
    let marker=null;
    async function searchPlace(name){
      const status=document.getElementById('mapStatus');status.textContent='Searching…';
      try{
        const response=await fetch('https://nominatim.openstreetmap.org/search?format=json&limit=1&q='+encodeURIComponent(name));
        if(!response.ok)throw new Error('Search service unavailable');
        const data=await response.json();if(!data.length)throw new Error('Destination not found');
        const p=data[0],lat=Number(p.lat),lon=Number(p.lon);
        map.setView([lat,lon],13);if(marker)map.removeLayer(marker);
        marker=L.marker([lat,lon]).addTo(map).bindPopup(p.display_name).openPopup();
        status.textContent='Location found: '+p.display_name;
      }catch(e){status.textContent=e.message+'. Try again later.'}
    }
    document.getElementById('mapForm').addEventListener('submit',e=>{e.preventDefault();searchPlace(document.getElementById('mapCity').value)});
    document.getElementById('locate').addEventListener('click',()=>{
      const status=document.getElementById('mapStatus');
      if(!navigator.geolocation){status.textContent='Geolocation is not supported by this browser.';return}
      status.textContent='Requesting location permission…';
      navigator.geolocation.getCurrentPosition(p=>{
        const lat=p.coords.latitude,lon=p.coords.longitude;map.setView([lat,lon],15);
        if(marker)map.removeLayer(marker);marker=L.marker([lat,lon]).addTo(map).bindPopup('Your device location').openPopup();
        status.textContent='Showing your device location. It has not been sent to SafeTrip.';
      },()=>{status.textContent='Location permission denied or unavailable.'});
    });
    searchPlace(document.getElementById('mapCity').value);
    </script>
    """
    return render_page("Interactive Map", body, city=city)

@app.route("/health")
def health():
    lang = request.args.get("lang", "en")
    if lang not in HEALTH_GUIDES:
        lang = "en"
    body = r"""
    <div class="card"><div class="eyebrow">Travel wellbeing</div><h2>Health preparation guide</h2>
    <form method="get"><label for="lang">Choose language / மொழி / భాష / भाषा</label><select name="lang" id="lang" onchange="this.form.submit()">
    {% for key, label in languages.items() %}<option value="{{ key }}" {{ 'selected' if key==lang else '' }}>{{ label }}</option>{% endfor %}
    </select></form>
    {% for heading, detail in guide %}<div style="padding:14px 0;border-bottom:1px solid #dce6ee"><h3>{{ heading }}</h3><p>{{ detail }}</p></div>{% endfor %}
    <div class="notice"><b>Health disclaimer:</b> General travel information only; not diagnosis or treatment advice. For urgent or severe symptoms, seek qualified medical care.</div></div>
    """
    return render_page("Health Guide", body, languages=LANGUAGES, lang=lang, guide=HEALTH_GUIDES[lang])

@app.route("/checklist", methods=["GET", "POST"])
def checklist():
    body = r"""
    <div class="card"><div class="eyebrow">Before you go</div><h2>Personal travel checklist</h2>
    <p class="muted">Your checklist progress is saved in this browser on this device only.</p>
    <div id="checklist">
    {% for item in items %}<label class="checkrow"><input type="checkbox" data-id="{{ loop.index0 }}"><span>{{ item }}</span></label>{% endfor %}
    </div><div style="margin-top:18px"><b id="progress">0 of {{ items|length }} complete</b><div style="height:8px;background:#e3ebf1;border-radius:99px;margin-top:8px"><div id="bar" style="height:8px;width:0;background:#16a6a1;border-radius:99px"></div></div></div>
    <div class="form-actions"><button id="reset" type="button" class="secondary">Reset checklist</button><button id="print" type="button">Print checklist</button></div></div>
    <script>
    const key='safetrip_checklist_v1', boxes=[...document.querySelectorAll('[data-id]')];
    function update(){let done=0;boxes.forEach(b=>{b.checked=JSON.parse(localStorage.getItem(key+'_'+b.dataset.id)||'false');b.closest('.checkrow').classList.toggle('done',b.checked);if(b.checked)done++});document.getElementById('progress').textContent=done+' of '+boxes.length+' complete';document.getElementById('bar').style.width=(done/boxes.length*100)+'%'}
    boxes.forEach(b=>b.addEventListener('change',()=>{localStorage.setItem(key+'_'+b.dataset.id,JSON.stringify(b.checked));update()}));
    document.getElementById('reset').onclick=()=>{boxes.forEach(b=>localStorage.removeItem(key+'_'+b.dataset.id));update()};
    document.getElementById('print').onclick=()=>window.print();update();
    </script>
    """
    items = [
        "Government ID / passport and copies", "Tickets, bookings and accommodation details",
        "Phone, charger and power bank", "Prescribed medicines and basic first-aid items",
        "Emergency contacts saved offline", "Travel insurance information if applicable",
        "Weather-appropriate clothing", "Safe drinking water and essential supplies",
        "Share itinerary with a trusted person", "Check official travel advisories"
    ]
    return render_page("Travel Checklist", body, items=items)

@app.route("/emergency")
def emergency():
    body = r"""
    <div class="hero"><div class="eyebrow" style="color:#9de8e3">Emergency information</div>
    <h2>Put your immediate safety first.</h2>
    <p>If there is immediate danger in India, call the official emergency number 112. If you are elsewhere, use the local emergency number.</p>
    <div class="two-buttons"><a class="btn" href="tel:112">Call 112 (India)</a><a class="btn secondary" href="https://112.gov.in/" target="_blank" rel="noopener">Official 112 website</a></div></div>
    <div class="grid">
      <div class="card col-6"><h3>When calling for help</h3><ul><li>State your location as clearly as possible.</li><li>Explain what happened and whether anyone is injured.</li><li>Follow the operator's instructions.</li><li>Do not put yourself in additional danger to collect information.</li></ul></div>
      <div class="card col-6"><h3>Before travelling</h3><ul><li>Save local emergency numbers offline.</li><li>Share your itinerary with a trusted person.</li><li>Keep identification and essential medication accessible.</li><li>Follow official weather and local authority guidance.</li></ul></div>
    </div>
    <div class="notice"><b>Important limitation:</b> SafeTrip does not call, dispatch or message emergency services automatically. The call link depends on your device and network.</div>
    """
    return render_page("Emergency Assistance", body)

@app.route("/alerts")
def alerts():
    severity = request.args.get("severity", "").strip().title()
    allowed = {"Low", "Medium", "High"}
    with db_connect() as con:
        if severity in allowed:
            rows = con.execute("SELECT * FROM alerts WHERE severity=? ORDER BY id DESC", (severity,)).fetchall()
        else:
            rows = con.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()
    body = r"""
    <div class="card"><div class="eyebrow">Community safety board</div><h2>Safety alerts and travel notices</h2>
    <p>Entries may be demonstrations or administrator-submitted reports. Verify important warnings through official sources.</p>
    <form method="get" class="form-row"><div><label>Filter by severity</label><select name="severity"><option value="">All levels</option>{% for s in ['Low','Medium','High'] %}<option {{ 'selected' if severity==s else '' }}>{{ s }}</option>{% endfor %}</select></div><div style="align-self:end"><button>Apply filter</button> <a class="btn secondary" href="{{ url_for('alerts') }}">Clear</a></div></form>
    {% for a in rows %}<div class="card"><span class="pill {{ 'danger' if a['severity']=='High' else 'warning' if a['severity']=='Medium' else 'good' }}">{{ a['severity'] }} severity</span> <span class="pill">{{ 'DEMO' if a['is_demo'] else 'USER SUBMITTED' }}</span><h3>{{ a['title'] }}</h3><p>{{ a['details'] }}</p><div class="small">Location: {{ a['location'] }} · Source: {{ a['source'] }} · {{ a['created_at'] }}</div></div>{% else %}<div class="empty">No entries match this filter.</div>{% endfor %}
    </div>
    """
    return render_page("Safety Alerts", body, rows=rows, severity=severity)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if secrets.compare_digest(username, ADMIN_USER) and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_logged_in"] = True
            session["admin_user"] = username
            flash("Signed in successfully.", "success")
            return redirect(url_for("admin"))
        flash("Login failed. Check the credentials and try again.", "error")
    if session.get("admin_logged_in"):
        with db_connect() as con:
            rows = con.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()
        body = r"""
        <div class="card"><div class="eyebrow">Restricted area</div><h2>Admin dashboard</h2>
        <p class="muted">Signed in as {{ session.get('admin_user','admin') }}. Only publish information you can substantiate.</p>
        <div class="grid">
        <div class="card col-6"><h3>{{ rows|length }}</h3><p class="muted">Total alert entries</p></div>
        <div class="card col-6"><h3>{{ rows|selectattr('is_demo','equalto',0)|list|length }}</h3><p class="muted">Submitted entries (not independently verified)</p></div></div>
        <h3>{{ 'Edit alert' if editing else 'Create alert' }}</h3>
        <form method="post" action="{{ url_for('save_alert') }}">{{ csrf|safe }}
        <input type="hidden" name="id" value="{{ editing['id'] if editing else '' }}">
        <div class="form-row"><div><label>Title</label><input name="title" maxlength="120" required value="{{ editing['title'] if editing else '' }}"></div>
        <div><label>Location / area</label><input name="location" maxlength="120" required value="{{ editing['location'] if editing else '' }}"></div>
        <div><label>Severity</label><select name="severity">{% for s in ['Low','Medium','High'] %}<option {{ 'selected' if editing and editing['severity']==s else '' }}>{{ s }}</option>{% endfor %}</select></div>
        <div><label>Source / verification note</label><input name="source" maxlength="160" required value="{{ editing['source'] if editing else 'Administrator submitted; verify externally' }}"></div></div>
        <label>Details</label><textarea name="details" rows="3" maxlength="1200" required>{{ editing['details'] if editing else '' }}</textarea>
        <div class="form-actions"><button>{{ 'Save changes' if editing else 'Add alert' }}</button>{% if editing %}<a class="btn secondary" href="{{ url_for('admin') }}">Cancel edit</a>{% endif %}</div></form>
        </div>
        <div class="card"><h3>Manage alerts</h3><div class="table-wrap"><table><tr><th>Alert</th><th>Severity</th><th>Source / status</th><th>Actions</th></tr>
        {% for a in rows %}<tr><td><b>{{ a['title'] }}</b><br><span class="small">{{ a['location'] }}</span></td><td>{{ a['severity'] }}</td><td>{{ a['source'] }}<br><span class="pill">{{ 'DEMO' if a['is_demo'] else 'USER SUBMITTED' }}</span></td><td><a href="{{ url_for('admin', edit=a['id']) }}">Edit</a>
        <form method="post" action="{{ url_for('delete_alert', alert_id=a['id']) }}" style="display:inline" onsubmit="return confirm('Delete this alert?')">{{ csrf|safe }}<button class="danger" style="padding:6px 8px">Delete</button></form></td></tr>{% endfor %}</table></div>
        <form method="post" action="{{ url_for('logout') }}">{{ csrf|safe }}<div class="form-actions"><button class="secondary">Sign out</button></div></form></div>
        """
        edit_id = request.args.get("edit", type=int)
        editing = None
        if edit_id:
            with db_connect() as con:
                editing = con.execute("SELECT * FROM alerts WHERE id=?", (edit_id,)).fetchone()
            if not editing:
                flash("Alert not found.", "error")
        return render_page("Admin Dashboard", body, rows=rows, editing=editing, csrf=csrf_field())
    body = r"""
    <div class="card" style="max-width:540px;margin:25px auto"><div class="eyebrow">Administrator access</div><h2>Sign in</h2>
    <p class="muted">Use the local demo credentials, or configure your own environment variables before deployment.</p>
    <form method="post">{{ csrf|safe }}<label>Username</label><input name="username" autocomplete="username" required>
    <label>Password</label><input type="password" name="password" autocomplete="current-password" required>
    <div class="form-actions"><button>Sign in</button></div></form>
    <div class="notice">Local demo only: username <b>admin</b>, password <b>SafeTrip@123</b>. Change these before any public deployment.</div></div>
    """
    return render_page("Admin Login", body, csrf=csrf_field())

@app.route("/admin/save", methods=["POST"])
@admin_required
def save_alert():
    title = request.form.get("title", "").strip()
    location = request.form.get("location", "").strip()
    severity = request.form.get("severity", "Low")
    details = request.form.get("details", "").strip()
    source = request.form.get("source", "").strip()
    alert_id = request.form.get("id", "").strip()
    if not title or not location or not details or not source or severity not in {"Low", "Medium", "High"}:
        flash("Please complete every field with valid values.", "error")
        return redirect(url_for("admin"))
    if len(title) > 120 or len(location) > 120 or len(details) > 1200 or len(source) > 160:
        flash("One or more fields are too long.", "error")
        return redirect(url_for("admin"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with db_connect() as con:
        if alert_id:
            con.execute("""UPDATE alerts SET title=?,location=?,severity=?,details=?,source=?,created_at=?,is_demo=0 WHERE id=?""",
                        (title, location, severity, details, source, now, int(alert_id)))
            flash("Alert updated. Its information has not been independently verified.", "success")
        else:
            con.execute("""INSERT INTO alerts(title,location,severity,details,source,created_at,is_demo)
                        VALUES(?,?,?,?,?,?,0)""", (title, location, severity, details, source, now))
            flash("Alert added. It is marked as user submitted, not independently verified.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/delete/<int:alert_id>", methods=["POST"])
@admin_required
def delete_alert(alert_id):
    with db_connect() as con:
        con.execute("DELETE FROM alerts WHERE id=?", (alert_id,))
    flash("Alert deleted.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/logout", methods=["POST"])
@admin_required
def logout():
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("admin"))

@app.errorhandler(404)
def not_found(_error):
    return render_page("Page not found", """
    <div class="card"><h2>Page not found</h2><p>The requested page does not exist.</p><a class="btn" href="/">Return home</a></div>
    """), 404

@app.errorhandler(500)
def internal_error(_error):
    app.logger.exception("Unexpected application error")
    return render_page("Temporary error", """
    <div class="card"><h2>Something went wrong</h2><p>The page could not be loaded. Return to the home page and try again.</p><a class="btn" href="/">Home</a><p class="small">For debugging, review the terminal where app.py is running.</p></div>
    """), 500

if __name__ == "__main__":
    init_db()
    print("=" * 58)
    print("SafeTrip is running: http://127.0.0.1:5000")
    print("Demo admin: admin / SafeTrip@123")
    print("Press Ctrl+C to stop the server.")
    print("=" * 58)
    app.run(host="127.0.0.1", port=5000, debug=False)
