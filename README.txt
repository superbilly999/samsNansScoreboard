Sam's Nan's Game Scoreboard

Overview
- Flask + HTMX scoreboard for 13 rounds (Ace through King)
- SQLite by default (scoreboard.db in project root)
- DATABASE_URL supported for Postgres

Local setup
1) Create a virtual environment
   python3 -m venv .venv
   source .venv/bin/activate
2) Install dependencies
   pip install -r requirements.txt
3) Set environment variables
   export SECRET_KEY="change-me"
   export FLASK_APP=app.py
   # optional: export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
4) Run migrations
   # First time only (if you do NOT already have the migrations folder):
   flask db init
   flask db migrate -m "init"
   flask db upgrade

   # If migrations already exist (this repo includes them):
   flask db upgrade
5) Start the server
   flask run

Open http://127.0.0.1:5000

Render deployment notes
- Build command: pip install -r requirements.txt
- Start command: gunicorn app:app
- Set environment variables in Render:
  - SECRET_KEY (required)
  - DATABASE_URL (recommended for Postgres)
- Run migrations on deploy (Render Shell or pre-deploy step):
  flask db upgrade

SQLite on Render
- SQLite is file-based. To persist data on Render, attach a Persistent Disk and point
  to a path on that disk.
- For reliable production persistence, use Render Postgres and set DATABASE_URL.

Database URL note
- If DATABASE_URL begins with postgres://, the app rewrites it to postgresql://
  for SQLAlchemy compatibility.
