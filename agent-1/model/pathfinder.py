import shapely.geometry as sg
from node import Node


class Pathfinder:
    @staticmethod
    def plot_path(graph: dict, point_a: int, point_b: int):
        target_node = graph[point_b]
        current_node = graph[point_a]
        previous_node = None

        path = [point_a]

        distances = {
            point_a: Pathfinder.heuristic(current_node, target_node),
        }
        visited = []

        steps = 0
        found = False
        while not found:
            # stop if found the target in neighbours
            if point_b in current_node.point_neighbors:
                found = True
                path.append(point_b)
                continue
            # collect dictionary of bird-fly distances from node to the final point
            for cur_p in current_node.point_neighbors:
                if cur_p not in distances:
                    distances[cur_p] = Pathfinder.heuristic(graph[cur_p], target_node)

            next_step = []
            for x in current_node.point_neighbors:
                if x in visited:
                    continue
                if x in path:
                    delta = len(path) - 1 - path.index(x)
                    if delta > 1:
                        next_step = []
                        # next_step.append((x, distances[x] + len(path[: path.index(x)])))
                        break
                else:
                    next_step.append((x, distances[x] + len(path) * 0.25))
            next_step.sort(key=lambda x: x[1])

            if len(next_step) > 0:
                path.append(next_step[0][0])
            else:
                vis_node = path.pop(-1)
                visited.append(vis_node)

            current_node = graph[path[-1]]
            # print("path", path, "\n\n")

            steps += 1
        print(steps)
        return path
        # return visited

    @staticmethod
    def heuristic(point_a: Node, point_b: Node):
        # manhattan distance
        return abs(point_a.x - point_a.y) + abs(point_b.y - point_b.y)
        # shapely in-build
        # return point_a.point.distance(point_b.point)
