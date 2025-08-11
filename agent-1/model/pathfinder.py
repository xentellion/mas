import logging

from extras import execution_timer
from node import Node, Graph, RoughGraph
from queue import PriorityQueue


class Pathfinder:
    @staticmethod
    @execution_timer("Path search")
    def plot_path(
        graph: Graph, point_a: int, point_b: int, rough_graph: RoughGraph = None
    ):
        if point_a == point_b:
            logging.warn("Searching path for a same node")
            return list()
        # Find and check points
        starting_node = graph.get_node(point_a)
        if starting_node is None:
            logging.error("Starting point not in graph")
            return list()
        target_node = graph.get_node(point_b)
        if target_node is None:
            logging.error("Target point not in graph")
            return list()
        # if different - consult rough_graph
        if target_node.subgraph != starting_node.subgraph:
            if not rough_graph:
                logging.error("No rough graph to navigate")
                return list()
            rough_graph.add_rough_node(point_a, starting_node)
            rough_graph.add_rough_node(point_b, target_node)
            rough_path = Pathfinder.search_one_path(
                rough_graph, point_a, point_b, starting_node, target_node
            )
            # return rough_path
            rough_path = [
                (rough_path[idx], rough_path[idx + 1])
                for idx in range(len(rough_path) - 1)
            ]

            path = []
            for idx, p in enumerate(rough_path[::-1]):
                # Uneven nodes are trasnmissions between points
                if idx % 2 == 1:
                    continue
                s_n = graph.get_node(p[0])
                e_n = graph.get_node(p[1])
                path += Pathfinder.search_one_path(graph, p[0], p[1], s_n, e_n)
        else:
            path = Pathfinder.search_one_path(
                graph, point_a, point_b, starting_node, target_node
            )
        logging.info(f"Found path in {len(path)} steps")
        return path

    @staticmethod
    def search_one_path(
        graph: Graph,
        point_a: int,
        point_b: int,
        starting_node: Node,
        target_node: Node,
    ):
        current_node = None
        weight = {point_a: 0}
        visited = {point_a: 0}

        search_border = PriorityQueue()
        search_border.put(point_a, 0)

        path_found = False
        while not (search_border.empty() or path_found):
            current_node = search_border.get()
            current_node_object = graph.get_node(current_node)
            if current_node == point_b:
                path_found = True
                break
            for node, edge in current_node_object.point_neighbors.items():
                new_weight = (
                    weight[current_node]
                    + edge
                    + Pathfinder.heuristic(graph.get_node(node), target_node)
                )
                if node not in weight or new_weight < weight[node]:
                    weight[node] = new_weight
                    search_border.put(node, new_weight)
                    visited[node] = current_node

        if not path_found:
            logging.warning("No path found")
            return list()

        current_node = point_b
        path = [point_b]
        while current_node != point_a:
            current_node = visited[current_node]
            path.append(current_node)

        return path

    @staticmethod
    def heuristic(point_a: Node, point_b: Node):
        # manhattan distance since we are using a grid
        # Not as natural as euclid but screw you
        # I ain't got time to calculate hundreds of sqrts
        # return abs(point_a.x - point_a.y) + abs(point_b.y - point_b.y)
        # shapely in-build euclidean (holy shit it's so much slower)
        return point_a.point.distance(point_b.point)
