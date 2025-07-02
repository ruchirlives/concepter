from helpers.random_names import random_names
from container_base import Container, baseTools
from handlers.openai_handler import (
    generate_piece_name,
    categorize_containers,
    get_relationships_from_openai,
    get_embeddings,
    distill_subject_object_pairs,
)
from typing import List, Any
from handlers.repository_handler import ContainerRepository

# from tkinter import simpledialog
import bson
import pickle


class ConceptContainer(Container):
    # Class‐level repository reference (set during app startup)
    repository: ContainerRepository | None = None  # type: ignore

    # Class variables
    random_names = random_names
    class_values = Container.class_values.copy()
    class_values.update({"Horizon": None, "Tags": [], "z": None})

    custom_values = {
        "Description": [],
        "Position": ["resources", "prepares", "delivers", "supports", "consideration"],
        "Horizon": ["short", "medium", "long", "completed"],
    }

    def __init__(self):
        super().__init__()

    # Overidden method
    def getValue(self, key, ifNone=None):
        if key == "Information":
            return self.information()
        return super().getValue(key, ifNone)

    def clear_descriptions(self, container_set):
        self.setValue("Description", "")

    def information(self, *args):
        # Get list of containers that parent this container
        parents = self.getParents()
        if hasattr(self, "current_parent"):
            # remove the current parent from the list
            if self.current_parent in parents:
                parents.remove(self.current_parent)
        if parents:
            return f"Also impact {', '.join([parent.getValue('Name') for parent in parents])}"

    @classmethod
    def get_container_names_from_db(cls) -> List[str]:
        if cls.repository is None:
            raise RuntimeError("ContainerRepository not configured")
        return cls.repository.list_project_names()

    @classmethod
    def load_project_from_db(cls, project_name: str) -> str:
        if cls.repository is None:
            raise RuntimeError("ContainerRepository not configured")
        baseTools.instances = cls.repository.load_project(project_name)

        # remove the shadow on every direct subclass
        for cls in baseTools.__subclasses__():
            if "instances" in cls.__dict__:
                delattr(cls, "instances")
        return "WORKED"

    @classmethod
    def import_containers(cls, project_name: str) -> str:
        """Load additional containers into the in-memory list."""
        if cls.repository is None:
            raise RuntimeError("ContainerRepository not configured")
        baseTools.instances.extend(cls.repository.load_project(project_name))
        return "WORKED"

    @classmethod
    def export_containers(cls, project_name: str, containers: List[Any]) -> str:
        """Export a specific list of containers back to storage under the given project name."""
        if cls.repository is None:
            raise RuntimeError("ContainerRepository not configured")
        # Detach orphaned links for the subset if needed
        for c in containers:
            c.containers = [p for p in c.containers if p[0] in containers]
        cls.repository.save_project(project_name, containers)
        return "WORKED"

    @classmethod
    def save_project_to_db(cls, project_name: str) -> str:
        """Save all in-memory container instances to storage."""
        if cls.repository is None:
            raise RuntimeError("ContainerRepository not configured")
        # Detach orphaned links first
        for c in cls.instances:
            c.containers = [p for p in c.containers if p[0] in cls.instances]
        cls.repository.save_project(project_name, cls.instances)
        return "WORKED"

    @classmethod
    def get_task_containers(cls):
        # Get all containers that have a "task" tag
        task_containers = []
        for container in cls.instances:
            if "task" in container.getValue("Tags"):
                task_containers.append(container)
        return task_containers

    @classmethod
    def embed_containers(cls, containers):
        # use openai get_embeddings to created embeddings in z variable

        for container in containers:
            # Get the description of the container
            description = container.getValue("Description") or container.getValue("Name")
            # Get the embedding for the description
            z = get_embeddings(description)
            # Set the embedding in the container
            container.setValue("z", z)

    def export_mermaid(self, *args):
        from helpers.mermaidExporter import MermaidExporter

        exporter = MermaidExporter()
        exporter.set_diagram_type("td")
        exporter.add_node(self.getValue("id") or self.assign_id(), self.name)

        def add_container_to_mermaid(container, current_depth=0, depth_limit=2):
            if current_depth > depth_limit:
                print("Recursion depth limit reached. Skipping deeper containers.")
                return  # Stop recursion when depth limit is reached

            for subcontainer, relationship in container.containers:
                # If has id use it, else use the .assign_id()
                subcontainer_id = subcontainer.getValue("id") or subcontainer.assign_id()
                exporter.add_node(subcontainer_id, subcontainer.name)
                try:
                    if relationship is not None:
                        # If relationship is a dict, use its description or label
                        if isinstance(relationship, dict):
                            label = relationship.get("description", relationship.get("label", ""))
                        else:
                            # If relationship is a string or other type, use it directly
                            label = relationship
                    else:
                        label = ""

                except Exception as e:
                    print(f"Error getting relationship description: {e}")
                    pass
                exporter.add_edge(container.getValue("id"), subcontainer_id, label)
                # Recursive call with incremented depth
                add_container_to_mermaid(subcontainer, current_depth + 1, depth_limit)

        # Start recursion with self
        add_container_to_mermaid(self)

        # Export to Mermaid text
        mermaid_text = exporter.to_mermaid()
        print(mermaid_text)

        # Save to file
        # exporter.save_to_file("output.mmd")
        return mermaid_text

    @classmethod
    def get_reasoning_doc(cls, reasoning):
        from handlers.rtf_handler import HTMLDocument

        html = HTMLDocument()

        html.add_content("Reasoning", "h1", newline=False)
        html.add_content(reasoning, "p", newline=True)
        doc = html.get_doc()
        return doc

    def create_rtf(self):
        from handlers.rtf_handler import HTMLDocument

        def add_description(description, title):
            if description and description != "New Description" and description != "" and description != title:
                html.add_content(" - ", newline=False)
                html.add_content(description, tag="body", newline=True)
            else:
                html.add_content("", newline=True)

        html = HTMLDocument()

        def add_container_to_html(container, level=0, is_last=False, is_first=False):

            title = container.getValue("Name")
            description = container.getValue("Description")
            # Limit recursion depth to prevent overly deep nesting
            if level == 0:
                # Top level
                html.add_content(title, "h1", newline=False)
                add_description(description, title)

            elif level == 1:
                html.add_content(title, "h2", newline=False)
                add_description(description, title)

            elif level == 2:
                # Bullet list
                html.add_bullet(title)
                add_description(description, title)
            elif level == 3:
                if is_first:
                    # Add a new line before the first item in the list
                    # html.add_content("", newline=True)
                    html.add_content("Considerations: ", newline=True)

                # Concatanate
                html.add_content(title, newline=False)
                if not is_last:
                    html.add_content(", ", newline=False)
                else:
                    html.add_content(".", newline=True)
            else:
                return

            for subcontainer, relationship in container.containers:
                # Check if this subcontainer is the first item in the list
                is_first = subcontainer == container.containers[0][0]
                # Check if this subcontainer is the last item in the list
                is_last = subcontainer == container.containers[-1][0]
                add_container_to_html(subcontainer, level + 1, is_last, is_first)

        add_container_to_html(self)
        return html

    def export_clipboard(self, *args):
        html = self.create_rtf()
        html.copy_to_clipboard()

    def export_docx(self, *args):
        html = self.create_rtf()
        html.save_doc()

    def get_docx(self):
        html = self.create_rtf()
        return html.get_doc()

    def rename_from_description(self):
        # Get the description of the container
        description = self.getValue("Description")
        # Generate a name based on the description
        if not description or description == "":
            return self.getValue("Name")

        name = generate_piece_name(description)
        # Set the name of the container to the generated name
        self.setValue("Name", name)
        return name

    @classmethod
    def merge_containers(cls, containers):
        # Merge the containers into a new container
        merged_container = cls()
        # merged_container.setValue("Name", "Merged Container")

        # Add all subcontainers and their relationships to the merged container
        name = ""
        description = ""
        for containerId in containers:
            # Get the container by ID
            container = cls.get_instance_by_id(containerId)
            if not container:
                print(f"Container with ID {containerId} not found.")
                continue
            # Add each container to the merged container
            merged_container.add_container(container, "contains")
            # Concatenate names for the merged container
            if name:
                name += ", "

            if description:
                description += ", "

            name += container.getValue("Name") + " (" + str(container.getValue("Description")) + ")"
            description += container.getValue("Name") + " (" + str(container.getValue("Description")) + ")"

        # Set the name of the merged container to the concatenated names
        piece_name = generate_piece_name(description)
        merged_container.setValue("Name", piece_name)
        merged_container.setValue("Description", "Brings together " + str(len(containers)) + " priorities.")
        # Set the tags for the merged container
        # merged_container.setValue("Tags", ["group"])

        return merged_container

    @classmethod
    def categorise_containers(cls, containers):
        """
        Create new category containers for each theme returned by OpenAI,
        attaching relevant existing containers as children. Returns list of
        the new category containers.
        """
        # Prepare items for OpenAI
        items = [{"name": c.getValue("Name"), "description": c.getValue("Description") or ""} for c in containers]

        # Ask OpenAI to produce category → [item names]
        categories_map = categorize_containers(items)

        new_categories: list[ConceptContainer] = []
        for category_name, item_names in categories_map.items():
            category_container = cls()
            category_container.setValue("Name", category_name)
            category_container.setValue("Description", "")
            cls.instances.append(category_container)
            # Link children by matching names
            for cont in containers:
                if cont.name in item_names:
                    category_container.add_container(cont, "includes")
            new_categories.append(category_container)

        return new_categories

    def append_tags(self, tags):
        # Append tags to the container
        container = self
        existing_tags = container.getValue("Tags", [])
        for tag in tags:
            if tag not in existing_tags and tag != "pieces" and tag != "group":
                existing_tags.append(tag)
        container.setValue("Tags", existing_tags)

    @classmethod
    def build_relationships(cls, containers):
        """
        Build relationships between containers based on their descriptions.
        """
        relationships = []
        for container in containers:
            # Get the description of the container
            description = container.getValue("Description") or container.getValue("Name")

            # Build a key, value object with the container id and its description
            container_id = container.getValue("id") or container.assign_id()
            container_description = {
                "id": container_id,
                "description": description,
            }
            relationships.append(container_description)

        # Get a list of relationships from OpenAI
        relationships = get_relationships_from_openai(relationships)
        # Iterate over the relationships and add them to the containers
        for relationship in relationships:
            # Get the container id and its description
            source_id = relationship["source_id"]
            target_id = relationship["target_id"]
            relationship = relationship["relationship"]

            # Get the container by id
            source_container: Container = cls.get_instance_by_id(source_id)
            target_container = cls.get_instance_by_id(target_id)
            if not container:
                print(f"Container with ID {container_id} not found.")
                continue

            # Add the relationship to the container
            # source_container.add_container(target_container, relationship)
            position = {"label": relationship}
            source_container.setPosition(target_container, position)

    @classmethod
    def create_containers_from_content(cls, prompt: str, content: str):
        """Create ConceptContainers from raw text content using OpenAI."""

        pairs = distill_subject_object_pairs(prompt, content)
        container_map: dict[str, ConceptContainer] = {}

        for pair in pairs:
            subject = str(pair.get("subject", "")).strip()
            object_ = str(pair.get("object", "")).strip()
            relationship = pair.get("relationship", "")
            subject_description = str(pair.get("subject_description", "")).strip()
            object_description = str(pair.get("object_description", "")).strip()

            if not subject or not object_:
                continue

            # Check for existing container with same name for subject
            subject_container = container_map.get(subject)
            if subject_container is None:
                # First check if container already exists in instances
                subject_container = cls.get_instance_by_name(subject)
                if subject_container is None:
                    # Create new container if none exists
                    subject_container = cls()
                    subject_container.setValue("Name", subject)
                    # Set description for new containers only
                    if subject_description:
                        subject_container.setValue("Description", subject_description)
                container_map[subject] = subject_container

            # Check for existing container with same name for object
            object_container = container_map.get(object_)
            if object_container is None:
                # First check if container already exists in instances
                object_container = cls.get_instance_by_name(object_)
                if object_container is None:
                    # Create new container if none exists
                    object_container = cls()
                    object_container.setValue("Name", object_)
                    # Set description for new containers only
                    if object_description:
                        object_container.setValue("Description", object_description)
                container_map[object_] = object_container

            subject_container.add_container(
                object_container, {"label": relationship}
            )

        return list(container_map.values())
