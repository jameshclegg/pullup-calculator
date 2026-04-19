"""Flask web app for the pull-up 1RM calculator."""

import json
import os
from datetime import date
from functools import wraps

import numpy as np
import plotly
import plotly.graph_objects as go
from flask import Flask, redirect, render_template, request, session, url_for
from plotly.subplots import make_subplots

from calculator import compute_1rm, compute_1rm_grid, compute_unweighted_reps
from db import add_timeline_entry, delete_timeline_entry, init_db, load_timeline

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# Password for the timeline page (set via environment variable)
TIMELINE_PASSWORD = os.environ.get("TIMELINE_PASSWORD", "")

CONTOUR_LEVELS = [10, 25, 40, 55, 65]

# Initialise the database table on startup
with app.app_context():
    init_db()


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def login_required(f):
    """Require login for a route (only if TIMELINE_PASSWORD is set)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if TIMELINE_PASSWORD and not session.get("authenticated"):
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Heatmap builder
# ---------------------------------------------------------------------------

def _extract_contour_paths(
    x: np.ndarray, y: np.ndarray, z: np.ndarray, levels: list[float]
) -> list[tuple[float, np.ndarray, np.ndarray]]:
    """Use matplotlib to compute contour paths at exact levels."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_mpl, ax = plt.subplots()
    cs = ax.contour(x, y, z, levels=levels)
    paths = []
    for level, segs in zip(cs.levels, cs.allsegs):
        for seg in segs:
            if len(seg) > 1:
                paths.append((float(level), seg[:, 0], seg[:, 1]))
    plt.close(fig_mpl)
    return paths


