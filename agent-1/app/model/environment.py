# import asyncio
import os
import json
import logging
import pickle

# from itertools import chain

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.collections import PatchCollection
from pydantic import ValidationError
from shapely.geometry import Polygon, MultiPolygon, LineString

from model.pathfinder import Pathfinder
from model.prompts import Prompts
from model.wall import Wall
from model.extras import execution_timer
from model.graph import Graph

GRAPH_PATH = "data/graph.bin"


class AreaRender:
    def __init__(self, step=1):
        self.step = step

        self.graph = None
        self.extra_connections = None

        self.flats = self.load_walls()

        self.edges_drawn = []
        self.fig, self.ax = plt.subplots(1, 1)
        self.interactables_mapping, self.interactables = None, None

    @execution_timer("Load walls data")
    def load_walls(self, path="data/walls.json") -> list[Wall]:
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

    def load_prompts(self, path="data/prompt.json") -> Prompts:
        with open(path, "r", encoding="UTF-8") as f:
            try:
                return Prompts.model_validate(json.load(f))
            except ValidationError:
                logging.error("Failed to load and validate prompts")
                return None

    def load_graph(self, path: str) -> Graph:
        with open(path, "rb") as f:
            return pickle.load(f)

    def save_graph(self, path: str):
        with open(path, "wb") as f:
            pickle.dump(self.graph, f, protocol=pickle.HIGHEST_PROTOCOL)

    def create_area(self, path: str = None, rebuild: bool = False):
        if path is not None:
            return
        plt.connect("button_press_event", self.on_click)
        self.fig.suptitle("Airport")

        area = self.draw_walkable_area()
        self.draw_map()

        if not self.flats:
            return
        nodes = Pathfinder.create_node_grid(area, self.step)
        if not os.path.isfile(GRAPH_PATH) or rebuild:
            self.graph = Pathfinder.construct_edges(area, nodes, self.step)
            self.save_graph(GRAPH_PATH)
        else:
            self.graph = self.load_graph(GRAPH_PATH)

        self.interactables_mapping, self.interactables = (
            Pathfinder.create_interactables(self.flats, self.graph)
        )
        self.graph.rough_graph = Pathfinder.construct_rough_graph(
            self.graph, self.extra_connections
        )

    @execution_timer("Draw map")
    def draw_map(self, show_scale: bool = False):
        self.ax.set_aspect("equal")
        self.ax.xaxis.set_major_locator(plt.MultipleLocator(1))
        self.ax.yaxis.set_major_locator(plt.MultipleLocator(1))

        try:
            area = self.flats[0].borders.boundary
        except IndexError as e:
            logging.error("Map building error: %s", e)
            return
        for x in self.flats[1:]:
            area = area.union(x.borders.boundary)
        for line in area.geoms:
            self.ax.plot(*line.xy, color="black", linewidth=1)

        if not show_scale:
            for label in self.ax.get_xticklabels():
                label.set_visible(False)
            for label in self.ax.get_yticklabels():
                label.set_visible(False)

    @execution_timer("Draw walkable area")
    def draw_walkable_area(self):
        if self.flats is None:
            return
        self.ax.plot(*self.flats[0].borders.exterior.xy, color="black")
        # total_area = MultiPolygon(x.borders for x in self.flats[1:])
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
            self.plot_polygon(walls, facecolor="green", edgecolor="black")

        return MultiPolygon(total_area)

    def plot_polygon(self, poly, **kwargs):
        path = Path.make_compound_path(
            Path(np.asarray(poly.exterior.coords)[:, :2]),
            *[Path(np.asarray(ring.coords)[:, :2]) for ring in poly.interiors],
        )

        patch = PathPatch(path, **kwargs)
        collection = PatchCollection([patch], **kwargs)

        self.ax.add_collection(collection, autolim=True)
        self.ax.autoscale_view()
        return collection

    def draw_intercatables(self):
        for room in self.interactables.values():
            self.ax.plot(*room.area.exterior.xy, color="red")

    def draw_nodes(self, ax, nodes):
        # Take list of nodes, convert to tuple of X's of Y's and draw on axis
        ax.scatter(*zip(*((point.x, point.y) for point in nodes)), color="black")

    @execution_timer("Draw coordinate grid")
    def draw_edges(self):
        for grid in self.graph.edges:
            for con in grid:
                self.ax.plot(*con.xy, color="#999999", linewidth=1)

    @execution_timer("Draw transitions")
    def draw_transitions(self):
        for line in self.extra_connections:
            con = LineString(
                [self.graph.get_node(line[0]).xy, self.graph.get_node(line[1]).xy]
            )
            self.ax.plot(*con.xy, "--", color="#999999", linewidth=1)

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
            self.ax.plot(*zip(p1, p2), color, zorder=200)

    def highlight_point(self, ax, index, human_size=0.25, show_numbers=True):
        target = self.graph.get_node(index)
        if not target:
            logging.warning("No point found")
        circle = plt.Circle(target.point.xy, human_size, color="blue", zorder=10)
        if show_numbers:
            plt.text(
                target.x - human_size / 2,
                target.y - human_size / 2,
                str(index),
                color="black",
                zorder=100,
            )
        ax.add_patch(circle)
        plt.show()

    def on_click(self, event):
        if event.dblclick:
            x, y = event.xdata, event.ydata
            for i in range(len(self.graph)):
                node = self.graph.get_node(i)
                if abs(x - node.x) < 1e-1 and abs(y - node.y) < 1e-1:
                    self.highlight_point(event.inaxes, i)
                    break
