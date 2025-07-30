import matplotlib.pyplot as plt
import numpy as np
import json

import shapely.geometry as sg
import shapely.ops as so
from shapely import union, difference

import time


# /////////////////////////////////////////////


class Node:
    def __init__(self, point: sg.Point):
        self.__point = point
        self.point_neighbors = []

    @property
    def point(self):
        return self.__point


class Wall:
    def __init__(
        self,
        area,
        enclosed=True,
    ):
        area = [(element["x"], element["y"], element["z"]) for element in area]
        if enclosed:
            area += [area[0]]
        self.__borders = sg.Polygon(area)

    @property
    def borders(self):
        return self.__borders


# /////////////////////////////////////////////


class Paths:
    def __init__(self, previous_path=None):
        self.__path = [] if previous_path is None else previous_path

    def __len__(self):
        return len(self.__path)


class Pathfinder:
    def __init__(self):
        pass

    @staticmethod
    def plot_path(graph: dict, point_a: int, point_b: int):
        target_node = graph[point_b]
        current_node = graph[point_a]
        previous_node = None

        path = [point_a]

        distances = {
            point_a: current_node.point.distance(target_node.point),
        }
        visited = []

        steps = 0
        found = False
        while not found:
            # stop if found the target in neighbours
            if point_b in current_node.point_neighbors:
                found = True
                path.append(point_b)
                continue
            # collect dictionary of bird-fly distances from node to the final point
            for cur_p in current_node.point_neighbors:
                if cur_p not in distances:
                    distances[cur_p] = graph[cur_p].point.distance(target_node.point)

            next_step = []
            for x in current_node.point_neighbors:
                if x in visited:
                    continue
                if x in path:
                    delta = len(path) - 1 - path.index(x)
                    if delta > 1:
                        next_step = []
                        # next_step.append((x, distances[x] + len(path[: path.index(x)])))
                        break
                else:
                    next_step.append((x, distances[x] + len(path)))
            next_step.sort(key=lambda x: x[1])

            if len(next_step) > 0:
                path.append(next_step[0][0])
            else:
                vis_node = path.pop(-1)
                visited.append(vis_node)

            current_node = graph[path[-1]]
            # print("path", path, "\n\n")

            steps += 1
        print(steps)
        return path
        # return visited


class AreaRender:
    def __init__(self, step=1):
        self.flats = self.load_walls()
        self.step = step

    def load_walls(self):
        flats = []
        try:
            with open(
                "/home/xentellion/Desktop/mas/agent-1/data/walls.json",  # I hate this hardode
                "r",
                encoding="UTF-8",
            ) as f:
                data = json.load(f)
                for x in data:
                    try:
                        element = Wall(**x)
                    except (ValueError, NameError, TypeError) as e:
                        print(f"\033[1;31mError loading JSON data:\033[0m {e}")
                        continue
                    flats.append(element)
        except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
            print(f"\033[1;31mError loading JSON data:\033[0m {e}")
        return flats

    def render(self):
        fig, ax = plt.subplots(1, 1)
        fig.suptitle("Airport")

        area = self.draw_walkable_area(ax, False)
        self.draw_map(ax, False)
        if area:
            points = self.get_nodes_coordinates(area)
            connections = self.construct_edges(area, points)
            self.draw_edges(ax)

        # test
        start_time = time.perf_counter()

        path = Pathfinder.plot_path(self.graph, 12, 44)
        # path = Pathfinder.plot_path(self.graph, 44, 12)
        # path = Pathfinder.plot_path(self.graph, 13, 71)

        end_time = time.perf_counter()
        print(f"Path found in {(end_time - start_time):.5f} seconds")

        for i in path:
            self.highlight_point(ax, i)

        # animation = ArtistAnimation(
        #     fig,
        #     frames,  # кадры
        #     interval=30,  # задержка между кадрами в мс
        #     blit=True,
        #     repeat=True,
        # )

        plt.show()

    def draw_map(self, ax, hide_scale: bool):
        ax.set_aspect("equal")
        ax.xaxis.set_major_locator(plt.MultipleLocator(1))
        ax.yaxis.set_major_locator(plt.MultipleLocator(1))

        try:
            area = self.flats[0].borders.boundary
        except IndexError as e:
            print(f"\033[1;31mMap building error:\033[0m {e}")
            return
        for x in self.flats[1:]:
            area = area.union(x.borders.boundary)
        for line in area.geoms:
            ax.plot(*line.xy, color="black", linewidth=1)

        if hide_scale:
            for label in ax.get_xticklabels():
                label.set_visible(False)
            for label in ax.get_yticklabels():
                label.set_visible(False)

    def draw_walkable_area(self, ax, hide_scale: bool):
        total_area = so.unary_union([x.borders for x in self.flats])
        for x in self.flats[1:]:
            total_area = total_area.difference(x.borders)

        if isinstance(total_area, sg.MultiPolygon):
            for line in total_area.geoms:
                ax.fill_between(*line.boundary.xy, color="green")
        elif isinstance(total_area, sg.Polygon):
            ax.fill_between(*total_area.boundary.xy, color="green")
        return total_area

    def get_nodes_coordinates(self, area: sg.Polygon):
        x_min, y_min, x_max, y_max = area.bounds
        n_spacing_x = int(np.ceil((x_max - x_min) / self.step))  # number of points on X
        n_spacing_y = int(np.ceil((y_max - y_min) / self.step))
        points = (
            sg.Point(x_min + x * self.step, y_min + y * self.step)
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
                if (pt.point.x - p.point.x == self.step and p.point.y == pt.point.y)
                or (pt.point.y - p.point.y == self.step and pt.point.x == p.point.x)
            ]
            # save and optionally draw
            if nearest_points:
                # Filter out lines intersecting borders and transpose to indexes and points
                transposed = tuple(
                    zip(
                        *filter(
                            # lambda z: z,
                            lambda z: not z[1].intersects(area.boundary),
                            (
                                (x, sg.LineString([p.point, y.point]))
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

    def highlight_point(self, ax, index, human_size=0.25):
        circle = plt.Circle(
            self.graph[index].point.xy, human_size, color="blue", zorder=10
        )
        text = plt.text(
            self.graph[index].point.x - human_size,
            self.graph[index].point.y - human_size / 2,
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