def build_heatmap(bodyweight: float) -> str:
    """Build a Plotly heatmap with contour line overlays."""
    added_weights, reps, rm_grid = compute_1rm_grid(bodyweight)

    fig = go.Figure(
        data=go.Heatmap(
            z=rm_grid,
            x=added_weights,
            y=reps,
            colorscale="YlOrRd",
            colorbar=dict(title="1RM (kg)"),
            hovertemplate=(
                "Added weight: %{x} kg<br>"
                "Reps: %{y}<br>"
                "1RM: %{z:.1f} kg<extra></extra>"
            ),
        )
    )

    paths = _extract_contour_paths(added_weights, reps, rm_grid, CONTOUR_LEVELS)
    legend_shown: set[float] = set()
    for level, xs, ys in paths:
        show_legend = level not in legend_shown
        legend_shown.add(level)
        fig.add_trace(
            go.Scatter(
                x=xs, y=ys, mode="lines",
                line=dict(color="white", width=2),
                name=f"{int(level)} kg",
                legendgroup=f"{level}",
                showlegend=show_legend,
                hoverinfo="skip",
            )
        )
        mid = len(xs) // 2
        fig.add_annotation(
            x=float(xs[mid]), y=float(ys[mid]),
            text=f"<b>{int(level)}</b>",
            showarrow=False,
            font=dict(size=13, color="white"),
            bgcolor="rgba(0,0,0,0.5)",
            borderpad=2,
        )

    fig.update_layout(
        title=dict(
            text=f"Estimated 1RM for Weighted Pull-Ups  (BW = {bodyweight} kg)",
            x=0.5,
        ),
        xaxis=dict(title="Added Weight (kg)", dtick=2),
        yaxis=dict(title="Repetitions", dtick=1),
        height=520,
        margin=dict(t=60, b=60),
        showlegend=False,
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


LINE_CHART_WEIGHTS = [9, 13, 18, 22, 27]
WEIGHT_COLORS = ["#3498db", "#2ecc71", "#f39c12", "#e74c3c", "#9b59b6"]


def build_line_chart(bodyweight: float) -> str:
    """Build a line chart of 1RM vs reps for specific added weights."""
    _, reps, _ = compute_1rm_grid(bodyweight)

    fig = go.Figure()
    for weight, color in zip(LINE_CHART_WEIGHTS, WEIGHT_COLORS):
        rm_values = [
            round(compute_1rm(bodyweight, weight, int(r)), 1) for r in reps
        ]
        fig.add_trace(
            go.Scatter(
                x=reps, y=rm_values, mode="lines+markers",
                name=f"+{weight} kg",
                line=dict(color=color, width=2),
                marker=dict(size=5),
                hovertemplate=(
                    f"+{weight} kg<br>"
                    "Reps: %{x}<br>"
                    "1RM: %{y:.1f} kg<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(
            text=f"1RM vs Reps at Selected Added Weights  (BW = {bodyweight} kg)",
            x=0.5,
        ),
        xaxis=dict(title="Repetitions", dtick=1),
        yaxis=dict(title="Estimated 1RM (kg)"),
        height=420,
        margin=dict(t=60, b=60),
        legend=dict(title="Added Weight"),
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def build_timeline_charts(entries: list[dict]) -> str | None:
    """Build a two-subplot timeline chart (1RM and unweighted reps vs date)."""
    if not entries:
        return None

    sorted_entries = sorted(entries, key=lambda e: e["date"])
    dates = [e["date"] for e in sorted_entries]
    rms = [
        round(compute_1rm(e["bodyweight"], e["added_weight"], e["reps"]), 1)
        for e in sorted_entries
    ]
    unweighted = [
        round(compute_unweighted_reps(e["bodyweight"], rm), 1)
        for rm, e in zip(rms, sorted_entries)
    ]

    reps_raw = [e["reps"] for e in sorted_entries]
    added_raw = [e["added_weight"] for e in sorted_entries]

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=(
            "Estimated 1RM (kg) over time",
            "Estimated unweighted reps over time",
            "Reps performed over time",
            "Added weight (kg) over time",
        ),
    )

    fig.add_trace(
        go.Scatter(
            x=dates, y=rms, mode="lines+markers",
            name="1RM",
            line=dict(color="#e74c3c", width=2),
            marker=dict(size=8),
            hovertemplate="Date: %{x}<br>1RM: %{y:.1f} kg<extra></extra>",
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=dates, y=unweighted, mode="lines+markers",
            name="Unweighted reps",
            line=dict(color="#3498db", width=2),
            marker=dict(size=8),
            hovertemplate="Date: %{x}<br>Est. reps: %{y:.1f}<extra></extra>",
        ),
        row=2, col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=dates, y=reps_raw, mode="lines+markers",
            name="Reps",
            line=dict(color="#2ecc71", width=2),
            marker=dict(size=8),
            hovertemplate="Date: %{x}<br>Reps: %{y}<extra></extra>",
        ),
        row=3, col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=dates, y=added_raw, mode="lines+markers",
            name="Added weight",
            line=dict(color="#f39c12", width=2),
            marker=dict(size=8),
            hovertemplate="Date: %{x}<br>Added: %{y} kg<extra></extra>",
        ),
        row=4, col=1,
    )

    # Annotate weight jumps on the added-weight chart
    from datetime import date as date_cls
    for i in range(1, len(added_raw)):
        if added_raw[i] > added_raw[i - 1]:
            jump_kg = added_raw[i] - added_raw[i - 1]
            d_prev = date_cls.fromisoformat(dates[i - 1])
            d_curr = date_cls.fromisoformat(dates[i])
            days_at_prev = (d_curr - d_prev).days
            fig.add_annotation(
                x=dates[i], y=added_raw[i],
                text=f"+{jump_kg:g}, {days_at_prev}d",
                showarrow=True, arrowhead=2, arrowsize=1, arrowcolor="#f39c12",
                ax=0, ay=-30,
                font=dict(size=11, color="#fff"),
                bgcolor="rgba(0,0,0,0.6)",
                borderpad=3, bordercolor="#f39c12", borderwidth=1,
                xref="x4", yref="y4",
            )

    fig.update_layout(
        height=1100,
        showlegend=False,
        margin=dict(t=40, b=40),
    )
    fig.update_yaxes(title_text="1RM (kg)", row=1, col=1)
    fig.update_yaxes(title_text="Reps (bodyweight)", row=2, col=1)
    fig.update_yaxes(title_text="Reps", row=3, col=1)
    fig.update_yaxes(title_text="Added weight (kg)", row=4, col=1)
    fig.update_xaxes(title_text="Date", row=4, col=1)

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    default_bw = 64.0
    bodyweight = default_bw
    plot_json = build_heatmap(default_bw)
    line_json = build_line_chart(default_bw)

    if request.method == "POST":
        try:
            bodyweight = float(request.form.get("bodyweight", ""))
            plot_json = build_heatmap(bodyweight)
            line_json = build_line_chart(bodyweight)
        except (ValueError, TypeError):
            bodyweight = default_bw
            plot_json = build_heatmap(default_bw)
            line_json = build_line_chart(default_bw)

    return render_template(
        "index.html", tab="calculator",
        bodyweight=bodyweight, plot_json=plot_json, line_json=line_json,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == TIMELINE_PASSWORD:
            session["authenticated"] = True
            return redirect(request.args.get("next", url_for("timeline")))
        error = "Incorrect password."
    return render_template("login.html", error=error)


@app.route("/logout")
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
                entry = {
                    "date": request.form["date"],
                    "bodyweight": float(request.form["bodyweight"]),
                    "added_weight": float(request.form["added_weight"]),
                    "reps": int(request.form["reps"]),
                }
                add_timeline_entry(entry)
                message = "Entry added."
            except (ValueError, KeyError):
                message = "Invalid input — please fill all fields."

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
