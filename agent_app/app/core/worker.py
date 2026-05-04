import os
import json
import logging
import time

from PyQt6.QtCore import QRunnable, pyqtSlot

from app.core import AreaRender
from app.models import PreparedAgent, PreparedPlane
from app.models.agents import Agent, Plane, agent_task
from app.models.graph import interactable
from app.models.qt import WorkerSignals
from app.utils import StartPrompt, State
from app.core.constants import TPS


class SimWorker(QRunnable):
    signals = WorkerSignals()

    def __init__(self, ren: AreaRender = None, step: int = 1):
        super().__init__()
        self.step = step
        self.ren = ren
        self.is_paused = False
        self.is_killed = False

    @pyqtSlot()
    def run(self):
        logging.info("Simulation started")
        self.main()

    def load_starting_positions(self, path):
        prepared_agents = []
        prepared_planes = []
        with open(path, "r", encoding="UTF-8") as f:
            data = json.load(f)
            for plane in data["planes"]:
                spawn_time = plane["spawn_time"]
                del plane["spawn_time"]

                passengers = []
                for psng in plane["passengers"]:
                    passengers.append(
                        Agent(
                            psng["name"],
                            os.environ[StartPrompt(int(psng["initial_state"])).name],
                        )
                    )
                plane["passengers"] = passengers

                prepared_planes.append(
                    PreparedPlane(plane=Plane(**plane), spawn_time=spawn_time)
                )
            for psng in data["departing_passengers"]:
                psng["agent"] = Agent(
                    psng["agent"]["name"],
                    os.environ[StartPrompt(int(psng["agent"]["initial_state"])).name],
                )
                prepared_agents.append(PreparedAgent(**psng))
        return prepared_agents, prepared_planes

    def main(self):
        if self.ren is None:
            return
        agents: list[Agent] = []

        prepared_agents, prepared_planes = self.load_starting_positions(
            "data/init_setup.json"
        )
        tick_count = 0

        sim_event_loop = True
        while sim_event_loop:
            if self.is_paused:
                time.sleep(0.1)
                continue
            if self.is_killed:
                sim_event_loop = False
                continue
            prepared_agents.sort(key=lambda x: x.spawn_time)
            prepared_planes.sort(key=lambda x: x.spawn_time)

            for loaded in prepared_planes.copy():
                if loaded.spawn_time > tick_count:
                    break
                self.ren.interactables[loaded.plane.gate].add_plane(loaded.plane)
                prepared_planes.remove(loaded)

            for loaded in prepared_agents.copy():
                if loaded.spawn_time > tick_count:
                    break
                self.ren.interactables[loaded.spawn_point].add_new_agent(
                    loaded.agent, self.ren.graph, loaded.flight, ""
                )
                prepared_agents.remove(loaded)

            for point in self.ren.interactables.values():
                if isinstance(point, (interactable.Entrance, interactable.Gate)):
                    new_ag = point.spawn_agent(
                        self.ren.graph, self.ren.interactables, self.step
                    )
                    if new_ag is not None:
                        self.signals.new_agent.emit(new_ag)
                        agents.append(new_ag)

            for a in agents:
                try:
                    new_pos = a.tick(self.ren.graph, self.ren.interactables)
                except AttributeError as e:
                    logging.error(f"Can't process agent tick: {e}")
                    self.signals.agent_error.emit(str(e))
                    self.toggle_pause()
                    break
                if new_pos is None:
                    a.change_task(self.ren.graph)
                    self.signals.agent_updated.emit(a)

                    if a.current_task is None and a.state is State.WALKING:
                        if a.position in self.ren.interactables_mapping:
                            inter = self.ren.interactables[
                                self.ren.interactables_mapping[a.position]
                            ]
                            a.add_task(inter.get_task(a))
                else:
                    if isinstance(a.current_task, agent_task.WalkingTask):
                        a.move(self.ren.graph.get_node(new_pos).point.xy, new_pos)

            for x in filter(lambda x: x.state is State.COMPLETE, agents):
                self.signals.agent_removed.emit(x.name)
            agents = list(filter(lambda x: x.state is not State.COMPLETE, agents))

            if not agents and not prepared_agents and not prepared_planes:
                sim_event_loop = False

            # Crutch to prevent re-rendering of agents if the simulation was stopped while waiting for llm
            if self.is_killed:
                continue

            self.ren.agent_items.setData(
                spots=[
                    {"pos": tuple(self.ren.graph.get_node(a.position).xy)}
                    for a in agents
                ]
            )
            self.ren.update()

            tick_count += 1
            time_delta = TPS - (time.time() % TPS)
            if time_delta > 0:
                time.sleep(time_delta)
        print("Loop stopped")
        self.signals.sim_stopped.emit("Complete")

    def toggle_pause(self):
        self.is_paused = not self.is_paused

    def kill(self):
        self.is_killed = True
        logging.info("Simulation stopped\n" + "-" * 40)
