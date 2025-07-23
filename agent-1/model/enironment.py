# import pydantic
import matplotlib.pyplot as plt
import numpy as np

import shapely.geometry as sg
import shapely.ops as so
from shapely import union, difference


class IntersectionException(Exception):
    def __init__(self, message="Walkable area is intersecting with itself."):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class Wall:
    """Depicts walls, that agents cannot pass through

    Args:
        area: list of coordinate pairs of a polygon corners
        enclosed (bool, optional): Describes whether the last point connects to the star or not. Defaults to True.
    """

    def __init__(
        self,
        area: list[tuple, ...],
        enclosed: bool = True,
    ):
        if enclosed:
            area = np.concatenate((area, [area[0]]))
        # self.__borders = zip(*area)
        self.__borders = sg.Polygon(area)

    @property
    def borders(self):
        return self.__borders


flats = [
    Wall(
        [
            (0, 0),
            (10, 0),
            (10, 10),
            (0, 10),
        ],
        True,
    ),
    Wall(
        [
            (0, 0),
            (5, 6),
            (9, 9),
            # (10, 10),
            (1, 5),
        ],
        True,
    ),
    Wall(
        [
            (0, 0),
            (10, 0),
            (5, 10),
            (0, 10),
        ],
        True,
    ),
]


def draw(func):
    def wrapper(ax, *args, **kwargs):
        ax.set_aspect("equal")
        # ax.grid(True)
        ax.xaxis.set_major_locator(plt.MultipleLocator(1))
        ax.yaxis.set_major_locator(plt.MultipleLocator(1))

        result = func(ax, *args, **kwargs)

        for label in ax.get_xticklabels():
            label.set_visible(False)
        for label in ax.get_yticklabels():
            label.set_visible(False)

        return result

    return wrapper


@draw
def draw_map(ax):
    area = flats[0].borders.boundary
    for x in flats[1:]:
        area = area.union(x.borders.boundary)
    for line in area.geoms:
        ax.plot(*line.xy, color="black", linewidth=1)


@draw
def draw_walkable(ax):
    total_area = so.unary_union([x.borders for x in flats])
    for x in flats[1:]:
        total_area = total_area.difference(x.borders)

    if isinstance(total_area, sg.MultiPolygon):
        for line in total_area.geoms:
            ax.fill_between(*line.boundary.xy, color="green")
    elif isinstance(total_area, sg.Polygon):
        ax.fill_between(*total_area.boundary.xy, color="green")
    return total_area


def get_nodes_coordinates(area: sg.Polygon, step: int = 1):
    x_min, y_min, x_max, y_max = area.bounds
    n_spacing_x = int(np.ceil((x_max - x_min) / step))  # number of points on X
    n_spacing_y = int(np.ceil((y_max - y_min) / step))
    points = (
        sg.Point(x_min + x * step, y_min + y * step)
        for y in range(n_spacing_y)
        for x in range(n_spacing_x)
    )
    return list(
        filter(lambda z: area.contains(z) and z.distance(area.boundary) > 1e-2, points)
    )


def draw_nodes(ax, nodes):
    # Take list of nodes, convert to tuple of X's of Y's and draw on axis
    ax.scatter(*zip(*((point.x, point.y) for point in nodes)), color="black")


def construct_edges(area, nodes, step=1):
    # two_dim_points = {}
    # for point in nodes:
    #     if point.x not in two_dim_points:
    #         two_dim_points[point.x] = []
    #     two_dim_points[point.x].append(point)
    # two_dim_points = [x for x in two_dim_points.values()]
    # print(two_dim_points)

    connections = []

    for idx, point in enumerate(nodes[:-1]):
        near = [
            pt
            for pt in nodes[idx + 1 :]
            if (pt.x - point.x == step and point.y == pt.y)
            or (pt.y - point.y == step and pt.x == point.x)
        ]
        if near:
            lines = filter(
                lambda x: not x.intersects(area.boundary),
                (sg.LineString([point, x]) for x in near),
            )
            connections += list(lines)
    return connections


def draw_edges(ax, connections):
    for con in connections:
        ax.plot(*con.xy, color="#999999", linewidth=1)


def main():
    # fig, (ax1, ax2, ax3) = plt.subplots(1, 3)
    # fig.suptitle("3 levels of airport")

    # ax = (ax1, ax2, ax3)
    # for idx, field in enumerate(ax):
    #     draw_walkable(field)
    #     draw_map(field)
    step = 0.25

    fig, ax = plt.subplots(1, 1)
    fig.suptitle("Airport")
    area = draw_walkable(ax)
    draw_map(ax)
    points = get_nodes_coordinates(area, step)

    connections = construct_edges(area, points, step)
    # draw_nodes(ax, points)

    draw_edges(ax, connections)
    plt.show()


if __name__ == "__main__":
    main()
