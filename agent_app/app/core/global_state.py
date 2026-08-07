from pydantic import BaseModel, ConfigDict, Field
from PyQt6.QtCore import QObject, pyqtSignal

from app.models.agents.simulation import Simulation
from app.utils import load_prompts


class StateChanged(QObject):
    valueChanged = pyqtSignal(str, object)


class GlobalStates(BaseModel):
    signals: StateChanged = Field(default_factory=StateChanged, exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)
    simulation: Simulation = None

    prompts: dict[str, str] = Field(default_factory=load_prompts)
    agents: dict[str, object] = {}
    tick: int = 0

    def __setattr__(self, name: str, value) -> None:
        has_old_value = name in self.__dict__
        old_value = self.__dict__.get(name) if has_old_value else None

        super().__setattr__(name, value)
        if has_old_value and old_value != getattr(self, name):
            self.signals.valueChanged.emit(name, getattr(self, name))


GLOBAL_STATE = GlobalStates()
