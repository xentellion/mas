import json
import logging

# import asyncio
from time import sleep

# from itertools import chain
import matplotlib.pyplot as plt

from shapely.geometry import MultiPolygon

from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

from agent import Agent
from agent_task import WalkingTask
from extras import execution_timer
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
        self.rough_graph = None
        self.extra_connections = None

        self.flats = self.load_walls()

        self.edges_drawn = []

    @execution_timer("Load walls data")
    def load_walls(self, path="data/walls.json"):
        flats = []
        try:
            with open(path, "r", encoding="UTF-8") as f:
                data = json.load(f)
                for x in data["blocks"]:
                    try:
                        element = Wall(**x, scale=data["scale"])
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

        area = self.draw_walkable_area(self.ax)

        self.draw_map(self.ax, True)

        nodes = Pathfinder.create_node_grid(self.ax, self.flats, area, 1)
        self.graph = Pathfinder.construct_edges(area, nodes, 1)
        self.rough_graph = Pathfinder.construct_rough_graph(
            self.graph, self.extra_connections
        )

    @execution_timer("Draw map")
    def draw_map(self, ax, show_scale: bool = False):
        ax.set_aspect("equal")
        ax.xaxis.set_major_locator(plt.MultipleLocator(1))
        ax.yaxis.set_major_locator(plt.MultipleLocator(1))

        try:
            area = self.flats[0].borders.boundary
        except IndexError as e:
            logging.error(f"Map building error: {e}")
            return
        for x in self.flats[1:]:
            area = area.union(x.borders.boundary)
        for line in area.geoms:
            ax.plot(*line.xy, color="black", linewidth=1)

        if not show_scale:
            for label in ax.get_xticklabels():
                label.set_visible(False)
            for label in ax.get_yticklabels():
                label.set_visible(False)

    @execution_timer("Draw walkable area")
    def draw_walkable_area(self, ax):
        if self.flats is None:
            return
        ax.plot(*self.flats[0].borders.exterior.xy, color="black")
        total_area = MultiPolygon(x.borders for x in self.flats[1:])
        for room in total_area.geoms:
            ax.plot(*room.exterior.xy, color="black")
            ax.fill_between(*room.boundary.xy, color="green")
        return total_area

    def draw_nodes(self, ax, nodes):
        # Take list of nodes, convert to tuple of X's of Y's and draw on axis
        ax.scatter(*zip(*((point.x, point.y) for point in nodes)), color="black")

    @execution_timer("Draw coordinate grid")
    def draw_edges(self):
        for grid in self.graph.edges:
            for con in grid:
                self.ax.plot(*con.xy, color="#999999", linewidth=1)

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
    ren = AreaRender(step=0.25)
    ren.create_area()
    ren.draw_edges()
    plt.show()

    ren.fig.canvas.draw()
    ren.fig.canvas.flush_events()
    # TPS = 10
    sleep(1)

    path = Pathfinder.plot_path(ren.graph, 1064, 59, ren.rough_graph)
    path_1 = Pathfinder.plot_path(ren.graph, 228, 991, ren.rough_graph)
    ren.draw_path(path)
    ren.draw_path(path_1)

    agent_1 = Agent(
        plt.Circle(
            ren.graph.get_node(path[0]).point.xy, 0.10, color="red", zorder=10000
        ),
        ren.graph,
    )
    agent_2 = Agent(
        plt.Circle(
            ren.graph.get_node(path_1[0]).point.xy, 0.10, color="red", zorder=10000
        ),
        ren.graph,
    )
    ren.ax.add_patch(agent_1.ui_object)
    ren.ax.add_patch(agent_2.ui_object)

    ren.fig.canvas.draw()
    ren.fig.canvas.flush_events()
    sleep(1)

    agents = []

    task = WalkingTask(path)
    task2 = WalkingTask(path[::-1])
    task_1 = WalkingTask(path_1)
    task2_1 = WalkingTask(path_1[::-1])
    agent_1.add_task(0, task)
    agent_1.add_task(1, task2)
    agent_2.add_task(0, task_1)
    agent_2.add_task(1, task2_1)
    agents.append(agent_1)
    agents.append(agent_2)

    while len(agents) > 0:
        for a in agents:
            a.tick()
        agents = list(x for x in agents if not x.finished)
        ren.fig.canvas.draw()
        ren.fig.canvas.flush_events()
    plt.show(block=True)


if __name__ == "__main__":
    main()
