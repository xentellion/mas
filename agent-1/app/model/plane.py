class Plane:
    def __init__(
        self,
        name: str,
        gate: str,
        volume: int,
        departure_time: int,
        is_arriving: bool,
        passengers: list = None,
    ):
        self.__name = name
        self.__gate = gate
        self.__volume = volume
        self.__is_arriving = is_arriving
        self.departure_time = departure_time
        self.passengers = [] if passengers is None else passengers

    @property
    def name(self):
        return self.__name

    @property
    def gate(self):
        return self.__gate

    @property
    def volume(self):
        return self.__volume

    @property
    def is_arriving(self):
        return self.__is_arriving
