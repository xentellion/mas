import matplotlib.pyplot as plt
import numpy as np
import json

import shapely.geometry as sg
import shapely.ops as so
from shapely import union, difference


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


class Pathfinder:
    def __init__(self):
        pass

    @staticmethod
    def plot_path(graph: dict, point_a: int, point_b: int):
        target_node = graph[point_b]
        current_node = graph[point_a]
        previous_node = None

        path = []
        distances = [
            (point_a, Pathfinder.euclidian_distance(current_node, target_node))
        ]
        visited = []

        steps = 0
        found = False
        while not found:
            if point_b in current_node.point_neighbors:
                found = True
                distances.append((point_b, np.float64(0)))
                continue
            for cur_p in current_node.point_neighbors:
                if any(x[0] == cur_p for x in distances):
                    continue
                distances.append(
                    (cur_p, Pathfinder.euclidian_distance(graph[cur_p], target_node))
                )
            distances.sort(key=lambda x: x[1])

            for x in distances:
                if x in visited:
                    continue
                new_node = graph[x[0]]
                if new_node == current_node:
                    visited.append(x)
                else:
                    current_node = new_node
                    break

            steps += 1
        print(path, distances, sep="\n\n")
        return list(zip(*distances))[0]

    # this method ABSOLUTELY should be on GPU
    @staticmethod
    def calculate_distance_heuristic(graph: dict, target: int):
        new_graph = {}
        for k, v in graph.items():
            dist = Pathfinder.euclidian_distance(v.point, graph[target].point)
            # Add some modifiers later
            new_graph[k] = dist

        return new_graph

    @staticmethod
    def euclidian_distance(point_a: Node, point_b: Node):
        return np.linalg.norm(np.array(point_a.point.xy) - np.array(point_b.point.xy))


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
        # self.highlight_point(ax, 0)
        # self.highlight_point(ax, len(self.graph) - 28)

        # pathfinding
        # path = Pathfinder.plot_path(self.graph, 0, len(self.graph) - 28)
        path = Pathfinder.plot_path(self.graph, 13, len(self.graph) - 28)

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
                for node in nearest_points:
                    self.graph[node[0]].point_neighbors += [idx]
                self.graph_lines += list(transposed[1])

    def draw_edges(self, ax):
        for con in self.graph_lines:
            ax.plot(*con.xy, color="#999999", linewidth=1)

    def highlight_point(self, ax, index, human_size=0.25):
        circle = plt.Circle(
            self.graph[index].point.xy, human_size, color="blue", zorder=10
        )
        ax.add_patch(circle)


# /////////////////////////////////////////////


def main():
    ren = AreaRender(step=0.5)
    ren.render()


if __name__ == "__main__":
    main()
