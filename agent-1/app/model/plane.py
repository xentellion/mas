class Plane:
    def __init__(self, name, board_number, volume, departure_time):
        self.__name = name
        self.__board_number = board_number
        self.__volume = volume
        self.__departure_time = departure_time

    @property
    def name(self):
        return self.__name

    @property
    def board_number(self):
        return self.__board_number

    @property
    def volume(self):
        return self.__volume

    @property
    def departure_time(self):
        return self.__departure_time
