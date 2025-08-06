from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional


class ContainerRepository(ABC):
    """Abstract interface for persisting ConceptContainer instances."""

    @abstractmethod
    def list_project_names(self) -> List[str]:
        """Return a list of all project names."""
        pass

    @abstractmethod
    def load_project(self, name: str) -> List[Any]:
        """Load all containers for the given project name."""
        pass

    @abstractmethod
    def save_project(self, name: str, containers: List[Any]) -> None:
        """Persist the list of containers under the given project name."""
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
