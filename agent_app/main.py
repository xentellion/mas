import logging
import sys
from datetime import datetime

from PyQt6.QtWidgets import QApplication

from app.utils import delete_oldest_logs
from app import MainWindow
from app.core.global_state import GLOBAL_STATE

# Some shenanigans to keep debug menu from screaming at me because tick in not yet declared
_orig_log_record_factory = logging.getLogRecordFactory()


def _log_record_factory(*args, **kwargs):
    record = _orig_log_record_factory(*args, **kwargs)
    if not hasattr(record, "tick"):
        record.tick = getattr(GLOBAL_STATE, "tick", "N/A")
    return record


logging.setLogRecordFactory(_log_record_factory)


logging.basicConfig(
    level=logging.DEBUG,
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
