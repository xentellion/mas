from shapely.geometry import Polygon


class Wall:
    def __init__(
        self,
        name,
        area,
        enclosed=True,
    ):
        self.__name = name
        area = [(element["x"], element["y"]) for element in area]
        if enclosed:
            area += [area[0]]
        self.__borders = Polygon(area)

    @property
    def borders(self):
        return self.__borders

    @property
    def name(self):
        return self.__name
