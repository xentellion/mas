import json
import logging
import numpy as np

# from itertools import chain
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon, MultiPolygon, LineString
from shapely.ops import unary_union

from node import Node, RoughConnection, Graph
from wall import Wall
from extras import execution_timer
from pathfinder import Pathfinder


logging.basicConfig(
    level=logging.INFO,
    filename="py_log.log",
    filemode="a+",
    format="%(asctime)s:%(levelname)s:%(message)s",
)


class AreaRender:
    def __init__(self, step=1):
        self.step = step
        self.graph = Graph()
        self.rough_graph = None
        self.graph_edges = []
        self.extra_connections = None

        self.flats = self.load_walls()

    @execution_timer("Load walls data")
    def load_walls(self, path="data/walls.json"):
        flats = []
        try:
            with open(path, "r", encoding="UTF-8") as f:
                data = json.load(f)
                for x in data["blocks"]:
                    try:
                        element = Wall(**x)
                    except (ValueError, NameError, TypeError) as e:
                        logging.error(f"JSON data cannot be loaded: {e}")
                        continue
                    flats.append(element)
                self.extra_connections = [
                    RoughConnection(**x) for x in data["connections"]
                ]
        except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
            logging.error(f"JSON data cannot be loaded: {e}")
            return
        return flats

    def render(self):
        fig, ax = plt.subplots(1, 1)
        plt.connect("button_press_event", self.on_click)
        fig.suptitle("Airport")

        area = self.draw_walkable_area(ax)
        if self.flats is None:
            return
        self.draw_map(ax, True)
        if isinstance(area, Polygon):
            points = [self.get_nodes_coordinates(area)]
        elif isinstance(area, MultiPolygon):
            points = [self.get_nodes_coordinates(a) for a in area.geoms]
        else:
            logging.error("Cannot create node grid")
            return
        self.construct_edges(area, points)
        self.construct_rough_graph()
        self.draw_edges(ax)

        path = []
        # path = Pathfinder.plot_path(self.graph, 12, 8750)
        # path = Pathfinder.plot_path(self.graph[0], 78, 22)
        path = Pathfinder.plot_path(self.graph[0], 6, 21)
        # path = Pathfinder.plot_path(self.graph, 13, 71)
        self.draw_path(ax, path)
        # for i in path:
        #     self.highlight_point(ax, i, show_numbers=False)

        plt.show()

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
        total_area = unary_union([x.borders for x in self.flats])
        for x in self.flats[1:]:
            total_area = total_area.difference(x.borders)

        if isinstance(total_area, MultiPolygon):
            for line in total_area.geoms:
                ax.fill_between(*line.boundary.xy, color="green")
        elif isinstance(total_area, Polygon):
            ax.fill_between(*total_area.boundary.xy, color="green")
        return total_area

    def get_nodes_coordinates(self, area: Polygon):
        x_min, y_min, x_max, y_max = area.bounds
        n_spacing_x = int(np.ceil((x_max - x_min) / self.step))  # number of points on X
        n_spacing_y = int(np.ceil((y_max - y_min) / self.step))
        points = (
            Point(x_min + x * self.step, y_min + y * self.step)
            for y in range(n_spacing_y)
            for x in range(n_spacing_x)
        )
        return list(
            filter(
                lambda z: area.contains(z) and z.distance(area.boundary) > 1e-2,
                points,
            )
        )

    def draw_nodes(self, ax, nodes):
        # Take list of nodes, convert to tuple of X's of Y's and draw on axis
        ax.scatter(*zip(*((point.x, point.y) for point in nodes)), color="black")

    @execution_timer("Building graph edges")
    def construct_edges(self, area, graphs):
        shift = 0

        for subgraph_id, sg in enumerate(graphs):
            for node_id, node in enumerate(sg):
                self.graph.set_node(subgraph_id, node_id + shift, Node(node, self.step))
            shift += len(sg)

        shift = 0

        for sg in self.graph:
            lines = []
            for node_id in self.graph[sg]:
                nearest_points = []
                this_point = self.graph.get_node(node_id)
                for i in range(node_id + 1 - shift, len(self.graph[sg]) + shift):
                    near_point = self.graph.get_node(i)
                    dx = near_point.x - this_point.x
                    dy = near_point.y - this_point.y
                    if dx > self.step or dy > self.step:
                        continue
                    if (dx == self.step and dy == 0) or (dy == self.step and dx == 0):
                        nearest_points.append((i, near_point))
                        if len(nearest_points) >= 2:
                            break
                if nearest_points:
                    connected = filter(
                        lambda z: not z[1].intersects(area.boundary),
                        (
                            (x, LineString([this_point.point, y.point]))
                            for x, y in nearest_points
                        ),
                    )
                    transposed = list(zip(*connected))
                    for node in transposed[0]:
                        self.graph[sg][node_id].point_neighbors[node] = self.step
                        self.graph[sg][node].point_neighbors[node_id] = self.step
                    lines += transposed[1]
            self.graph_edges.append(lines)
            shift += len(self.graph[sg])

    def construct_rough_graph(self):
        rough_graph = {}
        if not self.extra_connections:
            logging.warning("No rough graph on the map")
            return None
        for x in self.extra_connections:
            if x.start not in rough_graph:
                rough_graph[x.start] = []
            rough_graph[x.start].append((x.end,))
        # self.rough_graph = {}
        # active_points = tuple(chain(*self.extra_connections))
        # for idx, subg in enumerate(self.graph):
        #     nodes = filter(lambda x: x in subg, active_points)
        #     for x in nodes:
        #         self.rough_graph[idx] = subg[x]
        # self.rough_graph[idx].point_neighbors =
        # for connect in self.extra_connections:
        #     if any(x in for x in connect)

    @execution_timer("Draw coordinate grid")
    def draw_edges(self, ax):
        for grid in self.graph_edges:
            for con in grid:
                ax.plot(*con.xy, color="#999999", linewidth=1)

    @execution_timer("Draw found path")
    def draw_path(self, ax, path):
        if not path:
            return
        p1, p2 = (None, None), self.graph.get_node(path[0]).xy
        for i in range(len(path) - 1):
            p1 = self.graph.get_node(path[i + 1]).xy
            p1, p2 = p2, p1
            ax.plot(*zip(p1, p2), marker="o", color="blue", zorder=200)

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
    ren = AreaRender(step=0.5)
    ren.render()


if __name__ == "__main__":
    main()
