import logging
import random

from shapely import Point, Polygon
from shapely.ops import unary_union

import model.agent_task as agent_task


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

        self._task: agent_task.AgentTask = None
        self.status = None

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

    def get_task(self, agent):
        return self._task

    # def interact(self, agent):
    #     agent.status.append(self.status)
    #     return self._task


class Entrance(Interactable):
    _storage = []

    def add_new_agent(self, agent, graph, ticket_number=None, ticket_gate=None):
        node = random.choice(self.outlet_point)
        agent.move(graph.get_node(node).point.xy, node)
        if ticket_number is not None:
            agent.status.append(
                f"У тебя есть билет на борт {ticket_number}. Он будет пристыкован к воротам {ticket_gate}"
            )
        else:
            agent.status.append("У тебя нет билета")
        self._storage.append(agent)

    def spawn_agent(self, graph, interactables, step: int, starting_status=None):
        if self._storage:
            agent = self._storage.pop()
            agent.position = random.choice(self.outlet_point)
            agent.ui_object.radius = step * 0.4
            agent.set_visible()
            if starting_status is not None:
                agent.status.append(starting_status)
            agent.request_task(graph, interactables)
            return agent
        return None


class Exit(Interactable):
    def __init__(self, name, inlet_point, outlet_point, area, max_occupy, scale, step):
        super().__init__(name, inlet_point, outlet_point, area, max_occupy, scale, step)
        self._task = agent_task.CompletionTask()


class Gate(Entrance):
    def __init__(self, name, inlet_point, outlet_point, area, max_occupy, scale, step):
        super().__init__(name, inlet_point, outlet_point, area, max_occupy, scale, step)
        self.__releasing_passengers = None
        self.plane = None
        self._task = agent_task.BoardedTask()

    def get_task(self, agent):
        # TODO add ticket check
        if self.__releasing_passengers is False:
            return self._task
        return None

    def add_plane(self, plane):
        if self.plane is not None:
            logging.warning("Trying to dock a plane to an occupied gate")
            return
        self.__releasing_passengers = plane.is_arriving
        self.plane = plane
        self._storage = plane.passengers

    def depart(self):
        self._storage = []
        self.__releasing_passengers = None

    def spawn_agent(self, *args, **kwargs):
        if not self.__releasing_passengers:
            return None
        if self.plane is not None:
            if not self._storage:
                logging.warning("Plane %s is empty", self.plane.name)
                self.plane = None
                return None
            status = f"Ты только что сошел c рейса {self.plane.name}"
            return super().spawn_agent(starting_status=status, *args, **kwargs)


class SecurityCheckpoint(Interactable):
    def __init__(self, name, inlet_point, outlet_point, area, max_occupy, scale, step):
        super().__init__(name, inlet_point, outlet_point, area, max_occupy, scale, step)
        self.status = "Ты уже прошел досмотр"
        self._task = agent_task.InteractingTask(10, self.status)


class BaggageReclaim(Interactable):
    def __init__(self, name, inlet_point, outlet_point, area, max_occupy, scale, step):
        super().__init__(name, inlet_point, outlet_point, area, max_occupy, scale, step)
        self.status = "Ты получил свой багаж"
        self._task = agent_task.InteractingTask(10, self.status)


class RegistrationDesk(Interactable):
    def __init__(self, name, inlet_point, outlet_point, area, max_occupy, scale, step):
        super().__init__(name, inlet_point, outlet_point, area, max_occupy, scale, step)
        self.status = "Ты прошёл регистрацию"
        self._task = agent_task.InteractingTask(10, self.status)
