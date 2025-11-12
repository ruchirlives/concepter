from container_base import Container, baseTools
from typing import List, Any, Optional
from handlers.repository_handler import ContainerRepository
import datetime

CLASS_REGISTRY = {}


class BaseContainer(Container):
    # Class‐level repository reference (set during app startup)
    repository: ContainerRepository | None = None  # type: ignore

    # Class variables
    project_state_variables: Optional[List[Any]] = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        CLASS_REGISTRY[cls.__name__] = cls

    @classmethod
    def load_project_from_db(cls, project_name: str) -> str:
        if cls.repository is None:
            raise RuntimeError("ContainerRepository not configured")
        # Clear all in-memory instances before loading new project
        baseTools.instances.clear()
        load_result = cls.repository.load_project(project_name)

        if isinstance(load_result, tuple):
            containers, state_variables = load_result
        else:
            containers, state_variables = load_result, None

        containers_list = list(containers) if not isinstance(containers, list) else containers
        baseTools.instances = containers_list

        if isinstance(state_variables, list):
            cls.project_state_variables = list(state_variables)
        elif state_variables is None:
            cls.project_state_variables = []
        else:
            cls.project_state_variables = state_variables

        # remove the shadow on every direct subclass
        for subcls in baseTools.__subclasses__():
            if "instances" in subcls.__dict__:
                delattr(subcls, "instances")
        return "Worked"

    @classmethod
    def import_containers(cls, project_name: str) -> str:
        """Load additional containers into the in-memory list."""
        if cls.repository is None:
            raise RuntimeError("ContainerRepository not configured")
        load_result = cls.repository.load_project(project_name)

        if isinstance(load_result, tuple):
            new_instances, _ = load_result
        else:
            new_instances = load_result

        new_instances_list = (
            list(new_instances) if not isinstance(new_instances, list) else new_instances
        )
        baseTools.instances.extend(new_instances_list)
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

    def add_relationship(self, source_id, target_id, position):
        """
        Add or replace a reference to a relationship between two containers.
        """
        self.relationships = [rel for rel in self.relationships if rel["source"] != source_id and rel["target"] != target_id]
        self.relationships.append({"source": source_id, "target": target_id, "position": position})

    def remove_relationship(self, source_id, target_id):
        """
        Remove a relationship between two containers.
        """
        self.relationships = [rel for rel in self.relationships if not (rel["source"] == source_id and rel["target"] == target_id)]

    @classmethod
    def export_containers(cls, project_name: str, containers: List[Any]) -> str:
        """Export a specific list of containers back to storage under the given project name."""
        if cls.repository is None:
            raise RuntimeError("ContainerRepository not configured")
        # Detach orphaned links for the subset if needed
        # for c in containers:
        #     c.containers = [p for p in c.containers if p[0] in containers]
        cls.repository.save_project(project_name, containers)
        return "WORKED"

    @classmethod
    def save_project_to_db(cls, project_name: str, state_variables: Optional[List[Any]] = None) -> str:
        """Save all in-memory container instances to storage.

        Parameters
        ----------
        project_name: str
            The name under which the project should be saved.
        state_variables: Optional[List[Any]]
            Additional state metadata provided by the frontend that should be
            persisted alongside the project document.
        """

        if cls.repository is None:
            raise RuntimeError("ContainerRepository not configured")

        # If no instance, don't save
        if not cls.instances:
            return "NO INSTANCES TO SAVE"

        # Detach orphaned links first
        for c in cls.instances:
            c.containers = [p for p in c.containers if p[0] in cls.instances]
            c.prune_states()
        if isinstance(state_variables, list):
            cls.project_state_variables = list(state_variables)
        elif state_variables is not None:
            cls.project_state_variables = state_variables
        cls.repository.save_project(project_name, cls.instances, state_variables=state_variables)
        return "WORKED"

    @classmethod
    def save_nodes_to_db(cls, nodeIds: List[Any]) -> str:
        """Save a list of container instances to storage based on ids."""
        nodes = [c for c in cls.instances if c.getValue("id") in nodeIds]
        if cls.repository is None:
            raise RuntimeError("ContainerRepository not configured")
        cls.repository.save_nodes(nodes)
        return "WORKED"

    @classmethod
    def delete_project_from_db(cls, project_name: str) -> bool:
        """Delete a project from storage."""
        if cls.repository is None:
            raise RuntimeError("ContainerRepository not configured")
        return cls.repository.delete_project(project_name)

    def get_model(self):
        """Get the model from repository handler."""
        if self.repository is None:
            raise RuntimeError("ContainerRepository not configured")
        return self.repository.get_model_from_id(self.getValue("id"))

    # Add and remove container by id methods

    # @classmethod
    # def deduplicate_nodes(cls):
    #     """Deduplicate nodes in the database."""
    #     if cls.repository is None:
    #         raise RuntimeError("ContainerRepository not configured")
    #     return cls.repository.deduplicate_nodes()

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

    def serialize_node_info(self):
        """Serialize this container for MongoDB nodes collection."""
        if not self.getValue("id"):
            cid = self.assign_id()
            self.setValue("id", cid)

        # serialize values
        values = {}
        for k, v in self.values.items():
            if isinstance(v, (datetime.date, datetime.datetime)):
                values[k] = v.isoformat()
            else:
                values[k] = v

        # normal edges
        edges = [{"to": child.getValue("id"), "position": pos, "Name": child.getValue("Name")} for child, pos in self.containers]

        # relationships
        relationships = []
        for rel in self.relationships:
            rel_dict = {"source": rel["source"], "target": rel["target"], "position": rel["position"]}
            relationships.append(rel_dict)

        # add any pending edges (may include unmatched references)
        if getattr(self, "_pending_edges", None):
            edges.extend(self._pending_edges)

        return {
            "_id": self.getValue("id"),
            "type": self.__class__.__name__,
            "values": values,
            "containers": edges,
            "relationships": relationships,
        }

    @classmethod
    def deserialize_node_info(cls, doc: dict):
        """
        Rebuild a container from a MongoDB node doc.
        The correct subclass is chosen from doc["type"].
        Edges are left in _pending_edges for rehydration later.
        """
        # choose correct subclass if available
        type_name = doc.get("type", cls.__name__)
        container_cls = CLASS_REGISTRY.get(type_name, cls)

        inst = container_cls()

        # restore values
        for k, v in doc.get("values", {}).items():
            if isinstance(v, str) and k in ("StartDate", "EndDate"):
                try:
                    inst.setValue(k, datetime.datetime.fromisoformat(v))
                except ValueError:
                    try:
                        inst.setValue(k, datetime.date.fromisoformat(v))
                    except Exception:
                        inst.setValue(k, v)
            else:
                inst.setValue(k, v)

        # stash edges for re-link pass
        inst._pending_edges = doc.get("containers", [])

        # relationships
        inst.relationships = doc.get("relationships", [])

        return inst

    # Just remove from the project
    @classmethod
    def remove_container_from_project(cls, container_obj):
        cls.instances.remove(container_obj)
        # Append a reference to the deleted container to _pending_edges for its parent containers
        for parent in container_obj.getParents():
            edge = {
                "to": container_obj.getValue("id"),
                "position": parent.getPosition(container_obj),
                "Name": container_obj.getValue("Name"),
            }
            parent._pending_edges.append(edge)
            parent.remove_container(container_obj)
