from PyQt6.QtCore import QObject, pyqtSignal

from app.models.agents import Agent, Plane


class WorkerSignals(QObject):
    sim_tick = pyqtSignal(int)
    sim_stopped = pyqtSignal(str)

    new_agent = pyqtSignal(str, Agent)
    agent_updated = pyqtSignal(str, Agent)
    agent_removed = pyqtSignal(str)
    agent_error = pyqtSignal(str)
    agent_positions = pyqtSignal(list)

    new_plane = pyqtSignal(Plane)
    plane_updated = pyqtSignal(str)
    plane_removed = pyqtSignal(str)
