from flask import jsonify, request
import logging


class ContainerPersistenceMixin:
    """Mixin for container persistence operations (save/load/import/export)."""

    def setup_persistence_routes(self):
        """Setup routes for container persistence operations."""
        self.app.add_url_rule("/save_containers", "save_containers", self.save_containers, methods=["POST"])
        self.app.add_url_rule("/load_containers", "load_containers", self.load_containers, methods=["POST"])
        self.app.add_url_rule("/import_containers", "import_containers", self.import_containers, methods=["POST"])
        self.app.add_url_rule("/export_selected", "export_selected", self.export_containers, methods=["POST"])
        self.app.add_url_rule(
            "/get_loadable_containers", "get_loadable_containers", self.get_loadable_containers, methods=["GET"]
        )
        self.app.add_url_rule("/delete_project", "delete_project", self.delete_project, methods=["POST"])

    def save_containers(self):
        """Save all containers to database."""
        data = request.get_json()
        project_name = data["project_name"]
        self.container_class.save_project_to_db(project_name)
        return jsonify({"message": "Containers saved successfully"})

    def load_containers(self):
        """Load containers from database."""
        data = request.get_json()
        project_name = data["project_name"]
        logging.info("Container name: " + project_name)
        status = self.container_class.load_project_from_db(project_name)
        logging.info("Status: " + status)
        return jsonify({"message": "Containers loaded successfully"})

    def import_containers(self):
        """Import additional containers into memory."""
        data = request.get_json()
        project_name = data["project_name"]
        logging.info("Container name: " + project_name)
        status = self.container_class.import_containers(project_name)
        logging.info("Status: " + status)
        return jsonify({"message": "Containers loaded successfully"})

    def export_containers(self):
        """Export selected containers to a file."""
        data = request.get_json()
        containerIds = data["containers"]
        containers = []

        for containerId in containerIds:
            container = self.container_class.get_instance_by_id(containerId)
            if container:
                containers.append(container)

        if containers:
            project_name = f'Export {containers[0].getValue("Name")} et al.'
            self.container_class.export_containers(project_name, containers)
            return jsonify({"message": "Containers exported successfully"})
        else:
            return jsonify({"message": "No containers to export"})

    def get_loadable_containers(self):
        """Return all loadable container projects."""
        containers = self.container_class.get_container_names_from_db()
        return jsonify({"containers": containers})

    def delete_project(self):
        """Delete a project from database."""
        from handlers.mongodb_handler import delete_project

        data = request.get_json() or {}
        project_name = data.get("project_name")
        if not project_name:
            return jsonify({"message": "No project_name provided"}), 400

        success = delete_project(project_name)
        if success:
            return jsonify({"message": "Project deleted successfully"})
        else:
            return jsonify({"message": "Failed to delete project"}), 500
