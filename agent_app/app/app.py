"""starting script"""

import os
import json
import logging

import requests

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
)
from PyQt6 import uic
from PyQt6.QtCore import QThreadPool, pyqtSlot

from app.utils import data
from app.core import AreaRender, SimWorker, Spawner
from app.core.global_state import GLOBAL_STATE
from app.models.agents import agent_task, Agent
from app.models.qt import AgentPlate, GeneratorWindow, MetricWindiow
from app.core.constants import STEP


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(data.load_ui("main.ui"), self)
        self.setWindowTitle("AirportSim")

        self.ren: AreaRender = self.prepare_sim(STEP)

        self.create_mpl_layout()
        self.mpl_show.setLayout(self.layout)

        self.threadpool = QThreadPool()
        self.spawner = Spawner()
        self.worker = None
        self._worker_signal_handlers = [
            (lambda w: w.signals.new_agent, self.__agent_deployed),
            (lambda w: w.signals.agent_updated, self.__agent_updated),
            (lambda w: w.signals.agent_removed, self.__agent_removed),
            (lambda w: w.signals.agent_error, self.__agent_error),
            (lambda w: w.signals.sim_stopped, self.stop_sim),
            (lambda w: w.signals.sim_tick, self.__tick_handle),
            (lambda w: w.signals.agent_positions, self.__move_agent_positions),
        ]

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
        self.__metric_window = MetricWindiow()

        self.actionGenerate.triggered.connect(self.__generate_agents)
        self.actionQuit.triggered.connect(self.__quit_app)
        self.actionSet_metrics.triggered.connect(self.__set_metrics)
        QApplication.instance().aboutToQuit.connect(self.__cleanup_before_quit)

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
        # data.load_prompts()
        ren = AreaRender(step, False)
        return ren

    def start_sim(self):
        if self.worker:
            self.stop_sim()
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

        self.worker = SimWorker(self.ren, self.spawner, STEP)
        self.__handle_connections()
        self.threadpool.start(self.worker)

    def create_agents(self):
        gen = self.spawner.generate()
        if not gen:
            self.statusBar().showMessage("No valid generation settings found")

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
        self.__disconnect_worker_signals()
        self.worker.kill()
        self.worker.ren.reset_area()
        self.worker.ren.update()

        for _, plate in self.agent_plates.items():
            self.agents_list.layout().removeWidget(plate)
            plate.deleteLater()
        self.agent_plates.clear()
        GLOBAL_STATE.agents.clear()
        self.worker = None
        self.spawner = Spawner()
        self.statusBar().showMessage(f"Simulation {message}")

    def lock_buttons(self, state: bool):
        self.start_button.setEnabled(state)
        for button in self.play_buttons.findChildren(QPushButton):
            button.setEnabled(not state)

    def create_mpl_layout(self):
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.ren)

    def select_model_method(self):
        selected = self.select_model.currentText()
        current_llm = os.environ.get("LLM", "")
        base = current_llm.rsplit(":", 1)[0] if current_llm else ""

        if not selected:
            logging.info("No model selected; keeping existing LLM value")
            return

        model_val = self.models.get(selected) if isinstance(self.models, dict) else None
        if not model_val:
            logging.warning("Selected model '%s' is not available", selected)
            return

        try:
            os.environ["LLM"] = f"{base}:{model_val}" if base else str(model_val)
            os.environ["LLM_SELECTED"] = selected
        except Exception as e:
            logging.exception("Failed to set LLM environment: %s", e)
            return

        self.select_model.setPlaceholderText(f"Default: {selected}")
        logging.info("Target LLM changed to %s", os.environ["LLM"])

    @pyqtSlot(str, Agent)
    def __agent_deployed(self, _id: str, agent: Agent):
        GLOBAL_STATE.agents[_id] = agent
        if _id in self.agent_plates:
            logging.warning("Creating agent duplicate")
            return
        plate = AgentPlate(name=agent.name)
        self.agent_plates[_id] = plate
        self.agents_list.layout().insertWidget(0, plate)

    @pyqtSlot(str, Agent)
    def __agent_updated(self, _id: str, agent: Agent):
        GLOBAL_STATE.agents[_id] = agent
        if agent.current_task is None:
            logging.debug(f"No task present for agent {_id}")
            return
        plate = self.agent_plates.get(_id, None)
        if plate is not None:
            plate.setState(agent.state)
            if isinstance(agent.current_task, agent_task.WalkingTask):
                plate.setTarget(agent.current_task.dest_name)
        else:
            logging.error(f"Can't find plate of agent {_id}")

    @pyqtSlot(str)
    def __agent_removed(self, _id: str):
        GLOBAL_STATE.agents.pop(_id, None)
        target = self.agent_plates.pop(_id, None)
        if target:
            self.agents_list.layout().removeWidget(target)
            target.deleteLater()
        logging.info(f"Agent {_id} is removed")

    @pyqtSlot(str)
    def __agent_error(self, text):
        temp = self.agent_error_message
        temp.setText(temp.text().format(text))
        temp.exec()

    def __handle_connections(self):
        if not self.worker:
            return
        self.__update_worker_signal_connections(connect=True)

    def __disconnect_worker_signals(self):
        if not self.worker:
            return
        self.__update_worker_signal_connections(connect=False)

    def __update_worker_signal_connections(self, connect: bool):
        for signal_getter, slot in self._worker_signal_handlers:
            signal = signal_getter(self.worker)
            try:
                if connect:
                    signal.connect(slot)
                else:
                    signal.disconnect(slot)
            except TypeError:
                logging.warning(
                    f"Signal {signal} is already {'connected' if connect else 'disconnected'}"
                )

    def __clear_agent_plates(self):
        layout = self.agents_list.layout()
        for plate in list(self.agent_plates.values()):
            layout.removeWidget(plate)
            plate.deleteLater()
        self.agent_plates.clear()

    def __move_agent_positions(self, positions: list[tuple[int, int]]):
        self.ren.agent_items.setData(positions)
        self.ren.update()

    def __tick_handle(self, tick: int):
        GLOBAL_STATE.tick = tick

    def __generate_agents(self):
        self.__agent_generator.show()

    def __set_metrics(self):
        self.__metric_window.show()

    def __cleanup_before_quit(self):
        self.stop_sim()

    def __quit_app(self):
        self.stop_sim()
        QApplication.quit()
