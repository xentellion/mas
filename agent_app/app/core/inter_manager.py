import logging


class InteractablesManager:
    # 0. Find better way to keep data on interactables - CHECK
    # 1. pass interactables from AreaRender
    # 2. re-reference them here everywhere else
    # 3. make sure its thread safe
    # 4. give it next functions:
    # - Select free gate - to give plane a place to dock and agents to go
    # - Probably here should be where I can set up arrival curve for agents
    # - Get all eleemnts of a single type in general (e.g. all registartion decks) - CHECK
    def __init__(self, interactables: dict, interactables_mapping: dict):
        self.__interactables = interactables
        self.__mapped_interactables = interactables_mapping

    def __getitem__(self, key: int | str):
        try:
            if isinstance(key, int):
                return self.__interactables[self.__mapped_interactables[key]]
            elif isinstance(key, str):
                return self.__interactables[key]
            else:
                return None
        except KeyError as e:
            logging.error(f"Interactable not found: {e}")
            return None

    def __get_items_of_type(self, interactable_type):
        result = dict(
            filter(
                lambda k, v: isinstance(v, interactable_type),
                self.__interactables.items(),
            )
        )
        return result
