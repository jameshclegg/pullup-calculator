"""Flask web app for the pull-up 1RM calculator."""

import logging
import os
from datetime import date
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash

from charts import build_heatmap, build_line_chart, build_marginal_reps_chart, build_timeline_charts
from db import add_timeline_entry, delete_timeline_entry, init_db, load_timeline

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32).hex()
csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

PASSWORD_HASH = os.environ.get("TIMELINE_PASSWORD", "")

if PASSWORD_HASH and not PASSWORD_HASH.startswith(("scrypt:", "pbkdf2:", "$2b$")):
    logging.warning(
        "TIMELINE_PASSWORD does not look like a Werkzeug hash — "
        "login will not work. Generate one with: python -c "
        "\"from werkzeug.security import generate_password_hash; "
        "print(generate_password_hash('your-password'))\""
    )

# Initialise the database table on startup
with app.app_context():
    init_db()


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def login_required(f):
    """Require login for a route (only if PASSWORD_HASH is set)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if PASSWORD_HASH and not session.get("authenticated"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    default_bw = 64.0
    bodyweight = default_bw
    if request.method == "POST":
        try:
            bodyweight = float(request.form.get("bodyweight", ""))
        except (ValueError, TypeError):
            bodyweight = default_bw
    plot_json = build_heatmap(bodyweight)
    line_json = build_line_chart(bodyweight)
    marginal_json = build_marginal_reps_chart(bodyweight)

    return render_template(
        "index.html", tab="calculator",
        bodyweight=bodyweight, plot_json=plot_json, line_json=line_json,
        marginal_json=marginal_json,
    )


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10/minute", methods=["POST"])
def login():
    error = None
    if request.method == "POST":
        if check_password_hash(PASSWORD_HASH, request.form.get("password", "")):
            session["authenticated"] = True
            next_url = request.args.get("next", "")
            if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("timeline")
            return redirect(next_url)
        error = "Incorrect password."
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("authenticated", None)
    return redirect(url_for("index"))


@app.route("/timeline", methods=["GET", "POST"])
@login_required
def timeline():
    entries = load_timeline()
    message = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            try:
                parsed_date = date.fromisoformat(request.form["date"])
                bodyweight = float(request.form["bodyweight"])
                added_weight = float(request.form["added_weight"])
                reps = int(request.form["reps"])
                if not (55 <= bodyweight <= 75):
                    message = "Bodyweight must be between 55 and 75 kg."
                elif not (0 <= added_weight <= 65):
                    message = "Added weight must be between 0 and 65 kg."
                elif not (1 <= reps <= 40):
                    message = "Reps must be between 1 and 40."
                elif parsed_date > date.today():
                    message = "Date cannot be in the future."
                else:
                    entry = {
                        "date": parsed_date.isoformat(),
                        "bodyweight": bodyweight,
                        "added_weight": added_weight,
                        "reps": reps,
                    }
                    add_timeline_entry(entry)
                    message = "Entry added."
            except (ValueError, KeyError):
                message = "Invalid input — please enter valid values for all fields."

        elif action == "delete":
            try:
                identifier = int(request.form["index"])
                delete_timeline_entry(identifier)
                message = "Entry deleted."
            except (ValueError, IndexError):
                pass

        entries = load_timeline()

    timeline_json = build_timeline_charts(entries)

    return render_template(
        "index.html", tab="timeline",
        entries=entries, timeline_json=timeline_json,
        message=message, today=date.today().isoformat(),
    )


if __name__ == "__main__":
    app.run(debug=True, port=5050)
