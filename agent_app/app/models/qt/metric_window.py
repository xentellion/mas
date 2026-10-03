import os
import requests

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget,
    QDialogButtonBox,
    QMessageBox,
)

from app.utils import load_ui
from shared.schemas import AlignmentScoring


class MetricWindiow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(load_ui("metrics.ui"), self)

        self.metrics_url = os.getenv("METRICS")
        if not self.metrics_url:
            QMessageBox.critical(self, "Metrics error", "No url for metrics.")
            self.close()
            return

        try:
            response = requests.get(f"{self.metrics_url}/metrics", timeout=10)
            response.raise_for_status()
            scoring = AlignmentScoring.model_validate(response.json())
        except (requests.RequestException, ValueError) as exc:
            QMessageBox.critical(
                self, "Metrics error", f"Could not load settings: {exc}"
            )
            self.close()
            return

        self.gap_penalty.setValue(scoring.gap_penalty)
        self.high_threshold.setValue(scoring.high_threshold)
        self.medium_threshold.setValue(scoring.medium_threshold)
        self.high_score.setValue(scoring.high_score)
        self.medium_score.setValue(scoring.medium_score)
        self.low_score.setValue(scoring.low_score)
        self.missing_score.setValue(scoring.missing_score)

        ok = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        if ok:
            ok.clicked.connect(self.ok)

        cancel = self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel:
            cancel.clicked.connect(self.cancel)

    def ok(self):
        scoring = AlignmentScoring(
            gap_penalty=self.gap_penalty.value(),
            high_threshold=self.high_threshold.value(),
            medium_threshold=self.medium_threshold.value(),
            high_score=self.high_score.value(),
            medium_score=self.medium_score.value(),
            low_score=self.low_score.value(),
            missing_score=self.missing_score.value(),
        )
        try:
            response = requests.post(
                f"{self.metrics_url}/change",
                json=scoring.model_dump(),
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            QMessageBox.critical(
                self,
                "Metrics save failed",
                f"Could not send scoring settings: {exc}",
            )
            return
        self.close()

    def cancel(self):
        self.close()
