from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional, Tuple


class ContainerRepository(ABC):

    @abstractmethod
    def get_top_by_z(self, z_vector) -> Optional[Dict[str, Any]]:
        """Retrieve containers whose position.z is within the specified tolerance of z_value."""
        pass

    @abstractmethod
    def get_model_from_id(self, container_id: Any) -> Optional[Dict[str, Any]]:
        """Retrieve the model dictionary for the container with the given id."""
        pass

    @abstractmethod
    def search_position_z(self, searchTerm: str, top_n: int = 10) -> list:
        """Vector search: Find containers whose position.z is most similar to the searchTerm embedding.
        Returns a merged single list of parent_ids and container_ids (flat list, top_n results)."""
        pass

    @abstractmethod
    def load_node(self, node_id: Any) -> Optional[Any]:
        """Load an individual node document by its id and return the deserialized container instance."""
        pass

    """Abstract interface for persisting ConceptContainer instances."""

    @abstractmethod
    def search_nodes(self, search_term: str, tags: List[str]) -> List[Dict[str, Any]]:
        """Search nodes by a case-insensitive term and return id and Name fields."""
        pass

    @abstractmethod
    def deduplicate_nodes(self) -> None:
        """Remove duplicate nodes from the database."""
        pass

    @abstractmethod
    def list_project_names(self) -> List[str]:
        """Return a list of all project names."""
        pass

    @abstractmethod
    def load_project(self, name: str) -> Tuple[List[Any], Optional[List[Any]]]:
        """Load all containers and associated state variables for the given project name."""
        pass

    @abstractmethod
    def save_project(
        self, name: str, containers: List[Any], state_variables: Optional[List[Any]] = None
    ) -> None:
        """Persist the list of containers and optional state variables under the given project name."""
        pass

    @abstractmethod
    def save_nodes(self, nodes: List[Any]) -> None:
        """Persist a list of container instances."""
        pass

    @abstractmethod
    def delete_project(self, name: str) -> bool:
        """Delete a project by name. Returns True if successful, False otherwise."""
        pass

    @abstractmethod
    def save_transition_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save transition metadata."""
        pass

    @abstractmethod
    def load_transition_metadata(self) -> Optional[Dict[str, Any]]:
        """Load transition metadata. Returns None if not found."""
        pass

    @abstractmethod
    def delete_transition_metadata(self) -> bool:
        """Delete transition metadata. Returns True if successful, False otherwise."""
        pass

    @abstractmethod
    def delete_nodes(self, node_ids: List[Any]) -> int:
        """Delete nodes by their ids. Returns the count of deleted nodes."""
        pass

    @abstractmethod
    def find_relationship_influencers(
        self, pairs: List[Tuple[str, str]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return containers whose relationship pairs match the provided source/target ids."""
        pass

    @abstractmethod
    def remove_relationship(self, container_id: Any, source_id: str, target_id: str) -> bool:
        """Remove a relationship entry from the given container's persisted node.

        Returns True if a relationship was removed, False otherwise.
        """
        pass
