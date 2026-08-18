class Plane:
    def __init__(
        self,
        name: str,
        volume: int,
        arrival_time: int,
        departure_time: int,
        is_arriving: bool,
        passengers: list = None,
    ):
        self.__name = name
        self.__volume = volume
        self.__is_arriving = is_arriving
        self.arrival_time = arrival_time
        self.departure_time = departure_time
        self.passengers = [] if passengers is None else passengers

    @property
    def name(self):
        return self.__name

    @property
    def volume(self):
        return self.__volume

    @property
    def is_arriving(self):
        return self.__is_arriving
