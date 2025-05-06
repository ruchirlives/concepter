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
        gc.collect()  # Force garbage collection
        seen_ids = set()  # Track unique object IDs
        all_objs = []
        for obj in gc.get_objects():
            try:
                if isinstance(obj, cls) and id(obj) not in seen_ids:
                    all_objs.append(obj)
                    seen_ids.add(id(obj))  # Avoid duplicates
            except ReferenceError:
                pass  # Skip objects that may have been garbage collected
        return all_objs
