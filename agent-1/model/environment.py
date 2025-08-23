# import asyncio
import json
import logging
from time import sleep

# from itertools import chain
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.collections import PatchCollection
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, LineString

from agent import Agent
from agent_task import WalkingTask
from extras import execution_timer, State
import interactable
from pathfinder import Pathfinder
from wall import Wall


logging.basicConfig(
    level=logging.INFO,
    filename="py_log.log",
    filemode="a+",
    format="%(asctime)s:%(levelname)s:%(message)s",
)


class AreaRender:
    def __init__(self, step=1):
        self.step = step

        self.graph = None
        self.extra_connections = None

        self.flats = self.load_walls()

        self.edges_drawn = []

    @execution_timer("Load walls data")
    def load_walls(self, path="data/walls.json") -> list[Wall]:
        flats = []
        try:
            with open(path, "r", encoding="UTF-8") as f:
                data = json.load(f)
                for x in data["blocks"]:
                    try:
                        element = Wall(**x, scale=data["scale"], step=self.step)
                    except (ValueError, NameError, TypeError) as e:
                        logging.error(f"JSON data cannot be loaded: {e}")
                        continue
                    flats.append(element)
                self.extra_connections = data["connections"]
        except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
            logging.error(f"JSON data cannot be loaded: {e}")
            return
        return flats

    def create_area(self):
        self.fig, self.ax = plt.subplots(1, 1)
        plt.connect("button_press_event", self.on_click)
        self.fig.suptitle("Airport")

        area = self.draw_walkable_area()
        self.draw_map(True)

        if not self.flats:
            return
        nodes = Pathfinder.create_node_grid(self.ax, area, self.step)
        self.graph = Pathfinder.construct_edges(area, nodes, self.step)
        self.interactables_mapping, self.interactables = (
            Pathfinder.create_interactables(self.flats, self.graph)
        )
        self.draw_intercatables()
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
            logging.error(f"Map building error: {e}")
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


# /////////////////////////////////////////////


def main():
    logging.info("\n--------------Initializing--------------")
    plt.ion()
    step = 1
    ren = AreaRender(step)
    ren.create_area()
    ren.draw_edges()
    ren.draw_transitions()

    sleep(1)
    agents = []

    plt.show()
    sleep(1)

    agent_1 = Agent(step)
    agent_2 = Agent(step)

    ren.interactables["Gate_in"].add_new_agent(agent_1)
    ren.interactables["Entrance"].add_new_agent(agent_2)

    agent_1.add_task(WalkingTask("Exit", ren.interactables), ren.graph)
    agent_1.add_task(WalkingTask("Exit", ren.interactables), ren.graph)

    agent_2.add_task(WalkingTask("Gate_out", ren.interactables), ren.graph)
    agent_2.add_task(WalkingTask("Entrance", ren.interactables), ren.graph)

    while True:
        for a in agents:
            new_pos = a.tick(ren.graph)
            if new_pos is not None:
                a.ui_object.set_center(ren.graph.get_node(new_pos).point.xy)
            if a.state is State.COMPLETE:
                a.ui_object.remove()
                agents.remove(a)
        for i, point in ren.interactables.items():
            if isinstance(point, interactable.Entrance) or isinstance(
                point, interactable.Gate
            ):
                new_ag = point.spawn_agent(ren.graph)
                if new_ag is not None:
                    ren.ax.add_patch(new_ag.ui_object)
                    agents.append(new_ag)
            point.tick()
        ren.fig.canvas.draw()
        ren.fig.canvas.flush_events()
    plt.show(block=True)


if __name__ == "__main__":
    main()
