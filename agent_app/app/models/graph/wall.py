import logging

from shapely.geometry import Polygon, LineString

from . import interactable


class Wall:
    def __init__(
        self, name, area, walls, interactables, enclosed=True, scale=1, step=1
    ):
        self.__name = name
        area = [
            (
                element["x"] * scale,
                element["y"] * scale,
            )
            for element in area
        ]
        if enclosed:
            area += [area[0]]
        self.__borders = Polygon(area)
        walls = [[x * scale for x in w] for w in walls]
        self.__walls = [LineString([w[:2], w[-2:]]) for w in walls]
        self.__interactables = None
        if interactables:
            self.__interactables = []
            for i in interactables:
                itr = None
                match i["name"].split("_")[0].lower():
                    case "entrance":
                        itr = interactable.Entrance(**i, scale=scale, step=step)
                    case "exit":
                        itr = interactable.Exit(**i, scale=scale, step=step)
                    case "gate":
                        itr = interactable.Gate(**i, scale=scale, step=step)
                    case "security":
                        itr = interactable.SecurityCheckpoint(
                            **i, scale=scale, step=step
                        )
                    case "baggage":
                        itr = interactable.BaggageReclaim(**i, scale=scale, step=step)
                    case "registration":
                        itr = interactable.RegistrationDesk(**i, scale=scale, step=step)
                    case _:
                        itr = interactable.Interactable(**i, scale=scale, step=step)
                        logging.warning("Unidentified interactable")
                self.__interactables.append(itr)

    @property
    def borders(self):
        return self.__borders

    @property
    def name(self):
        return self.__name

    @property
    def walls(self):
        return self.__walls

    @property
    def interactables(self):
        return self.__interactables

    # def move_interactable(self, idx: int, point: Point):
    #     if not self.interactables:
    #         return
    #     self.__interactables[idx].inlet_point = [
    #         point.x // self.__scale,
    #         point.y // self.__scale,
    #     ]
