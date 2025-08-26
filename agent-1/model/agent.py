import logging

# from queue import PriorityQueue
from collections import deque
import uuid

import matplotlib.pyplot as plt
import requests

import agent_task
from extras import State

# from node import Graph


class Agent:
    def __init__(self, name, step):
        self.id = uuid.uuid4()
        self.name = name
        self.__ui_object = plt.Circle(
            (0, 0),
            step * 0.4,
            color="red",
            zorder=10000,
            visible=False,
        )
        self.__current_task = None
        self.tasks = deque()
        self.position = None
        self.state = State.IDLE

    @property
    def current_task(self):
        return self.__current_task

    @property
    def ui_object(self):
        return self.__ui_object

    def tick(self, graph, interactables):
        if self.__current_task is None:
            res = self.change_task(graph)
            if res is None:
                self.request_task(graph, interactables)
                return
        status = self.__current_task.tick()
        if status is None:
            self.change_task(graph)
            return None
        return status

    def request_task(self, graph, interactables):
        if self.__current_task is not None:
            self.tasks.appendleft(self.__current_task)
            self.__current_task = None
        # insert propmt request to LLM based on agent state
        # %TODO remove temporary hardcoded data
        if self.name == "agent_1":
            t_1 = agent_task.WalkingTask("Exit", interactables)
            # t_1.setup(self.position, graph)
            self.add_task(t_1, graph)
        elif self.name == "agent_2":
            t_1 = agent_task.WalkingTask("Gate_out", interactables)
            # t_1.setup(self.position, graph)
            self.add_task(t_1, graph)

        # this shit ^

    def add_task(self, task: agent_task.AgentTask, graph):
        if task is None:
            return
        if not self.tasks:
            task.setup(self.position, graph)
            self.__current_task = task
        if task.priority:
            self.tasks.appendleft(task)
        else:
            self.tasks.append(task)

    def clear_tasks(self):
        self.tasks = deque()

    def change_task(self, graph):
        if not self.tasks:
            return None
        self.__current_task = self.tasks.popleft()
        if self.__current_task is None:
            return None
        self.state = self.__current_task.state
        self.__ui_object.set_visible(True)
        if isinstance(self.__current_task, agent_task.WalkingTask):
            self.__current_task.setup(self.position, graph)
        if isinstance(self.__current_task, agent_task.WaitingTask):
            # self.__current_task.setup(self.position, graph)
            self.__ui_object.set_visible(False)
        return True

    def move(self, point: tuple[int], index):
        self.position = index
        self.__ui_object.set_center(point)

    def set_visible(self, visibility: bool = True):
        self.__ui_object.set_visible(visibility)

    def remove_token(self):
        self.__ui_object.remove()
