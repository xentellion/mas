import logging
import time

from enum import Enum


class State(Enum):
    IDLE = 0
    WALKING = 1
    PERFORMING = 2
    COMPLETE = 3


def execution_timer(msg: str = "Task"):
    def outer_wrapper(func):
        def inner_wrapper(*args, **kwargs):
            logging.info(f'Task "{msg}" started')
            start_time = time.perf_counter()

            function = func(*args, **kwargs)

            end_time = time.perf_counter()
            logging.info(
                f'Task "{msg}"complete in {(end_time - start_time):.5f} seconds'
            )
            return function

        return inner_wrapper

    return outer_wrapper
