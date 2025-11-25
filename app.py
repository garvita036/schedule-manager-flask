from flask import Flask, request, redirect, url_for, render_template_string, send_file, flash
import sqlite3
from datetime import datetime
import csv
import io
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "timetable.db")

app = Flask(__name__)
app.secret_key = "replace-this-with-a-secure-random-key"

# -- DB helpers
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

init_db()

# -- HTML template (single-file using render_template_string)
TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Timetable Manager</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    body { font-family: Inter, system-ui, Arial; max-width:900px; margin:30px auto; padding:10px; }
    header { display:flex; justify-content:space-between; align-items:center; }
    form { margin: 18px 0; display:flex; gap:8px; flex-wrap:wrap; }
    input, select, textarea { padding:8px; border:1px solid #ddd; border-radius:6px; }
    button { padding:8px 12px; border-radius:6px; cursor:pointer; }
    table { width:100%; border-collapse:collapse; margin-top:14px; }
    th, td { padding:8px; border-bottom:1px solid #eee; text-align:left; }
    .small { font-size:0.9rem; color:#555; }
    .actions { display:flex; gap:6px; }
    .flash { color: #064e3b; background:#ecfdf5; padding:8px; border-radius:6px; margin:10px 0; }
  </style>
</head>
<body>
  <header>
    <h1>📚 Timetable Manager</h1>
    <div>
      <a href="{{ url_for('export_csv') }}" title="Export CSV">Export CSV</a> |
      <a href="{{ url_for('index') }}">Refresh</a>
    </div>
  </header>

  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <div class="flash">{{ messages[0] }}</div>
    {% endif %}
  {% endwith %}

  <section>
    <h3>Add / Edit Entry</h3>
    <form method="post" action="{{ form_action }}">
      <input type="hidden" name="id" value="{{ entry.id if entry else '' }}">
      <input required name="title" placeholder="Title (e.g., Math)" value="{{ entry.title if entry else '' }}">
      <select name="day" required>
        {% for d in ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'] %}
          <option value="{{d}}" {% if entry and entry.day==d %}selected{% endif %}>{{d}}</option>
        {% endfor %}
      </select>
      <input required type="time" name="start_time" value="{{ entry.start_time if entry else '' }}">
      <input required type="time" name="end_time" value="{{ entry.end_time if entry else '' }}">
      <input name="location" placeholder="Location (optional)" value="{{ entry.location if entry else '' }}">
      <input name="notes" placeholder="Notes (optional)" value="{{ entry.notes if entry else '' }}">
      <button type="submit">{{ 'Update' if entry else 'Add' }}</button>
      {% if entry %}
        <a href="{{ url_for('index') }}"><button type="button">Cancel</button></a>
      {% endif %}
    </form>
  </section>

  <section>
    <h3>Timetable</h3>
    <div class="small">Ordered by day & start time</div>
    {% if rows %}
      <table>
        <thead><tr><th>Title</th><th>Day</th><th>Start</th><th>End</th><th>Location</th><th>Notes</th><th>Actions</th></tr></thead>
        <tbody>
        {% for r in rows %}
          <tr>
            <td>{{ r.title }}</td>
            <td>{{ r.day }}</td>
            <td>{{ r.start_time }}</td>
            <td>{{ r.end_time }}</td>
            <td>{{ r.location or '' }}</td>
            <td>{{ r.notes or '' }}</td>
            <td class="actions">
              <a href="{{ url_for('edit', entry_id=r.id) }}">Edit</a>
              <a href="{{ url_for('delete', entry_id=r.id) }}" onclick="return confirm('Delete this entry?')">Delete</a>
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    {% else %}
      <p class="small">No entries yet — add one above.</p>
    {% endif %}
  </section>

  <footer style="margin-top:20px" class="small">
    Built with Flask • Created: {{ now }}
  </footer>
</body>
</html>
"""

# -- Routes
@app.route("/", methods=["GET", "POST"])
def index():
    # POST => create
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        day = request.form.get("day", "").strip()
        start_time = request.form.get("start_time", "").strip()
        end_time = request.form.get("end_time", "").strip()
        location = request.form.get("location", "").strip()
        notes = request.form.get("notes", "").strip()

        if not title or not day or not start_time or not end_time:
            flash("Please fill required fields.")
            return redirect(url_for("index"))

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO entries (title, day, start_time, end_time, location, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, day, start_time, end_time, location, notes, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()
        flash("Entry added.")
        return redirect(url_for("index"))

    # GET => list
    conn = get_conn()
    cur = conn.cursor()
    # order by day of week manually: use CASE to define order
    cur.execute(
        """
        SELECT * FROM entries
        ORDER BY
          CASE day
            WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
            WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7
            ELSE 8 END,
          start_time
        """
    )
    rows = cur.fetchall()
    conn.close()

    return render_template_string(TEMPLATE, rows=rows, entry=None, form_action=url_for("index"), now=datetime.utcnow().date())

@app.route("/edit/<int:entry_id>", methods=["GET", "POST"])
def edit(entry_id):
    conn = get_conn()
    cur = conn.cursor()
    if request.method == "POST":
        # update
        title = request.form.get("title", "").strip()
        day = request.form.get("day", "").strip()
        start_time = request.form.get("start_time", "").strip()
        end_time = request.form.get("end_time", "").strip()
        location = request.form.get("location", "").strip()
        notes = request.form.get("notes", "").strip()

        if not title or not day or not start_time or not end_time:
            flash("Please fill required fields.")
            return redirect(url_for("edit", entry_id=entry_id))

        cur.execute(
            "UPDATE entries SET title=?, day=?, start_time=?, end_time=?, location=?, notes=? WHERE id=?",
            (title, day, start_time, end_time, location, notes, entry_id),
        )
        conn.commit()
        conn.close()
        flash("Entry updated.")
        return redirect(url_for("index"))

    cur.execute("SELECT * FROM entries WHERE id=?", (entry_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        flash("Entry not found.")
        return redirect(url_for("index"))

    return render_template_string(TEMPLATE, rows=[], entry=row, form_action=url_for("edit", entry_id=entry_id), now=datetime.utcnow().date())

@app.route("/delete/<int:entry_id>")
def delete(entry_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM entries WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()
    flash("Entry deleted.")
    return redirect(url_for("index"))

@app.route("/export")
def export_csv():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM entries ORDER BY day, start_time")
    rows = cur.fetchall()
    conn.close()

    # create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "title", "day", "start_time", "end_time", "location", "notes", "created_at"])
    for r in rows:
        writer.writerow([r["id"], r["title"], r["day"], r["start_time"], r["end_time"], r["location"], r["notes"], r["created_at"]])

    output.seek(0)
    mem = io.BytesIO()
    mem.write(output.getvalue().encode("utf-8"))
    mem.seek(0)
    filename = f"timetable_export_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
    return send_file(mem, as_attachment=True, download_name=filename, mimetype="text/csv")

if __name__ == "__main__":
    # Use port 5000 by default. In production, use gunicorn/uvicorn.
    app.run(debug=True, host="0.0.0.0", port=5000)
