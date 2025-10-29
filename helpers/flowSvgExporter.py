"""Utilities for exporting simple flow diagrams as SVG.

This module provides a tiny, dependency free helper for generating
rectangular nodes linked with straight arrows.  The goal is to produce
compact connector paths without the extra spacing that the previous
implementation introduced.  The exporter keeps track of nodes and their
positions and can produce SVG snippets describing the connections
between them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(slots=True)
class _Node:
    """Simple rectangle used by :class:`FlowSvgExporter`.

    Attributes
    ----------
    x, y:
        Top left coordinate of the rectangle.
    width, height:
        Dimensions of the rectangle.
    label:
        Optional text label that can be rendered alongside the node.
    """

    x: float
    y: float
    width: float
    height: float
    label: Optional[str] = None

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def cx(self) -> float:
        return self.x + self.width / 2

    @property
    def cy(self) -> float:
        return self.y + self.height / 2


@dataclass(slots=True)
class _Edge:
    """Connection between two nodes."""

    source: str
    target: str
    path: str
    label: Optional[str] = None


class FlowSvgExporter:
    """Exporter that generates basic SVG flows without extra spacing.

    The exporter focuses on calculating arrow paths that meet the edge of
    rectangles directly so the connectors do not have the unnecessary
    padding/gaps that existed before.  Consumers can query individual
    paths or render the full SVG.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, _Node] = {}
        self._edges: List[_Edge] = []

    # ------------------------------------------------------------------
    # Node helpers
    # ------------------------------------------------------------------
    def add_node(
        self,
        node_id: str,
        *,
        x: float,
        y: float,
        width: float,
        height: float,
        label: Optional[str] = None,
    ) -> None:
        """Register a node in the diagram."""

        self._nodes[node_id] = _Node(x=x, y=y, width=width, height=height, label=label)

    def get_node(self, node_id: str) -> _Node:
        try:
            return self._nodes[node_id]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise KeyError(f"Unknown node '{node_id}'") from exc

    # ------------------------------------------------------------------
    # Edge helpers
    # ------------------------------------------------------------------
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        *,
        label: Optional[str] = None,
    ) -> str:
        """Create an edge and return the SVG path string.

        The computed arrow path connects the closest sides of the two
        rectangles without applying any artificial padding.
        """

        path = self.get_arrow_path(source_id, target_id)
        self._edges.append(_Edge(source=source_id, target=target_id, path=path, label=label))
        return path

    def get_arrow_path(self, source_id: str, target_id: str) -> str:
        """Return the SVG path for an arrow between two nodes."""

        start, end = self._edge_points(source_id, target_id)
        return f"M {start[0]} {start[1]} L {end[0]} {end[1]}"

    def _edge_points(self, source_id: str, target_id: str) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Calculate connector points on the edges of two nodes.

        The method picks the most suitable sides based on the relative
        position of the nodes.  Horizontal links attach to the left/right
        sides, vertical links to the top/bottom sides, ensuring the arrow
        meets the rectangle edges directly.
        """

        source = self.get_node(source_id)
        target = self.get_node(target_id)

        dx = target.cx - source.cx
        dy = target.cy - source.cy

        if abs(dx) >= abs(dy):
            # Prefer a horizontal connector
            if dx >= 0:
                start = (source.right, source.cy)
                end = (target.left, target.cy)
            else:
                start = (source.left, source.cy)
                end = (target.right, target.cy)
        else:
            # Prefer a vertical connector
            if dy >= 0:
                start = (source.cx, source.bottom)
                end = (target.cx, target.top)
            else:
                start = (source.cx, source.top)
                end = (target.cx, target.bottom)

        return start, end

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def iter_nodes(self) -> Iterable[_Node]:
        return self._nodes.values()

    def iter_edges(self) -> Iterable[_Edge]:
        return self._edges

    def to_svg(
        self,
        *,
        stroke: str = "#1f2933",
        fill: str = "#ffffff",
        text_color: str = "#1f2933",
        font_size: int = 14,
        margin: float = 16.0,
    ) -> str:
        """Render the current flow diagram to an SVG string."""

        if not self._nodes:
            return "<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>"

        max_right = max(node.right for node in self._nodes.values())
        max_bottom = max(node.bottom for node in self._nodes.values())
        min_left = min(node.left for node in self._nodes.values())
        min_top = min(node.top for node in self._nodes.values())

        width = max_right - min_left + margin * 2
        height = max_bottom - min_top + margin * 2

        offset_x = margin - min_left
        offset_y = margin - min_top

        svg_parts: List[str] = [
            f"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\">",
            "  <defs>"
            "<marker id=\"arrowhead\" markerWidth=\"10\" markerHeight=\"7\" refX=\"10\" refY=\"3.5\" orient=\"auto\">"
            f"<polygon points=\"0 0, 10 3.5, 0 7\" fill=\"{stroke}\" />"
            "</marker>"
            "</defs>",
        ]

        # Draw edges first so they appear behind nodes
        for edge in self._edges:
            path = edge.path
            svg_parts.append(
                f"  <path d=\"{path}\" stroke=\"{stroke}\" fill=\"none\" stroke-width=\"2\" marker-end=\"url(#arrowhead)\" transform=\"translate({offset_x},{offset_y})\" />"
            )

        for node in self._nodes.values():
            svg_parts.append(
                f"  <rect x=\"{node.left + offset_x}\" y=\"{node.top + offset_y}\" width=\"{node.width}\" height=\"{node.height}\" rx=\"8\" ry=\"8\" fill=\"{fill}\" stroke=\"{stroke}\" stroke-width=\"2\" />"
            )
            if node.label:
                svg_parts.append(
                    f"  <text x=\"{node.cx + offset_x}\" y=\"{node.cy + offset_y}\" fill=\"{text_color}\" font-size=\"{font_size}\" text-anchor=\"middle\" dominant-baseline=\"middle\">{node.label}</text>"
                )

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)


__all__ = ["FlowSvgExporter"]
