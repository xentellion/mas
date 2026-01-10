"""starting script"""

import os
import sys
import json
import time
import logging

from copy import deepcopy

# import threading

# from time import sleep
# https://stackoverflow.com/questions/33969053/how-to-pause-play-a-thread-in-pyqt5
# import matplotlib.pyplot as plt
import requests
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QLabel,
)
from PyQt6 import uic
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot

# from PyQt6.QtCore import QThread

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


class WorkerSignals(QObject):
    new_agent = pyqtSignal(Agent)
    new_plane = pyqtSignal(Plane)

    agent_updated = pyqtSignal(Agent)
    plane_updated = pyqtSignal(str)

    agent_removed = pyqtSignal(str)
    plane_removed = pyqtSignal(str)


class SimWorker(QRunnable):
    signals = WorkerSignals()

    def __init__(self, ren: AreaRender):
        super().__init__()
        self.ren = ren
        self.is_paused = False
        self.is_killed = False

    @pyqtSlot()
    def run(self):
        logging.info("Simulation started")
        self.main(self.ren, STEP)

    def load_starting_positions(self, path):
        prepared_agents = []
        prepared_planes = []
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

                prepared_planes.append(
                    PreparedPlane(plane=Plane(**plane), spawn_time=spawn_time)
                )
            for psng in data["departing_passengers"]:
                psng["agent"] = Agent(
                    psng["agent"]["name"],
                    os.environ[StartPrompt(int(psng["agent"]["initial_state"])).name],
                )
                prepared_agents.append(PreparedAgent(**psng))
        return prepared_agents, prepared_planes

    def main(self, ren, step):
        agents: list[Agent] = []
        prepared_agents, prepared_planes = self.load_starting_positions(
            "data/init_setup.json"
        )
        tick_count = 0

        while True:
            if self.is_paused:
                time.sleep(0.1)
                continue
            if self.is_killed:
                break
            prepared_agents.sort(key=lambda x: x.spawn_time)
            prepared_planes.sort(key=lambda x: x.spawn_time)

            for loaded in prepared_planes.copy():
                if loaded.spawn_time > tick_count:
                    break
                ren.interactables[loaded.plane.gate].add_plane(loaded.plane)
                prepared_planes.remove(loaded)

            for loaded in prepared_agents.copy():
                if loaded.spawn_time > tick_count:
                    break
                ren.interactables[loaded.spawn_point].add_new_agent(
                    loaded.agent, ren.graph, loaded.flight, ""
                )
                prepared_agents.remove(loaded)

            for point in ren.interactables.values():
                if isinstance(point, (interactable.Entrance, interactable.Gate)):
                    new_ag = point.spawn_agent(ren.graph, ren.interactables, step)
                    if new_ag is not None:
                        ren.ax.add_patch(new_ag.ui_object)
                        self.signals.new_agent.emit(new_ag)
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
                    # self.signals.agent_updated.emit(a)
                else:
                    if isinstance(a.current_task, agent_task.WalkingTask):
                        a.move(ren.graph.get_node(new_pos).point.xy, new_pos)

            for x in filter(lambda x: x.state is State.COMPLETE, agents):
                self.signals.agent_removed.emit(x.name)
            agents = list(filter(lambda x: x.state is not State.COMPLETE, agents))

            try:
                ren.fig.canvas.draw()
                ren.fig.canvas.flush_events()
            except Exception as e:
                logging.error(e)

            tick_count += 1
            time.sleep(TPS - (time.time() % TPS))

    def toggle_pause(self):
        self.is_paused = not self.is_paused

    def kill(self):
        self.is_killed = True
        logging.info("Simulation stopped\n" + "-" * 40)


