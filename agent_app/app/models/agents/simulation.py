from pydantic import BaseModel


class SimulationCompany(BaseModel):
    # passengers
    children: int
    young: int
    middle: int
    elderly: int
    gender_ratio: int
    purposes: list[str]
    # planes
    planes_count: int
    average_time_between: int
    allowed_models: list[str]
    arriving_part: int
    internal_route: int


class Simulation(BaseModel):
    random_seed: int
    countries: list[str]
    companies: dict[str, SimulationCompany]
