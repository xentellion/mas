import logging

from extras import execution_timer
from node import Node
from queue import PriorityQueue


class Pathfinder:
    @staticmethod
    @execution_timer("Path search")
    def plot_path(graph, point_a: int, point_b: int):
        if point_a not in graph:
            logging.error("Starting point not in graph")
            return list()
        if point_b not in graph:
            logging.error("Target point not in graph")
            return list()

        current_node = None
        target_node = graph[point_b]
        weight = {point_a: 0}
        visited = {point_a: 0}

        search_border = PriorityQueue()
        search_border.put(point_a, 0)

        found = False

        while not (search_border.empty() or found):
            current_node = search_border.get()
            if current_node == point_b:
                found = True
                break
            for node, edge in graph[current_node].point_neighbors.items():
                new_weight = (
                    weight[current_node]
                    + edge
                    + Pathfinder.heuristic(graph[node], target_node)
                )
                if node not in weight or new_weight < weight[node]:
                    weight[node] = new_weight
                    search_border.put(node, new_weight)
                    visited[node] = current_node

        if not found:
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
        return abs(point_a.x - point_a.y) + abs(point_b.y - point_b.y)
        # shapely in-build euclidean (holy shit it's so much slower)
        # return point_a.point.distance(point_b.point)
