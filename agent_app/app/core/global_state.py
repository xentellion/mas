from pydantic import BaseModel, ConfigDict, Field
from PyQt6.QtCore import QObject, pyqtSignal

from app.models.agents.simulation import Simulation
from app.models.agents import Agent


class StateChanged(QObject):
    valueChanged = pyqtSignal(str, object)


class GlobalStates(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)
    signals: StateChanged = Field(default_factory=StateChanged, exclude=True)
    simulation: Simulation = None
    agents: dict[str, Agent] = {}
    tick: int = 0

    def __setattr__(self, name: str, value) -> None:
        has_old_value = name in self.__dict__
        old_value = self.__dict__.get(name) if has_old_value else None

        super().__setattr__(name, value)
        if has_old_value and old_value != getattr(self, name):
            self.signals.valueChanged.emit(name, getattr(self, name))


GLOBAL_STATE = GlobalStates()
