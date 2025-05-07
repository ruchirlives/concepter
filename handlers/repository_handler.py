from abc import ABC, abstractmethod
from typing import List, Any

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
