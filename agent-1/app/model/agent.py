"""Agent"""

import logging
import os


from collections import deque
import uuid

import matplotlib.pyplot as plt
import requests

from model import agent_task
from model.extras import State
from model.graph import Graph


class Agent:
    """Describes active agent, capable of interacting with the environment

    Args:
        name (str): agent name
        prompt (str): LLM prompt, used to describe the agent
    """

    def __init__(self, name: str, prompt: str):
        self.id = uuid.uuid4()
        self.name = name
        self.__ui_object = plt.Circle(
            (0, 0),
            color="red",
            zorder=10000,
            visible=False,
        )
        self.__current_task = None
        self.tasks = deque()
        self.position = None
        self.state = State.IDLE

        self.__prompt = prompt
        self.status = []

    @property
    def current_task(self) -> agent_task.AgentTask:
        """Current agent task"""
        return self.__current_task

    @property
    def ui_object(self) -> plt.Circle:
        """Agent matplotlib ui object"""
        return self.__ui_object

    def tick(self, graph: Graph, interactables: dict):
        """Updates agent tasks status

        Args:
            graph (Graph): walkable area graph
            interactables (dict[str, Interactable]): list of interactable objects

        Returns:
            _type_: Current status info or None
        """
        if self.__current_task is None:
            if not self.tasks:
                self.request_task(graph, interactables)
            self.change_task(graph)
        status = self.__current_task.tick()
        if status is None:
            self.__current_task = None
            self.change_task(graph)
            return None
        return status

    def request_task(self, graph, interactables):
        """Send request to LLM on next point of interaction

        Args:
            graph (Graph): walkable area graph
            interactables (dict[str, Interactable]): list of interactable objects
        """
        if self.__current_task is not None:
            self.tasks.appendleft(self.__current_task)
            self.__current_task = None
        try:
            prompt = self.__prompt.format(" ".join(self.status))
            path = requests.post(
                os.getenv("LLM"),
                params={"prompt": prompt},
                timeout=5,
            ).json()["response"]
        except requests.HTTPError as e:
            logging.error(e)
            path = None
        print(f"{self.name} -> {path}")
        task = agent_task.WalkingTask(path, interactables)
        task.setup(self.position, graph)
        self.add_task(task, graph)

    def add_task(self, task: agent_task.AgentTask, graph: Graph):
        """Add new task to the list of available tasks

        Args:
            task (agent_task.AgentTask): new task
            graph (Graph): walkable area graph
        """
        if task is None:
            return
        if not self.tasks:
            if isinstance(task, agent_task.WalkingTask):
                task.setup(self.position, graph)
            self.__current_task = task
        if task.priority:
            self.tasks.appendleft(task)
        else:
            self.tasks.append(task)

    def clear_tasks(self):
        """Delete all agent tasks"""
        self.tasks = deque()

    def change_task(self, graph):
        """Clear current task and puul a new one from the list of available tasks

        Args:
            graph (Graph): walkable area graph
        """
        if not self.tasks:
            return
        self.__current_task = self.tasks.popleft()
        self.state = self.__current_task.state
        self.__ui_object.set_visible(True)
        if isinstance(self.__current_task, agent_task.WalkingTask):
            self.__current_task.setup(self.position, graph)

    def move(self, point: tuple[int], index: int):
        """Move agent to the set point in graph

        Args:
            point (tuple[int]): new coordinates
            index (int): target node index
        """
        self.position = index
        self.__ui_object.set_center(point)

    def set_visible(self, visibility: bool = True):
        """Set visibility of agent mark on a plan

        Args:
            visibility (bool, optional): True if visible. Defaults to True.
        """
        self.__ui_object.set_visible(visibility)

    def remove_token(self):
        """Delete visible token"""
        self.__ui_object.remove()
