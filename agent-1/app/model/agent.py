"""Agent"""

import datetime
import logging
import os

from collections import deque
import uuid

import requests

from model import agent_task
from model.extras import State
from model.graph import Graph


LOG_PROMPTS = os.getenv("LOG_PROMPTS") == "True"


class Agent:
    """Describes active agent, capable of interacting with the environment

    Args:
        name (str): agent name
        prompt (str): LLM prompt, used to describe the agent
    """

    def __init__(self, name: str, prompt: str):
        self.id = uuid.uuid4()
        self.name = name
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

    def tick(self, graph: Graph, interactables: dict):
        """Updates agent tasks status

        Args:
            graph (Graph): walkable area graph
            interactables (dict[str, Interactable]): list of interactable objects

        Returns:
            [bool, None]: Current status info or None
        """
        if self.__current_task is None:
            if not self.tasks:
                self.request_task(graph, interactables)
            self.change_task(graph)
        status = self.__current_task.tick()
        if status is None:
            if self.__current_task.status is not None:
                self.status.append(self.__current_task.status)
            self.__current_task = None
            self.change_task(graph)
            return None
        return status

    def request_task(
        self,
        graph,
        interactables,
    ):
        """Send request to LLM on next point of interaction

        Args:
            graph (Graph): walkable area graph
            interactables (dict[str, Interactable]): list of interactable objects
        """
        if self.__current_task is not None:
            self.tasks.appendleft(self.__current_task)
            self.__current_task = None
        tm = datetime.datetime.now()
        try:
            prompt = self.__prompt.format(". ".join(self.status))
            logging.info("%s -> %s", self.name, prompt)
            # print(os.getenv("LLM_SELECTED"))
            path = requests.post(
                os.getenv("LLM"),
                params={
                    "prompt": prompt,
                    "model": os.getenv("LLM_SELECTED"),
                },
                timeout=120,
            ).json()["response"]
        except requests.HTTPError as e:
            logging.error(e)
            path = None
        except Exception as e:
            logging.error(e)
            return
        if LOG_PROMPTS is True:
            logging.info(
                "%s -> [%s] in %s",
                self.name,
                path,
                datetime.datetime.now() - tm,
            )
        # Agent only requests walking tasks as other tasks are just
        # sitting around with different flavors
        task = agent_task.WalkingTask(path.lower().strip(), interactables)
        task.setup(self.position, graph)
        self.add_task(task)

    def add_task(self, task: agent_task.AgentTask):
        """Add new task to the list of available tasks

        Args:
            task (agent_task.AgentTask): new task
        """
        if task is None:
            return
        elif task.priority:
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
            return None
        self.__current_task = self.tasks.popleft()
        self.state = self.__current_task.state
        if isinstance(self.__current_task, agent_task.WalkingTask):
            self.__current_task.setup(self.position, graph)
        logging.debug(
            "Agent %s changed task to <<%s>>",
            self.name,
            self.__current_task.__class__.__name__,
        )

    def move(self, point: tuple[int], index: int):
        """Move agent to the set point in graph

        Args:
            point (tuple[int]): new coordinates
            index (int): target node index
        """
        self.position = index

    def reset_status(self, is_departing: bool = True, extra_message=""):
        self.__prompt = os.environ[
            "PROMPT_DEPARTING" if is_departing else "PROMPT_ARRIVING"
        ]
        self.status = [extra_message]
