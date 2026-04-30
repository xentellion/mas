"""Agent"""

import datetime
import logging
import os

from collections import deque, Counter
import uuid
import json

import requests
import asyncio
import aiohttp

from . import agent_task
from app.models.graph import Graph
from app.utils import State
from app.core.constants import LOG_PROMPTS


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
            return None
        status = self.__current_task.tick()
        if status is None:
            if self.__current_task.status is not None:
                self.status.append(self.__current_task.status)
            self.__current_task = None
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
            prompt = self.__prompt.format(
                ". ".join(self.status + [os.environ["PROMPT_END"]])
            )
            logging.info("%s -> %s", self.name, prompt)
            # print(os.getenv("LLM_SELECTED"))
            path = self.get_path(prompt=prompt)
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

    def get_path(self, prompt):
        result = asyncio.run(self.send_request_async(prompt))
        if not result:
            return None
        if len(result) == 1:
            return json.loads(result[0])["response"]
        data = sorted(dict(Counter(result)).items(), key=lambda x: x[1])
        return json.loads(data[0][0])["response"]

    async def send_request_async(self, prompt: str):
        url = os.getenv("LLM")
        json = {
            "prompt": prompt,
            "model": os.getenv("LLM_SELECTED"),
        }
        instances = int(os.getenv("ACTIVE_LLMS"))

        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch(session, url, json) for _ in range(instances)]
            statuses = await asyncio.gather(*tasks)
            return [x.decode() for x in statuses]

    async def fetch(self, session: aiohttp.ClientSession, url: str, json: dict):
        async with session.post(url=url, json=json) as response:
            return await response.read()

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
        #     return self.__current_task.dest_name

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
