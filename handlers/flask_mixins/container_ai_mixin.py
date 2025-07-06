from flask import jsonify, request, send_file
from handlers.openai_mixins.openai_handler_modular import get_openai_client

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
        self.app.add_url_rule("/add_similar", "add_similar", self.add_similar, methods=["POST"])
        self.app.add_url_rule("/build_relationships", "build_relationships", self.build_relationships, methods=["POST"])
        self.app.add_url_rule("/build_chain_beam", "build_chain_beam", self.build_chain_beam, methods=["POST"])
        self.app.add_url_rule("/autocomplete", "autocomplete", self.autocomplete, methods=["POST"])

    def autocomplete(self):
        data = request.json
        prompt = data.get('prompt', '')

        if not prompt:
            return jsonify({'suggestions': []})

        try:
            openai_client = get_openai_client()
            if openai_client is None:
                return jsonify({'error': 'OpenAI client not initialized'}), 500
            # Use OpenAI's chat completion to generate suggestions
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f"Complete the following text:\n\n{prompt}"}],
                max_tokens=20,
                temperature=0.7,
                n=1,
                stop=["\n"]
            )
            text = response.choices[0].message.content.strip()
            suggestions = [line for line in text.split('\n') if line]
            return jsonify({'suggestions': suggestions})

        except Exception as e:
            print(f"OpenAI API error: {e}")
        return jsonify({'suggestions': []}), 500

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
