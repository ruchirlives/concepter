from flask import jsonify, request
import logging


class ContainerPersistenceMixin:
    """Mixin for container persistence operations (save/load/import/export)."""

    def setup_persistence_routes(self):
        """Setup routes for container persistence operations."""
        self.app.add_url_rule("/save_containers", "save_containers", self.save_containers, methods=["POST"])
        self.app.add_url_rule("/load_containers", "load_containers", self.load_containers, methods=["POST"])
        self.app.add_url_rule("/save_nodes", "save_nodes", self.save_nodes, methods=["POST"])
        self.app.add_url_rule("/import_containers", "import_containers", self.import_containers, methods=["POST"])
        self.app.add_url_rule("/export_selected", "export_selected", self.export_containers, methods=["POST"])
        self.app.add_url_rule("/export_branch", "export_branch", self.export_branch, methods=["POST"])
        self.app.add_url_rule(
            "/get_loadable_containers", "get_loadable_containers", self.get_loadable_containers, methods=["GET"]
        )
        self.app.add_url_rule("/delete_project", "delete_project", self.delete_project, methods=["POST"])

    def save_nodes(self):
        """Save all nodes to database."""
        data = request.get_json()
        nodes = data["nodes"]
        self.container_class.save_nodes_to_db(nodes)
        return jsonify({"message": "Nodes saved successfully"})

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
            project_name = f"Export {containers[0].getValue('Name')} et al."
            self.container_class.export_containers(project_name, containers)
            return jsonify({"message": "Containers exported successfully"})
        else:
            return jsonify({"message": "No containers to export"})

    def export_branch(self):
        """Export the selected containers and all their dependencies recursively."""

        from containers.baseContainer import BaseContainer
        data = request.get_json()
        containerIds = data.get("containers", [])
        containers = set()

        def recurse(container: BaseContainer):
            """Recursively find all dependencies of a container."""
            dependencies = container.containers
            for dep, _ in dependencies:
                if dep not in containers:
                    containers.add(dep)
                    recurse(dep)

        # Start recursion from the user-specified containers
        for containerId in containerIds:
            container = self.container_class.get_instance_by_id(containerId)
            if container and container not in containers:
                containers.add(container)
                recurse(container)

        containers = list(containers)
        if containers:
            project_name = f"Export {containers[0].getValue('Name')} et al."
            self.container_class.export_containers(project_name, containers)
            return jsonify({"message": "Containers exported successfully"})
        else:
            return jsonify({"message": "No containers to export"})

    def get_loadable_containers(self):
        """Return all loadable container projects."""
        containers = self.container_class.repository.list_project_names()
        return jsonify({"containers": containers})

    def delete_project(self):
        """Delete a project from database."""
        data = request.get_json() or {}
        project_name = data.get("project_name")
        if not project_name:
            return jsonify({"message": "No project_name provided"}), 400

        success = self.container_class.delete_project_from_db(project_name)
        if success:
            return jsonify({"message": "Project deleted successfully"})
        else:
            return jsonify({"message": "Failed to delete project"}), 500
