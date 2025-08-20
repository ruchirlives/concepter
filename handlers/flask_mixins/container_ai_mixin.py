from flask import jsonify, request, send_file
from handlers.openai_handler import openai_handler


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
            for container in self.container_class.instances:
                for child, relation in container.containers:
                    label = ""
                    if isinstance(relation, dict):
                        label = relation.get("label", "")
                    elif isinstance(relation, str):
                        label = relation
                    context_lines.append(f"{container.getValue('Name')} -[{label}]-> {child.getValue('Name')}")
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
        container_ids = data.get("containers", [])

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
                    continue
                containers.append(container)

        self.container_class.embed_containers(containers)
        return jsonify({"message": "Containers embedded successfully"})

    def embed_positions(self):
        """Generate embeddings for relationship positions."""
        data = request.get_json() or {}
        container_ids = data.get("container_ids", [])

        if not container_ids:
            return jsonify({"message": "No container IDs provided"}), 400

        for container_id in container_ids:
            container = self.container_class.get_instance_by_id(container_id)
            if not container:
                continue

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

                text = f"{container.getValue('Name')} {label} {child.getValue('Name')}".strip()
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
            if child not in container.getChildren() and child != container:
                child_z = child.getValue("z")
                if child_z is None:
                    continue

                # Vector match parent_z and child_z
                score = self.vector_match(parent_z, child_z)
                print("Score: " + str(score))
                if score > 0.8:
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
            relationship_description = self.container_class.suggest_relationship(subject_container, object_container)
            return jsonify({"relationship": relationship_description})

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
