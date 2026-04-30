import logging
import time


def execution_timer(msg: str = "Task"):
    def outer_wrapper(func):
        def inner_wrapper(*args, **kwargs):
            logging.debug('Task "%s" started', msg)
            start_time = time.perf_counter()

            function = func(*args, **kwargs)

            end_time = time.perf_counter()
            logging.debug(
                'Task "%s"complete in %.2f seconds', msg, (end_time - start_time)
            )
            return function

        return inner_wrapper

    return outer_wrapper
