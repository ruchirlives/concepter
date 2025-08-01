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
        self.app.add_url_rule("/join_containers", "join_containers", self.join_containers, methods=["POST"])
        self.app.add_url_rule("/clear_containers", "clear_containers", self.clear_containers, methods=["GET"])
        self.app.add_url_rule(
            "/write_back_containers", "write_back_containers", self.write_back_containers, methods=["POST"]
        )
        # Add state management routes
        self.app.add_url_rule("/switch_state/<newState>", "switch_state", self.switch_state, methods=["GET"])
        self.app.add_url_rule("/remove_state/<stateName>", "remove_state", self.remove_state, methods=["GET"])
        self.app.add_url_rule("/clear_states", "clear_states", self.clear_states, methods=["GET"])
        self.app.add_url_rule("/list_states", "list_states", self.list_states, methods=["GET"])

    def switch_state(self, newState):
        """Switch to a new state, saving the current containers."""
        try:
            self.container_class.switch_state_all(newState)
            return jsonify({"message": f"Switched to state '{newState}' successfully"})
        except Exception as e:
            logging.error(f"Error switching state: {e}")
            return jsonify({"message": "Error switching state", "error": str(e)}), 500

    def remove_state(self, stateName):
        """Remove a state by its name."""
        try:
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
        from containers.baseContainer import ConceptContainer

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
                elif key in ("TimeRequired", "Impact", "Effort"):
                    if value:
                        value = float(value)
                elif key == "Tags":
                    if value is None:
                        value = ""
                    value = value.split(",")
                elif key == "id":
                    continue
                target_container.setValue(key, value)

        return jsonify({"message": "Containers written back successfully"})
