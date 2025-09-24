import logging

from time import sleep

import matplotlib.pyplot as plt

from model import agent_task, interactable
from model.agent import Agent, State
from model.environment import AreaRender
from model.plane import Plane


logging.basicConfig(
    level=logging.INFO,
    filename="py_log.log",
    filemode="a+",
    format="%(asctime)s:%(levelname)s:%(message)s",
)


def main():
    logging.info("\n--------------Initializing--------------")

    plt.ion()
    step = 1
    ren = AreaRender(step)
    prompts = ren.load_prompts()
    ren.create_area()
    ren.draw_intercatables()

    ren.draw_edges()
    ren.draw_transitions()

    sleep(1)
    agents = []

    plt.show()
    sleep(1)

    agent_1 = Agent("agent_1", prompts.prompt_arriving)
    agent_1.ui_object.radius = step * 0.4
    agent_2 = Agent("agent_2", prompts.prompt_departing)
    agent_2.ui_object.radius = step * 0.4

    plane_1 = Plane("arriver", "1", 1, None)
    plane_2 = Plane("departer", "2", 1, None)

    ren.interactables["Gate_2"].add_arriving_plane(plane_1, [agent_1])
    ren.interactables["Gate_1"].add_departing_plane(plane_2)

    ren.interactables["Entrance"].add_new_agent(agent_2, ren.graph, "2")

    while True:
        for a in agents.copy():
            if a.state is State.COMPLETE:
                a.remove_token()
                agents.remove(a)
            new_pos = a.tick(ren.graph, ren.interactables)
            if new_pos is not None:
                if isinstance(new_pos, bool):
                    continue
                a.move(ren.graph.get_node(new_pos).point.xy, new_pos)
            else:
                if a.position not in ren.interactables_mapping:
                    continue
                if isinstance(a.current_task, agent_task.InteractingTask):
                    a.request_task(ren.graph, ren.interactables)
                inter = ren.interactables[ren.interactables_mapping[a.position]]
                a.add_task(
                    inter.task,
                    ren.graph,
                )
            if a.state == State.WALKING and a.current_task:
                if isinstance(a.current_task, agent_task.WalkingTask):
                    ren.draw_path(a.current_task.path)

        for _, point in ren.interactables.items():
            if isinstance(point, (interactable.Entrance, interactable.Gate)):
                new_ag = point.spawn_agent(ren.graph, ren.interactables)
                if new_ag is not None:
                    ren.ax.add_patch(new_ag.ui_object)
                    agents.append(new_ag)
        ren.fig.canvas.draw()
        ren.fig.canvas.flush_events()
    plt.show(block=True)


if __name__ == "__main__":
    main()
