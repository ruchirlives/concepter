"""Tests for the FlowSvgExporter arrow generation."""

from helpers.flowSvgExporter import FlowSvgExporter


def make_basic_exporter():
    exporter = FlowSvgExporter()
    exporter.add_node("a", x=0, y=0, width=100, height=60)
    exporter.add_node("b", x=150, y=0, width=100, height=60)
    exporter.add_node("c", x=150, y=160, width=100, height=60)
    return exporter


def test_horizontal_arrow_has_no_gap():
    exporter = make_basic_exporter()
    path = exporter.get_arrow_path("a", "b")
    assert path == "M 100 30.0 L 150 30.0"


def test_horizontal_arrow_reversed_direction():
    exporter = make_basic_exporter()
    path = exporter.get_arrow_path("b", "a")
    assert path == "M 150 30.0 L 100 30.0"


def test_vertical_arrow_uses_top_and_bottom_edges():
    exporter = make_basic_exporter()
    path = exporter.get_arrow_path("b", "c")
    assert path == "M 200.0 60 L 200.0 160"
