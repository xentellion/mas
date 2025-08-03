import matplotlib.pyplot as plt
import numpy as np
import json
import time

from shapely.geometry import Point, Polygon, MultiPolygon, LineString
from shapely.ops import unary_union

from node import Node
from wall import Wall
from pathfinder import Pathfinder
from aux import achtung_print


class AreaRender:
    def __init__(self, step=1):
        self.flats = self.load_walls()
        self.step = step

    def load_walls(self, path="data/walls.json"):
        flats = []
        try:
            with open(
                path,  # I hate this hardode
                "r",
                encoding="UTF-8",
            ) as f:
                data = json.load(f)
                for x in data:
                    try:
                        element = Wall(**x)
                    except (ValueError, NameError, TypeError) as e:
                        achtung_print("Error loading JSON data", e)
                        continue
                    flats.append(element)
        except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
            achtung_print("Error loading JSON data", e)
            return
        return flats

    def render(self):
        fig, ax = plt.subplots(1, 1)
        fig.suptitle("Airport")

        area = self.draw_walkable_area(ax)
        if self.flats is None:
            return
        self.draw_map(ax, False)
        if isinstance(area, Polygon):
            points = self.get_nodes_coordinates(area)
            self.construct_edges(area, points)
            # self.draw_edges(ax)
        elif isinstance(area, MultiPolygon):
            points = [self.get_nodes_coordinates(a) for a in area.geoms]
            for i in points:
                self.construct_edges(area, i)
                # self.draw_edges(ax)

        # test
        start_time = time.perf_counter()

        path = []
        path = Pathfinder.plot_path(self.graph, 12, 8750)
        # path = Pathfinder.plot_path(self.graph, 44, 12)
        # path = Pathfinder.plot_path(self.graph, 13, 71)

        end_time = time.perf_counter()
        print(f"Path found in {(end_time - start_time):.5f} seconds")

        for i in path:
            self.highlight_point(ax, i, show_numbers=False)
        # animation = ArtistAnimation(
        #     fig,
        #     frames,  # кадры
        #     interval=30,  # задержка между кадрами в мс
        #     blit=True,
        #     repeat=True,
        # )

        plt.show()

    def draw_map(self, ax, show_scale: bool = False):
        ax.set_aspect("equal")
        ax.xaxis.set_major_locator(plt.MultipleLocator(1))
        ax.yaxis.set_major_locator(plt.MultipleLocator(1))

        try:
            area = self.flats[0].borders.boundary
        except IndexError as e:
            achtung_print("Map building error", e)
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

    def construct_edges(self, area, nodes):
        self.graph = {k: Node(v) for k, v in enumerate(nodes)}
        self.graph_lines = []
        nodes = tuple(self.graph.values())

        for idx, p in self.graph.items():
            # check bottom and right connections
            nearest_points = [
                (i, pt)
                for i, pt in enumerate(nodes[idx + 1 :], start=idx + 1)
                if (pt.x - p.x == self.step and p.y == pt.y)
                or (pt.y - p.y == self.step and pt.x == p.x)
            ]
            # save and optionally draw
            if nearest_points:
                # Filter out lines intersecting borders and transpose to indexes and points
                transposed = tuple(
                    zip(
                        *filter(
                            lambda z: not z[1].intersects(area.boundary),
                            (
                                (x, LineString([p.point, y.point]))
                                for x, y in nearest_points
                            ),
                        )
                    )
                )
                # Add indexes to correlating nodes
                self.graph[idx].point_neighbors += transposed[0]
                for node in transposed[0]:
                    self.graph[node].point_neighbors += [idx]
                self.graph_lines += list(transposed[1])

    def draw_edges(self, ax):
        for con in self.graph_lines:
            ax.plot(*con.xy, color="#999999", linewidth=1)

    def highlight_point(self, ax, index, human_size=0.25, show_numbers=True):
        circle = plt.Circle(
            self.graph[index].point.xy, human_size, color="blue", zorder=10
        )
        if show_numbers:
            plt.text(
                self.graph[index].x - human_size,
                self.graph[index].y - human_size / 2,
                str(index),
                color="black",
                zorder=100,
            )
        ax.add_patch(circle)
        # ax.add_patch(text)


# /////////////////////////////////////////////


def main():
    ren = AreaRender(step=0.5)
    ren.render()


if __name__ == "__main__":
    main()
