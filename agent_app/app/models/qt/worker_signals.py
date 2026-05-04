from PyQt6.QtCore import QObject, pyqtSignal

from app.models.agents import Agent, Plane


class WorkerSignals(QObject):
    sim_stopped = pyqtSignal(str)

    new_agent = pyqtSignal(Agent)
    agent_updated = pyqtSignal(Agent)
    agent_removed = pyqtSignal(str)
    agent_error = pyqtSignal(str)

    new_plane = pyqtSignal(Plane)
    plane_updated = pyqtSignal(str)
    plane_removed = pyqtSignal(str)
