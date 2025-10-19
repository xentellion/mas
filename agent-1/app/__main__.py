"""starting script"""

import os
import json
import time
import logging

from time import sleep

import matplotlib.pyplot as plt

from model import agent_task, interactable
from model.agent import Agent, State
from model.environment import AreaRender
from model.plane import Plane
from model.prepared_items import PreparedPlane, PreparedAgent

TPS = 1 / float(os.environ["TPS"])
logging.basicConfig(
    level=logging.INFO,
    filename="py_log.log",
    filemode="a+",
    format="%(asctime)s:%(levelname)s:%(message)s",
)


def load_prompts(path="data/prompt.json"):
    with open(path, "r", encoding="UTF-8") as f:
        try:
            data = json.load(f)
        except FileNotFoundError:
            logging.error("Failed to load prompts")
            return None
        for k, v in data.items():
            os.environ[str(k).upper()] = str(v)


def main():
    """main"""
    logging.info("\n--------------Initializing--------------")
    load_prompts()
    step = 1
    ren = AreaRender(step, False)
    agents = []
    # planes = []

    prepared_agents = [
        PreparedAgent(
            agent=Agent("agent_departing", os.environ["PROMPT_DEPARTING"]),
            flight="plane_a",
            spawn_point="entrance",
            spawn_time=0,
        ),
        PreparedPlane(
            plane=Plane("plane_d", "gate_1", 1, None, False),
            spawn_time=0,
        ),
        PreparedPlane(
            plane=Plane(
                "plane_a",
                "gate_2",
                1,
                None,
                True,
                [
                    Agent("agent_arriving", os.environ["PROMPT_ARRIVING"]),
                ],
            ),
            spawn_time=0,
        ),
    ]

    plt.show()
    sleep(2)

    tick_count = 0

    while True:
        for loaded in prepared_agents.copy():
            if loaded.spawn_time > tick_count:
                break
            if isinstance(loaded, PreparedPlane):
                ren.interactables[loaded.plane.gate].add_plane(loaded.plane)
            elif isinstance(loaded, PreparedAgent):
                ren.interactables[loaded.spawn_point].add_new_agent(
                    loaded.agent, ren.graph, loaded.flight, ""
                )
            prepared_agents.remove(loaded)

        prepared_agents.sort(key=lambda x: x.spawn_time)

        for point in ren.interactables.values():
            if isinstance(point, (interactable.Entrance, interactable.Gate)):
                new_ag = point.spawn_agent(ren.graph, ren.interactables, step)
                if new_ag is not None:
                    ren.ax.add_patch(new_ag.ui_object)
                    agents.append(new_ag)

        for a in agents:
            new_pos = a.tick(ren.graph, ren.interactables)
            if new_pos is None:
                a.change_task(ren.graph)
                if a.current_task is None and a.state is State.WALKING:
                    if a.position in ren.interactables_mapping:
                        inter = ren.interactables[ren.interactables_mapping[a.position]]
                        a.add_task(inter.get_task(a))
            else:
                if isinstance(a.current_task, agent_task.WalkingTask):
                    a.move(ren.graph.get_node(new_pos).point.xy, new_pos)

        agents = [x for x in agents if x.state is not State.COMPLETE]

        ren.fig.canvas.draw()
        ren.fig.canvas.flush_events()
        tick_count += 1
        time.sleep(TPS - (time.time() % TPS))
    plt.show(block=True)


if __name__ == "__main__":
    main()
