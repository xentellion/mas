import logging
from PyQt6.QtCore import QMutex

import app.models.graph.interactable as interactable


class InteractablesManager:
    # 4. give it next functions:
    # - Select free gate - to give plane a place to dock and agents to go
    # - Probably here should be where I can set up arrival curve for agents
    # - Get all eleemnts of a single type in general (e.g. all registartion decks) - CHECK
    def __init__(
        self,
        interactables: dict = None,
        interactables_mapping: dict = None,
    ):
        self.__lock = QMutex()
        self.__interactables: dict[str, object] | None = None
        self.__mapped_interactables: dict[int, str] | None = None
        self.set_interactables(interactables, interactables_mapping)
        # Interactables themselves are kept in _interactables
        # in mapped there are only node ID and name

    def set_interactables(
        self,
        interactables: dict = None,
        interactables_mapping: dict = None,
    ):
        self.__lock.lock()
        try:
            self.__interactables = interactables or {}
            self.__mapped_interactables = interactables_mapping or {}
        finally:
            self.__lock.unlock()

    def __getitem__(self, key: int | str):
        self.__lock.lock()
        result = None
        try:
            if isinstance(key, int):
                result = self.__interactables[self.__mapped_interactables[key]]
            elif isinstance(key, str):
                result = self.__interactables[key]
        except KeyError as e:
            logging.error(f"Interactable not found: {e}")
        finally:
            self.__lock.unlock()
            return result

    def __iter__(self):
        self.__lock.lock()
        try:
            values_copy = self.__interactables.values()
        finally:
            self.__lock.unlock()
        return iter(values_copy)

    def __len__(self):
        self.__lock.lock()
        try:
            return len(self.__interactables)
        finally:
            self.__lock.unlock()

    def get_interactables_of_type(self, interactable_type):
        if not self.__interactables or not self.__mapped_interactables:
            return {}
        result = dict(
            filter(
                lambda v: isinstance(v[1], interactable_type),
                self.__interactables.items(),
            )
        )
        return result

    def occupy_free_gate(
        self,
        plane,
        allowed_type: interactable.GateTransition = interactable.GateTransition.Any,
    ):
        possible_gates = {
            k: v
            for k, v in self.get_interactables_of_type(interactable.Gate).items()
            if v.plane is None
        }
        if not possible_gates:
            return None
        gate = next(
            filter(
                lambda x: x.gate_transition
                in (
                    interactable.GateTransition.Any,
                    allowed_type,
                ),
                possible_gates.values(),
            )
        ).name
        self.__interactables[gate].add_plane(plane)
        return gate
