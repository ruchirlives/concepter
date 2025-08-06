#!/usr/bin/env python3
"""
Example usage of the transition metadata repository pattern.
This demonstrates how to use the repository through the container class.
"""

from containers.baseContainer import ConceptContainer
from handlers.mongodb_handler import MongoContainerRepository


def example_usage():
    """Example of how to use the transition metadata repository through the container class."""

    # Set up the repository (this is normally done in app.py)
    ConceptContainer.repository = MongoContainerRepository()

    # Example metadata
    sample_metadata = {
        "project_id": "example_project",
        "transitions": [
            {
                "id": "t1",
                "name": "Initialize",
                "from_state": "start",
                "to_state": "planning",
                "timestamp": "2025-08-06T10:00:00Z",
            },
            {
                "id": "t2",
                "name": "Design",
                "from_state": "planning",
                "to_state": "design",
                "timestamp": "2025-08-06T11:00:00Z",
            },
        ],
        "metadata": {"version": "1.0", "created_by": "system", "last_updated": "2025-08-06T12:00:00Z"},
    }

    try:
        # Save transition metadata using the class repository
        print("Saving transition metadata...")
        ConceptContainer.repository.save_transition_metadata(sample_metadata)
        print("✅ Metadata saved successfully")

        # Load transition metadata using the class repository
        print("Loading transition metadata...")
        loaded_metadata = ConceptContainer.repository.load_transition_metadata()

        if loaded_metadata:
            print("✅ Metadata loaded successfully")
            print(f"Project ID: {loaded_metadata.get('project_id')}")
            print(f"Number of transitions: {len(loaded_metadata.get('transitions', []))}")
            print(f"Version: {loaded_metadata.get('metadata', {}).get('version')}")
        else:
            print("ℹ️ No metadata found")

        # Delete transition metadata using the class repository
        print("Deleting transition metadata...")
        deleted = ConceptContainer.repository.delete_transition_metadata()

        if deleted:
            print("✅ Metadata deleted successfully")
        else:
            print("ℹ️ No metadata to delete")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    example_usage()
