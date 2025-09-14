from flask import jsonify, request
from handlers.openai_handler import openai_handler
from collections import deque


class ContainerAIMixin:
    """Mixin for AI-powered container operations."""

    def setup_ai_routes(self):
        """Setup routes for AI-powered operations."""
        self.app.add_url_rule(
            "/create_containers_from_content",
            "create_containers_from_content",
            self.create_containers_from_content,
            methods=["POST"],
        )
        self.app.add_url_rule(
            "/categorize_containers", "categorize_containers", self.categorize_containers, methods=["POST"]
        )
        self.app.add_url_rule("/embed_containers", "embed_containers", self.embed_containers, methods=["POST"])
        self.app.add_url_rule("/embed_positions", "embed_positions", self.embed_positions, methods=["POST"])
        self.app.add_url_rule("/add_similar", "add_similar", self.add_similar, methods=["POST"])
        self.app.add_url_rule("/join_similar", "join_similar", self.join_similar, methods=["POST"])
        self.app.add_url_rule("/build_relationships", "build_relationships", self.build_relationships, methods=["POST"])
        self.app.add_url_rule(
            "/suggest_relationship", "suggest_relationship", self.suggest_relationship, methods=["POST"]
        )
        self.app.add_url_rule("/build_chain_beam", "build_chain_beam", self.build_chain_beam, methods=["POST"])
        self.app.add_url_rule("/autocomplete", "autocomplete", self.autocomplete, methods=["POST"])
        self.app.add_url_rule(
            "/find_similar_positions", "find_similar_positions", self.find_similar_positions, methods=["POST"]
        )
        self.app.add_url_rule(
            "/search_position_z", "search_position_z", self.search_position_z_route, methods=["POST"]
        )

    def search_position_z_route(self):
        """API endpoint for vector search on position.z."""
        data = request.get_json() or {}
        search_term = data.get("searchTerm", "")
        top_n = int(data.get("top_n", 10))
        if not search_term:
            return jsonify({"error": "searchTerm is required"}), 400
        # Assumes self.repository is set to a ContainerRepository instance
        try:
            id_list, names_list = self.container_class.repository.search_position_z(search_term, top_n=top_n)
            names = []
            for node_id in id_list:
                node = self.container_class.repository.load_node(node_id)
                if node is not None and hasattr(node, 'getValue'):
                    names.append(node.getValue("Name"))
            return jsonify({"result": names})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def autocomplete(self):
        data = request.json
        prompt = data.get("prompt", "")

        if not prompt:
            return jsonify({"suggestions": []})

        try:
            openai_client = openai_handler.get_openai_client()
            if openai_client is None:
                return jsonify({"error": "OpenAI client not initialized"}), 500

            # Build context from existing containers and their relationships
            context_lines = []
            container_id = data.get("containerId")

            def format_container(c):
                name = c.getValue("Name")
                desc = c.getValue("Description", "")
                if desc:
                    return f"{name} ({desc})"
                return name

            if container_id:
                start_container = self.container_class.get_instance_by_id(container_id)
                if start_container:
                    max_containers = 20
                    visited = {start_container}
                    queue = deque([start_container])
                    selected = []

                    while queue and len(selected) < max_containers:
                        current = queue.popleft()
                        selected.append(current)
                        neighbours = current.getParents() + current.getChildren()
                        for neighbour in neighbours:
                            if neighbour not in visited and len(selected) + len(queue) < max_containers:
                                visited.add(neighbour)
                                queue.append(neighbour)

                    for container in selected:
                        for child, relation in container.containers:
                            if child not in selected:
                                continue
                            label = ""
                            if isinstance(relation, dict):
                                label = relation.get("label", "")
                            elif isinstance(relation, str):
                                label = relation
                            context_lines.append(
                                f"{format_container(container)} -[{label}]-> {format_container(child)}"
                            )
                            if len(context_lines) >= 20:
                                break
                        if len(context_lines) >= 20:
                            break

            if not context_lines:
                for container in self.container_class.instances:
                    for child, relation in container.containers:
                        label = ""
                        if isinstance(relation, dict):
                            label = relation.get("label", "")
                        elif isinstance(relation, str):
                            label = relation
                        context_lines.append(
                            f"{format_container(container)} -[{label}]-> {format_container(child)}"
                        )
                        if len(context_lines) >= 20:
                            break
                    if len(context_lines) >= 20:
                        break

            if context_lines:
                context = "\n".join(context_lines)
                user_msg = f"Context:\n{context}\n\nComplete the following text:\n\n{prompt}"
            else:
                user_msg = f"Complete the following text:\n\n{prompt}"

            # Use OpenAI's chat completion to generate suggestions
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=20,
                temperature=0.7,
                n=1,
                stop=["\n"],
            )
            text = response.choices[0].message.content.strip()
            suggestions = [line for line in text.split("\n") if line]
            return jsonify({"suggestions": suggestions})

        except Exception as e:
            print(f"OpenAI API error: {e}")
        return jsonify({"suggestions": []}), 500

    def create_containers_from_content(self):
        """Create containers from raw text content using OpenAI."""
        data = request.get_json()

        # Validate required fields
        if not data:
            return jsonify({"error": "No data provided"}), 400

        prompt = data.get("prompt", "")
        content = data.get("content", "")

        if not content:
            return jsonify({"error": "Content is required"}), 400

        try:
            # Create containers from content
            new_containers = self.container_class.create_containers_from_content(prompt, content)

            # Get IDs (containers are already added to instances by __init__)
            created_ids = []
            for container in new_containers:
                container_id = container.getValue("id")
                created_ids.append(container_id)

            return jsonify(
                {"message": f"{len(new_containers)} containers created successfully", "container_ids": created_ids}
            )

        except Exception as e:
            return jsonify({"error": f"Failed to create containers: {str(e)}"}), 500

    def categorize_containers(self):
        """Categorize containers using AI."""
        data = request.get_json() or {}
        container_ids = data.get("container_ids", [])

        if not container_ids:
            return jsonify({"message": "No container IDs provided"}), 400

        # Resolve to actual container objects
        containers = []
        for cid in container_ids:
            inst = self.container_class.get_instance_by_id(cid)
            if inst:
                # Only add if inst has not parents
                if not inst.getParents():
                    containers.append(inst)

        if not containers:
            return jsonify({"message": "None of the provided IDs matched existing containers"}), 404

        # Perform the OpenAI-driven categorisation
        new_categories = self.container_class.categorise_containers(containers)

        if not new_categories:
            return jsonify({"message": "No categories were generated"}), 200

        # Collect IDs of created categories
        created_ids = []
        for cat in new_categories:
            created_ids.append(cat.getValue("id"))

        return jsonify({"message": "Containers categorised successfully", "new_category_ids": created_ids}), 201

    def embed_containers(self):
        """Generate embeddings for containers."""
        data = request.get_json()
        container_ids = data["containers"]
        containers = []

        for container_id in container_ids:
            container = self.container_class.get_instance_by_id(container_id)
            if container:
                # Skip containers that are already embedded
                if container.getValue("z") is not None:
                    print("CONTAINER Z IS ALREADY EMBEDDED: " + str(container.getValue("Name")))
                    continue
                containers.append(container)
                print("CONTAINER Z IS NONE, EMBEDDING: " + str(container.getValue("Name")))

        self.container_class.embed_containers(containers)
        return jsonify({"message": "Containers embedded successfully"})

    def embed_positions(self):
        """Generate embeddings for relationship positions with enhanced context."""
        data = request.get_json() or {}
        container_ids = data.get("container_ids", [])

        if not container_ids:
            return jsonify({"message": "No container IDs provided"}), 400

        for container_id in container_ids:
            container = self.container_class.get_instance_by_id(container_id)
            if not container:
                continue

            # Gather parent container names
            parent_names = []
            if hasattr(container, 'getParents'):
                for parent in container.getParents():
                    parent_name = parent.getValue("Name")
                    if parent_name:
                        parent_names.append(parent_name)
            parent_names_str = ", ".join(parent_names)

            # Gather all child containers for context
            all_children = [c for c, _ in container.getPositions()]

            for child, position in container.getPositions():
                label = ""
                if isinstance(position, dict):
                    label_val = position.get("label", "")
                    if isinstance(label_val, list):
                        label = " ".join(label_val)
                    else:
                        label = str(label_val)
                else:
                    label = str(position)
                    position = {"label": label}

                # Source node info
                src_name = container.getValue("Name") or ""
                src_desc = container.getValue("Description") or ""
                src_desc = src_desc.strip()
                if src_desc and src_desc != src_name:
                    src_info = f"{src_name} ({src_desc})"
                else:
                    src_info = src_name

                # Destination node info
                dst_name = child.getValue("Name") or ""
                dst_desc = child.getValue("Description") or ""
                dst_desc = dst_desc.strip()
                if dst_desc and dst_desc != dst_name:
                    dst_info = f"{dst_name} ({dst_desc})"
                else:
                    dst_info = dst_name

                # Other child names (excluding this child)
                other_children = [c.getValue("Name") for c in all_children if c != child and hasattr(c, 'getValue')]
                other_children_str = ", ".join([n for n in other_children if n])

                # Compose context string
                context_parts = []
                if parent_names_str:
                    context_parts.append(f"Parents: {parent_names_str}")
                if other_children_str:
                    context_parts.append(f"Other children: {other_children_str}")
                context_str = "; ".join(context_parts)

                # Compose embedding text
                text = f"Source: {src_info}; Label: {label}; Target: {dst_info}"
                if context_str:
                    text = f"{text}; Context: {context_str}"
                text = text.strip()

                z = openai_handler.get_embeddings(text)
                position["z"] = z
                container.setPosition(child, position)

        return jsonify({"message": "Positions embedded successfully"})

    def find_similar_positions(self):
        """Find containers with similar position embeddings (from position dicts set by embed_positions)."""
        data = request.get_json()
        position_text = data.get("position_text", "")
        if not position_text:
            return jsonify({"message": "No position text provided"}), 400

        # Get the embedding for the provided position text
        position_embedding = openai_handler.get_embeddings(position_text)
        if position_embedding is None:
            return jsonify({"message": "Failed to generate embedding"}), 500

        # Find containers/positions with similar position embeddings
        similar_positions = []
        for container in self.container_class.get_all_instances():
            # getPositions() yields (child, position_dict)
            for child, position in getattr(container, 'getPositions', lambda: [])():
                z = None
                if isinstance(position, dict):
                    z = position.get("z")
                if z is not None:
                    score = self.vector_match(position_embedding, z)
                    if score > 0.77:
                        similar_positions.append({
                            "container_id": container.getValue("id"),
                            "position_label": position.get("label"),
                            "child_id": child.getValue("id"),
                            "score": score
                        })

        return (
            jsonify(
                {
                    "message": "Similar positions found",
                    "similar_positions": similar_positions,
                }
            ),
            200,
        )

    def add_similar(self):
        """Add similar containers based on embeddings."""
        data = request.get_json()
        children_ids = data["children_ids"]
        parent_id = data["parent_id"]
        container = self.container_class.get_instance_by_id(parent_id)

        # Check if parent container has embeddings
        parent_z = container.getValue("z")
        if parent_z is None:
            print("Parent container has no z, embedding parent container")
            container.embed_containers([container])
            parent_z = container.getValue("z")

        counter = 0
        candidate_children = []

        for child_id in children_ids:
            child = self.container_class.get_instance_by_id(child_id)
            if child is None:
                continue
            if child not in container.getChildren() and child != container:
                child_z = child.getValue("z")
                if child_z is None:
                    continue

                # Vector match parent_z and child_z
                score = self.vector_match(parent_z, child_z)
                print("Score: " + str(score))
                if score > 0.75:
                    candidate_children.append(child)
                    counter += 1

        # Sort candidates by score
        candidate_children.sort(key=lambda x: self.vector_match(parent_z, x.getValue("z")), reverse=True)

        # Add top 5 candidates to the parent container
        for child in candidate_children[:5]:
            if child not in container.getChildren() and child != container:
                print("Adding similar container: " + str(child.getValue("Name")))
                self.add_child_with_tags(container, child)

        return jsonify({"message": f"Top 5 scoring of {counter} similar containers added successfully"})

    def join_similar(self):
        """Join top similar containers into a single new container,
        cycling through unmatched containers up to 10 times."""
        data = request.get_json()
        container_ids = data["container_ids"]
        remaining_ids = set(container_ids)
        joined_ids = []
        cycles = 0
        new_container_ids = []
        while remaining_ids and cycles < 10:
            cycles += 1
            # Always use the first remaining container as the base
            base_id = next(iter(remaining_ids))
            container = self.container_class.get_instance_by_id(base_id)
            parent_z = container.getValue("z")
            if parent_z is None:
                print("Parent container has no z, embedding parent container")
                container.embed_containers([container])
                parent_z = container.getValue("z")

            candidate_children = []
            for child_id in list(remaining_ids):
                child = self.container_class.get_instance_by_id(child_id)
                if child not in container.getChildren() and child != container:
                    child_z = child.getValue("z")
                    if child_z is None:
                        child.embed_containers([child])
                        child_z = child.getValue("z")
                    score = self.vector_match(parent_z, child_z)
                    print("Score: " + str(score))
                    if score > 0.8:
                        candidate_children.append(child)

            # Sort candidates by score
            candidate_children.sort(key=lambda x: self.vector_match(parent_z, x.getValue("z")), reverse=True)

            if not candidate_children:
                # Remove the base container from remaining_ids and continue
                remaining_ids.remove(base_id)
                continue

            # Add base container to candidates
            candidate_children.insert(0, container)
            joined_container = self.container_class.join_containers(candidate_children[:5])
            new_id = joined_container.getValue("id")
            new_container_ids.append(new_id)
            # Remove all joined containers from remaining_ids
            for c in candidate_children[:5]:
                cid = c.getValue("id")
                if cid in remaining_ids:
                    remaining_ids.remove(cid)

        if not new_container_ids:
            return jsonify({"message": "No similar containers found"})

        return jsonify(
            {
                "message": f"Joined containers in up to {cycles} cycles.",
                "new_container_ids": new_container_ids,
            }
        )

    def suggest_relationship(self):
        """Suggest a relationship between two containers using OpenAI."""
        data = request.get_json()
        source_id = data.get("source_id")
        target_id = data.get("target_id")

        if not source_id or not target_id:
            return jsonify({"error": "Both subject and object IDs must be provided"}), 400

        subject_container = self.container_class.get_instance_by_id(source_id)
        object_container = self.container_class.get_instance_by_id(target_id)

        if not subject_container or not object_container:
            return jsonify({"error": "Invalid subject or object ID"}), 404

        try:
            # Gather context using search_position_z for both subject and object container names
            repo = getattr(self.container_class, 'repository', None)
            context_lines = []
            if repo is not None:
                # Search for similar positions to subject_container Name
                subject_name = subject_container.getValue("Name")
                object_name = object_container.getValue("Name")
                if subject_name:
                    subject_similar_ids, subject_names = repo.search_position_z(subject_name, top_n=5)
                    for name in subject_names:
                        context_lines.append(f"Other factors: {name}")
                if object_name:
                    object_similar_ids, object_names = repo.search_position_z(object_name, top_n=5)
                    for name in object_names:
                        context_lines.append(f"Also impacts: {name}")

            # Optionally, pass this context to the suggest_relationship method if it supports it
            # Otherwise, just append to the prompt if you build it here
            if hasattr(self.container_class, 'suggest_relationship'):
                # Try to pass context if supported, else fallback
                relationship_description = subject_container.suggest_relationship(
                    object_container, context_lines
                )
            else:
                relationship_description = None

            return jsonify({"relationship": relationship_description, "context": context_lines})

        except Exception as e:
            return jsonify({"error": f"Failed to suggest relationship: {str(e)}"}), 500

    def build_relationships(self):
        """Build relationships between containers using AI."""
        data = request.get_json()
        container_ids = data["containers"]
        containers = []

        for container_id in container_ids:
            container = self.container_class.get_instance_by_id(container_id)
            if container:
                containers.append(container)

        self.container_class.build_relationships(containers)
        return jsonify({"message": "Relationships built successfully"})

    def build_chain_beam(self):
        """Build reasoning chain using beam search."""
        data = request.get_json()
        visible_ids = data["visible_ids"]
        start_id = data["start_id"]
        end_id = data["end_id"]
        max_jumps = data.get("max_jumps", 5)
        beam_width = data.get("beam_width", 3)

        # Filter selected ids to only those that have embeddings
        selected_ids = []
        for id in visible_ids:
            container = self.container_class.get_instance_by_id(id)
            if container and container.getValue("z") is not None:
                selected_ids.append(id)

        try:
            narrative = self.build_reasoning_chain_beam(selected_ids, start_id, end_id, max_jumps, beam_width)
            return jsonify({"message": "Reasoning chain built successfully", "narrative": narrative})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400