class AgentPlate(QWidget):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("agent.ui", self)
        self.__name = name
        self.agent_data.setTitle(str(name))

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name == name


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("main.ui", self)

        self.setWindowTitle("AirportSim")

        self.ren = self.prepare_sim(STEP)

        self.create_mpl_layout()
        self.mpl_show.setLayout(self.layout)

        self.paused = False

        self.threadpool = QThreadPool()
        self.worker = None

        self.lock_buttons(True)

        try:
            with open("data/supported_models.json", "r", encoding="UTF-8") as f:
                self.models = json.load(f)["models"]
        except FileNotFoundError as e:
            logging.error("Supported models not found: %s", e)
        else:
            for item in self.models:
                self.select_model.addItem(item)

        self.start_button.clicked.connect(self.start_sim)
        self.restart_button.clicked.connect(self.restart_sim)
        self.pause_button.clicked.connect(self.pause_sim)
        self.stop_button.clicked.connect(self.stop_sim)
        self.select_model.currentTextChanged.connect(self.select_model_method)
        self.select_model.setPlaceholderText(f"Default: {os.environ["LLM_SELECTED"]}")

        self.actionQuit.triggered.connect(self.quit_app)

        self.agent_plates = {}

    def prepare_sim(self, step):
        load_prompts()
        ren = AreaRender(step, False)
        return ren

    def start_sim(self):
        try:
            requests.get(os.getenv("LLM"), timeout=5).status_code
        except Exception as e:
            self.statusbar.showMessage("LLM is not responding")
            self.statusbar.setStyleSheet("color: red;")
            logging.error(e)
            return
        self.statusbar.showMessage("Connection established")
        self.statusbar.setStyleSheet(
            "colorGroup: SystemPalette.Active; color: default;"
        )

        self.lock_buttons(False)
        self.worker = SimWorker(self.ren)
        self.worker.signals.new_agent.connect(self.agent_deployed)
        self.worker.signals.agent_updated.connect(self.agent_updated)
        self.worker.signals.agent_removed.connect(self.agent_removed)
        self.threadpool.start(self.worker)

    def restart_sim(self):
        if not self.worker:
            return
        self.stop_sim()
        self.start_sim()

    def pause_sim(self):
        if not self.worker:
            return
        self.worker.toggle_pause()
        self.pause_button.setText("Continue" if self.worker.is_paused else "Pause")

    def stop_sim(self):
        if not self.worker:
            return
        if self.worker.is_paused:
            self.pause_sim()
        self.lock_buttons(True)
        self.ren.fig.canvas.draw()
        self.ren.fig.canvas.flush_events()
        self.worker.kill()

        self.ren.fig.clf()
        self.ren = self.prepare_sim(STEP)

        self.create_mpl_layout()
        temp = QWidget().setLayout(self.mpl_show.layout())
        del temp

        self.mpl_show.setLayout(self.layout)

        for x in deepcopy(list(self.agent_plates.keys())):
            self.agent_removed(x)
        self.agent_plates = {}

    def lock_buttons(self, state: bool):
        self.start_button.setEnabled(state)
        for button in self.play_buttons.findChildren(QPushButton):
            button.setEnabled(not state)

    def create_mpl_layout(self):
        self.toolbar = NavigationToolbar(self.ren, self)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.ren)

    def select_model_method(self):
        os.environ["LLM"] = (
            f"http://localhost:{self.models[self.select_model.currentText()]}"
        )
        os.environ["LLM_SELECTED"] = self.select_model.currentText()
        logging.info("Target LLM changed")

    def agent_deployed(self, agent: Agent):
        if agent.name in self.agent_plates:
            logging.warning("Creating agent duplicate")
            return
        self.agent_plates[agent.name] = AgentPlate(name=agent.name)
        self.agents_list.layout().insertWidget(0, self.agent_plates[agent.name])

    def agent_removed(self, agent: str):
        target = self.agent_plates.pop(agent, None)
        if target:
            self.agents_list.layout().removeWidget(target)

    def agent_updated(self, agent: Agent):
        print("up")
        target = self.agent_plates.get(agent.name, None)
        if target:
            target.target_label = agent.current_task.status

    def quit_app(self):
        QApplication.quit()


if __name__ == "__main__":
    logging.info("\n--------------Initializing--------------")
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
