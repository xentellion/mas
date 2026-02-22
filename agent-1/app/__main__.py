"""starting script"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from copy import deepcopy

import requests

# import pika

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QMessageBox,
    # QLabel,
)
from PyQt6 import uic
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot

from model import agent_task, interactable
from model.agent import Agent, State
from model.extras import StartPrompt
from model.environment import AreaRender
from model.plane import Plane
from model.prepared_items import PreparedPlane, PreparedAgent


TPS = 1 / float(os.environ["TPS"])
STEP = 1

logging.basicConfig(
    level=logging.INFO,
    filename=f"logs/{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log",
    filemode="a+",
    format="%(asctime)s:%(levelname)s:%(message)s",
)


def delete_oldest_logs(path: str = "logs", logs_count: int = 10):
    files = []
    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)
        if os.path.isfile(filepath):
            files.append(filepath)
    if not files:
        return
    if len(files) < logs_count:
        return
    files.sort(key=os.path.getctime, reverse=True)
    for file in files[logs_count - 1 : -2]:
        try:
            os.remove(file)
            logging.info(f"Oldest log cleared: {file}")
        except OSError as e:
            logging.error(f"Error deleting file {file}: {e}")


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
    agent_updated = pyqtSignal(Agent)
    agent_removed = pyqtSignal(str)
    agent_error = pyqtSignal(str)

    new_plane = pyqtSignal(Plane)
    plane_updated = pyqtSignal(str)
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

        sim_event_loop = True
        while sim_event_loop:
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
                        # ren.ax.add_patch(new_ag.ui_object)
                        self.signals.new_agent.emit(new_ag)
                        agents.append(new_ag)

            for a in agents:
                try:
                    new_pos = a.tick(ren.graph, ren.interactables)
                except AttributeError as e:
                    logging.error(f"Can't process agent tick: {e}")
                    self.signals.agent_error.emit(e)
                    break
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

            self.ren.agent_items.setData(
                spots=[
                    {"pos": tuple(ren.graph.get_node(a.position).xy)} for a in agents
                ]
            )
            self.ren.update()

            tick_count += 1
            time_delta = TPS - (time.time() % TPS)
            if time_delta > 0:
                time.sleep(time_delta)

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

        self.ren: AreaRender = self.prepare_sim(STEP)

        self.create_mpl_layout()
        self.mpl_show.setLayout(self.layout)

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

        self.paused = False

        self.start_button.clicked.connect(self.start_sim)
        self.restart_button.clicked.connect(self.restart_sim)
        self.pause_button.clicked.connect(self.pause_sim)
        self.stop_button.clicked.connect(self.stop_sim)
        self.select_model.currentTextChanged.connect(self.select_model_method)
        self.select_model.setPlaceholderText(f"Default: {os.environ["LLM_SELECTED"]}")

        self.actionQuit.triggered.connect(self.__quit_app)

        self.agent_plates = {}

        # Error pop up message
        self.agent_error_message = QMessageBox(self)
        self.agent_error_message.setIcon = QMessageBox.Icon.Critical
        self.agent_error_message.setWindowTitle("Error has occured")
        self.agent_error_message.setText(
            "A mistake was encontered while processing agents.\n\nDetails:\n{0}"
        )
        self.agent_error_message.setStandardButtons(QMessageBox.StandardButton.Ok)

        self.select_model_method()

    def prepare_sim(self, step):
        load_prompts()
        ren = AreaRender(step, False)
        return ren

    def start_sim(self):
        try:
            requests.get(os.getenv("LLM"), timeout=5).status_code
        except Exception as e:
            self.statusBar().showMessage("LLM is not responding")
            self.statusBar().setStyleSheet("color: red;")
            logging.error(e)
            return
        self.statusBar().showMessage("Connection established")
        self.statusBar().setStyleSheet("")

        self.lock_buttons(False)
        self.worker = SimWorker(self.ren)
        self.worker.signals.new_agent.connect(self.__agent_deployed)
        self.worker.signals.agent_updated.connect(self.__agent_updated)
        self.worker.signals.agent_removed.connect(self.__agent_removed)
        self.worker.signals.agent_error.connect(self.__agent_error)

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
        self.worker.kill()
        del self.worker

        self.ren.agent_items.clear()

        for x in deepcopy(list(self.agent_plates.keys())):
            self.__agent_removed(x)
        self.agent_plates = {}

    def lock_buttons(self, state: bool):
        self.start_button.setEnabled(state)
        for button in self.play_buttons.findChildren(QPushButton):
            button.setEnabled(not state)

    def create_mpl_layout(self):
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.ren)

    def select_model_method(self):
        try:
            os.environ["LLM"] = (
                f"http://localhost:{self.models[self.select_model.currentText()]}"
            )
            os.environ["LLM_SELECTED"] = self.select_model.currentText()
        except KeyError:
            logging.warning("Can't change the model. Using last or default value")
        # try:
        #     response = requests.post(
        #         f"{os.getenv("LLM")}/swap",
        #         params={
        #             "model": os.getenv("LLM_SELECTED"),
        #         },
        #         timeout=120,
        #     ).json()["response"]
        # except requests.exceptions.ConnectionError as e:
        #     logging.error(f"Cannot connect to models: {e}")
        #     response = None
        # if not response:
        #     logging.error("Can't change an LLM")
        # else:
        logging.info("Target LLM changed")

    def __agent_deployed(self, agent: Agent):
        if agent.name in self.agent_plates:
            logging.warning("Creating agent duplicate")
            return
        self.agent_plates[agent.name] = AgentPlate(name=agent.name)
        self.agents_list.layout().insertWidget(0, self.agent_plates[agent.name])

    def __agent_removed(self, agent: str):
        target = self.agent_plates.pop(agent, None)
        if target:
            self.agents_list.layout().removeWidget(target)

    def __agent_updated(self, agent: Agent):
        target = self.agent_plates.get(agent.name, None)
        if target:
            target.target_label = agent.current_task.status

    def __agent_error(self, text):
        temp = self.agent_error_message
        temp.setText(temp.text().format(text))
        temp.exec()

    def __quit_app(self):
        QApplication.quit()


def main():
    logging.info("\n--------------Initializing--------------")
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    delete_oldest_logs()
    main()
