from shapely.geometry import Point


class Node:
    def __init__(self, point: Point, weight: int = 1):
        self.__node_id = None
        self._subgraph = None
        self.__point = point
        self.__x = self.__point.x
        self.__y = self.__point.y
        self.point_neighbors = {}
        self.transmission_point = None

    @property
    def id(self):
        return self.__id

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


class RoughConnection:
    def __init__(self, start: int, end: int, both_way: bool):
        self.__start = start
        self.__end = end
        self.__both_way = both_way

    @property
    def start(self):
        return self.__start

    @property
    def end(self):
        return self.__end

    @property
    def both_way(self):
        return self.__both_way


class SubGraph:
    def __init__(self):
        self.__nodes = {}

    def __getitem__(self, key):
        return self.__nodes[key]

    def __setitem__(self, key, value):
        if not isinstance(key, int):
            raise TypeError("Key must be an integer")
        if not isinstance(value, Node):
            raise TypeError("Value must be a Node")
        self.__nodes[key] = value

    def __delitem__(self, key):
        del self.__nodes[key]

    def __iter__(self):
        for item in self.__nodes.keys():
            yield item

    def __len__(self):
        return len(self.__nodes)


class Graph:
    def __init__(self):
        self.__subgraphs = {}

    def __getitem__(self, key):
        return self.__subgraphs[key]

    def __setitem__(self, key, value):
        if not isinstance(key, int):
            raise TypeError("Key must be an integer")
        if not isinstance(value, SubGraph):
            raise TypeError("Value must be a SubGraph")
        self.__subgraphs[key] = value

    def __delitem__(self, key):
        del self.__subgraphs[key]

    def get_node(self, key):
        subg = next((x for x in self.__subgraphs.values() if key in x), None)
        if not subg:
            return None
        return subg[key]

    def set_node(self, subgraph, key, value):
        if subgraph not in self.__subgraphs:
            self.__subgraphs[subgraph] = SubGraph()
        self.__subgraphs[subgraph][key] = value

    def __iter__(self):
        for item in self.__subgraphs.keys():
            yield item

    def __len__(self):
        return sum(len(self.__subgraphs[x]) for x in self.__subgraphs)
