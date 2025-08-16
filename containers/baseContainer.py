from helpers.random_names import random_names
from container_base import Container, baseTools
from handlers.openai_handler import openai_handler
from typing import List, Any
from handlers.repository_handler import ContainerRepository
from containers.stateTools import StateTools


class BaseContainer(Container):
    # Class‐level repository reference (set during app startup)
    repository: ContainerRepository | None = None  # type: ignore

    # Class variables
    random_names = random_names

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
        new_instances = cls.repository.load_project(project_name)
        for instance in new_instances:
            # Check if instance is already in baseTools, and if so rewire its parents and children to the new instance
            # then remove the old one
            existing_instance = baseTools.get_instance_by_id(instance.getValue("id"))
            if existing_instance:
                existing_instance.rewire(instance, new_instances)
                existing_instance.delete()
        # Remove duplicates, keeping the newly imported ones (default behavior)
        baseTools.instances.extend(new_instances)
        return "WORKED"

    def rewire(self, new_instance: "BaseContainer", all_instances: List["BaseContainer"]):
        """Rewire self's parents to new_instance, then same with children."""
        for parent in self.getParents():
            # Skip if  parent already in all_instances
            if parent in all_instances:
                continue
            # Get relationship as well
            relationship = parent.getPosition(self)
            parent.remove_container(self)
            parent.add_container(new_instance, relationship)

        for child in self.getChildren():
            # Skip if child already in all_instances
            if child in all_instances:
                continue
            # Get relationship as well
            relationship = self.getPosition(child)
            new_instance.add_container(child, relationship)

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
