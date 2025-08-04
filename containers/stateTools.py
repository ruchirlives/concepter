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
        List all stored states. If "base" is not present, switch to it first.
        """
        if "allStates" not in self.values or not isinstance(self.values["allStates"], dict):
            self.values["allStates"] = {}

        if "base" not in self.values["allStates"]:
            self.switch_state("base")

        return list(self.values["allStates"].keys())

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

    def _check_relationship(self, relationship):
        """
        Check if the relationship is a dictionary and has a 'label' key.
        """
        if isinstance(relationship, dict) and "label" in relationship:
            return relationship
        elif isinstance(relationship, str):
            return {"label": relationship}
        return {"label": ""}

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
            # print(f"Comparing container {container_id} with relationship {relationship}")
            relationship_dict = self._check_relationship(relationship)
            relationship_label = relationship_dict["label"]
            if container_id not in base_dict:
                differences[container_id] = {
                    "status": "added",
                    "relationship": relationship_label,
                    "relationship_dict": relationship_dict,
                }
            else:
                base_relationship = base_dict[container_id]
                base_relationship_dict = self._check_relationship(base_relationship)
                base_relationship_label = self._check_relationship(base_relationship)["label"]
                if base_relationship_dict != relationship_dict:
                    differences[container_id] = {
                        "status": "changed",
                        "relationship": f"{base_relationship_label} -> {relationship_label}",
                        "relationship_dict": relationship_dict,
                        "base_relationship_dict": base_relationship_dict,
                    }

        # Track removed relationships
        for container_id, base_relationship in base_dict.items():
            if container_id not in current_dict:
                base_relationship_dict = self._check_relationship(base_relationship)
                relationship_label = base_relationship_dict["label"]
                differences[container_id] = {
                    "status": "removed",
                    "relationship": relationship_label,
                    "base_relationship_dict": base_relationship_dict,
                }

        return differences

    # Collect compare with base state for instances provided in array
    @classmethod
    def collect_compare_with_state(cls, instances: list, stateName: str = "base"):
        """
        Collect differences with base state from multiple instances.
        """
        differences_all = {}
        for instance in instances:
            if hasattr(instance, "compare_with_state"):
                differences = instance.compare_with_state(stateName)
                if differences:
                    differences_all[instance.getValue("id")] = differences
        return differences_all

    def apply_differences(self, differences: dict):
        """
        Apply the differences to self container in the current state.
        """
        # Get the differences specific to this container instance
        container_id = self.getValue("id")
        if container_id not in differences:
            return  # No differences for this container

        container_differences = differences[container_id]

        for child_container_id, change in container_differences.items():
            if change["status"] == "added":
                relationship_dict = change.get("relationship_dict", {})
                self.add_container_by_id(child_container_id, relationship_dict)
            elif change["status"] == "changed":
                relationship_dict = change.get("relationship_dict", {})
                # base_relationship_dict = change.get("base_relationship_dict", {})
                container = self.get_instance_by_id(child_container_id)
                if container:
                    self.update_container_relationship(child_container_id, relationship_dict)
            elif change["status"] == "removed":
                # base_relationship_dict = change.get("base_relationship_dict", {})
                self.remove_container_by_id(child_container_id)

    def revert_differences(self, differences: dict):
        """
        Revert the differences in the current state.
        """
        # Get the differences specific to this container instance
        container_id = self.getValue("id")
        if container_id not in differences:
            return  # No differences for this container

        container_differences = differences[container_id]

        for child_container_id, change in container_differences.items():
            if change["status"] == "added":
                self.remove_container_by_id(child_container_id)
            elif change["status"] == "changed":
                base_relationship_dict = change.get("base_relationship_dict", {})
                self.update_container_relationship(child_container_id, base_relationship_dict)
            elif change["status"] == "removed":
                relationship_dict = change.get("relationship_dict", {})
                self.add_container_by_id(child_container_id, relationship_dict)

    @classmethod
    def apply_differences_all(cls, instances: list, differences: dict):
        """
        Apply differences to all instances.
        """
        for instance in instances:
            if hasattr(instance, "apply_differences"):
                instance.apply_differences(differences)

    @classmethod
    def revert_differences_all(cls, instances: list, differences: dict):
        """
        Revert differences in all instances.
        """
        for instance in instances:
            if hasattr(instance, "revert_differences"):
                instance.revert_differences(differences)

    @classmethod
    def compute_propagated_change_scores(cls, container_delta: dict):
        """
        For each container, compute the sum of its own changes + all downstream changes recursively in `state`.
        Cycles are prevented via a visited set.
        """
        from container_base import baseTools
        scores = {}

        def count_own_changes(change_entry: dict) -> int:
            """
            Count the number of relationship changes in this container's diff entry.
            """
            if not change_entry:
                return 0
            return sum(1 for rel in change_entry.values() if rel.get("status") in {"added", "removed", "changed"})

        def recursive_score(container, visited):
            cid = container.getValue("id")
            if cid in visited:
                return 0

            visited.add(cid)

            score = count_own_changes(container_delta.get(cid, {}))

            # Get children in the target state
            child_ids = [child_id for child_id in baseTools.instances]

            for child_id in child_ids:
                child = baseTools.get_instance_by_id(child_id)
                if child:
                    score += recursive_score(child, visited)

            return score

        for container in baseTools.instances:
            visited = set()
            cid = container.getValue("id")
            scores[cid] = recursive_score(container, visited)

        return scores
