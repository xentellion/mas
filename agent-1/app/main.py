"""starting script"""

import os
import sys
import json
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
    QMessageBox,
)
from PyQt6 import uic
from PyQt6.QtCore import QThreadPool

import model.agent_task as agent_task
from model.agent import Agent
from model.agent_plate import AgentPlate
from model.environment import AreaRender
from model.worker import SimWorker


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


class MainWindow(QMainWindow):
    worker = None

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
        self.worker = SimWorker(self.ren, STEP)
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
        self.worker.ren.reset_area()
        self.worker.ren.update()

        for x in deepcopy(list(self.agent_plates.keys())):
            self.__agent_removed(x)
        self.agent_plates.clear()

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
