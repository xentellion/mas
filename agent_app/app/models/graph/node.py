from shapely.geometry import Point


class Node:
    def __init__(self, point: Point, subgraph: int):
        # self.__node_id = None
        self.__subgraph = subgraph

        self.__point = point
        self.__x = self.__point.x
        self.__y = self.__point.y
        self.point_neighbors = {}
        self.rough_graph = None

        self.transmission_point = None
        self.pass_through = False

    @property
    def subgraph(self):
        return self.__subgraph

    @property
    def point(self):
        return self.__point

    @property
    def x(self):
        return self.__x

    @property
    def y(self):
        return self.__y

    @property
    def xy(self):
        return self.__x, self.__y

    def interact(self, agent):
        print(f"use node at {self.xy}")
