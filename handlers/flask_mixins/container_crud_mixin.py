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
        self.app.add_url_rule("/clear_containers", "clear_containers", self.clear_containers, methods=["GET"])
        self.app.add_url_rule(
            "/write_back_containers", "write_back_containers", self.write_back_containers, methods=["POST"]
        )

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
