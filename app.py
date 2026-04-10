"""Flask web app for the pull-up 1RM calculator."""

import json

import numpy as np
import plotly
import plotly.graph_objects as go
from flask import Flask, render_template, request

from calculator import compute_1rm_grid

app = Flask(__name__)


def build_heatmap(bodyweight: float) -> str:
    """Build a Plotly heatmap and return its JSON representation."""
    added_weights, reps, rm_grid = compute_1rm_grid(bodyweight)

    fig = go.Figure(
        data=go.Heatmap(
            z=rm_grid,
            x=added_weights,
            y=reps,
            colorscale="YlOrRd",
            text=rm_grid,
            texttemplate="%{text}",
            textfont={"size": 11},
            colorbar=dict(title="1RM (kg)"),
            hovertemplate=(
                "Added weight: %{x} kg<br>"
                "Reps: %{y}<br>"
                "1RM: %{z:.1f} kg<extra></extra>"
            ),
        )
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
