from flask import jsonify, request
import logging


class ContainerRelationshipMixin:
    """Mixin for container relationship and hierarchy operations."""

    def setup_relationship_routes(self):
        """Setup routes for container relationships."""
        self.app.add_url_rule("/get_parents/<id>", "get_parents", self.get_parents, methods=["GET"])
        self.app.add_url_rule("/children/<id>", "children", self.children, methods=["GET"])
        self.app.add_url_rule("/manyChildren", "manyChildren", self.manyChildren, methods=["POST"])
        self.app.add_url_rule("/add_children", "add_children", self.add_children, methods=["POST"])
        self.app.add_url_rule("/remove_children", "remove_children", self.remove_children, methods=["POST"])
        self.app.add_url_rule("/merge_containers", "merge_containers", self.merge_containers, methods=["POST"])
        self.app.add_url_rule("/get_position/<sourceId>/<targetId>", "get_position", self.get_position, methods=["GET"])
        self.app.add_url_rule("/set_position", "set_position", self.set_position, methods=["POST"])
        self.app.add_url_rule(
            "/get_subcontainers/<url_encoded_container_name>",
            "get_subcontainers",
            self.get_subcontainers,
            methods=["GET"],
        )

    def get_parents(self, id):
        """Return all parents of a container."""
        container = self.container_class.get_instance_by_id(id)
        parents = container.getParents()
        export = self.serialize_container_info(parents)
        return jsonify({"containers": export})

    def children(self, id):
        """Return all children of a container."""
        container = self.container_class.get_instance_by_id(id)
        children = container.getChildren()
        export = self.serialize_container_info(children)
        return jsonify({"containers": export})

    def manyChildren(self):
        """Return children for multiple containers."""
        data = request.get_json() or {}
        container_ids = set(data.get("container_ids", []))

        result = []
        for cid in container_ids:
            container = self.container_class.get_instance_by_id(cid)
            if not container:
                continue

            children = []
            for child, pos in container.getPositions():
                child_id = child.getValue("id")
                child_name = child.getValue("Name")
                if child_id is None:
                    continue

                children.append({"id": child_id, "name": child_name, "position": pos, "tags": child.getValue("Tags")})

            result.append({"container_id": cid, "children": children})

        return jsonify(result)

    def add_children(self):
        """Add children to a parent container."""
        from time import sleep

        sleep(0.05)

        data = request.get_json()
        children_ids = data["children_ids"]
        parent_id = data["parent_id"]
        container = self.container_class.get_instance_by_id(parent_id)

        print(container.getValue("Name"))
        print("Parent ID: " + str(parent_id))
        print("Children IDs: " + str(children_ids))

        for child_id in children_ids:
            child = self.container_class.get_instance_by_id(child_id)
            if child not in container.getChildren() and child != container:
                container.add_container(child)

        return jsonify({"message": "Children added successfully"})

    def remove_children(self):
        """Remove children from a parent container."""
        data = request.get_json()
        children_ids = data["children_ids"]
        parent_id = data["parent_id"]
        container = self.container_class.get_instance_by_id(parent_id)

        for child_id in children_ids:
            child = self.container_class.get_instance_by_id(child_id)
            container.remove_container(child)

        return jsonify({"message": "Children removed successfully"})

    def merge_containers(self):
        """Merge multiple containers into one."""
        data = request.get_json()
        containerIds = data["containers"]
        container = self.container_class.merge_containers(containerIds)

        if container:
            # self.container_class.instances.append(container)
            id = container.assign_id()
            container.setValue("id", id)
            return jsonify({"message": "Containers merged successfully", "id": id})
        else:
            return jsonify({"message": "No containers to merge"})

    def get_position(self, sourceId, targetId):
        """Return relationship positions between two containers."""
        source = self.container_class.get_instance_by_id(sourceId)
        target = self.container_class.get_instance_by_id(targetId)

        if source and target:
            position = source.getPosition(target)

            if isinstance(position, dict):
                position_dict = position

            else:
                position_dict = {"label": position}

            return jsonify(position_dict)
        else:
            return jsonify({"message": "Container not found"}), 404

    def set_position(self):
        """Set relationship position between two containers."""
        data = request.get_json()
        source = self.container_class.get_instance_by_id(data["source_id"])
        target = self.container_class.get_instance_by_id(data["target_id"])

        # First get the existing position if it exists
        existing_position = source.getPosition(target)
        if existing_position is not None:
            # If the position already exists, we can update it
            if isinstance(existing_position, dict):
                position = existing_position
            else:
                # Convert existing position to a dict if it's not already
                position = {"label": existing_position}
        else:
            # If no existing position, create a new one
            position = {}
        # Update the position with new data while preserving existing keys
        position.update(data.get("position", {}))

        if source and target:
            source.setPosition(target, position)
            return jsonify({"message": "Position set successfully"})
        else:
            return jsonify({"message": "Container not found"}), 404

    def get_subcontainers(self, url_encoded_container_name):
        """Return all subcontainers of a container by name."""
        container_name = url_encoded_container_name.replace("%20", " ")
        containers = self.container_class.get_instance_by_name(container_name).getChildren()
        export = self.serialize_container_info(containers)
        return jsonify({"containers": export})
