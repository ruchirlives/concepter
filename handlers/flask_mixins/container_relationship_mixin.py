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
        self.app.add_url_rule(
            "/add_children_batch", "add_children_batch", self.add_children_batch, methods=["POST"]
        )
        self.app.add_url_rule("/remove_children", "remove_children", self.remove_children, methods=["POST"])
        self.app.add_url_rule(
            "/apply_instruction_set",
            "apply_instruction_set",
            self.apply_instruction_set,
            methods=["POST"],
        )
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
        self._add_children_to_parent(parent_id, children_ids)

        return jsonify({"message": "Children added successfully"})

    def _add_children_to_parent(self, parent_id, children_ids):
        """Internal helper that encapsulates the existing add-children behavior."""
        container = self.container_class.get_instance_by_id(parent_id)

        print(container.getValue("Name"))
        print("Parent ID: " + str(parent_id))
        print("Children IDs: " + str(children_ids))

        for child_id in children_ids:
            child = self.container_class.get_instance_by_id(child_id)
            if child not in container.getChildren() and child != container:
                container.add_container(child)

    def add_children_batch(self):
        """Add children for many parents, mirroring the single add_children behavior per mapping."""
        data = request.get_json() or {}
        mappings = data.get("mappings")

        if not isinstance(mappings, list):
            return jsonify({"success": False, "message": "mappings must be provided as a list"}), 400

        results = []
        overall_success = True

        for mapping in mappings:
            parent_id = None
            children_ids = None
            if isinstance(mapping, dict):
                parent_id = mapping.get("parent_id")
                children_ids = mapping.get("children_ids")

            result = {"parent_id": parent_id}

            if not isinstance(mapping, dict):
                result["success"] = False
                result["message"] = "Each mapping must be an object with parent_id and children_ids"
                overall_success = False
                results.append(result)
                continue

            if not parent_id or not isinstance(children_ids, list):
                result["success"] = False
                result["message"] = "Each mapping must include parent_id and a list of children_ids"
                overall_success = False
                results.append(result)
                continue

            try:
                self._add_children_to_parent(parent_id, children_ids)
            except Exception as exc:
                logging.exception("Failed to add children for parent %s", parent_id)
                result["success"] = False
                result["message"] = str(exc)
                overall_success = False
                results.append(result)
                continue

            result["success"] = True
            results.append(result)

        response_body = {"results": results}
        if not overall_success:
            response_body["success"] = False
            response_body["message"] = "One or more mappings failed"

        return jsonify(response_body)

    def apply_instruction_set(self):
        """Apply a batch of structural instructions to containers.

        The endpoint accepts either a raw JSON array or an object with an
        ``instructions`` key whose value is the array. Each instruction can be
        expressed as:

        * A list/tuple where the first element is the action name followed by
          optional arguments. Arguments may be provided directly (e.g. ``[
          "remove", "123" ]``) or wrapped in single-element lists (e.g. ``[
          "remove", ["123"] ]``) to match the original client payload pattern.
        * A dict with ``action`` (or ``type``) plus optional ``id``, ``childId``
          and ``label`` keys.

        Placeholder IDs (e.g. ``temp-123``) are supported for newly created
        containers. The backend will generate the real identifier, store a
        placeholder mapping, and rewrite subsequent instructions within the same
        request.
        """

        payload = request.get_json() or {}
        instructions = payload.get("instructions") if isinstance(payload, dict) else payload

        if not isinstance(instructions, list):
            return jsonify({"success": False, "message": "instructions must be provided as a list"}), 400

        results = []
        overall_success = True
        placeholder_map = {}

        for index, raw_instruction in enumerate(instructions):
            normalized = self._normalize_instruction(raw_instruction)
            if normalized is None:
                overall_success = False
                results.append(
                    {
                        "success": False,
                        "message": f"Instruction at index {index} is malformed; expected list/tuple or dict",
                    }
                )
                continue

            try:
                success, message = self._apply_single_instruction(
                    placeholder_map=placeholder_map, **normalized
                )
            except Exception as exc:  # pragma: no cover - safety net
                logging.exception("Failed to apply instruction %s", normalized)
                success = False
                message = str(exc)

            if not success:
                overall_success = False

            results.append(
                {
                    "success": success,
                    "message": message,
                    "action": normalized.get("action"),
                }
            )

        if placeholder_map:
            self._rewrite_placeholders_in_instances(placeholder_map)

        response_body = {"success": overall_success, "results": results}
        if placeholder_map:
            response_body["placeholderMapping"] = placeholder_map

        return jsonify(response_body), (200 if overall_success else 400)

    def _normalize_instruction(self, raw_instruction):
        """Return a dict with action, target_id, child_id and label extracted from list/tuple/dict."""

        action = target_id = child_id = label = None

        if isinstance(raw_instruction, (list, tuple)):
            if not raw_instruction:
                return None
            action = raw_instruction[0]
            if len(raw_instruction) > 1:
                target_id = raw_instruction[1]
            if len(raw_instruction) > 2:
                child_id = raw_instruction[2]
            if len(raw_instruction) > 3:
                label = raw_instruction[3]
        elif isinstance(raw_instruction, dict):
            action = raw_instruction.get("action") or raw_instruction.get("type")
            target_id = raw_instruction.get("id") or raw_instruction.get("containerId")
            child_id = raw_instruction.get("childId") or raw_instruction.get("child")
            label = raw_instruction.get("label") or raw_instruction.get("relationship")
        else:
            return None

        if not action:
            return None

        def _unwrap_singleton(value):
            if isinstance(value, (list, tuple)) and len(value) == 1:
                return value[0]
            return value

        return {
            "action": str(action),
            "target_id": _unwrap_singleton(target_id),
            "child_id": _unwrap_singleton(child_id),
            "label": _unwrap_singleton(label),
        }

    def _apply_single_instruction(
        self, action, target_id=None, child_id=None, label=None, placeholder_map=None
    ):
        """Apply a single normalized instruction and return (success, message)."""

        placeholder_map = placeholder_map or {}
        action_lower = action.lower()

        def resolve_identifier(identifier, role):
            if identifier is None:
                return None, None
            identifier_str = str(identifier)
            if self._is_placeholder_id(identifier_str):
                if identifier_str not in placeholder_map:
                    return None, f"Unknown placeholder {identifier_str} for {role}"
                return placeholder_map[identifier_str], None
            return identifier_str, None

        if action_lower == "remove":
            resolved_target, error = resolve_identifier(target_id, "remove")
            if error:
                return False, error
            if not resolved_target:
                return False, "remove requires an id"
            container = self.container_class.get_instance_by_id(resolved_target)
            if not container:
                return False, f"Container {resolved_target} not found"
            container.delete()
            return True, f"Container {resolved_target} removed"

        if action_lower == "addnew":
            new_container = self.container_class()
            new_id = new_container.getValue("id")

            if target_id and not self._is_placeholder_id(str(target_id)):
                new_container.setValue("id", str(target_id))
                new_id = new_container.getValue("id")
            elif target_id and self._is_placeholder_id(str(target_id)):
                placeholder_map[str(target_id)] = new_id

            return True, f"Container {new_id} created"

        if action_lower in {"addchild", "removechild", "modifychild"}:
            resolved_target, error = resolve_identifier(target_id, "parent")
            if error:
                return False, error
            resolved_child, error_child = resolve_identifier(child_id, "child")
            if error_child:
                return False, error_child

            if not resolved_target or not resolved_child:
                return False, f"{action} requires both id and childId"

            parent = self.container_class.get_instance_by_id(resolved_target)
            child = self.container_class.get_instance_by_id(resolved_child)

            if not parent or not child:
                missing = resolved_target if not parent else resolved_child
                return False, f"Container {missing} not found"

            if action_lower == "addchild":
                parent.add_container(child, label)
                return True, f"Child {resolved_child} added to {resolved_target}"

            if action_lower == "removechild":
                parent.remove_container(child)
                return True, f"Child {resolved_child} removed from {resolved_target}"

            if action_lower == "modifychild":
                parent.setPosition(child, label)
                return True, f"Child {resolved_child} updated on {resolved_target}"

        return False, f"Unknown action '{action}'"

    @staticmethod
    def _is_placeholder_id(identifier):
        return isinstance(identifier, str) and identifier.startswith("temp-")

    def _rewrite_placeholders_in_instances(self, placeholder_map):
        """Replace any lingering placeholder ids on in-memory instances and child edges."""

        if not placeholder_map:
            return

        for container in list(self.container_class.instances):
            current_id = container.getValue("id")
            if current_id in placeholder_map:
                # If a container somehow retained a placeholder, update it to the mapped id
                container.setValue("id", placeholder_map[current_id])


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
