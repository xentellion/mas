# import asyncio
import os
import json
import logging
import pickle

import numpy as np
import pyqtgraph as pg

from pyqtgraph.Qt import QtCore, QtGui
from PyQt6.QtWidgets import QGraphicsPathItem
from PyQt6.QtCore import Qt
from shapely.geometry import Polygon, MultiPolygon, LineString

from .pathfinder import Pathfinder
from app.models.graph import Graph, Wall
from app.utils import execution_timer
from app.core.constants import GRAPH_PATH


class AreaRender(pg.PlotWidget):
    def __init__(
        self,
        step=1,
        draw_grid=False,
        parent=None,
        background="white",
    ):
        super().__init__(parent, background)
        self.create_renderer(step, draw_grid)

    def create_renderer(self, step, draw_grid):
        self.step = step
        self.draw_grid = False
        self.graph = None
        self.extra_connections = None
        self.flats = self._load_walls()

        pg.setConfigOptions(antialias=True)

        self.setLabel("left", "Y Axis")
        self.setLabel("bottom", "X Axis")
        self.setAspectLocked(lock=True, ratio=1)
        self.showGrid(x=self.draw_grid, y=self.draw_grid)
        self.viewBox = self.plotItem.getViewBox()

        self.edges_drawn = []
        self.interactables_mapping, self.interactables = None, None
        self.create_area()
        self.draw_intercatables()
        if self.draw_grid:
            # Atrociously bad performance (edges are drawn twice)
            # Might tackle, don't care tho
            self.draw_edges()
            self.draw_transitions()

        self.highlight_points = pg.ScatterPlotItem(
            size=self.step - 0.1,
            pen=pg.mkPen(None),
            brush=pg.mkBrush(0, 0, 255),
            hoverable=True,
            hoverBrush=pg.mkBrush(0, 255, 255),
            pxMode=False,
        )
        self.highlight_points.setZValue(2)
        self.points = []
        self.addItem(self.highlight_points)

        self.agent_items = pg.ScatterPlotItem(
            size=self.step - 0.1,
            pen=pg.mkPen("black"),
            brush=pg.mkBrush("red"),
            hoverable=True,
            hoverBrush=pg.mkBrush(0, 255, 255),
            pxMode=False,
        )
        self.agent_items.setZValue(3)
        self.addItem(self.agent_items)

    def reset_area(self):
        self.removeItem(self.agent_items)
        self.removeItem(self.highlight_points)
        self.create_renderer(self.step, self.draw_grid)

    @execution_timer("Load walls data")
    def _load_walls(self, path="data/walls.json") -> list[Wall]:
        flats = []
        try:
            with open(path, "r", encoding="UTF-8") as f:
                data = json.load(f)
                for x in data["blocks"]:
                    element = Wall(**x, scale=data["scale"], step=self.step)
                    flats.append(element)
                self.extra_connections = data["connections"]
        except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
            logging.error("JSON data cannot be loaded: %s", e)
            return
        except (ValueError, NameError, TypeError) as e:
            logging.error("JSON data cannot be loaded: %s", e)
            return
        return flats

    def create_area(self, path: str = None, rebuild: bool = False):
        if path is not None:
            return
        area = self.draw_walkable_area()

        if not self.flats:
            return
        nodes = Pathfinder.create_node_grid(area, self.step)
        if not os.path.isfile(GRAPH_PATH) or rebuild:
            self.graph = Pathfinder.construct_edges(area, nodes, self.step)
            self._save_graph(GRAPH_PATH)
        else:
            self.graph = self._load_graph(GRAPH_PATH)

        self.interactables_mapping, self.interactables = (
            Pathfinder.create_interactables(self.flats, self.graph)
        )
        self.graph.rough_graph = Pathfinder.construct_rough_graph(
            self.graph, self.extra_connections
        )

    @execution_timer("Draw walkable area")
    def draw_walkable_area(self):
        if self.flats is None:
            return
        self._draw_wall(self.flats[0].borders)
        cords = np.array(self.flats[0].borders.exterior.coords.xy)
        x_d, y_d = np.max(cords[0]), np.max(cords[1])
        self.setLimits(
            xMin=-x_d * 0.5,
            yMin=-y_d * 0.5,
            xMax=x_d * 1.5,
            yMax=y_d * 1.5,
        )
        total_area = []
        for room in self.flats[1:]:
            walls = room.borders

            for w in room.walls:
                bounds = list(w.bounds)
                if bounds[0] == bounds[2]:
                    bounds += (
                        bounds[2] + 0.1,
                        bounds[3],
                        bounds[0] + 0.1,
                        bounds[1],
                    )
                else:
                    bounds += (
                        bounds[2],
                        bounds[3] + 0.1,
                        bounds[0],
                        bounds[1] + 0.1,
                    )
                thin_wall = Polygon(
                    tuple(bounds[i : i + 2] for i in range(0, len(bounds), 2))
                )
                walls = walls.difference(thin_wall)
            total_area.append(walls)
            self._draw_wall(walls, True)

        return MultiPolygon(total_area)

    def draw_intercatables(self):
        for room in self.interactables.values():
            self._draw_wall(room.area, color="red")

    @execution_timer("Draw coordinate grid")
    def draw_edges(self):
        for grid in self.graph.edges:
            for con in grid:
                self.plot(*con.xy, pen="#999999")

    @execution_timer("Draw transitions")
    def draw_transitions(self):
        for line in self.extra_connections:
            con = LineString(
                [self.graph.get_node(line[0]).xy, self.graph.get_node(line[1]).xy]
            )
            self.plot(*con.xy, pen="#999999")

    @execution_timer("Draw found path")
    def draw_path(self, path):
        if not path:
            return
        p1, p2 = (None, None), self.graph.get_node(path[0]).xy
        for i in range(len(path) - 1):
            p1 = self.graph.get_node(path[i + 1]).xy
            p1, p2 = p2, p1
            color = (
                "b--" if abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) > self.step else "blue"
            )
            self.plot(*zip(p1, p2), color, zorder=200)

    def _load_graph(self, path: str) -> Graph:
        with open(path, "rb") as f:
            return pickle.load(f)

    def _save_graph(self, path: str):
        with open(path, "wb") as f:
            pickle.dump(self.graph, f, protocol=pickle.HIGHEST_PROTOCOL)

    def _shapely_polygon_to_qt(
        self, poly: [Polygon, MultiPolygon], closed: bool = True
    ):
        path = QtGui.QPainterPath()
        # Outer border
        exterior_coords = np.array(poly.exterior.coords.xy).T
        path.moveTo(exterior_coords[0, 0], exterior_coords[0, 1])
        for x, y in exterior_coords[1:]:
            path.lineTo(x, y)
        path.closeSubpath()
        # Inner walls
        for interior_ring in poly.interiors:
            interior_coords = np.array(interior_ring.coords.xy).T
            path.moveTo(interior_coords[0, 0], interior_coords[0, 1])
            for x, y in interior_coords[1:]:
                path.lineTo(x, y)

        if closed:
            path.closeSubpath()

        return path

    def _draw_wall(
        self,
        border,
        fill: bool = False,
        color: str = "black",
        closed: bool = True,
    ):
        border = self._shapely_polygon_to_qt(border, closed=closed)
        pen = QGraphicsPathItem(border)
        pen.setPen(pg.mkPen(color=color, width=2))
        if fill:
            pen.setBrush(pg.mkBrush(color="green"))
        self.addItem(pen)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = QtCore.QPointF(event.pos())
            point = self.viewBox.mapSceneToView(scene_pos)  # get the point clicked
            x, y = point.x(), point.y()
            for i in range(len(self.graph)):
                node = self.graph.get_node(i)
                if abs(x - node.x) < self.step / 2 and abs(y - node.y) < self.step / 2:
                    self.points.append({"pos": (node.x, node.y), "data": f"ID: {i}"})
                    self.highlight_points.setData(spots=self.points)
                    break
        super().mousePressEvent(event)
