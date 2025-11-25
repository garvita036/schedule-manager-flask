# Timetable Manager (Flask + SQLite)

Simple single-file Flask web app to create/edit/delete timetable entries and export them as CSV.

## Features
- Add timetable entries (title, day, start/end, location, notes)
- Edit & delete entries
- Export all entries to CSV
- Single-file app, uses built-in SQLite (no DB setup)

## Run locally
1. Create a virtual environment (recommended)
   python3 -m venv venv
   source venv/bin/activate        # Linux/macOS
   venv\Scripts\activate           # Windows

2. Install requirements
   pip install -r requirements.txt

3. Run
   python app.py

4. Open http://127.0.0.1:5000 in your browser.

## Make it GitHub-ready
- Add `README.md` (this text)
- Add `LICENSE` (MIT is common)
- Push to GitHub:
  git init
  git add .
  git commit -m "Initial commit - timetable manager"
  git branch -M main
  git remote add origin https://github.com/<yourusername>/<repo>.git
  git push -u origin main
