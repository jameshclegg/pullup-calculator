"""Flask web app for the pull-up 1RM calculator."""

import json

import numpy as np
import plotly
import plotly.graph_objects as go
from flask import Flask, render_template, request

from calculator import compute_1rm_grid

app = Flask(__name__)


CONTOUR_LEVELS = [10, 25, 40, 55, 65]


def _extract_contour_paths(
    x: np.ndarray, y: np.ndarray, z: np.ndarray, levels: list[float]
) -> list[tuple[float, np.ndarray, np.ndarray]]:
    """Use matplotlib to compute contour paths at exact levels.

    Returns a list of (level, xs, ys) tuples — one per path segment.
    """
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

    # Overlay contour lines at the requested levels
    paths = _extract_contour_paths(added_weights, reps, rm_grid, CONTOUR_LEVELS)
    legend_shown: set[float] = set()
    for level, xs, ys in paths:
        show_legend = level not in legend_shown
        legend_shown.add(level)
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(color="white", width=2),
                name=f"{int(level)} kg",
                legendgroup=f"{level}",
                showlegend=show_legend,
                hoverinfo="skip",
            )
        )
        # Add a label near the midpoint of each contour segment
        mid = len(xs) // 2
        fig.add_annotation(
            x=float(xs[mid]),
            y=float(ys[mid]),
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


@app.route("/", methods=["GET", "POST"])
def index():
    bodyweight = None
    plot_json = None

    if request.method == "POST":
        try:
            bodyweight = float(request.form.get("bodyweight", ""))
            plot_json = build_heatmap(bodyweight)
        except (ValueError, TypeError):
            bodyweight = None

    return render_template("index.html", bodyweight=bodyweight, plot_json=plot_json)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
