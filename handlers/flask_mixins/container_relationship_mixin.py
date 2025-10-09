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
        self.app.add_url_rule("/get_narratives", "get_narratives", self.get_narratives, methods=["GET"])
        self.app.add_url_rule("/inherit_positions", "inherit_positions", self.inherit_positions, methods=["POST"])

        # relationship routes
        self.app.add_url_rule("/get_relationships/<sourceId>", "get_relationships", self.get_relationships, methods=["GET"])
        self.app.add_url_rule("/add_relationship", "add_relationship", self.add_relationship, methods=["POST"])
        self.app.add_url_rule("/remove_relationship", "remove_relationship", self.remove_relationship, methods=["POST"])
        self.app.add_url_rule("/get_influencers", "get_influencers", self.get_influencers, methods=["POST"])
        self.app.add_url_rule(
            "/get_subcontainers/<url_encoded_container_name>",
            "get_subcontainers",
            self.get_subcontainers,
            methods=["GET"],
        )

    def get_influencers(self):
        """Return containers whose relationship pairs match the provided source/target ids."""

        data = request.get_json() or {}

        raw_pairs = data.get("pairs")
        if raw_pairs is None:
            # Backwards compatibility with the previous single-pair payload
            source_id = data.get("source_id")
            target_id = data.get("target_id")
            if source_id and target_id:
                raw_pairs = [(source_id, target_id)]
            else:
                return jsonify({"message": "At least one source_id/target_id pair is required"}), 400

        if isinstance(raw_pairs, (dict, tuple)):
            raw_pairs = [raw_pairs]
        elif not isinstance(raw_pairs, list):
            logging.warning("Expected 'pairs' to be a list, received %s", type(raw_pairs))
            return jsonify({"message": "pairs must be provided as a list"}), 400

        normalized_pairs = []
        seen = set()
        for pair in raw_pairs:
            src = tgt = None
            if isinstance(pair, dict):
                src = pair.get("source_id") or pair.get("source")
                tgt = pair.get("target_id") or pair.get("target")
            elif isinstance(pair, (list, tuple)) and len(pair) >= 2:
                src, tgt = pair[0], pair[1]
            else:
                logging.warning("Skipping malformed influencer pair: %s", pair)
                continue

            if not src or not tgt:
                logging.warning("Skipping influencer pair missing identifiers: %s", pair)
                continue

            normalized = (str(src), str(tgt))
            if normalized in seen:
                continue
            seen.add(normalized)
            normalized_pairs.append(normalized)

        if not normalized_pairs:
            return jsonify({"message": "No valid source/target pairs were provided"}), 400

        repository = getattr(self.container_class, "repository", None)
        if repository is None:
            logging.error("Container repository is not configured; cannot look up influencers")
            return jsonify({"message": "Container repository is not configured"}), 500

        try:
            influencer_map = repository.find_relationship_influencers(normalized_pairs)
        except NotImplementedError:
            logging.error("find_relationship_influencers is not implemented for this repository")
            return jsonify({"message": "Repository does not support influencer lookups"}), 501

        return jsonify(influencer_map)

    def get_relationships(self, sourceId):
        """Return all relationships of a container."""
        container = self.container_class.get_instance_by_id(sourceId)
        if not container:
            return jsonify({"message": "Container not found"}), 404

        relationships = []
        for src, tgt, pos in container.relationships:
            relationships.append(
                {"source_id": src.getValue("id"), "source_name": src.getValue("Name"), "target_id": tgt.getValue("id"), "target_name": tgt.getValue("Name"), "position": pos}
            )
        return jsonify(relationships)

    def add_relationship(self):
        """Add a reference to a relationship between two containers."""
        data = request.get_json()
        container_id = data["container_id"]
        source_id = data["source_id"]
        target_id = data["target_id"]
        position = data.get("position", {})

        container = self.container_class.get_instance_by_id(container_id)
        # source = self.container_class.get_instance_by_id(source_id)
        # target = self.container_class.get_instance_by_id(target_id)
        if not container:
            return jsonify({"message": "Container not found"}), 404
        container.add_relationship(source_id, target_id, position)

        # Immediately save container to the repository node if available
        repository = getattr(self.container_class, "repository", None)
        if repository:
            try:
                repository.save_node(container)
            except Exception as e:
                logging.error("Failed to save container after adding relationship: %s", e)

        return jsonify({"message": "Relationship added successfully"})

    def remove_relationship(self):
        """Remove a relationship between two containers."""
        data = request.get_json() or {}
        container_id = data.get("container_id")
        source_id = data.get("source_id")
        target_id = data.get("target_id")

        if not container_id or not source_id or not target_id:
            return jsonify({"message": "container_id, source_id and target_id are required"}), 400

        # Prefer operating directly on the repository node
        repository = getattr(self.container_class, "repository", None)
        if repository is not None:
            try:
                removed = repository.remove_relationship(container_id, str(source_id), str(target_id))
                if removed:
                    # Keep in-memory instance consistent if it exists, but don't persist
                    container_mem = self.container_class.get_instance_by_id(container_id)
                    if container_mem:
                        container_mem.remove_relationship(source_id, target_id)
                    return jsonify({"message": "Relationship removed successfully"})
            except Exception as e:
                logging.error("Repository remove_relationship failed: %s", e)

        # Fallback: update in-memory instance if loaded, then persist
        container = self.container_class.get_instance_by_id(container_id)
        if not container:
            # Couldn’t remove via repository and container not in memory
            return jsonify({"message": "Container not found"}), 404

        container.remove_relationship(source_id, target_id)

        if repository is not None:
            try:
                repository.save_node(container)
            except Exception as e:
                logging.error("Failed to save node after relationship removal: %s", e)

        return jsonify({"message": "Relationship removed successfully"})

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

    def inherit_positions(self):
        """Inherit positions from child containers with other group tagged containers if this container is tagged as a group."""
        data = request.get_json()
        container_id = data["container_id"]
        container = self.container_class.get_instance_by_id(container_id)

        if not container:
            return jsonify({"message": "Container not found"}), 404

        if "group" not in (container.getValue("Tags") or []):
            return jsonify({"message": "Container is not tagged as a group"}), 400

        children = container.getChildren()
        for child in children:
            child_tags = child.getValue("Tags") or []
            if "group" in child_tags:
                continue  # Skip if the child is also a group

            for related_container, position in child.getPositions():
                related_tags = related_container.getValue("Tags") or []
                if "group" not in related_tags or related_container == container:
                    continue  # Skip if the related container is not a group or the same as the parent

                existing_position = container.getPosition(related_container)
                if existing_position is None:
                    container.setPosition(related_container, position)

        return jsonify({"message": "Positions inherited successfully"})

    def get_narratives(self):
        """Return all relationships with narratives."""
        containers = self.container_class.get_all_instances()
        narratives = []
        for container in containers:
            for related_container, position in container.getPositions():
                if isinstance(position, dict) and "narrative" in position:
                    narratives.append(
                        {
                            "source_id": container.getValue("id"),
                            "source_name": container.getValue("Name"),
                            "target_id": related_container.getValue("id"),
                            "target_name": related_container.getValue("Name"),
                            "label": position.get("label", ""),
                        }
                    )
        return jsonify(narratives)

    def get_subcontainers(self, url_encoded_container_name):
        """Return all subcontainers of a container by name."""
        container_name = url_encoded_container_name.replace("%20", " ")
        containers = self.container_class.get_instance_by_name(container_name).getChildren()
        export = self.serialize_container_info(containers)
        return jsonify({"containers": export})
