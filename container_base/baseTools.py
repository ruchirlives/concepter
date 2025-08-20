import random
from dateutil.parser import parse
import uuid
import copy


class baseTools:
    instances = []
    random_names = {}
    class_values = {
        "id": None,  # Unique identifier for the container
        "Name": "Unnamed",
    }

    def __init__(self):
        # Set default values
        self.containers = []
        self.values = copy.deepcopy(self.class_values)

        # Generate id as a has of current time
        self.assign_id()

        baseTools.instances.append(self)

    @classmethod
    def set_instances(cls, new_instances):
        baseTools.instances = list(new_instances)  # explicitly refer to base class

    def assign_id(self):
        unique_id = str(uuid.uuid4())
        self.setValue("id", unique_id)
        return unique_id

    @classmethod
    def list_ids(cls):
        """
        Returns a list of all container IDs.
        :return: List of container IDs.
        """
        ids = [container.getValue("id") for container in cls.instances]
        print(ids)

    @classmethod
    def random_name(cls):
        """
        Generates a random name for a container using a combination of adjectives and nouns.

        :return: A random name string.
        """
        if not cls.random_names:
            print("Error: Adjectives and nouns lists are empty.")
            return "Unnamed"

        adjectives = cls.random_names["adjectives"]
        nouns = cls.random_names["nouns"]

        return f"{random.choice(adjectives)} {random.choice(nouns)}"

    # @property
    # def name(self):
    #     return self.getValue("Name")

    # @name.setter
    # def name(self, value):
    #     self.setValue("Name", value)

    # @property
    # def Description(self):
    #     return self.getValue("Description")

    @classmethod
    def get_instance_by_name(cls, name):
        for instance in cls.instances:
            if instance.getValue("Name") == name:
                return instance
        return None

    @classmethod
    def get_instance_by_id(cls, id):
        for instance in cls.instances:
            # Check if the id is a string or an integer
            id = str(id)
            cid = str(instance.getValue("id"))

            if cid == id:
                return instance
        return None

    @classmethod
    def get_all_subclasses(cls):
        subclasses = cls.__subclasses__()
        for subclass in subclasses:
            subclasses += subclass.get_all_subclasses()
        return set(subclasses)

    @classmethod
    def get_container(cls, container_name):
        for container in cls.instances:
            # find any case match inside the container name
            if container_name.lower() in container.getValue("Name").lower():
                return container
        return None

    def delete(self):
        # Remove the container from the list of containers
        self.remove_container_everywhere(self)
        print(f"Deleted container: {self.getValue("Name")}")

    @classmethod
    def remove_container_everywhere(cls, container_obj):
        cls.instances.remove(container_obj)
        # Iterate through all existing containers and remove any references to the deleted container in it subcontainers
        for container in cls.instances:
            container.remove_container(container_obj)

    # Just remove from the project
    @classmethod
    def remove_container(cls, container_obj):
        cls.instances.remove(container_obj)

    @classmethod
    def get_all_subcontainers(cls, container_id):
        container = cls.instances[container_id]
        subcontainers = container.getChildren()
        return subcontainers

    def setValue(self, key, value):
        self.values[key] = value

    def getValue(self, key, ifNone=None):
        return self.values.get(key, ifNone)

    def getParents(self):
        parents = []
        cls = type(self)
        for container in cls.instances:
            if container.checkDirectDescendents(self):
                parents.append(container)
        return parents

    def getChildren(self):
        children = []
        for container, position in self.containers:
            children.append(container)
        return children

    def getPositions(self):
        positions = []
        for container, position in self.containers:
            positions.append((container, position))
        return positions

    def getPosition(self, target):
        # Get the position of the target container
        for container, pos in self.containers:
            if container == target:
                return pos
        return None

    def setPosition(self, target, position):
        # Set the position of the target container
        print(f"Setting position of {target.getValue("Name")} to {position}")
        for i, (container, pos) in enumerate(self.containers):
            if container == target:
                self.containers[i] = (container, position)
                return True

        # If target is not found, add it to the list with the new position
        self.containers.append((target, position))
        return False

    def clone_container(self):
        """
        Creates a deep copy of the container instance.
        :return: A new instance of the container with copied attributes.
        """
        new_container = self.clone_single_container()

        for container, position in self.containers:
            cloned_subcontainer = container.clone_container()
            new_container.containers.append((cloned_subcontainer, position))
            self.instances.remove(cloned_subcontainer)  # Remove the original container from the instances list

        return new_container

    def clone_single_container(self):
        """
        Creates a shallow copy of the container instance.
        :return: A new instance of the container with copied attributes.
        """
        # Clone the stream into a new container
        new_container = self.__class__()
        new_container.__dict__.update({k: v for k, v in self.__dict__.items()})

        # Deepcopy the values array
        new_container.values = copy.deepcopy(self.values)
        new_container.containers = []

        name = f"{self.getValue('Name')} (Clone)"
        new_container.setValue("Name", name)

        # unique id
        new_container.assign_id()

        return new_container

    @classmethod
    def rekey_all_ids(cls):
        # Iterate through all existing containers and rekey their IDs as integers
        # first get all containers even ones that are not in the cls.instances list
        all_containers = cls.get_all_containers()
        for container in all_containers:
            # Generate a new integer ID for the container
            new_id = container.assign_id()

            # Check if the new ID already exists in the container's ID list
            container.setValue("id", new_id)

        print("All container IDs have been rekeyed.")

        # Check if the IDs are unique
        ids = [container.getValue("id") for container in all_containers]
        if len(ids) != len(set(ids)):
            print("Warning: Duplicate IDs found after rekeying.")

    @classmethod
    def recopy_values(cls):
        """
        Ensures all container values are deep copied and not shared between instances.
        This method recreates the values dictionary for each container to prevent
        unintended sharing of mutable objects.
        """
        # Get all containers even ones that are not in the cls.instances list
        all_containers = cls.get_all_containers()
        for container in all_containers:
            # Create a deep copy of the current values to ensure no sharing
            container.values = copy.deepcopy(container.values)

        print(f"All container values have been deep copied. {len(all_containers)} containers processed.")

    # deduplicate_all
    @classmethod
    def deduplicate_all(cls, keep_last=True):
        """
        Deduplicate all containers by removing duplicates based on their IDs.
        :param keep_last: If True, keeps the last occurrence of each ID (default, useful for imports).
        If False, keeps the first occurrence.
        """
        seen_ids = set()
        unique_containers = []

        containers_to_process = reversed(cls.instances) if keep_last else cls.instances

        for container in containers_to_process:
            container_id = container.getValue("id")
            if container_id not in seen_ids:
                seen_ids.add(container_id)
                unique_containers.append(container)

        # If we processed in reverse, reverse back to maintain original order
        if keep_last:
            unique_containers = list(reversed(unique_containers))

        cls.instances = unique_containers
        keep_type = "last" if keep_last else "first"
        print(f"Deduplication complete (keeping {keep_type}). {len(cls.instances)} unique containers remain.")

    @classmethod
    def get_all_containers(cls):
        all_containers = set()
        visited = set()

        def add_container(container):
            if container in visited:
                return
            visited.add(container)
            all_containers.add(container)
            for child in container.getChildren():
                add_container(child)

        for container in cls.instances:
            cls.recurseFunc(container, add_container)

        return list(all_containers)  # ✅ convert back to list before returning

    def recurseFunc(self, func, max_depth=5, current_depth=0, visited=None):
        if visited is None:
            visited = set()

        if current_depth >= max_depth or self in visited:
            return

        visited.add(self)
        func(self)  # apply before recursing

        for container in self.containers:
            obj = container[0]
            obj.recurseFunc(func, max_depth, current_depth + 1, visited)

    def checkIsAnyDescendent(self, source_containers):
        for container in source_containers:
            if self.checkIsDescendent(container):
                return True
        return False

    def checkIsDescendent(b, a, depth_limit=4, current_depth=0):
        """
        Checks if b is a descendent of a with a recursion depth limit.
        :param a: The container to search within.
        :param depth_limit: Maximum recursion depth allowed.
        :param current_depth: Current depth of recursion (used internally).
        :return: True if b is a descendent of a, False otherwise.
        """
        # Stop recursion if depth limit is reached
        if current_depth > depth_limit:
            return False

        for child_container, pos in b.containers:
            if child_container is a:
                return True
            if child_container.checkIsDescendent(a, depth_limit, current_depth + 1):
                return True

        return False  # Return False if no match found

    def checkAncestor(self):
        # target container must have an ancestor in self.containers
        for target_container in self.instances:
            if self.checkIsDescendent(target_container):
                return True
        return False

    def checkIsCloseRelation(self, source_container):
        """
        Checks if self is a direct descendent or a sibling of source_container.
        :param source_container: The container to search within.
        :return: True if self is a direct descendent or a sibling of source_container, False otherwise.
        """
        # First check if it is the same container
        if self == source_container:
            return True
        # First loop through parents
        parents = self.getParents()
        for parent in parents:
            if parent == source_container:
                return True
        # Then loop through children
        children = self.getChildren()
        for child in children:
            if child == source_container:
                return True
        return False

    def checkIsChild(self):
        cls = type(self)
        for container in cls.instances:
            if self in container.getChildren():
                return True
        return False

    def checkDirectDescendents(self, source_container):
        for container, position in self.containers:
            if container == source_container:
                return True
        return False

    def add_container(self, child_container, position=None):
        # First check child_if the child_container is already in the descendents
        if child_container.checkIsDescendent(self):
            print("Note: container is already in the descendents")

        # Add the container to the listchild_ of containers
        self.containers.append((child_container, position))

    def remove_container(self, container):
        # Remove the container from the list of containers
        self.containers = [c for c in self.containers if c[0] != container]

    def parse_date_auto(self, input_string):
        if not input_string:
            return None
        try:
            # Automatically parse the input string into a date
            return parse(input_string).date()
        except ValueError:
            # Handle invalid formats
            print(f"Invalid date input: {input_string}")
            return None
