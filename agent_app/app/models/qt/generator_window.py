from PyQt6.QtWidgets import QMainWindow
from PyQt6 import uic

from app.utils import load_ui


class GeneratorWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(load_ui("generator.ui"), self)

        self.agentCountSlider.valueChanged.connect(self.agentCountSpin.setValue)
        self.agentCountSpin.valueChanged.connect(self.agentCountSlider.setValue)

        self.genderSlider.valueChanged.connect(self.genderSpin.setValue)
        self.genderSpin.valueChanged.connect(self.genderSlider.setValue)
