from pydantic import BaseModel, ConfigDict

from model.agent import Agent
from model.plane import Plane


class Prepared(BaseModel):
    """"""

    # TODO turn spawntime into time not tick counter
    spawn_time: int
    model_config = ConfigDict(arbitrary_types_allowed=True)


class PreparedAgent(Prepared):
    """Block of data containing agent and information about its whereabouts on the start"""

    agent: Agent
    flight: str
    spawn_point: str


class PreparedPlane(Prepared):
    """Block of data containing plane and information about its whereabouts on the start"""

    plane: Plane
