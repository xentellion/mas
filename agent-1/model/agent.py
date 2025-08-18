from queue import PriorityQueue
from agent_task import AgentTask, WalkingTask, InteractingTask
from node import Graph


class Agent:
    def __init__(self, ui_object, graph: Graph):
        self.ui_object = ui_object
        self.target = None
        self.tasks = PriorityQueue()

        self.__current_task: AgentTask = None

        self.graph = graph

        self.finished = False

    def add_task(self, priotity: int, task: AgentTask):
        self.tasks.put((priotity, task))

    def clear_tasks(self):
        self.tasks = PriorityQueue()

    def tick(self):
        if self.__current_task is None:
            if self.tasks.empty():
                # print("Nothing to do")
                self.finished = True
                self.ui_object.remove()
                return
            self.__current_task = self.tasks.get()[1]

        status = self.__current_task.tick()

        if status is None:
            self.__current_task = None
            return

        if isinstance(self.__current_task, WalkingTask):
            self.ui_object.set_center(self.graph.get_node(status).point.xy)
        elif isinstance(self.__current_task, InteractingTask):
            # self.__current_task.tick()
            pass
