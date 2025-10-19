from copy import deepcopy
from model.node import Node


class Graph:
    def __init__(self, subgraph: dict = None):
        self._subgraphs = {} if not subgraph else subgraph
        self.edges = []
        self.rough_graph = None

    @property
    def subgraphs(self):
        return self._subgraphs

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self._subgraphs))
            return [self._subgraphs[index] for index in range(start, stop, step)]
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
            return None
        return subg[key]

    def set_node(self, subgraph, key, value):
        if subgraph not in self._subgraphs:
            self._subgraphs[subgraph] = SubGraph()
        self._subgraphs[subgraph][key] = value

    def copy(self):
        return self.__class__(deepcopy(self._subgraphs))

    def __iter__(self):
        yield from self._subgraphs.keys()

    def __len__(self):
        return sum(map(len, self._subgraphs.values()))


class SubGraph:  # Glorified dictionary bruh
    def __init__(self):
        self.__nodes = {}

    def __getitem__(self, key: int):
        if key in self.__nodes:
            return self.__nodes[key]
        return None

    def __setitem__(self, key: int, value: Node):
        if not isinstance(key, int):
            raise TypeError("Key must be an integer")
        if not isinstance(value, Node):
            raise TypeError("Value must be a Node")
        self.__nodes[key] = value

    def __delitem__(self, key: int):
        del self.__nodes[key]

    def __iter__(self):
        yield from self.__nodes

    def items(self):
        return self.__nodes.items()

    def values(self):
        return self.__nodes.values()

    def __len__(self):
        return len(self.__nodes)


class RoughGraph(Graph):
    def add_rough_node(self, node_id: int, node: Node):
        """Create node and connect it to all nodes in subgraph

        Args:
            node_id (int): id
            node (Node): node object
        """
        if self._subgraphs[0][node_id] is not None:
            return
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
