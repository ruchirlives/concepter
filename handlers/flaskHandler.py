from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
from container_base import Container, baseTools
from containers.projectContainer import ProjectContainer
import logging
from time import sleep
from handlers.ServerHelperFunctions import ServerHelperFunctions
from handlers.mongodb_handler import delete_project
import datetime


# FLASK SERVER =========================================================
class FlaskServer(ServerHelperFunctions):
    def __init__(self, container_class: Container, port=8080):
        self.app = Flask(__name__, static_folder="../react-build")
        CORS(self.app)
        # Get single container by id
        self.app.add_url_rule("/get_container/<id>", "get_container", self.get_container, methods=["GET"])
        self.app.add_url_rule("/rename_container/<id>", "rename_container", self.rename_container, methods=["GET"])
        self.app.add_url_rule("/get_containers", "get_containers", self.get_containers, methods=["GET"])
        self.app.add_url_rule(
            "/get_subcontainers/<url_encoded_container_name>",
            "get_subcontainers",
            self.get_subcontainers,
            methods=["GET"],
        )
        self.app.add_url_rule(
            "/write_back_containers",
            "write_back_containers",
            self.write_back_containers,
            methods=["POST"],
        )
        self.app.add_url_rule("/get_task_containers", "get_task_containers", self.get_task_containers, methods=["GET"])
        self.app.add_url_rule("/get_parents/<id>", "get_parents", self.get_parents, methods=["GET"])
        self.app.add_url_rule("/children/<id>", "children", self.children, methods=["GET"])
        self.app.add_url_rule("/manyChildren", "manyChildren", self.manyChildren, methods=["POST"])

        # Save and Load
        self.app.add_url_rule("/save_containers", "save_containers", self.save_containers, methods=["POST"])
        self.app.add_url_rule("/load_containers", "load_containers", self.load_containers, methods=["POST"])
        self.app.add_url_rule("/import_containers", "import_containers", self.import_containers, methods=["POST"])
        self.app.add_url_rule(
            "/categorize_containers", "categorize_containers", self.categorize_containers, methods=["POST"]
        )

        self.app.add_url_rule("/export_selected", "export_selected", self.export_containers, methods=["POST"])
        self.app.add_url_rule("/embed_containers", "embed_containers", self.embed_containers, methods=["POST"])
        self.app.add_url_rule("/add_similar", "add_similar", self.add_similar, methods=["POST"])
        self.app.add_url_rule("/build_relationships", "build_relationships", self.build_relationships, methods=["POST"])
        self.app.add_url_rule("/build_chain_beam", "build_chain_beam", self.build_chain_beam, methods=["POST"])
        self.app.add_url_rule("/delete_containers", "delete_containers", self.delete_containers, methods=["POST"])
        self.app.add_url_rule("/clear_containers", "clear_containers", self.clear_containers, methods=["GET"])
        self.app.add_url_rule(
            "/create_containers_from_content",
            "create_containers_from_content",
            self.create_containers_from_content,
            methods=["POST"],
        )
        self.app.add_url_rule("/get_mermaid", "get_mermaid", self.export_mermaid, methods=["POST"])
        self.app.add_url_rule("/get_gantt", "get_gantt", self.export_gantt, methods=["POST"])
        self.app.add_url_rule("/get_docx", "get_word_doc", self.get_docx, methods=["POST"])
        self.app.add_url_rule(
            "/get_loadable_containers",
            "get_loadable_containers",
            self.get_loadable_containers,
            methods=["GET"],
        )

        # AddChildren
        self.app.add_url_rule("/create_container", "create_container", self.create_container, methods=["GET"])
        self.app.add_url_rule("/add_children", "add_children", self.add_children, methods=["POST"])
        self.app.add_url_rule("/remove_children", "remove_children", self.remove_children, methods=["POST"])
        self.app.add_url_rule("/merge_containers", "merge_containers", self.merge_containers, methods=["POST"])
        self.app.add_url_rule("/request_rekey", "request_rekey", self.request_rekey, methods=["GET"])

        # Get positions
        self.app.add_url_rule(
            "/get_positions/<sourceId>/<targetId>", "get_positions", self.get_positions, methods=["GET"]
        )
        self.app.add_url_rule("/set_position", "set_position", self.set_position, methods=["POST"])

        # Serve React static files
        self.app.add_url_rule("/static/<path:path>", "serve_static", self.serve_static)
        self.app.add_url_rule("/", "index", self.index, methods=["GET"])
        self.container_class: Container = container_class

        # MongoDB delete project
        self.app.add_url_rule("/delete_project", "delete_project", self.delete_project, methods=["POST"])

        # Detect runtime environment
        runtime_env = os.getenv("RUNTIME_ENV", None)

        # Use the PORT environment variable on Cloud Run or fallback to default_port
        self.port = port

        # Start logging
        logging.basicConfig(level=logging.INFO)
        logging.info("Flask server started")

    def serve_static(self, path):
        return send_from_directory(os.path.join(self.app.static_folder, "static"), path)

    def index(self):
        # Render the index.html template
        # return render_template("index.html")
        return send_from_directory(self.app.static_folder, "index.html")

    def get_loadable_containers(self):
        # Return all loadable containers
        containers = self.container_class.get_container_names_from_db()

        return jsonify({"containers": containers})

    # Get containers tagged with task
    def get_task_containers(self):
        items = []
        for c in self.container_class.get_task_containers():
            sd = c.getValue("StartDate")
            if isinstance(sd, datetime.datetime):
                sd = sd.date().isoformat()
            elif isinstance(sd, datetime.date):
                sd = sd.isoformat()
            else:
                sd = "No start date"

            ed = c.getValue("EndDate")
            if isinstance(ed, datetime.datetime):
                ed = ed.date().isoformat()
            elif isinstance(ed, datetime.date):
                ed = ed.isoformat()
            else:
                ed = "No end date"

            body = "<p>".join(
                [
                    c.getValue("Name") or "",
                    "Starts " + sd,
                    "Ends " + ed,
                    # …
                ]
            )

            item = {
                "subject": c.getValue("Name"),
                "body": body,
            }

            end_date = c.getValue("EndDate")
            if end_date:
                item["end_date"] = str(end_date)

            items.append(item)

        return jsonify({"containers": items})

    def load_containers(self):
        data = request.get_json()
        project_name = data["project_name"]
        logging.info("Container name: " + project_name)
        status = self.container_class.load_project_from_db(project_name)
        logging.info("Status: " + status)
        return jsonify({"message": "Containers loaded successfully"})

    def import_containers(self):
        data = request.get_json()
        project_name = data["project_name"]
        logging.info("Container name: " + project_name)
        status = self.container_class.import_containers(project_name)
        logging.info("Status: " + status)
        return jsonify({"message": "Containers loaded successfully"})

    def clear_containers(self):
        baseTools.instances = []
        return jsonify({"message": "Containers cleared successfully"})

    def save_containers(self):
        data = request.get_json()
        project_name = data["project_name"]
        self.container_class.save_project_to_db(project_name)
        return jsonify({"message": "Containers saved successfully"})

    def embed_containers(self):
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

    def build_relationships(self):
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
        data = request.get_json()
        visible_ids = data["visible_ids"]
        start_id = data["start_id"]
        end_id = data["end_id"]
        max_jumps = data.get("max_jumps", 5)
        beam_width = data.get("beam_width", 3)

        # filter selected ids to only those that have a z value
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

    def categorize_containers(self):
        data = request.get_json() or {}
        # 1) pull the array of IDs
        container_ids = data.get("containers", [])
        if not container_ids:
            return jsonify({"message": "No container IDs provided"}), 400

        # 2) resolve to actual container objects
        containers = []
        for cid in container_ids:
            inst = self.container_class.get_instance_by_id(cid)
            if inst:
                containers.append(inst)

        if not containers:
            return jsonify({"message": "None of the provided IDs matched existing containers"}), 404

        # 3) perform the OpenAI‐driven categorisation
        new_categories = self.container_class.categorise_containers(containers)

        if not new_categories:
            return jsonify({"message": "No categories were generated"}), 200

        # 4) register each new category, assign its ID, and collect IDs
        created_ids = []
        for cat in new_categories:
            # self.container_class.instances.append(cat)
            # new_id = cat.assign_id()
            # cat.setValue("id", new_id)
            created_ids.append(cat.getValue("id"))

        return jsonify({"message": "Containers categorised successfully", "new_category_ids": created_ids}), 201

    def delete_containers(self):
        data = request.get_json()
        containerIds = data["containers"]
        for containerId in containerIds:
            container = self.container_class.get_instance_by_id(containerId)
            if container:
                self.container_class.remove_container_everywhere(container)
        return jsonify({"message": "Containers deleted successfully"})

    def create_containers_from_content(self):
        """
        Create containers from raw text content using OpenAI.

        **API Endpoint:** POST /create_containers_from_content

        **Request Body (JSON):**
        {
            "prompt": "Optional prompt to guide container creation (string, optional)",
            "content": "The raw text content to extract containers from (string, required)"
        }

        **Example Request:**
        ```json
        {
            "prompt": "Extract project tasks and their relationships",
            "content": "The yellow fox jumped over the red chicken. The fox was eating the blue rabbit."
        }
        ```

        **Success Response (200):**
        ```json
        {
            "message": "X containers created successfully",
            "container_ids": ["uuid1", "uuid2", "uuid3"]
        }
        ```

        **Error Responses:**
        - 400: Missing or invalid data
        ```json
        {
            "error": "No data provided" | "Content is required"
        }
        ```

        - 500: Processing error
        ```json
        {
            "error": "Failed to create containers: [error details]"
        }
        ```

        **What it does:**
        1. Extracts subject-object relationships from the provided text using OpenAI
        2. Creates ConceptContainer instances for each unique subject/object
        3. Establishes relationships between containers based on detected connections
        4. Automatically assigns IDs and adds containers to the global instances list
        5. Returns the IDs of all newly created containers

        **Use cases:**
        - Import project documentation and auto-generate task containers
        - Parse meeting notes into actionable items and relationships
        - Convert free-form text into structured container hierarchies
        """
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

    def create_container(self):
        container = self.container_class()
        id = container.getValue("id")
        return jsonify({"message": "Container created successfully", "id": id})

    def export_containers(self):
        # Export containers to a file
        data = request.get_json()
        containerIds = data["containers"]
        containers = []
        for containerId in containerIds:
            container = self.container_class.get_instance_by_id(containerId)
            if container:
                containers.append(container)
        if containers:
            project_name = f'Export {containers[0].getValue("Name")} et al.'
            self.container_class.export_containers(containers, project_name)
            return jsonify({"message": "Containers exported successfully"})
        else:
            return jsonify({"message": "No containers to export"})

    def merge_containers(self):
        data = request.get_json()
        containerIds = data["containers"]
        container = self.container_class.merge_containers(containerIds)
        if container:
            self.container_class.instances.append(container)
            id = container.assign_id()
            container.setValue("id", id)
            return jsonify({"message": "Containers merged successfully", "id": id})
        else:
            return jsonify({"message": "No containers to merge"})

    def rename_container(self, id):
        # Rename a container by ID
        container = self.container_class.get_instance_by_id(id)
        if container:
            container.rename_from_description()
            return jsonify({"message": "Container renamed successfully"})
        else:
            return jsonify({"message": "Container not found"}), 404

    def export_mermaid(self):
        data = request.get_json()
        container_id = data["container_id"]
        container = self.container_class.get_instance_by_id(container_id)
        if container:
            mermaid = container.export_mermaid()
            return jsonify({"mermaid": mermaid})
        return jsonify({"mermaid": "Container not found"})

    def export_gantt(self):
        data = request.get_json()
        container_id = data["container_id"]
        container = self.container_class.get_instance_by_id(container_id)
        if container:
            mermaid = container.exportGantt()
            return jsonify({"mermaid": mermaid})
        return jsonify({"mermaid": "Container not found"})

    def get_docx(self):
        data = request.get_json()
        container_id = data["container_id"]
        container = self.container_class.get_instance_by_id(container_id)
        if container:
            # Assume container.get_docx() returns a BytesIO stream containing the DOCX
            doc_stream = container.get_docx()
            doc_stream.seek(0)  # Ensure the stream is at the beginning
            return send_file(
                doc_stream,
                as_attachment=True,
                download_name="output.docx",
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        return jsonify({"doc": "Container not found"})

    def write_back_containers(self):
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
                    pass

            # Write back values to target container
            for key, value in container.items():
                if key == "StartDate" or key == "EndDate":
                    value = target_container.parse_date_auto(value)
                elif key == "TimeRequired":
                    if value:
                        value = float(value)
                elif key == "Tags":
                    # make blank if null
                    if value is None:
                        value = ""
                    value = value.split(",")
                elif key == "id":
                    # skip id
                    continue

                target_container.setValue(key, value)
        return jsonify({"message": "Containers written back successfully"})

    def request_rekey(self):
        # Request a rekey of the containers
        self.container_class.rekey_all_ids()
        return jsonify({"message": "Rekey requested successfully"})

    def add_similar(self):
        data = request.get_json()
        children_ids = data["children_ids"]
        parent_id = data["parent_id"]
        container: ProjectContainer = self.container_class.get_instance_by_id(parent_id)

        # Does parent container have z?
        # If not, embed parent container

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
                    # skip if z is None
                    continue

                # Vector match parent_z and child_z
                score = self.vector_match(parent_z, child_z)
                print("Score: " + str(score))
                if score > 0.8:
                    # Add to candidates
                    candidate_children.append(child)
                    counter += 1

        # Sort candidates by score
        candidate_children.sort(key=lambda x: self.vector_match(parent_z, x.getValue("z")), reverse=True)

        # Add all candidates to the parent container
        for child in candidate_children[:5]:
            # Only add if the child is not already a child of the parent
            if child not in container.getChildren() and child != container:
                # Add the child to the parent container
                print("Adding similar container: " + str(child.getValue("Name")))
                # Add the child to the parent container
                self.add_child_with_tags(container, child)

        return jsonify({"message": f"Top 5 scoring of {counter} similar containers added successfully"})

    def add_children(self):
        sleep(0.05)
        data = request.get_json()
        children_ids = data["children_ids"]
        parent_id = data["parent_id"]
        container: ProjectContainer = self.container_class.get_instance_by_id(parent_id)

        print(container.name)
        print("Parent ID: " + str(parent_id))
        print("Children IDs: " + str(children_ids))

        for child_id in children_ids:
            child = self.container_class.get_instance_by_id(child_id)

            # print("Container Name: " + str(container.name))
            # print("Child Name: " + str(child.name))

            # Only add if the child is not already a child of the parent
            if child not in container.getChildren() and child != container:
                self.add_child_with_tags(container, child)

        return jsonify({"message": "Children added successfully"})

    def remove_children(self):
        data = request.get_json()
        children_ids = data["children_ids"]
        parent_id = data["parent_id"]
        container = self.container_class.get_instance_by_id(parent_id)
        for child_id in children_ids:
            child = self.container_class.get_instance_by_id(child_id)
            container.remove_container(child)
        return jsonify({"message": "Children removed successfully"})

    def children(self, id):
        # Return all children of a container
        container = self.container_class.get_instance_by_id(id)
        children = container.getChildren()
        export = self.serialize_container_info(children)

        return jsonify({"containers": export})

    def manyChildren(self):
        data = request.get_json() or {}
        container_ids = set(data.get("container_ids", []))

        result = []
        for cid in container_ids:
            container = self.container_class.get_instance_by_id(cid)
            if not container:
                continue

            # Build a list of full child-objects, not just IDs
            children = []
            for child, pos in container.getPositions():
                child_id = child.getValue("id")
                child_name = child.getValue("Name")
                if child_id is None:
                    continue

                children.append({"id": child_id, "name": child_name, "position": pos, "tags": child.getValue("Tags")})

            result.append({"container_id": cid, "children": children})

        return jsonify(result)

    def get_parents(self, id):
        # Return all parents of a container
        container = self.container_class.get_instance_by_id(id)
        parents = container.getParents()
        export = self.serialize_container_info(parents)

        return jsonify({"containers": export})

    def get_container(self, id):
        # Return a single container by ID
        container = self.container_class.get_instance_by_id(id)
        if container:
            export = self.serialize_container_info([container])
            return jsonify({"containers": export})
        else:
            return jsonify({"message": "Container not found"}), 404

    def get_containers(self):
        # Return all containers
        # self.container_class.instances = ConceptContainer.instances
        containers = baseTools.instances
        export = self.serialize_container_info(containers)

        return jsonify({"containers": export})

    def get_subcontainers(self, url_encoded_container_name):
        # Decode the URL encoded container name
        container_name = url_encoded_container_name.replace("%20", " ")
        # Return all subcontainers of a container
        containers = self.container_class.get_instance_by_name(container_name).getChildren()
        export = self.serialize_container_info(containers)

        return jsonify({"containers": export})

    def get_positions(self, sourceId, targetId):
        # Return all positions of a container
        source = self.container_class.get_instance_by_id(sourceId)
        target = self.container_class.get_instance_by_id(targetId)
        if source and target:
            positions = source.getPositions()

            relationshipString = ""
            for container, position in positions:
                if container is target:
                    # skip if position is None
                    if position is None:
                        continue
                    if isinstance(position, dict):
                        label = position.get("label", [])
                    elif isinstance(position, str):
                        label = position
                    relationshipString += label + "\n"
            return jsonify({"relationshipString": relationshipString})
        else:
            return jsonify({"message": "Container not found"}), 404

    def set_position(self):
        data = request.get_json()
        # Set the position of a container
        source = self.container_class.get_instance_by_id(data["source_id"])
        target = self.container_class.get_instance_by_id(data["target_id"])
        position = {"label": data["relationship_string"]}
        if source and target:
            source.setPosition(target, position)
            return jsonify({"message": "Position set successfully"})
        else:
            return jsonify({"message": "Container not found"}), 404

    def delete_project(self):
        """
        Request JSON: { "project_name": "MyProject" }
        Drops the corresponding MongoDB collection for the project.
        """
        data = request.get_json() or {}
        project_name = data.get("project_name")
        if not project_name:
            return jsonify({"message": "No project_name provided"}), 400

        success = delete_project(project_name)
        if success:
            return jsonify({"message": "Project deleted successfully"})
        else:
            return jsonify({"message": "Failed to delete project"}), 500

    def start(self):
        self.app.run(host="0.0.0.0", port=self.port)


if __name__ == "__main__":
    flask_server = FlaskServer(ProjectContainer)
    flask_server.start()
