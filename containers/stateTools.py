import copy


class StateTools:
    """
    Each state entry stores the .containers value against the its named key.
    """

    def switch_state(self, newState: str):
        """
        Store the current .containers in the state under the given key.
        """
        # Ensure allStates exists and is a dictionary
        if "allStates" not in self.values or not isinstance(self.values["allStates"], dict):
            self.values["allStates"] = {}

        # Get a copy of the current containers
        activeState = self.getValue("activeState")
        if not activeState:
            activeState = "base"

        # Create a lightweight representation using container IDs with object ID backup
        containers_state = []
        for container, relationship in self.containers:
            # Use container ID as primary, object ID as backup for same-session reliability
            container_id = container.getValue("id")
            container_object_id = id(container)
            # Deep copy only the relationship dict, not the container
            relationship_copy = copy.deepcopy(relationship) if relationship else None
            containers_state.append((container_id, container_object_id, relationship_copy))

        # Save the current state
        self.values["allStates"][activeState] = containers_state

        # Swap for the new state
        if newState in self.values["allStates"]:
            # Reconstruct containers from saved state
            self.containers = []
            saved_state = self.values["allStates"][newState]
            for container_id, container_object_id, relationship in saved_state:
                # Try object ID first (fast, works if no pickle/unpickle happened)
                container = None
                for inst in self.__class__.instances:
                    if id(inst) == container_object_id:
                        container = inst
                        break

                # Fall back to container ID if object ID fails (after pickle/unpickle)
                if not container:
                    container = self.__class__.get_instance_by_id(container_id)

                if container:
                    self.containers.append((container, relationship))
        else:
            # store the newState with the current containers set
            self.values["allStates"][newState] = containers_state

        # Set the new active state
        self.values["activeState"] = newState

    @classmethod
    def switch_state_all(cls, newState: str):
        """
        Switch state for all container instances.
        """
        for instance in cls.instances:
            if hasattr(instance, "switch_state"):
                instance.switch_state(newState)

    def remove_state(self, stateName: str):
        """
        Remove a state by its name.
        """
        if "allStates" in self.values and isinstance(self.values["allStates"], dict):
            if stateName in self.values["allStates"]:
                del self.values["allStates"][stateName]

    @classmethod
    def remove_state_all(cls, stateName: str):
        """
        Remove a state from all container instances.
        """
        for instance in cls.instances:
            if hasattr(instance, "remove_state"):
                instance.remove_state(stateName)

    def clear_states(self):
        """
        Clear all stored states.
        """
        if "allStates" in self.values and isinstance(self.values["allStates"], dict):
            self.values["allStates"].clear()
            self.values["activeState"] = "base"

    @classmethod
    def clear_states_all(cls):
        """
        Clear states for all container instances.
        """
        for instance in cls.instances:
            if hasattr(instance, "clear_states"):
                instance.clear_states()

    def list_states(self):
        """
        List all stored states.
        """
        if "allStates" in self.values and isinstance(self.values["allStates"], dict):
            return list(self.values["allStates"].keys())
        return []

    @classmethod
    def list_states_all(cls):
        """
        List states from the first available container instance.
        """
        for instance in cls.instances:
            if hasattr(instance, "list_states"):
                return instance.list_states()
        return []

    # Compare with base state
    def compare_with_state(self, stateName: str = "base"):
        """
        Compare the current state with the base state.
        Returns a dictionary of differences.
        """
        base_state = self.getValue("allStates").get(stateName, [])
        current_state = self.getValue("allStates").get(self.getValue("activeState"), [])

        differences = {}

        # Convert states to dictionaries for easier comparison
        base_dict = {container_id: relationship for container_id, container_object_id, relationship in base_state}
        current_dict = {container_id: relationship for container_id, container_object_id, relationship in current_state}

        # Track added and changed container relationships
        for container_id, relationship in current_dict.items():
            relationship_label = relationship["label"] if relationship else "unspecified"
            if container_id not in base_dict:
                differences[container_id] = {"status": "added", "relationship": relationship_label}
            else:
                base_relationship = base_dict[container_id]
                base_relationship_label = base_relationship["label"] if base_relationship else "unspecified"
                if base_relationship != relationship:
                    differences[container_id] = {
                        "status": "changed",
                        "relationship": f"{base_relationship_label} -> {relationship_label}",
                    }

        # Track removed relationships
        for container_id, relationship in base_dict.items():
            if container_id not in current_dict:
                relationship_label = relationship["label"] if relationship else "unspecified"
                differences[container_id] = {"status": "removed", "relationship": relationship_label}

        return differences

    # Collect compare with base state for instances provided in array
    @classmethod
    def collect_compare_with_state(cls, instances: list, stateName: str = "base"):
        """
        Collect differences with base state from multiple instances.
        """
        collected_differences = {}
        for instance in instances:
            if hasattr(instance, "compare_with_state"):
                differences = instance.compare_with_state(stateName)
                if differences:
                    collected_differences[instance.getValue("id")] = differences
        return collected_differences
