import random

from pydantic import BaseModel
from app.models.agents import Agent, Plane


class Simulation(BaseModel):
    # planes
    planes_count: int
    average_time_between: int
    allowed_models: list[str]
    arriving_part: int
    internal_route: int
    countries: list[str]
    # passengers
    children: int
    young: int
    middle: int
    elderly: int
    gender_ratio: int
    purposes: list[str]
    # extra
    random_seed: int

    def generate_agents(self) -> tuple(list):
        prepared_agents = []
        prepared_planes = []

        for i in self.planes_count:
            plane = Plane()
            prepared_planes.append(plane)
        # generate planes
        # on each plane generate agents
        # get passengers from the ariving plane and shove them into the general pool

        return prepared_agents, prepared_planes

    # def plane
    def generate_flight_number():
        airlines = ["AAL", "DAL", "UAL", "BAW", "DLH", "AFR", "QFA"]
        carrier = random.choice(airlines)
        number = random.randint(100, 9999)
        return f"{carrier}{number}"
