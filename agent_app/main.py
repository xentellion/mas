import logging
import sys
from datetime import datetime

from PyQt6.QtWidgets import QApplication

from app.utils import delete_oldest_logs
from app import MainWindow
from app.core.global_state import GLOBAL_STATE


logging.basicConfig(
    level=logging.INFO,
    filename=f"logs/{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log",
    filemode="a+",
    format="%(asctime)s:tick %(tick)s:%(levelname)s:%(message)s",
)


class GlobalStateFilter(logging.Filter):
    def filter(self, record):
        record.tick = GLOBAL_STATE.tick
        return True


def main():
    logging.getLogger().addFilter(GlobalStateFilter())
    logging.info("\n--------------Initializing--------------")
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    delete_oldest_logs()
    main()
