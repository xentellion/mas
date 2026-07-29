"""starting script"""

import os
import json
import logging
from copy import deepcopy

import requests

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
)
from PyQt6 import uic
from PyQt6.QtCore import QThreadPool

from app.utils import data
from app.core import AreaRender, SimWorker
from app.core.global_states import global_state
from app.models.agents import agent_task, Agent
from app.models.qt import AgentPlate, GeneratorWindow
from app.core.constants import STEP


class MainWindow(QMainWindow):
    worker = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(data.load_ui("main.ui"), self)
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
        self.createAgentsButton.clicked.connect(self.create_agents)

        self.__agent_generator = GeneratorWindow()

        self.actionGenerate.triggered.connect(self.__generate_agents)
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
        data.load_prompts()
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
        self.worker = SimWorker(self.ren, STEP)
        QApplication.instance().aboutToQuit.connect(self.worker.kill)
        self.worker.signals.new_agent.connect(self.__agent_deployed)
        self.worker.signals.agent_updated.connect(self.__agent_updated)
        self.worker.signals.agent_removed.connect(self.__agent_removed)
        self.worker.signals.agent_error.connect(self.__agent_error)
        self.worker.signals.sim_stopped.connect(self.stop_sim)

        self.threadpool.start(self.worker)

    def create_agents(self):
        print(global_state.simulation)

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

    def stop_sim(self, message: str = "Stopped"):
        if not self.worker:
            return
        if self.worker.is_paused:
            self.pause_sim()
        self.lock_buttons(True)
        self.worker.kill()
        self.worker.ren.reset_area()
        self.worker.ren.update()

        for x in deepcopy(list(self.agent_plates.keys())):
            self.__agent_removed(x)
        self.agent_plates.clear()
        self.statusBar().showMessage(f"Simulation {message}")

    def lock_buttons(self, state: bool):
        self.start_button.setEnabled(state)
        for button in self.play_buttons.findChildren(QPushButton):
            button.setEnabled(not state)

    def create_mpl_layout(self):
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.ren)

    def select_model_method(self):
        try:
            os.environ["LLM"] = "{0}:{1}".format(
                os.getenv("LLM").split(":")[0],
                self.models[self.select_model.currentText()],
            )
            os.environ["LLM_SELECTED"] = self.select_model.currentText()
        except KeyError:
            logging.warning("Can't change the model. Using last or default value")
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
        if agent.name not in self.agent_plates:
            logging.warning(f"Plake does not exist for agent {agent.name}")
            return
        if agent.current_task is None:
            logging.warning(f"No task present for agent {agent.name}")
            return
        self.agent_plates[agent.name].setState(agent.state)
        if isinstance(agent.current_task, agent_task.WalkingTask):
            self.agent_plates[agent.name].setTarget(agent.current_task.dest_name)

    def __agent_error(self, text):
        temp = self.agent_error_message
        temp.setText(temp.text().format(text))
        temp.exec()

    def __generate_agents(self):
        self.__agent_generator.show()

    def __quit_app(self):
        self.stop_sim()
        QApplication.quit()
