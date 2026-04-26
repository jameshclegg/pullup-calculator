"""Chart-building helpers for the pull-up 1RM calculator."""

import json
from datetime import date, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from calculator import compute_1rm, compute_1rm_grid, compute_unweighted_reps

CONTOUR_LEVELS = [10, 25, 40, 55, 65]
LINE_CHART_WEIGHTS = [9, 13, 18, 22, 27]
WEIGHT_COLORS = ["#3498db", "#2ecc71", "#f39c12", "#e74c3c", "#9b59b6"]


def _extract_contour_paths(
    x: np.ndarray, y: np.ndarray, z: np.ndarray, levels: list[float]
) -> list[tuple[float, np.ndarray, np.ndarray]]:
    """Use matplotlib to compute contour paths at exact levels."""
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


def build_line_chart(bodyweight: float) -> str:
    """Build a line chart of 1RM vs reps for specific added weights."""
    reps = np.arange(1, 26)

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


def build_marginal_reps_chart(bodyweight: float) -> str:
    """Show the gain in estimated max unweighted reps from doing +1 rep at each added weight."""
    added_weights = list(range(0, 31))
    rep_levels = [(8, "#9b59b6"), (11, "#3498db")]

    fig = go.Figure()
    for base_reps, color in rep_levels:
        delta_reps = []
        for w in added_weights:
            rm_base = compute_1rm(bodyweight, w, base_reps)
            rm_plus1 = compute_1rm(bodyweight, w, base_reps + 1)
            uw_base = compute_unweighted_reps(bodyweight, rm_base)
            uw_plus1 = compute_unweighted_reps(bodyweight, rm_plus1)
            delta_reps.append(round(uw_plus1 - uw_base, 2))

        fig.add_trace(
            go.Scatter(
                x=added_weights, y=delta_reps, mode="lines+markers",
                name=f"{base_reps} → {base_reps + 1} reps",
                line=dict(color=color, width=2),
                marker=dict(size=6),
                hovertemplate=(
                    "Added weight: %{x} kg<br>"
                    f"Going from {base_reps} → {base_reps + 1} reps<br>"
                    "Unweighted rep gain: +%{y:.2f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(
            text=f"Gain in Max Unweighted Reps from +1 Rep  (BW = {bodyweight} kg)",
            x=0.5,
        ),
        xaxis=dict(title="Added Weight (kg)", dtick=2),
        yaxis=dict(title="Extra Unweighted Reps"),
        height=420,
        margin=dict(t=60, b=60),
        legend=dict(title="Rep Transition"),
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
        shared_xaxes=False,
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

    # Linear trendline projected 6 months into the future
    date_objs = [date.fromisoformat(d) for d in dates]
    day_nums = np.array([(d - date_objs[0]).days for d in date_objs], dtype=float)
    coeffs = np.polyfit(day_nums, unweighted, 1)
    future_end = day_nums[-1] + 183  # ~6 months
    trend_days = np.array([day_nums[0], future_end])
    trend_vals = np.polyval(coeffs, trend_days)
    trend_dates = [(date_objs[0] + timedelta(days=int(d))).isoformat() for d in trend_days]
    fig.add_trace(
        go.Scatter(
            x=trend_dates, y=[round(v, 1) for v in trend_vals],
            mode="lines", name="Trend (6mo projection)",
            line=dict(color="black", width=1.5, dash="dash"),
            hovertemplate="Date: %{x}<br>Projected: %{y:.1f} reps<extra></extra>",
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
    for i in range(1, len(added_raw)):
        if added_raw[i] > added_raw[i - 1]:
            jump_kg = added_raw[i] - added_raw[i - 1]
            # Find when the previous weight level was first adopted
            prev_weight = added_raw[i - 1]
            first_at_prev = i - 1
            while first_at_prev > 0 and added_raw[first_at_prev - 1] == prev_weight:
                first_at_prev -= 1
            d_start = date.fromisoformat(dates[first_at_prev])
            d_curr = date.fromisoformat(dates[i])
            days_at_prev = (d_curr - d_start).days
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
