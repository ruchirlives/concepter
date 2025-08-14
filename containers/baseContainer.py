from helpers.random_names import random_names
from container_base import Container, baseTools
from handlers.openai_handler import openai_handler
from typing import List, Any
from handlers.repository_handler import ContainerRepository
from containers.stateTools import StateTools


class ConceptContainer(Container, StateTools):
    # Class‐level repository reference (set during app startup)
    repository: ContainerRepository | None = None  # type: ignore

    # Class variables
    random_names = random_names
    class_values = Container.class_values.copy()
    class_values.update({"Horizon": None, "Tags": [], "z": None, "allStates": {}, "activeState": "base"})

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
        # Remove duplicates, keeping the newly imported ones (default behavior)
        baseTools.deduplicate_all()
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
    def delete_project_from_db(cls, project_name: str) -> bool:
        """Delete a project from storage."""
        if cls.repository is None:
            raise RuntimeError("ContainerRepository not configured")
        return cls.repository.delete_project(project_name)

    @classmethod
    def get_task_containers(cls):
        # Get all containers that have a "task" tag
        task_containers = []
        for container in cls.instances:
            tags = [tag.strip() for tag in container.getValue("Tags", [])]
            if "task" in tags:
                task_containers.append(container)
        return task_containers

    @classmethod
    def embed_containers(cls, containers):
        # use openai_handler.get_embeddings to create embeddings in z variable
        for container in containers:
            description = container.getValue("Description") or container.getValue("Name")
            z = openai_handler.get_embeddings(description)
            container.setValue("z", z)

    def export_mermaid(self, *args):
        from helpers.mermaidExporter import MermaidExporter

        exporter = MermaidExporter()
        exporter.set_diagram_type("td")
        exporter.add_node(self.getValue("id") or self.assign_id(), self.getValue("Name"))

        def add_container_to_mermaid(container, current_depth=0, depth_limit=2):
            if current_depth > depth_limit:
                print("Recursion depth limit reached. Skipping deeper containers.")
                return  # Stop recursion when depth limit is reached

            for subcontainer, relationship in container.containers:
                # If has id use it, else use the .assign_id()
                subcontainer_id = subcontainer.getValue("id") or subcontainer.assign_id()
                exporter.add_node(subcontainer_id, subcontainer.getValue("Name"))
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
        description = self.getValue("Description")
        if not description or description == "":
            return self.getValue("Name")
        name = openai_handler.generate_piece_name(description)
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
            merged_container.add_container(container, {})
            # Concatenate names for the merged container
            if name:
                name += ", "

            if description:
                description += ", "

            name += container.getValue("Name") + " (" + str(container.getValue("Description")) + ")"
            description += container.getValue("Name") + " (" + str(container.getValue("Description")) + ")"

        # Set the name of the merged container to the concatenated names
        piece_name = openai_handler.generate_piece_name(description)
        merged_container.setValue("Name", piece_name)
        merged_container.setValue("Description", "Brings together " + str(len(containers)) + " priorities.")

        # Set the tags for the merged container, by adding all the common tags from the merged containers.
        # tags must be in all containers
        tags = set()
        for containerId in containers:
            container = cls.get_instance_by_id(containerId)
            if not container:
                continue
            container_tags = set(container.getValue("Tags", []))
            if not tags:
                tags = container_tags
            else:
                tags.intersection_update(container_tags)

        merged_container.setValue("Tags", list(tags))
        return merged_container

    @classmethod
    def join_containers(cls, containers):
        """
        Join multiple containers into a single container.
        """
        if not containers:
            return None

        # Create a new container to hold the joined content
        joined_container = cls()
        name = ""
        description = ""
        sub_containers = []
        values = {}

        for container in containers:
            name += container.getValue("Name") + ", "
            description += container.getValue("Description") + "\n\n"
            sub_containers.extend(container.containers)

            # Merge values from the containers
            for key, value in container.values.items():
                if key in values:
                    # merge the value
                    if isinstance(values[key], list) and isinstance(value, list):
                        values[key].extend(value)
                    elif isinstance(values[key], str) and isinstance(value, str):
                        values[key] += ", " + value
                else:
                    values[key] = value

            # Add parents
            for parent in container.getParents():
                if parent not in joined_container.getParents():
                    joined_container.add_parent(parent, container)

            # Add children
            for subcontainer, relationship in container.containers:
                if subcontainer not in joined_container.containers:
                    joined_container.add_container(subcontainer, relationship)

        # Set the name and description for the joined container
        joined_container.setValue("Name", name.strip(", "))
        joined_container.setValue("Description", description.strip())

        # Set the values for the joined container
        for key, value in values.items():
            joined_container.setValue(key, value)

        # Remove the now joined containers
        for container in containers:
            if container in joined_container.instances:
                joined_container.instances.remove(container)

        return joined_container

    @classmethod
    def joinContainers(cls, containers):
        """Alias for join_containers to maintain backwards compatibility."""
        return cls.join_containers(containers)

    def add_parent(self, parent, sibling):
        """
        Add a parent to this container, ensuring no duplicates.
        """
        if parent not in self.getParents():
            # Find the position of the sibling in the parent's containers
            for subcontainer, pos in parent.containers:
                if subcontainer == sibling:
                    position = pos
                    break

            # Add the parent with the sibling's position
            parent.containers.append((self, position))

    @classmethod
    def categorise_containers(cls, containers):
        """
        Create new category containers for each theme returned by OpenAI,
        attaching relevant existing containers as children. Returns list of
        the new category containers.
        """
        items = [{"name": c.getValue("Name"), "description": c.getValue("Description") or ""} for c in containers]
        categories_map = openai_handler.categorize_containers(items)
        new_categories: list[ConceptContainer] = []
        for category_name, item_names in categories_map.items():
            category_container = cls()
            category_container.setValue("Name", category_name)
            category_container.setValue("Description", "")
            cls.instances.append(category_container)
            for cont in containers:
                if cont.getValue("Name") in item_names:
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

    def _build_description(self, container=None):

        if container is None:
            container = self

        # Get the description of the container
        description = container.getValue("Description")
        name = container.getValue("Name")
        if not description:
            return name
        elif description == name:
            return name
        return f"{name} - {description}"

    def suggest_relationship(self, target_container):
        """
        Suggest a relationship between this container and the target container.
        Uses OpenAI to generate a relationship description.
        """
        source_description = self._build_description()
        target_description = self._build_description(target_container)
        relationship = openai_handler.suggest_relationship_from_openai(source_description, target_description)
        self.setPosition(target_container, {"label": relationship, "description": relationship})

    @classmethod
    def build_relationships(cls, containers):
        """
        Build relationships between containers based on their descriptions.
        """
        relationships = []
        for container in containers:
            description = cls._build_description(container)
            container_id = container.getValue("id") or container.assign_id()
            container_description = {
                "id": container_id,
                "description": description,
            }
            relationships.append(container_description)
        relationships = openai_handler.get_relationships_from_openai(relationships)
        for relationship in relationships:
            source_id = relationship["source_id"]
            target_id = relationship["target_id"]
            rel_text = relationship["relationship"]
            source_container: Container = cls.get_instance_by_id(source_id)
            target_container = cls.get_instance_by_id(target_id)
            if not source_container or not target_container:
                print(f"Container with ID {source_id} or {target_id} not found.")
                continue
            position = {"label": rel_text}
            source_container.setPosition(target_container, position)

    @classmethod
    def create_containers_from_content(cls, prompt: str, content: str):
        """Create ConceptContainers from raw text content using OpenAI."""
        pairs = openai_handler.distill_subject_object_pairs(prompt, content)
        container_map: dict[str, ConceptContainer] = {}
        for pair in pairs:
            subject = str(pair.get("subject", "")).strip()
            object_ = str(pair.get("object", "")).strip()
            relationship = pair.get("relationship", "")
            subject_description = str(pair.get("subject_description", "")).strip()
            object_description = str(pair.get("object_description", "")).strip()
            if not subject or not object_:
                continue
            subject_container = container_map.get(subject)
            if subject_container is None:
                subject_container = cls.get_instance_by_name(subject)
                if subject_container is None:
                    subject_container = cls()
                    subject_container.setValue("Name", subject)
                    if subject_description:
                        subject_container.setValue("Description", subject_description)
                container_map[subject] = subject_container
            object_container = container_map.get(object_)
            if object_container is None:
                object_container = cls.get_instance_by_name(object_)
                if object_container is None:
                    object_container = cls()
                    object_container.setValue("Name", object_)
                    if object_description:
                        object_container.setValue("Description", object_description)
                container_map[object_] = object_container
            subject_container.add_container(object_container, {"label": relationship})
        return list(container_map.values())

# Add and remove container by id methods

    def add_container_by_id(self, container_id: str, relationship: dict):
        """
        Add a container by its ID.
        """
        container = self.get_instance_by_id(container_id)
        if container:
            self.add_container(container, relationship)

    def remove_container_by_id(self, container_id: str):
        """
        Remove a container by its ID.
        """
        container = self.get_instance_by_id(container_id)
        if container:
            self.remove_container(container)

    def update_container_relationship(self, container_id: str, relationship: dict):
        """
        Update the relationship of a container by its ID.
        """
        container = self.get_instance_by_id(container_id)
        if container:
            self.setPosition(container, relationship)
        else:
            raise ValueError(f"Container with ID {container_id} not found.")
