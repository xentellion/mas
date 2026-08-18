# import asyncio
import functools
import logging
from copy import deepcopy
from multiprocessing import Process, Manager
from queue import PriorityQueue
from enum import Enum

from numpy import ceil
from shapely import LineString, MultiPolygon, Point, Polygon

from app.models.graph import Node, Graph, SubGraph, RoughGraph
from app.utils import execution_timer


SENTINEL = "SENTINEL"


class HeuristicsDistance(Enum):
    MANHATTAN = 0
    EUCLID = 1


class Pathfinder:
    @staticmethod
    @execution_timer("Path search")
    def plot_path(
        graph: Graph,
        point_a: int,
        point_b: int,
        heuristic=HeuristicsDistance.MANHATTAN,
    ):
        if point_a == point_b:
            logging.warning("Searching path for a same node")
            return []
        # Find and check points
        starting_node = graph.get_node(point_a)
        if starting_node is None:
            logging.error("Starting point not in graph")
            return []
        target_node = graph.get_node(point_b)
        if target_node is None:
            logging.error("Target point not in graph")
            return []
        # if different - consult rough_graph
        if target_node.subgraph != starting_node.subgraph:
            if not graph.rough_graph:
                logging.error("No rough graph to navigate")
                return []
            graph.rough_graph.add_rough_node(point_a, starting_node)
            graph.rough_graph.add_rough_node(point_b, target_node)
            rough_path = Pathfinder.search_path(
                graph.rough_graph,
                point_a,
                point_b,
                target_node,
                heuristic,
            )
            # return rough_path
            rough_path = [
                (rough_path[idx], rough_path[idx + 1])
                for idx in range(0, len(rough_path) - 1, 2)
            ]

            path = [point_a]
            for idx, p in enumerate(rough_path[::-1]):
                e_n = graph.get_node(p[1])
                path += Pathfinder.search_path(
                    graph,
                    p[0],
                    p[1],
                    e_n,
                    heuristic,
                )
        else:
            path = Pathfinder.search_path(graph, point_a, point_b, target_node)[::-1]
        logging.debug("Found path in %s steps", len(path))
        return path

    @staticmethod
    def search_path(
        graph: Graph,
        point_a: int,
        point_b: int,
        target_node: Node,
        heuristic_distance: HeuristicsDistance = HeuristicsDistance.MANHATTAN,
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
                    + Pathfinder.heuristic(
                        graph.get_node(node), target_node, heuristic_distance
                    )
                )
                if node not in weight or new_weight < weight[node]:
                    weight[node] = new_weight
                    search_border.put(node, new_weight)
                    visited[node] = current_node

        if not path_found:
            logging.warning("No path found")
            return []

        current_node = point_b
        path = [point_b]
        while current_node != point_a:
            current_node = visited[current_node]
            path.append(current_node)

        return path

    @staticmethod
    def heuristic(
        point_a: Node,
        point_b: Node,
        distance: HeuristicsDistance = HeuristicsDistance.MANHATTAN,
    ):
        dist = None
        if isinstance(point_a, tuple):
            point_a = point_a[1]
        match distance:
            case HeuristicsDistance.MANHATTAN:
                # manhattan distance since we are using a grid
                # Not as natural as euclid but screw you
                # I ain't got time to calculate hundreds of sqrts
                dist = abs(point_a.x - point_a.y) + abs(point_b.y - point_b.y)
            case HeuristicsDistance.EUCLID:
                # shapely in-build euclidean (holy shit it's so much slower)
                dist = point_a.point.distance(point_b.point)
        return dist

    @execution_timer("Create node grid")
    @staticmethod
    def create_node_grid(area, step=0.25):
        if isinstance(area, Polygon):
            points = [Pathfinder.get_nodes_coordinates(area, step)]
        elif isinstance(area, MultiPolygon):
            points = [Pathfinder.get_nodes_coordinates(a, step) for a in area.geoms]
        else:
            logging.error("Cannot create node grid")
            return
        return points

    @staticmethod
    def get_nodes_coordinates(area: Polygon, step=0.25):
        x_min, y_min, x_max, y_max = area.bounds
        n_spacing_x = int(ceil((x_max - x_min) / step))  # number of points on X
        n_spacing_y = int(ceil((y_max - y_min) / step))
        points = (
            Point(x_min + x * step, y_min + y * step)
            for y in range(n_spacing_y)
            for x in range(n_spacing_x)
        )
        return list(
            filter(
                lambda z: area.contains(z) and z.distance(area.boundary) > 1e-2,
                points,
            )
        )

    @staticmethod
    @execution_timer("Connecting nodes")
    def construct_edges(area, nodes_clusters, step=0.25):
        graph = Graph()

        shift = 0

        for subgraph_id, sg in enumerate(nodes_clusters):
            for node_id, node in enumerate(sg):
                graph.set_node(subgraph_id, node_id + shift, Node(node, subgraph_id))
            shift += len(sg)
        edges = Manager().Queue()
        processes = [
            Process(
                target=Pathfinder.process_subgraph, args=(area, sg, graph, step, edges)
            )
            for sg in graph
        ]
        for p in processes:
            p.start()
        for p in processes:
            p.join()
            for x in iter(edges.get, SENTINEL):
                graph.edges.append(x[0])
                for node in x[2]:
                    for con in node["connections"]:
                        graph[x[1]][node["id"]].point_neighbors[con] = step
                        graph[x[1]][con].point_neighbors[node["id"]] = step
        return graph

    @execution_timer("Placing interactables")
    @staticmethod
    def create_interactables(flats, graph):
        mapping = {}
        interactables = {}
        for idx, room in enumerate(flats[1:]):
            if not room.interactables:
                continue
            for inter in room.interactables:
                new_points = []
                for point_type in (inter.inlet_point, inter.outlet_point):
                    batch = []
                    for p in point_type:
                        pt = Node(p, idx)
                        points = sorted(
                            graph[idx].items(),
                            key=functools.partial(
                                Pathfinder.heuristic,
                                point_b=pt,
                                distance=HeuristicsDistance.EUCLID,
                            ),
                        )
                        mapping[points[0][0]] = inter.name
                        batch.append(points[0])
                    new_points.append(batch)
                inter.reposition_points(*new_points)
                interactables[inter.name] = inter
        return interactables, mapping

    @execution_timer("Building rough graph")
    @staticmethod
    def construct_rough_graph(graph, extra_connections, step=0.25):
        rough_graph = RoughGraph()
        rough_graph[0] = SubGraph()
        if not extra_connections:
            logging.info("No rough graph on the map")
            return None
        for c in extra_connections:
            for node in c:
                # Fuck python constant linking
                rough_graph[0][node] = deepcopy(graph.get_node(node))
        # holy shit it is so bad
        for c in extra_connections:
            rough_graph.get_node(c[0]).point_neighbors = {c[1]: step}
            rough_graph.get_node(c[1]).point_neighbors = {c[0]: step}

        def comparator(x, y):
            nonlocal rough_graph
            return rough_graph.get_node(x).subgraph == y

        # Even worse
        for idx in graph.subgraphs:
            close_by = tuple(
                filter(
                    functools.partial(comparator, y=idx),
                    (x for x in rough_graph[0]),
                )
            )
            for node in close_by:
                this_node = rough_graph.get_node(node)
                rough_graph.get_node(node).point_neighbors.update(
                    {
                        x: this_node.point.distance(rough_graph.get_node(x).point)
                        for x in close_by
                        if x != node
                    }
                )

        return rough_graph

    @staticmethod
    def process_subgraph(area, sg, graph, step, result_queue):
        lines = []
        regraph = []
        shift = sum(len(x) for x in graph[:sg])
        for node_id in graph[sg]:
            nearest_points = []
            this_point = graph.get_node(node_id)
            for i in range(node_id + 1 - shift, len(graph[sg]) + shift):
                near_point = graph.get_node(i)
                dx = near_point.x - this_point.x
                dy = near_point.y - this_point.y
                if dx > step or dy > step:
                    continue
                if (dx == step and dy == 0) or (dy == step and dx == 0):
                    nearest_points.append((i, near_point))
                    if len(nearest_points) >= 2:
                        break
            if nearest_points:
                connected = filter(
                    lambda z: not z[1].intersects(area.geoms[sg].boundary),
                    (
                        (x, LineString([this_point.point, y.point]))
                        for x, y in nearest_points
                    ),
                )
                transposed = list(zip(*connected))
                if not transposed:
                    continue
                regraph.append({"id": node_id, "connections": transposed[0]})
                # for node in transposed[0]:
                #     graph[sg][node_id].point_neighbors[node] = step
                #     graph[sg][node].point_neighbors[node_id] = step
                lines += transposed[1]
        result_queue.put((lines, sg, regraph))
        result_queue.put(SENTINEL)
        print(f"Area_{sg + 1} complete")
