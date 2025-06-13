from .baseTools import baseTools
import gc

# from random_names import random_names


class Container(baseTools):
    """
    Inherit from this class to create a new container type.
    Need to set class_values to define the default values for the container.
    Need to set random_names to define the random names for the container.
    And any custom methods can be added here.
    """

    # instances = baseTools.instances

    def __init__(self):
        super().__init__()

    def log(self, message):
        print(message)
        if hasattr(self, "app"):
            if hasattr(self.app, "addline"):
                self.app.addline(message)

    @classmethod
    def get_all_instances(cls):
        # gc.collect()  # Force garbage collection
        seen_ids = set()  # Track unique object IDs

        def recurse(inst, seen_ids=seen_ids):
            if inst is None:
                return
            if inst not in seen_ids:
                seen_ids.add(inst)
                for child, _ in inst.containers:
                    recurse(child, seen_ids)

        for inst in cls.instances:
            recurse(inst)

        return seen_ids
