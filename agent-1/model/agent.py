# from queue import PriorityQueue
from collections import deque

import matplotlib.pyplot as plt

from agent_task import AgentTask, WalkingTask, InteractingTask
from extras import State

# from node import Graph


class Agent:
    def __init__(self, step):
        self.ui_object = plt.Circle(
            (0, 0),
            step * 0.4,
            color="red",
            zorder=10000,
            visible=False,
        )
        self.target = None
        self.tasks = deque()
        self.__current_task: AgentTask = None
        self.position = None
        self.state = State.IDLE

    @property
    def current_task(self):
        return self.__current_task

    def add_task(self, task: AgentTask, graph, priority=False):
        if self.__current_task is None:
            task.setup(self.position, graph)
            self.__current_task = task

        elif priority:
            self.tasks.appendleft(self.__current_task)
            self.__current_task = task
        else:
            self.tasks.append(task)

    def clear_tasks(self):
        self.tasks = deque()

    def tick(self, graph):
        if self.__current_task is None:
            if len(self.tasks) == 0:
                # print("Nothing to do")
                self.state = State.COMPLETE
                return
            self.__current_task = self.tasks.pop()
            self.__current_task.setup(self.position, graph)
            self.state = self.__current_task.state

        status = self.__current_task.tick()

        if status is None:
            self.__current_task = None
            return None

        if isinstance(status, int):
            self.position = status
        if isinstance(self.__current_task, WalkingTask):
            if self.state != State.WALKING:
                self.state = State.WALKING
        elif isinstance(self.__current_task, InteractingTask):
            pass
        return status
