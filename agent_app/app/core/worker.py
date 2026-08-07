import logging
import time
import uuid
from copy import deepcopy

from PyQt6.QtCore import QRunnable, pyqtSlot

from app.core import AreaRender, Spawner
from app.core.constants import TPS
from app.core.global_state import GLOBAL_STATE
from app.models.agents import Agent, agent_task
from app.models.graph import interactable
from app.models.qt import WorkerSignals
from app.utils import State


class SimWorker(QRunnable):
    def __init__(self, ren: AreaRender = None, spawner: Spawner = None, step: int = 1):
        super().__init__()
        self.signals = WorkerSignals()
        self.spawner = spawner
        self.step = step
        self.ren = ren
        self.is_paused = False
        self.is_killed = False

    @pyqtSlot()
    def run(self):
        logging.info("Simulation started")
        self.main()

    def main(self):
        if self.ren is None:
            logging.error("No map found")
            return
        if self.spawner is None:
            logging.error("No spawner found")
            return

        tick_count = 0
        agents: dict[str, Agent] = deepcopy(GLOBAL_STATE.agents)

        sim_event_loop = True
        while sim_event_loop:
            if self.is_paused:
                time.sleep(0.1)
                continue
            if self.is_killed:
                sim_event_loop = False
                continue

            prepared_planes = self.spawner.pull(tick_count)
            for plane in prepared_planes:
                if plane.plane.is_arriving:
                    self.ren.interactables["gate_2"].add_plane(plane.plane)
                else:
                    for p in plane.plane.passengers:
                        self.ren.interactables["entrance"].add_new_agent(
                            p, self.ren.graph, plane.plane.name, ""
                        )
            # prepared_agents = self.spawner.pull(tick_count)
            # for agt in prepared_agents:
            #     if isinstance(agt.agent, PreparedPlane):
            #         self.ren.interactables[agt.agent.plane.gate].add_plane(
            #             agt.agent.plane
            #         )
            #     else:
            #         self.ren.interactables[agt.dest].add_new_agent(
            #             agt.agent.agent, self.ren.graph, agt.agent.flight, ""
            #         )

            for point in self.ren.interactables.values():
                if isinstance(point, (interactable.Entrance, interactable.Gate)):
                    new_ag = point.spawn_agent(
                        self.ren.graph, self.ren.interactables, self.step
                    )
                    if new_ag is not None:
                        self.signals.new_agent.emit(str(uuid.uuid4()), new_ag)

            for _id, agt in agents.items():
                try:
                    new_pos = agt.tick(self.ren.graph, self.ren.interactables)
                except AttributeError as e:
                    logging.error(f"Can't process agent tick: {e}")
                    self.signals.agent_error.emit(str(e))
                    self.toggle_pause()
                    break
                if new_pos is None:
                    agt.change_task(self.ren.graph)

                    if agt.current_task is None and agt.state is State.WALKING:
                        if agt.position in self.ren.interactables_mapping:
                            inter = self.ren.interactables[
                                self.ren.interactables_mapping[agt.position]
                            ]
                            new_task = inter.get_task(agt)
                            agt.add_task(new_task)
                else:
                    if isinstance(agt.current_task, agent_task.WalkingTask):
                        agt.move(self.ren.graph.get_node(new_pos).point.xy, new_pos)
                self.signals.agent_updated.emit(_id, agt)
                if agt.state == State.COMPLETE:
                    self.signals.agent_removed.emit(_id)

            # Throttle to let main thread catch up
            time.sleep(0.01)

            agents = deepcopy(GLOBAL_STATE.agents)

            if not agents and not prepared_planes:
                sim_event_loop = False

            # Crutch to prevent re-rendering of agents if the simulation was stopped while waiting for llm
            if self.is_killed:
                continue

            spots = [
                {"pos": tuple(self.ren.graph.get_node(a.position).xy)}
                for a in agents.values()
            ]
            self.signals.agent_positions.emit(spots)

            tick_count += 1
            time_delta = TPS - (time.time() % TPS)
            if time_delta > 0:
                time.sleep(time_delta)
            self.signals.sim_tick.emit(tick_count)
        print("Loop stopped")
        self.signals.sim_stopped.emit("Complete")

    def toggle_pause(self):
        self.is_paused = not self.is_paused

    def kill(self):
        self.is_killed = True
        logging.info(f"Simulation stopped\n{"-" * 40}")
