from helpers.random_names import random_names
from containers.baseContainer import BaseContainer
from handlers.openai_handler import openai_handler


class StateContainer(BaseContainer):
    class_values = BaseContainer.class_values.copy()
    class_values.update({"State": {}, "allStates": {}, "activeState": "base"})
