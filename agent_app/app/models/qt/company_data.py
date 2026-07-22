from PyQt6.QtWidgets import QWidget
from PyQt6 import uic

from app.utils import load_ui


class CompanyData(QWidget):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(load_ui("company.ui"), self)
