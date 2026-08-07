import heapq
import random
from functools import total_ordering
from typing import List, Iterable, NamedTuple, Union

import uuid

import numpy as np
from sqlalchemy import select
from PyQt6.QtCore import QMutex, QMutexLocker

from app.models.agents import Agent, Plane
from app.core.global_state import GLOBAL_STATE
from app.models.agents import SimulationCompany
from app.utils.database import PlaneTable, Company, Country, with_orm_session


@total_ordering
class SpawnerObject(NamedTuple):
    tick: int
    plane: Plane

    def __eq__(self, other):
        return self.tick == other.tick

    def __lt__(self, other):
        return self.tick < other.tick


class Spawner:
    def __init__(self):
        self.agents: List[SpawnerObject] = []
        self.lock = QMutex()

    def generate(self):
        data = self.generate_agents()
        if not data:
            return False

        self.push(
            (
                SpawnerObject(
                    tick=x.arrival_time,
                    plane=x,
                )
                for x in data
            )
        )

        return True

    def generate_agents(self) -> tuple(list):
        if GLOBAL_STATE.simulation is None:
            return []
        preset = GLOBAL_STATE.simulation
        random.seed(preset.random_seed)
        np.random.default_rng(preset.random_seed)

        company_data = self.__get_companies()
        planes_data = self.__get_planes()

        prepared_planes = []

        for c_name, comp in preset.companies.items():
            for i in range(comp.planes_count):
                plane_volume = planes_data[random.choice(comp.allowed_models)].seats
                is_arriving = random.random() <= (comp.arriving_part / 100)
                plane = Plane(
                    name=self.__generate_flight_number(company_data[c_name].iata),
                    volume=plane_volume,
                    arrival_time=0,
                    departure_time=1000,
                    is_arriving=is_arriving,
                    passengers=self.__generate_passengers(
                        comp, plane_volume, is_arriving
                    ),
                )
                prepared_planes.append(plane)

        # @TODO - add arrival time to plane
        # get passengers from the ariving plane and shove them into the general pool

        return prepared_planes

    def __generate_flight_number(self, iata: str):
        number = random.randint(100, 9999)
        return f"{iata}{number}"

    def __generate_passengers(
        self, company: SimulationCompany, volume: int, is_arriving: bool
    ):
        result = []
        # age distribution
        age_weights = np.array(
            [company.children, company.young, company.middle, company.elderly]
        )
        age_probs = age_weights / age_weights.sum()
        age_values = np.random.multinomial(volume, age_probs)
        age_values = [i for i, c in enumerate(age_values) for _ in range(c)]

        # gender distribution
        gender_distribution = np.random.random(volume)
        gender_values = (
            (gender_distribution >= company.gender_ratio / 100).astype(int).tolist()
        )

        # 0 - age
        # 1 - gender
        # 2 - is arriving
        presets = list(
            zip(
                age_values,
                gender_values,
                [is_arriving] * volume,
            )
        )

        for i in presets:
            # before I knbow how to handle children i'll just remove them
            if i[0] < 1:
                continue
            new_ag = Agent(
                name=str(uuid.uuid4()),
                prompt=i,
            )
            result.append(new_ag)

        return result

    @with_orm_session
    def __get_planes(self, session=None):
        statement = select(PlaneTable)
        data = session.scalars(statement).all()
        result = {row.name: row for row in data}
        return result

    @with_orm_session
    def __get_companies(self, session=None):
        statement = select(Company).join(Country).distinct()
        data = session.scalars(statement).all()
        result = {row.name: row for row in data}
        return result

    def push(self, items: Union[SpawnerObject, Iterable]):
        with QMutexLocker(self.lock):
            if isinstance(items, SpawnerObject):
                heapq.heappush(self.agents, items)
                return

            seq = list(items)
            if not seq:
                return
            self.agents.extend(seq)
            heapq.heapify(self.agents)

    def pull(self, tick) -> List[SpawnerObject]:
        queue = []
        with QMutexLocker(self.lock):
            while self.agents and self.agents[0].tick <= tick:
                queue.append(heapq.heappop(self.agents))
        return queue
