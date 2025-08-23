import random

from extras import State
from node import Graph
from pathfinder import Pathfinder


class AgentTask:
    state = None

    def tick(self):
        raise NotImplementedError("Tick action not implemented")


class WalkingTask(AgentTask):
    def __init__(self, dest: str, interactables):
        self.dest = random.choice(interactables[dest].outlet_point)
        self.path = None
        self.state = State.WALKING

    def setup(self, source, graph: Graph):
        self.path = Pathfinder.plot_path(
            graph,
            source,
            self.dest,
        )

    def tick(self):
        if not self.path:
            return None
        return self.path.pop(0)


class InteractingTask(AgentTask):
    def __init__(self, time: int):
        self.time = time
        self.state = State.PERFORMING

    def tick(self):
        if self.time <= 0:
            return None
        self.time -= 1
