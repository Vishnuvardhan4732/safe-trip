# SafeTrip — Tourist Safety, Health & Emergency Assistance Platform

SafeTrip is a Flask + SQLite hackathon prototype that brings travel-safety guidance, destination weather lookup, emergency information, a travel checklist, a Leaflet map, and administrator-managed safety alerts into one web app.

## Features

- Responsive dashboard and navigation
- Destination lookup with live current weather from Open-Meteo when internet access is available
- Clear messaging when live weather cannot be loaded
- Interactive Leaflet / OpenStreetMap map with **clearly labelled illustrative demo markers**
- Health and safety guidance in English, Tamil, Telugu, and Hindi
- India emergency number 112 information
- Interactive checklist saved in the browser on that device
- SQLite-backed alerts with add/edit/resolve/delete administrator tools
- Password hashes using PBKDF2-HMAC-SHA256 and session-based admin access

## Important limitations

- The map markers are demonstration examples, not a verified directory of hospitals, shelters, or hazard reports. Do not rely on them for navigation or emergency response.
- Weather lookup uses Open-Meteo's public geocoding and forecast endpoints. It may fail without internet access.
- This prototype does not automatically call emergency services, dispatch an ambulance, or send alerts to authorities.
- It is not a replacement for official government warnings or professional medical advice.

## Run locally (Windows / IDLE / VS Code)

1. Install Python 3.10 or newer.
2. Open Command Prompt in the SafeTrip folder.
3. Install packages:

   ```bash
   py -m pip install -r requirements.txt
   ```

4. Optional but recommended: set a custom admin password and secret key before first run.

   **Command Prompt:**
   ```bat
   set SAFETRIP_ADMIN_USER=admin
   set SAFETRIP_ADMIN_PASSWORD=Choose-A-Strong-Password
   set SAFETRIP_SECRET_KEY=replace-with-a-long-random-secret
   ```

   The initial demo credentials, if no environment variables are set before the database is first created, are:
   - Username: `admin`
   - Password: `SafeTrip@123`

   Change these before showing the app publicly. The initial admin record is created only when the database has no admin record.

5. Run:

   ```bash
   py app.py
   ```

6. Open `http://127.0.0.1:5000` in your browser.

If using IDLE, open `app.py` and press **F5**. Keep the IDLE shell running while using the site.

## Public deployment (Render)

1. Push this folder to a GitHub repository.
2. Create a new **Web Service** on Render and connect the repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variables in the hosting dashboard:
   - `SAFETRIP_SECRET_KEY`: long random secret
   - `SAFETRIP_ADMIN_USER`: your admin username
   - `SAFETRIP_ADMIN_PASSWORD`: strong admin password
6. Ensure SQLite persistence is appropriate for your deployment. On ephemeral hosting filesystems, the database may reset on redeploy/restart. For a durable public service, use a persistent disk or managed database and configure backups.

## Project structure

```text
SafeTrip/
├── app.py
├── requirements.txt
├── README.md
├── safetrip.db          # created automatically at first run
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── destination.html
│   ├── map.html
│   ├── health.html
│   ├── emergency.html
│   ├── checklist.html
│   ├── about.html
│   ├── admin_login.html
│   ├── admin_dashboard.html
│   ├── alert_form.html
│   └── error.html
└── static/
    ├── style.css
    └── app.js
```

## Suggested 2-minute demo

1. Open the home dashboard and explain the five core safety tools.
2. Search a destination on the Destination page to show current weather if the API is reachable.
3. Open the Safety Map and point out the demo marker disclosure.
4. Mark checklist items as complete.
5. Sign in to the administrator panel, add an example alert, edit it, then resolve it.
6. Explain that a real deployment would connect to official warning feeds and a verified facility directory.
