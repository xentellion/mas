from pydantic import BaseModel


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
