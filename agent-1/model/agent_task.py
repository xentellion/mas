class AgentTask:
    def tick(self):
        raise NotImplementedError("Tick action not implemented")


class WalkingTask(AgentTask):
    def __init__(self, path: list[int]):
        self.path = path

    def tick(self):
        if not self.path:
            return None
        return self.path.pop(0)


class InteractingTask(AgentTask):
    def __init__(self, time: int):
        self.time = time

    def tick(self):
        if self.time <= 0:
            return None
        self.time -= 1
