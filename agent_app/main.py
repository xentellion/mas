import logging
import sys
from datetime import datetime

from PyQt6.QtWidgets import QApplication

from app.utils import delete_oldest_logs
from app import MainWindow

logging.basicConfig(
    level=logging.INFO,
    filename=f"logs/{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log",
    filemode="a+",
    format="%(asctime)s:%(levelname)s:%(message)s",
)


def main():
    logging.info("\n--------------Initializing--------------")
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    delete_oldest_logs()
    main()
