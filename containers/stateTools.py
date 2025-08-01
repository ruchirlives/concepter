import copy
from containers.baseContainer import Container


class StateTools(Container):
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
        containers = copy.deepcopy(self.containers)

        # Save the current state
        self.values["allStates"][activeState] = containers

        # Swap for the new state
        if newState in self.values["allStates"]:
            # grab it from the existing states
            self.containers = copy.deepcopy(self.values["allStates"][newState])
        else:
            # store the newState with the current containers set
            self.values["allStates"][newState] = containers

        # Set the new active state
        self.values["activeState"] = newState

    def remove_state(self, stateName: str):
        """
        Remove a state by its name.
        """
        if "allStates" in self.values and isinstance(self.values["allStates"], dict):
            if stateName in self.values["allStates"]:
                del self.values["allStates"][stateName]

    def clear_states(self):
        """
        Clear all stored states.
        """
        if "allStates" in self.values and isinstance(self.values["allStates"], dict):
            self.values["allStates"].clear()
            self.values["activeState"] = "base"
