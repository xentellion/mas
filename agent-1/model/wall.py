from shapely.geometry import Polygon, LineString  # , Point

from interactable import Interactable


class Wall:
    def __init__(
        self, name, area, walls, interactables, enclosed=True, scale=1, step=1
    ):
        self.__name = name
        self.__scale = scale
        area = [
            (
                element["x"] * scale,
                element["y"] * scale,
            )
            for element in area
        ]
        if enclosed:
            area += [area[0]]
        self.__borders = Polygon(area)
        walls = [[x * scale for x in w] for w in walls]
        self.__walls = [LineString([w[:2], w[-2:]]) for w in walls]
        self.__interactables = None
        if interactables:
            self.__interactables = [
                Interactable(**i, scale=scale, step=step) for i in interactables
            ]
        pass

    @property
    def borders(self):
        return self.__borders

    @property
    def name(self):
        return self.__name

    @property
    def walls(self):
        return self.__walls

    @property
    def interactables(self):
        return self.__interactables

    # def move_interactable(self, idx: int, point: Point):
    #     if not self.interactables:
    #         return
    #     self.__interactables[idx].inlet_point = [
    #         point.x // self.__scale,
    #         point.y // self.__scale,
    #     ]
