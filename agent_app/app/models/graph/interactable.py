import logging
import random
from copy import deepcopy

from shapely import Point, Polygon
from shapely.ops import unary_union

from app.models.agents import agent_task
from app.utils import GateAllowedSize, GateTransition


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


class Entrance(Interactable):
    _storage = []

    def add_new_agent(self, agent, graph, plane_number: str, ticket_gate: str):
        node = random.choice(self.outlet_point)
        agent.move(graph.get_node(node).point.xy, node)
        agent.status.append(
            f"You have a ticket for a plane {plane_number}. It will be at the gate {ticket_gate}"
        )
        # if ticket_number is not None:
        #     agent.status.append(
        #         # f"У тебя есть билет на борт {ticket_number}. Он будет пристыкован к воротам {ticket_gate}"
        #         f"You have a ticket for a plane {ticket_number}. It will be at the gate {ticket_gate}"
        #     )
        # else:
        #     agent.status.append("You have no ticket")
        self._storage.append(agent)

    def spawn_agent(self, graph, step: int, starting_status=None):
        if self._storage:
            agent = self._storage.pop()
            agent.position = random.choice(self.outlet_point)
            if starting_status is not None:
                agent.status.append(starting_status)
            # agent.request_task(graph, interactables)
            return agent
        return None


class Exit(Interactable):
    def __init__(self, name, inlet_point, outlet_point, area, max_occupy, scale, step):
        super().__init__(name, inlet_point, outlet_point, area, max_occupy, scale, step)
        self._task = agent_task.CompletionTask()


class Gate(Interactable):
    def __init__(
        self,
        name,
        inlet_point,
        outlet_point,
        area,
        max_occupy,
        scale,
        step,
        gate_transition: GateTransition = GateTransition.Any,
        gate_size: GateAllowedSize = GateAllowedSize.Any,
    ):
        super().__init__(name, inlet_point, outlet_point, area, max_occupy, scale, step)
        # self.__releasing_passengers = None
        self.plane = None
        self.gate_transition = GateTransition(gate_transition)
        self.gate_size = GateAllowedSize(gate_size)
        self._task = agent_task.BoardingTask()

    def get_task(self, agent):
        if not self.plane:
            return None
        # TODO add ticket check
        if self.plane.is_arriving:
            return None
        if agent.name not in self.plane.expected_passengers:
            logging.warning(f"Passenger {agent.name} tried to board wrong plane")
            return None
        if self.plane.ready_to_depart:
            logging.info(
                f"Plane {self.plane.name} "
                + f"{"can't take more passengers" if not self.plane.is_arriving else "has no more passengers."}"
            )
            return None
        self.plane.add_passenger(agent)
        return self._task

    def add_plane(self, plane):
        if self.plane is not None:
            logging.warning("Trying to dock a plane to an occupied gate")
            return False
        self.plane = plane
        return True

    def depart(self, graph, current_tick):
        if self.plane.passengers:
            data = deepcopy(self.plane.passengers)
            self.plane.passengers = []
            return data
        elif not self.plane.will_turnaround:
            self.plane = None
            return None
        else:
            # @TODO - use on the other side to add again
            return deepcopy(self.plane)

    def spawn_agent(self, graph, step: int, starting_status=None):
        if not self.plane:
            return None
        if not self.plane.is_arriving:
            return None
        if not self.plane.passengers:
            return None
        starting_status = f"You have just got off the plane {self.plane.name}"

        agent = self.plane.pop_passenger()
        agent.position = random.choice(self.outlet_point)
        if starting_status is not None:
            agent.status.append(starting_status)
        # agent.request_task(graph, interactables)
        return agent


class SecurityCheckpoint(Interactable):
    def __init__(self, name, inlet_point, outlet_point, area, max_occupy, scale, step):
        super().__init__(name, inlet_point, outlet_point, area, max_occupy, scale, step)
        self.status = "You have passed the security checkpoint"
        self._task = agent_task.InteractingTask(10, self.status)


class BaggageReclaim(Interactable):
    def __init__(self, name, inlet_point, outlet_point, area, max_occupy, scale, step):
        super().__init__(name, inlet_point, outlet_point, area, max_occupy, scale, step)
        self.status = "You got your luggage"
        self._task = agent_task.InteractingTask(10, self.status)


class RegistrationDesk(Interactable):
    def __init__(self, name, inlet_point, outlet_point, area, max_occupy, scale, step):
        super().__init__(name, inlet_point, outlet_point, area, max_occupy, scale, step)
        self.status = (
            "You passed the check-in and can board your plane whenever possible."
        )
        self._task = agent_task.InteractingTask(10, self.status)
