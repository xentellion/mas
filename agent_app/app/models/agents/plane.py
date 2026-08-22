import logging


class Plane:
    def __init__(
        self,
        name: str,
        volume: int,
        arrival_time: int,
        departure_time: int,
        is_arriving: bool,
        expected_count: int,
        expected_passengers: list[str],
        passengers: list = None,
        will_turnaround: bool = False,
    ):
        self.__name = name
        self.__volume = volume
        self.__is_arriving = is_arriving
        self.arrival_time = arrival_time
        self.departure_time = departure_time
        self.expected_count = expected_count
        self.expected_passengers = expected_passengers
        self.__passengers = [] if passengers is None else passengers
        self.__ready_to_depart = False
        self.will_turnaround = will_turnaround

    @property
    def name(self):
        return self.__name

    @property
    def volume(self):
        return self.__volume

    @property
    def is_arriving(self):
        return self.__is_arriving

    @property
    def passengers(self):
        return self.__passengers

    @passengers.setter
    def passengers(self, data: list):
        if isinstance(data, list):
            self.__passengers = data

    @property
    def ready_to_depart(self):
        return self.__ready_to_depart

    @ready_to_depart.setter
    def ready_to_depart(self, value: bool):
        self.__ready_to_depart = value
        if self.is_arriving:
            logging.info(f"Plane '{self.name}' is ready for turnaround.")
        else:
            logging.info(f"Plane '{self.name}' is ready to take off.")

    def add_passenger(self, passenger):
        if self.ready_to_depart:
            return
        set_full = len(self.expected_passengers) - len(self.__passengers)
        if set_full <= 1:
            self.ready_to_depart = True
        self.__passengers.append(passenger.name)

    def pop_passenger(self):
        psg = self.passengers.pop()
        if self.is_arriving and not self.__passengers:
            self.ready_to_depart = True
        return psg
