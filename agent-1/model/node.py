from shapely.geometry import Point
from copy import deepcopy


class Node:
    def __init__(self, point: Point, subgraph: int, weight: int = 1):
        self.__node_id = None
        self.__subgraph = subgraph
        self.__point = point
        self.__x = self.__point.x
        self.__y = self.__point.y
        self.point_neighbors = {}
        self.transmission_point = None
        self.rough_graph = None

    @property
    def id(self):
        return self.__id

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
    def __init__(self, subgraph=None):
        self._subgraphs = {} if not subgraph else subgraph

    @property
    def subgraphs(self):
        return self._subgraphs

    def __getitem__(self, key):
        return self._subgraphs[key]

    def __setitem__(self, key, value):
        if not isinstance(key, int):
            raise TypeError("Key must be an integer")
        if not isinstance(value, SubGraph):
            raise TypeError("Value must be a SubGraph")
        self._subgraphs[key] = value

    def __delitem__(self, key):
        del self._subgraphs[key]

    def get_node(self, key) -> Node:
        subg = next((x for x in self._subgraphs.values() if key in x), None)
        if not subg:
            raise KeyError("Node not found")
        return subg[key]

    def set_node(self, subgraph, key, value):
        if subgraph not in self._subgraphs:
            self._subgraphs[subgraph] = SubGraph()
        self._subgraphs[subgraph][key] = value

    def copy(self):
        return self.__class__(deepcopy(self._subgraphs))

    def __iter__(self):
        for item in self._subgraphs.keys():
            yield item

    def __len__(self):
        return sum(len(self._subgraphs[x]) for x in self._subgraphs)


class RoughGraph(Graph):
    def add_rough_node(self, node_id: int, node: Node):
        self._subgraphs[0][node_id] = deepcopy(node)
        close_by = tuple(
            filter(
                lambda z: self.get_node(z).subgraph == node.subgraph,
                (x for x in self._subgraphs[0]),
            )
        )
        self._subgraphs[0][node_id].point_neighbors = {
            x: node.point.distance(self.get_node(x).point) for x in close_by
        }

        for point in close_by:
            self.get_node(point).point_neighbors[node_id] = self._subgraphs[0][
                node_id
            ].point_neighbors[point]
