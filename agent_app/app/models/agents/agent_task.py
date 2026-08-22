"""Contains all the possible necessary actions for agents"""

import logging
import random
from abc import ABC, abstractmethod

from app.core.global_state import GLOBAL_STATE
from app.models.graph import Graph
from app.utils import State


class AgentTask(ABC):
    """Generic task"""

    def __init__(self, status: str = None, priority: bool = False):
        self.state: State = None
        self.priority: bool = priority
        self.status: str = status

    @abstractmethod
    def tick(self):
        """Performs actions on each simulation tick

        Raises:
            NotImplementedError: NotImplementedError
        """
        raise NotImplementedError


class WalkingTask(AgentTask):
    """Creates the path for the agent to the final point; exoires on reaching it

    Args:
        dest (str): name of the point for the agent to walk to
        interactables (dict[str, Interactable]): list of possible interactive points
    """

    def __init__(self, dest: str, status: str = None, priority: bool = False):
        super().__init__(status, priority)
        try:
            # @TODO - proper decision making by LLM
            self.dest = (
                random.choice(GLOBAL_STATE.interactables[dest].outlet_point)
                if dest is not None
                else None
            )
        except KeyError as e:
            logging.error(e)
            self.dest = None
        self.path = None
        self.state = State.WALKING
        self.status = status
        self.dest_name = dest

    def setup(self, source: int, graph: Graph):
        """Rebuilds path based on agent location

        Args:
            source (int): id of target node
            graph (Graph): walkable graph
        """
        from app.core import Pathfinder

        self.path = Pathfinder.plot_path(
            graph,
            source,
            self.dest,
        )

    def tick(self):
        if not self.path:
            return None
        return self.path.pop(0)


class BoardingTask(AgentTask):
    """Task to keep an agent IDLE ob board of a plane until something happens.

    Args:
        AgentTask (_type_): _description_
    """

    def __init__(self, status: str = None, priority: bool = False):
        super().__init__(status, priority)
        self.state = State.BOARDING

    def tick(self):
        return False


class InteractingTask(AgentTask):
    """Task to occupy the point for set amount of time

    Args:
        time (int): time in tics
    """

    def __init__(self, time: int, status: str = None, priority: bool = False):
        super().__init__(status, priority)
        self.__max_time = time
        self.time = time
        self.state = State.PERFORMING
        self.status = status

    def tick(self):
        self.time -= 1
        if self.time <= 0:
            self.time = self.__max_time
            return None
        return True


class CompletionTask(AgentTask):
    """Final task, given to agent on reaching exit or on plane departing"""

    def __init__(self, status: str = None, priority: bool = False):
        super().__init__(status, priority)
        self.state = State.COMPLETE

    def tick(self):
        logging.info("Agent done")
