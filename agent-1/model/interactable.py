import logging
import random

from shapely import Point, Polygon
from shapely.ops import unary_union

import agent_task


class Interactable:
    def __init__(self, name, inlet_point, outlet_point, area, max_occupy, scale, step):
        self.name = name
        self.__scale = scale
        self.__step = step

        self.__inlet_point = None
        self.__outlet_point = None
        self.__area = None

        self.inlet_point = inlet_point
        self.outlet_point = outlet_point
        self.area = area

        self.max_occupy = max_occupy
        self.current_occupy = 0

        self._task = None

    @property
    def inlet_point(self):
        return self.__inlet_point

    @inlet_point.setter
    def inlet_point(self, value):
        self.__inlet_point = [
            Point(gate[0] * self.__scale, gate[1] * self.__scale) for gate in value
        ]

    @property
    def outlet_point(self):
        return self.__outlet_point

    @outlet_point.setter
    def outlet_point(self, value):
        if value is None:
            self.__outlet_point = self.__inlet_point
        else:
            self.__outlet_point = [Point(*gate) for gate in value]

    @property
    def area(self):
        if self.__area is not None:
            return self.__area

    @area.setter
    def area(self, value):
        if value is None:
            self.__area = None
        else:
            areas = [Polygon(tuple((x[0, x[1]]) for x in area)) for area in value]
            self.__area = unary_union(areas)

    def reposition_points(self, inlets, outlets):
        self.__inlet_point = list(zip(*inlets))[0]
        self.__outlet_point = list(zip(*outlets))[0]
        areas = []
        for point in inlets:
            x, y = point[1].x, point[1].y
            half_step = self.__step / 2
            x_m, x_l = x + half_step, x - half_step
            y_m, y_l = y + half_step, y - half_step
            # square around the point
            areas.append(
                Polygon(((x_m, y_m), (x_m, y_l), (x_l, y_l), (x_l, y_m), (x_m, y_m)))
            )
        self.__area = unary_union(areas)

    def interact(self, agent):
        return self._task


class Entrance(Interactable):
    _storage = []

    def add_new_agent(self, agent, graph):
        node = random.choice(self.outlet_point)
        agent.move(graph.get_node(node).point.xy, node)
        self._storage.append(agent)

    def spawn_agent(self, graph, interactables):
        if self._storage:
            agent = self._storage.pop()
            agent.position = random.choice(self.outlet_point)
            agent.set_visible()
            agent.request_task(graph, interactables)
            return agent
        return None


class Exit(Interactable):
    def __init__(self, name, inlet_point, outlet_point, area, max_occupy, scale, step):
        super().__init__(name, inlet_point, outlet_point, area, max_occupy, scale, step)
        self._task = agent_task.CompletionTask()

    # def interact(self):
    #     return self.__task


class Gate(Entrance):
    def __init__(self, name, inlet_point, outlet_point, area, max_occupy, scale, step):
        super().__init__(name, inlet_point, outlet_point, area, max_occupy, scale, step)
        self.__releasing_passengers = None
        self.plane = None

    def interact(self, agent):
        if not self.plane:
            return None
        if self.__releasing_passengers is False:
            self._storage.append(agent)
            if len(self._storage) >= self.plane.volume:
                logging.warning(f"Plane {self.plane.board_number} is full")
                self.__releasing_passengers = None
            return agent_task.CompletionTask()
        elif self.__releasing_passengers is True:
            return agent_task.WaitingTask()

    def add_arriving_plane(self, plane, agents: list):
        self._storage = agents
        self.__releasing_passengers = True
        self.plane = plane

    def add_departing_plane(self, plane):
        self.__releasing_passengers = False
        self.plane = plane

    def spawn_agent(self, *args, **kwargs):
        if not self.__releasing_passengers:
            return None
        if self.plane is not None and not self._storage:
            logging.warning(f"Plane {self.plane.board_number} is empty")
            self.plane = None
            # return None
        return super().spawn_agent(*args, **kwargs)

    def depart(self):
        self._storage = []
        self.is_plane_attached = False
