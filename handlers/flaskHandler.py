from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
from container_base import Container, baseTools
from containers.projectContainer import ProjectContainer
import logging
from time import sleep
from handlers.mongodb_handler import delete_project


class FlaskServer:
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
        self.app.add_url_rule("/build_relationships", "build_relationships", self.build_relationships, methods=["POST"])
        self.app.add_url_rule("/delete_containers", "delete_containers", self.delete_containers, methods=["POST"])
        self.app.add_url_rule("/clear_containers", "clear_containers", self.clear_containers, methods=["GET"])
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
        # Return all containers tagged with task
        containers = self.container_class.get_task_containers()
        items = []
        for container in containers:
            # Concatenate with new line the various fields
            body = "<p>".join(
                [
                    container.getValue("Name") or "",
                    "Description: " + (container.getValue("Description") or "No description provided"),
                    "Starts " + str(container.getValue("StartDate") or "No start date"),
                    "Ends " + str(container.getValue("EndDate") or "No end date"),
                    "Required days " + str(container.getValue("TimeRequired") or "Not specified"),
                    "Horizon " + (container.getValue("Horizon") or "Not set"),
                    "Tagged as " + str(container.getValue("Tags") or "No tags"),
                ]
            )

            item = {
                "subject": container.getValue("Name"),
                "body": body,
            }

            end_date = container.getValue("EndDate")
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
                container.add_container(child)
                # For each tag in the parent's Tags array, add it to the child unless it already exists
                parent_tags = container.getValue("Tags") or []
                child_tags = child.getValue("Tags") or []
                if parent_tags and child_tags:
                    for tag in parent_tags:
                        if tag not in child_tags and tag != "pieces" and tag != "group":
                            child_tags.append(tag)
                child.setValue("Tags", child_tags)
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

                children.append({
                    "id": child_id,
                    "Name": child_name,
                    "position": pos
                })

            result.append({
                "container_id": cid,
                "children": children
            })

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
                if container == target:
                    relationshipString += position or "" + "\n"
            return jsonify({"relationshipString": relationshipString})
        else:
            return jsonify({"message": "Container not found"}), 404

    def set_position(self):
        data = request.get_json()
        # Set the position of a container
        source = self.container_class.get_instance_by_id(data["source_id"])
        target = self.container_class.get_instance_by_id(data["target_id"])
        position = data["relationship_string"]
        if source and target:
            source.setPosition(target, position)
            return jsonify({"message": "Position set successfully"})
        else:
            return jsonify({"message": "Container not found"}), 404

    def serialize_container_info(self, containers):
        export = []
        for container in containers:
            if not container.getValue("id"):
                id = container.assign_id()
                container.setValue("id", id)

            if container not in self.container_class.instances:
                self.container_class.instances.append(container)

            id = container.getValue("id")
            Name = container.getValue("Name")
            StartDate = container.getValue("StartDate")
            EndDate = container.getValue("EndDate")
            TimeRequired = container.getValue("TimeRequired")
            Horizon = container.getValue("Horizon")
            tags = container.getValue("Tags")
            if tags:
                tags = ",".join(tags)
            else:
                tags = ""

            export.append(
                {
                    "id": id,
                    "Name": Name,
                    "Tags": tags,
                    "Description": container.getValue("Description"),
                    "StartDate": StartDate,
                    "EndDate": EndDate,
                    "TimeRequired": TimeRequired,
                    "Horizon": Horizon,
                }
            )
        return export

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
