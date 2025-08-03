from node import Node
from queue import PriorityQueue
from aux import achtung_print


class Pathfinder:
    @staticmethod
    def plot_path(graph, point_a: int, point_b: int):
        if point_a not in graph:
            achtung_print("Starting point not in graph")
            return list()
        if point_b not in graph:
            achtung_print("Target point not in graph")
            return list()

        current_node = None
        target_node = graph[point_b]
        weight = {point_a: 0}
        visited = {point_a: 0}

        search_border = PriorityQueue()
        search_border.put(point_a, 0)

        found = False

        while not search_border.empty() or not found:
            current_node = search_border.get()
            if current_node == point_b:
                found = True
                break
            for node in graph[current_node].point_neighbors:
                new_weight = (
                    weight[current_node]
                    + graph[node].weight
                    + Pathfinder.heuristic(graph[node], target_node)
                )
                if node not in weight or new_weight < weight[node]:
                    weight[node] = new_weight
                    search_border.put(node, new_weight)
                    visited[node] = current_node

        if not found:
            achtung_print("No path found")
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
        return abs(point_a.x - point_a.y) + abs(point_b.y - point_b.y)
        # shapely in-build euclidean (holy shit so much slower)
        # return point_a.point.distance(point_b.point)
