from flask import jsonify, request
import logging


class ContainerCRUDMixin:
    """Mixin for basic container CRUD operations."""

    def setup_container_crud_routes(self):
        """Setup routes for container CRUD operations."""
        self.app.add_url_rule("/get_container/<id>", "get_container", self.get_container, methods=["GET"])
        self.app.add_url_rule("/get_containers", "get_containers", self.get_containers, methods=["GET"])
        self.app.add_url_rule("/create_container", "create_container", self.create_container, methods=["GET"])
        self.app.add_url_rule("/rename_container/<id>", "rename_container", self.rename_container, methods=["GET"])
        self.app.add_url_rule("/delete_containers", "delete_containers", self.delete_containers, methods=["POST"])
        # remove containers from project
        self.app.add_url_rule("/remove_containers", "remove_containers", self.remove_containers, methods=["POST"])
        self.app.add_url_rule("/join_containers", "join_containers", self.join_containers, methods=["POST"])
        self.app.add_url_rule("/clear_containers", "clear_containers", self.clear_containers, methods=["GET"])
        self.app.add_url_rule(
            "/write_back_containers", "write_back_containers", self.write_back_containers, methods=["POST"]
        )
        # Add state management routes
        self.app.add_url_rule("/switch_state", "switch_state", self.switch_state, methods=["POST"])
        self.app.add_url_rule("/remove_state", "remove_state", self.remove_state, methods=["POST"])
        self.app.add_url_rule("/clear_states", "clear_states", self.clear_states, methods=["GET"])
        self.app.add_url_rule("/list_states", "list_states", self.list_states, methods=["GET"])
        self.app.add_url_rule("/compare_states", "compare_states", self.compare_states, methods=["POST"])
        self.app.add_url_rule("/apply_differences", "apply_differences", self.apply_differences, methods=["POST"])
        self.app.add_url_rule("/revert_differences", "revert_differences", self.revert_differences, methods=["POST"])
        self.app.add_url_rule(
            "/calculate_state_scores", "calculate_state_scores", self.calculate_state_scores, methods=["POST"]
        )
        # Add route for nodes
        self.app.add_url_rule("/load_node", "load_node", self.load_node, methods=["POST"])
        self.app.add_url_rule("/search_nodes", "search_nodes", self.search_nodes, methods=["POST"])

    def remove_containers(self):
        """API endpoint to remove containers from the project."""
        try:
            data = request.get_json()
            container_ids = data.get("container_ids", [])
            if not container_ids:
                return jsonify({"message": "No container IDs provided."}), 400

            for container_id in container_ids:
                self.container_class.remove_instance(container_id)

            return jsonify({"message": "Containers removed successfully."})
        except Exception as e:
            logging.error(f"Error removing containers: {e}")
            return jsonify({"message": "Error removing containers", "error": str(e)}), 500

    def search_nodes(self):
        """API endpoint to search nodes by a search term."""
        try:
            data = request.get_json()
            search_term = data.get("search_term", "")
            tags_to_match = data.get("tags", [])
            # Assumes self.container_class has a search_nodes method, or adapt as needed
            results = self.container_class.repository.search_nodes(search_term, tags=tags_to_match)
            return jsonify({"results": results})
        except Exception as e:
            logging.error(f"Error searching nodes: {e}")
            return jsonify({"message": "Error searching nodes", "error": str(e)}), 500

    def load_node(self):
        """API endpoint to load a single node from the repository by its id."""
        try:
            data = request.get_json()
            node_id = data.get("id")

            existing_instance = self.container_class.get_instance_by_id(node_id)
            if existing_instance:
                node = existing_instance
            else:
                node = self.container_class.repository.load_node(node_id)

            if node:
                export = self.serialize_container_info([node])
                return jsonify({"containers": export})
            else:
                return jsonify({"message": "Node not found"}), 404
        except Exception as e:
            logging.error(f"Error loading node {id}: {e}")
            return jsonify({"message": "Error loading node", "error": str(e)}), 500

    def compare_states(self):
        """Compare two arbitrary states for provided containers, without switching active state."""
        data = request.get_json()
        source_state = data.get("sourceState")
        target_state = data.get("targetState")
        containerIds = data.get("containerIds", [])
        if not source_state or not target_state:
            return jsonify({"message": "Both sourceState and targetState must be provided."}), 400

        containers = []
        for container_id in containerIds:
            container = self.container_class.get_instance_by_id(container_id)
            if not container:
                container = self.container_class.get_instance_by_name(container_id)
            if not container:
                try:
                    container = self.container_class.unpickle(container_id)
                except Exception as e:
                    logging.error(f"Failed to unpickle container {container_id}: {e}")
            containers.append(container)

        differences_all = {}
        for container in containers:
            if container:
                diff = container.compare_two_states(source_state, target_state)
                if diff:
                    differences_all[container.getValue("id")] = diff

        return jsonify({"differences_all": differences_all})

    def calculate_state_scores(self):
        """Calculate and print scores for all containers based on their differences."""
        data = request.get_json()
        baseState = data.get("baseState")

        from container_base import baseTools

        differences_all = self.container_class.collect_compare_with_state(baseTools.instances, baseState)

        scores = self.container_class.compute_propagated_change_scores(differences_all)

        for cid, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            container = baseTools.get_instance_by_id(cid)
            print(f"{container.getValue('Name')}: Propagated Score = {score}")

        return jsonify({"scores": scores})

    def switch_state(self):
        """Switch to a new state, saving the current containers."""
        try:
            data = request.get_json()
            newState = data.get("state")

            if not newState:
                return jsonify({"message": "No state provided"}), 400

            self.container_class.switch_state_all(newState)
            return jsonify({"message": f"Switched to state '{newState}' successfully"})
        except Exception as e:
            logging.error(f"Error switching state: {e}")
            return jsonify({"message": "Error switching state", "error": str(e)}), 500

    def remove_state(self):
        """Remove a state by its name."""
        try:
            data = request.get_json()
            stateName = data.get("state")

            if not stateName:
                return jsonify({"message": "No state name provided"}), 400

            self.container_class.remove_state_all(stateName)
            return jsonify({"message": f"State '{stateName}' removed successfully"})
        except Exception as e:
            logging.error(f"Error removing state: {e}")
            return jsonify({"message": "Error removing state", "error": str(e)}), 500

    def clear_states(self):
        """Clear all stored states."""
        try:
            self.container_class.clear_states_all()
            return jsonify({"message": "All states cleared successfully"})
        except Exception as e:
            logging.error(f"Error clearing states: {e}")
            return jsonify({"message": "Error clearing states", "error": str(e)}), 500

    def list_states(self):
        """List all stored states."""
        try:
            states = self.container_class.list_states_all()
            return jsonify({"states": states})
        except Exception as e:
            logging.error(f"Error listing states: {e}")
            return jsonify({"message": "Error listing states", "error": str(e)}), 500

    def get_container(self, id):
        """Return a single container by ID."""
        container = self.container_class.get_instance_by_id(id)
        if container:
            export = self.serialize_container_info([container])
            return jsonify({"containers": export})
        else:
            return jsonify({"message": "Container not found"}), 404

    def get_containers(self):
        """Return all containers."""
        from container_base import baseTools

        containers = baseTools.instances
        export = self.serialize_container_info(containers)
        return jsonify({"containers": export})

    def create_container(self):
        """Create a new empty container."""
        container = self.container_class()
        id = container.getValue("id")
        return jsonify({"message": "Container created successfully", "id": id})

    def rename_container(self, id):
        """Rename a container by ID using its description."""
        container = self.container_class.get_instance_by_id(id)
        if container:
            container.rename_from_description()
            return jsonify({"message": "Container renamed successfully"})
        else:
            return jsonify({"message": "Container not found"}), 404

    def delete_containers(self):
        """Delete multiple containers by their IDs."""
        data = request.get_json()
        containerIds = data["containers"]
        for containerId in containerIds:
            container = self.container_class.get_instance_by_id(containerId)
            if container:
                self.container_class.remove_container_everywhere(container)
        return jsonify({"message": "Containers deleted successfully"})

    def clear_containers(self):
        """Clear all containers from memory."""
        from container_base import baseTools

        baseTools.instances = []
        return jsonify({"message": "Containers cleared successfully"})

    def join_containers(self):
        """Join multiple containers into one."""
        from containers.conceptContainer import ConceptContainer

        data = request.get_json()
        container_ids = data.get("containers", [])
        if not container_ids:
            return jsonify({"message": "No container IDs provided"}), 400
        # Resolve to actual container objects
        containers = []
        for cid in container_ids:
            inst = self.container_class.get_instance_by_id(cid)
            if inst:
                containers.append(inst)
        if not containers:
            return jsonify({"message": "None of the provided IDs matched existing containers"}), 404

        # Create a new container to hold the joined content
        joined_container = ConceptContainer.join_containers(containers)
        return jsonify(
            {"message": "Containers joined successfully", "new_container_id": joined_container.getValue("id")}
        )

    def write_back_containers(self):
        """Update container properties from client data."""
        data = request.get_json()
        try:
            containers = data["containers"]
        except KeyError:
            return jsonify({"message": "No containers to write back"})

        for container in containers:
            target_container = self.container_class.get_instance_by_id(container.get("id"))
            if not target_container:
                target_container = self.container_class.get_instance_by_name(container.get("Name"))
            if not target_container:
                target_container = self.container_class()
                if target_container not in self.container_class.instances:
                    self.container_class.instances.append(target_container)

            # Write back values to target container
            for key, value in container.items():
                if key == "StartDate" or key == "EndDate":
                    value = target_container.parse_date_auto(value)
                elif key == "Tags":
                    if value is None:
                        value = ""
                    value = value.split(",")
                elif key == "id":
                    continue
                target_container.setValue(key, value)

        return jsonify({"message": "Containers written back successfully"})

    def apply_differences(self):
        """Apply differences to specified containers."""
        data = request.get_json()
        containerIds = data.get("containerIds", [])
        differences = data.get("differences", {})
        targetState = data.get("targetState", None)  # State to apply differences to

        if not containerIds:
            return jsonify({"message": "No container IDs provided"}), 400

        if not differences:
            return jsonify({"message": "No differences provided"}), 400

        try:
            # Store the current state to restore later
            original_state = None
            if targetState:
                # Get the current active state from any container instance
                if self.container_class.instances:
                    original_state = self.container_class.instances[0].getValue("activeState")
                # Switch to target state
                self.container_class.switch_state_all(targetState)
            # Get the containers for the specified IDs
            containers = []
            for container_id in containerIds:
                container = self.container_class.get_instance_by_id(container_id)
                if not container:
                    # Try to get the container by name if ID fails
                    container = self.container_class.get_instance_by_name(container_id)
                if not container:
                    # If still not found, try to unpickle the container
                    try:
                        container = self.container_class.unpickle(container_id)
                    except Exception as e:
                        logging.error(f"Failed to unpickle container {container_id}: {e}")
                        continue
                containers.append(container)

            # Apply differences to all found containers
            self.container_class.apply_differences_all(containers, differences)

            # Restore original state if we switched
            if targetState and original_state and original_state != targetState:
                self.container_class.switch_state_all(original_state)

            message = f"Differences applied to {len(containers)} containers successfully"
            if targetState:
                message += f" in state '{targetState}'"
            return jsonify({"message": message})

        except Exception as e:
            logging.error(f"Error applying differences: {e}")
            return jsonify({"message": "Error applying differences", "error": str(e)}), 500

    def revert_differences(self):
        """Revert differences from specified containers."""
        data = request.get_json()
        containerIds = data.get("containerIds", [])
        differences = data.get("differences", {})
        targetState = data.get("targetState", None)  # State to revert differences in

        if not containerIds:
            return jsonify({"message": "No container IDs provided"}), 400

        if not differences:
            return jsonify({"message": "No differences provided"}), 400

        try:
            # Store the current state to restore later
            original_state = None
            if targetState:
                # Get the current active state from any container instance
                if self.container_class.instances:
                    original_state = self.container_class.instances[0].getValue("activeState")
                # Switch to target state
                self.container_class.switch_state_all(targetState)
            # Get the containers for the specified IDs
            containers = []
            for container_id in containerIds:
                container = self.container_class.get_instance_by_id(container_id)
                if not container:
                    # Try to get the container by name if ID fails
                    container = self.container_class.get_instance_by_name(container_id)
                if not container:
                    # If still not found, try to unpickle the container
                    try:
                        container = self.container_class.unpickle(container_id)
                    except Exception as e:
                        logging.error(f"Failed to unpickle container {container_id}: {e}")
                        continue
                containers.append(container)

            # Revert differences from all found containers
            self.container_class.revert_differences_all(containers, differences)

            # Restore original state if we switched
            if targetState and original_state and original_state != targetState:
                self.container_class.switch_state_all(original_state)

            message = f"Differences reverted from {len(containers)} containers successfully"
            if targetState:
                message += f" in state '{targetState}'"
            return jsonify({"message": message})

        except Exception as e:
            logging.error(f"Error reverting differences: {e}")
            return jsonify({"message": "Error reverting differences", "error": str(e)}), 500
