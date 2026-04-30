from PyQt6.QtWidgets import QWidget
from PyQt6 import uic

from app.utils import load_ui


class AgentPlate(QWidget):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(load_ui("agent.ui"), self)
        self.agent_name.setText(str(name).replace("_", " "))
        self.details_frame.setVisible(False)

    def setTarget(self, target):
        self.target_name.setText(str(target).replace("_", " "))
        self.target_name.setToolTip(str(target).replace("_", " "))

    def setState(self, state):
        self.state_name.setText(str(state.name))
