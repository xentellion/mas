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
            logging.info('Task "%s" started', msg)
            start_time = time.perf_counter()

            function = func(*args, **kwargs)

            end_time = time.perf_counter()
            logging.info(
                'Task "%s"complete in %.2f seconds', msg, (end_time - start_time)
            )
            return function

        return inner_wrapper

    return outer_wrapper
