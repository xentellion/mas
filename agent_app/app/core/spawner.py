import logging
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
class SpawnerPlane(NamedTuple):
    tick: int
    agent: Plane

    def __eq__(self, other):
        return self.tick == other.tick

    def __lt__(self, other):
        return self.tick < other.tick


@total_ordering
class SpawnerAgent(NamedTuple):
    tick: int
    agent: list[Agent]
    plane_name: str
    gate: str = None

    def __eq__(self, other):
        return self.tick == other.tick

    def __lt__(self, other):
        return self.tick < other.tick


class Spawner:
    def __init__(self):
        self.planes: List[SpawnerPlane] = []
        self.agents: List[SpawnerPlane] = []
        self.lock = QMutex()

    def generate(self):
        data = self.generate_agents()
        if not data:
            return False

        self.push_plane(
            (
                SpawnerPlane(
                    tick=x.arrival_time,
                    agent=x,
                )
                for x in data
            )
        )

        return True

    def generate_agents(self) -> tuple(tuple(list), list):
        if GLOBAL_STATE.simulation is None:
            logging.error("Generating empty sim")
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
                passengers, names = self.__generate_passengers(
                    comp, plane_volume, is_arriving
                )

                plane = Plane(
                    name=self.__generate_flight_number(company_data[c_name].iata),
                    volume=plane_volume,
                    arrival_time=0,
                    departure_time=1000,
                    is_arriving=is_arriving,
                    # In case of possible overbooking
                    expected_count=min(len(passengers), plane_volume),
                    expected_passengers=names,
                    passengers=passengers,
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

        name_list = []

        for i in presets:
            # before I knbow how to handle children i'll just remove them
            if i[0] < 1:
                continue
            name = str(uuid.uuid4())
            new_ag = Agent(
                name=name,
                prompt=i,
            )
            name_list.append(name)
            result.append(new_ag)

        return result, name_list

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

    def push_plane(self, items: Union[SpawnerPlane, Iterable]):
        with QMutexLocker(self.lock):
            if isinstance(items, SpawnerPlane):
                heapq.heappush(self.planes, items)
                return

            seq = list(items)
            if not seq:
                return
            self.planes.extend(seq)
            heapq.heapify(self.planes)

    def pull_planes(self, tick) -> List[SpawnerPlane]:
        queue = []
        with QMutexLocker(self.lock):
            while self.planes and self.planes[0].tick <= tick:
                queue.append(heapq.heappop(self.planes))
        return queue

    def push_agents(self, current_tick: int, plane: Plane, gate: str):
        with QMutexLocker(self.lock):
            items = plane.passengers
            # @TODO - reconsider shuffle when in groups. Use tuples?
            random.shuffle(items)

            min_time = 3
            max_time = 50
            vals = self.skewed_bell_range(
                min_time,
                max_time,
                n=len(items),
                skew=4.0,
            )
            vals = np.asarray(vals, dtype=int) + current_tick

            data = []
            for i in range(len(items)):
                data.append(
                    SpawnerAgent(
                        tick=vals[i],
                        agent=items[i],
                        plane_name=plane.name,
                        gate=gate,
                    )
                )

            if isinstance(data, SpawnerPlane):
                heapq.heappush(self.agents, data)
                return
            seq = list(data)
            if not seq:
                return
            self.agents.extend(seq)
            heapq.heapify(self.agents)

    def pull_agents(self, tick) -> List[SpawnerPlane]:
        queue = []
        with QMutexLocker(self.lock):
            while self.agents and self.agents[0].tick <= tick:
                queue.append(heapq.heappop(self.agents))
        return queue

    def skewed_bell_range(self, low, high, n=1000, skew=4.0, rng=None):
        if rng is None:
            rng = np.random.default_rng()

        if low > high:
            low, high = high, low

        if n <= 0:
            return np.array([], dtype=int)

        # Center the distribution inside [low, high]
        center = (low + high) / 2.0
        spread = max((high - low) / 6.0, 1.0)

        # Skew-normal sample
        delta = skew / np.sqrt(1 + skew**2)
        u0 = rng.normal(size=n)
        u1 = rng.normal(size=n)
        x = center + spread * (delta * np.abs(u0) + np.sqrt(1 - delta**2) * u1)

        # Convert to integers and keep them inside the requested bounds
        x = np.rint(x).astype(int)
        x = np.clip(x, low, high)
        return x
