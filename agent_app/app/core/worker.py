import logging
import time
from copy import deepcopy
from typing import Any, Callable
import queue
import random

from PyQt6.QtCore import QRunnable, pyqtSlot

from app.core import AreaRender, Spawner
from app.core.constants import TPS
from app.core.global_state import GLOBAL_STATE
from app.models.agents import Agent, Plane, agent_task
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

        self._request_queue = queue.Queue()
        self.request_handler = None

    def enqueue_request(self, req: Any) -> None:
        self._request_queue.put(req)

    def set_request_handler(self, handler: Callable) -> None:
        self.request_handler = handler

    @pyqtSlot()
    def run(self):
        logging.info("Simulation started")
        self.main()

    def _process_external_requests(self):
        try:
            while True:
                req = self._request_queue.get_nowait()
                try:
                    if self.request_handler:
                        self.request_handler(req)
                    else:
                        # default: emit a generic signal so UI/main thread can react
                        try:
                            self.signals.message.emit(str(req))
                        except Exception:
                            # fallback to logging
                            logging.info("AI Tool request: %s", req)
                finally:
                    self._request_queue.task_done()
        except queue.Empty:
            pass

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

        entrances = list(
            GLOBAL_STATE.interactables.get_interactables_of_type(
                interactable.Entrance
            ).keys()
        )

        random.seed(GLOBAL_STATE.simulation.random_seed)

        while sim_event_loop:
            if self.is_paused:
                time.sleep(0.1)
                continue
            if self.is_killed:
                sim_event_loop = False
                continue

            self._process_external_requests()
            prepared_planes = self.spawner.pull_planes(tick_count)
            prepared_agents = self.spawner.pull_agents(tick_count)

            for plane in prepared_planes:
                if plane.agent.is_arriving:
                    gate = GLOBAL_STATE.interactables.occupy_free_gate(
                        plane.agent, interactable.GateTransition.InOnly
                    )
                    if gate is None:
                        readd_plane = plane._replace(tick=tick_count + TPS)
                        logging.info(
                            f"Plane '{plane.agent.name}' will attemt to dock on tick {tick_count + TPS}"
                        )
                        self.spawner.push_plane([readd_plane])
                else:
                    this_plane = deepcopy(plane.agent)
                    this_plane.passengers = []
                    gate = GLOBAL_STATE.interactables.occupy_free_gate(
                        this_plane, interactable.GateTransition.OutOnly
                    )
                    if gate is None:
                        readd_plane = plane._replace(
                            tick=tick_count + TPS,
                            agent=this_plane,
                        )
                        self.spawner.push_plane([readd_plane])
                    else:
                        for p in this_plane.expected_passengers:
                            if p in GLOBAL_STATE.agents:
                                agents[p].status.append(
                                    f"Your plane is docked at the gate {gate}."
                                )
                                agents[p].status.append("You can board your plane.")
                    self.spawner.push_agents(tick_count, plane.agent, gate)

            for agt in prepared_agents:
                GLOBAL_STATE.interactables[random.choice(entrances)].add_new_agent(
                    agt.agent, self.ren.graph, agt.plane_name, agt.gate
                )

            for point in GLOBAL_STATE.interactables:
                if isinstance(point, interactable.Entrance):
                    new_ag = point.spawn_agent(self.ren.graph, self.step)
                    if new_ag is not None:
                        self.signals.new_agent.emit(str(new_ag.name), new_ag)
                elif isinstance(point, interactable.Gate):
                    new_ag = point.spawn_agent(self.ren.graph, self.step)
                    if new_ag is not None:
                        self.signals.new_agent.emit(new_ag.name, new_ag)
                    if point.plane is not None:
                        if point.plane.ready_to_depart:
                            result = point.depart(self.ren.graph, tick_count)
                            if not result:
                                pass
                            elif isinstance(result, list):
                                for ag in result:
                                    try:
                                        agents[ag].clear_tasks()
                                        agents[ag].add_task(
                                            agent_task.CompletionTask("Plane departs")
                                        )
                                        agents[ag].change_task(self.ren.graph)
                                    except KeyError:
                                        logging.warning(
                                            "Trying to remove nonexistent agent"
                                        )
                            elif isinstance(result, Plane):
                                # Rejoin plane in the big list
                                pass
                            else:
                                pass

            for _id, agt in agents.items():
                try:
                    new_pos = agt.tick(self.ren.graph)
                except AttributeError as e:
                    logging.error(f"Can't process agent tick: {e}")
                    self.signals.agent_error.emit(str(e))
                    self.toggle_pause()
                    break
                if new_pos is None:
                    agt.change_task(self.ren.graph)

                    if agt.current_task is None and agt.state is State.WALKING:
                        inter = GLOBAL_STATE.interactables[agt.position]
                        if inter is not None:
                            new_task = inter.get_task(agt)
                            logging.debug(f"New task for agent {_id} - {new_task}")
                            agt.add_task(new_task)
                elif new_pos is not False:
                    if isinstance(agt.current_task, agent_task.WalkingTask):
                        try:
                            agt.move(self.ren.graph.get_node(new_pos).point.xy, new_pos)
                        except AttributeError as e:
                            # Prevents an error on stopping sim while requesting
                            logging.error(f"Can't move agent {agt.name}: {e}")
                self.signals.agent_updated.emit(_id, agt)
                if agt.state == State.COMPLETE:
                    self.signals.agent_removed.emit(_id)

            # Throttle to let the main thread catch up
            time.sleep(0.01)

            agents = deepcopy(GLOBAL_STATE.agents)
            # Probably can be done easier but i can't be assed to recheck
            if (
                not agents
                and not prepared_planes
                and not prepared_agents
                and not self.spawner.planes
                and not self.spawner.agents
            ):
                sim_event_loop = False

            # Crutch to prevent re-rendering of agents if the simulation was stopped while waiting for llm
            if self.is_killed:
                continue

            spots = [
                {
                    "pos": tuple(self.ren.graph.get_node(a.position).xy),
                    "data": {"id": a.name},
                }
                for a in agents.values()
                if a.state is not State.BOARDING
            ]
            self.signals.agent_positions.emit(spots)

            tick_count += 1
            time_delta = 1 / TPS - (time.time() % (1 / TPS))
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
