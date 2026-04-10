"""Flask web app for the pull-up 1RM calculator."""

import json
from datetime import date
from pathlib import Path

import numpy as np
import plotly
import plotly.graph_objects as go
from flask import Flask, redirect, render_template, request, url_for
from plotly.subplots import make_subplots

from calculator import compute_1rm, compute_1rm_grid, compute_unweighted_reps

app = Flask(__name__)

CONTOUR_LEVELS = [10, 25, 40, 55, 65]
TIMELINE_FILE = Path(__file__).parent / "data" / "timeline.json"


# ---------------------------------------------------------------------------
# Timeline data helpers
# ---------------------------------------------------------------------------

def _load_timeline() -> list[dict]:
    if TIMELINE_FILE.exists():
        return json.loads(TIMELINE_FILE.read_text())
    return []


def _save_timeline(entries: list[dict]) -> None:
    TIMELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    TIMELINE_FILE.write_text(json.dumps(entries, indent=2))


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


# ---------------------------------------------------------------------------
# Timeline chart builder
# ---------------------------------------------------------------------------

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

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=("Estimated 1RM (kg) over time", "Estimated unweighted reps over time"),
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

    fig.update_layout(
        height=600,
        showlegend=False,
        margin=dict(t=40, b=40),
    )
    fig.update_yaxes(title_text="1RM (kg)", row=1, col=1)
    fig.update_yaxes(title_text="Reps (bodyweight)", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    default_bw = 64.0
    bodyweight = default_bw
    plot_json = build_heatmap(default_bw)

    if request.method == "POST":
        try:
            bodyweight = float(request.form.get("bodyweight", ""))
            plot_json = build_heatmap(bodyweight)
        except (ValueError, TypeError):
            bodyweight = default_bw
            plot_json = build_heatmap(default_bw)

    return render_template(
        "index.html", tab="calculator",
        bodyweight=bodyweight, plot_json=plot_json,
    )


@app.route("/timeline", methods=["GET", "POST"])
def timeline():
    entries = _load_timeline()
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
                entries.append(entry)
                _save_timeline(entries)
                message = "Entry added."
            except (ValueError, KeyError):
                message = "Invalid input — please fill all fields."

        elif action == "delete":
            try:
                idx = int(request.form["index"])
                entries.pop(idx)
                _save_timeline(entries)
                message = "Entry deleted."
            except (ValueError, IndexError):
                pass

    timeline_json = build_timeline_charts(entries)

    return render_template(
        "index.html", tab="timeline",
        entries=entries, timeline_json=timeline_json,
        message=message, today=date.today().isoformat(),
    )


if __name__ == "__main__":
    app.run(debug=True, port=5050)
