"""Tests for charts.py chart-building functions."""

import json

from charts import (
    build_heatmap,
    build_line_chart,
    build_marginal_reps_chart,
    build_timeline_charts,
)

SAMPLE_ENTRIES = [
    {"date": "2024-01-01", "bodyweight": 64.0, "added_weight": 20.0, "reps": 5},
    {"date": "2024-02-01", "bodyweight": 64.0, "added_weight": 22.0, "reps": 5},
    {"date": "2024-03-01", "bodyweight": 65.0, "added_weight": 24.0, "reps": 6},
]


class TestBuildHeatmap:
    def test_returns_valid_json(self):
        result = build_heatmap(64)
        data = json.loads(result)
        assert "data" in data
        assert "layout" in data

    def test_title_contains_bodyweight(self):
        data = json.loads(build_heatmap(64))
        title_text = data["layout"]["title"]["text"]
        assert "64" in title_text


class TestBuildLineChart:
    def test_returns_valid_json(self):
        data = json.loads(build_line_chart(64))
        assert "data" in data
        assert "layout" in data


class TestBuildMarginalRepsChart:
    def test_returns_valid_json(self):
        data = json.loads(build_marginal_reps_chart(64))
        assert "data" in data
        assert "layout" in data


class TestBuildTimelineCharts:
    def test_empty_entries_returns_none(self):
        assert build_timeline_charts([]) is None

    def test_sample_entries_return_valid_json(self):
        result = build_timeline_charts(SAMPLE_ENTRIES)
        assert result is not None
        data = json.loads(result)
        assert "data" in data
        assert "layout" in data
