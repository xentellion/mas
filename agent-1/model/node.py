from shapely.geometry import Point


class Node:
    def __init__(self, point: Point, weight: int = 1):
        self.__point = point
        self.__x = self.__point.x
        self.__y = self.__point.y
        self.__weight = weight
        self.point_neighbors = []

    @property
    def point(self):
        return self.__point

    @property
    def weight(self):
        return self.__weight

    @property
    def x(self):
        return self.__x

    @property
    def y(self):
        return self.__y
