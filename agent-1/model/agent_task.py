import random

from extras import State
from node import Graph
from pathfinder import Pathfinder


class AgentTask:
    state = None
    priority = False

    def tick(self):
        raise NotImplementedError("Tick action not implemented")

    def setup(self, *args, **kwargs):
        pass


class WalkingTask(AgentTask):
    def __init__(self, dest: str, interactables):
        self.dest = random.choice(interactables[dest].outlet_point) if dest is not None else None
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
        self.__max_time = time
        self.time = time
        self.state = State.PERFORMING

    def tick(self):
        if self.time <= 0:
            self.time = self.__max_time
            print("done")
            return None
        self.time -= 1
        return True


class CompletionTask(AgentTask):
    def __init__(self):
        self.state = State.COMPLETE

    def tick(self):
        pass


class WaitingTask(AgentTask):
    def __init__(self):
        self.state = State.IDLE

    def tick(self):
        pass
