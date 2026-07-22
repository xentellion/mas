from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QWidget,
    # QPushButton,
    QVBoxLayout,
    QGridLayout,
    # QLabel,
    QCheckBox,
)


NUM_COLUMNS = 2


class SelectCountry(QWidget):
    submitted = pyqtSignal(list)

    def __init__(self, parent_window, items_list):
        super().__init__()
        self.setWindowTitle("Select countries")
        self.resize(300, 200)

        self.parent_window = parent_window

        main_layout = QVBoxLayout()
        grid_layout = QGridLayout()

        self.checkboxes = []
        for index, item in enumerate(items_list):
            cb = QCheckBox(str(item))
            self.checkboxes.append(cb)
            row = index // NUM_COLUMNS
            col = index % NUM_COLUMNS
            grid_layout.addWidget(cb, row, col)

        main_layout.addLayout(grid_layout)

        buttons = (
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Discard
        )

        self.button_box = QDialogButtonBox(buttons)

        self.button_box.accepted.connect(self.handle_ok)
        self.button_box.rejected.connect(self.handle_cancel)

        discard_button = self.button_box.button(QDialogButtonBox.StandardButton.Discard)
        discard_button.clicked.connect(self.clear_all_checkboxes)

        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def clear_all_checkboxes(self):
        for cb in self.checkboxes:
            cb.setChecked(False)

    def handle_ok(self):
        selected_items = [cb.text() for cb in self.checkboxes if cb.isChecked()]
        self.submitted.emit(selected_items)
        self.close()

    def handle_cancel(self):
        self.close()

    def closeEvent(self, event):
        # bruh how is it even safe
        # screw you i ain't making circular imports
        self.parent_window.new_window = None
        event.accept()
