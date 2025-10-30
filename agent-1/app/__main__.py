"""starting script"""

import os
import sys
import json
import time
import logging

# from time import sleep

# import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout
from PyQt6 import uic


from model import agent_task, interactable
from model.agent import Agent, State
from model.extras import StartPrompt
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

STEP = 1


def load_prompts(path="data/prompt.json"):
    with open(path, "r", encoding="UTF-8") as f:
        try:
            data = json.load(f)
        except FileNotFoundError:
            logging.error("Failed to load prompts")
            return None
        for k, v in data.items():
            os.environ[str(k).upper()] = str(v)


def start_simulation(step):
    load_prompts()
    ren = AreaRender(step, False)
    # planes = []
    return ren


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("main.ui", self)

        self.ren = start_simulation(STEP)

        toolbar = NavigationToolbar(self.ren, self)

        layout = QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(self.ren)

        self.plt_window.setLayout(layout)
        self.start_button.clicked.connect(self.start_sim)

    def start_sim(self):
        self.main(self.ren, STEP)

    def load_starting_positions(self, path):
        prepared_agents = []
        with open(path, "r", encoding="UTF-8") as f:
            data = json.load(f)
            for plane in data["planes"]:
                spawn_time = plane["spawn_time"]
                del plane["spawn_time"]

                passengers = []
                for psng in plane["passengers"]:
                    passengers.append(
                        Agent(
                            psng["name"],
                            os.environ[StartPrompt(int(psng["initial_state"])).name],
                        )
                    )
                plane["passengers"] = passengers

                prepared_agents.append(
                    PreparedPlane(plane=Plane(**plane), spawn_time=spawn_time)
                )
            for psng in data["departing_passengers"]:
                psng["agent"] = Agent(
                    psng["agent"]["name"],
                    os.environ[StartPrompt(int(psng["agent"]["initial_state"])).name],
                )
                prepared_agents.append(PreparedAgent(**psng))
        return prepared_agents

    def main(self, ren, step):
        agents: list[Agent] = []
        prepared_agents = self.load_starting_positions("data/init_setup.json")
        tick_count = 0

        while True:
            self.plt_window.update()
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
                            inter = ren.interactables[
                                ren.interactables_mapping[a.position]
                            ]
                            a.add_task(inter.get_task(a))
                else:
                    if isinstance(a.current_task, agent_task.WalkingTask):
                        a.move(ren.graph.get_node(new_pos).point.xy, new_pos)

            agents = [x for x in agents if x.state is not State.COMPLETE]

            ren.fig.canvas.draw()
            ren.fig.canvas.flush_events()
            tick_count += 1
            time.sleep(TPS - (time.time() % TPS))


if __name__ == "__main__":
    logging.info("\n--------------Initializing--------------")
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
