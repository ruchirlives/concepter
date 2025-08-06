from flask import jsonify, request
import logging


class TransitionMetadataMixin:
    """Mixin for handling transition metadata storage and retrieval."""

    def setup_transition_metadata_routes(self):
        """Setup routes for transition metadata operations."""
        self.app.add_url_rule(
            "/save_transition_metadata", "save_transition_metadata", self.save_transition_metadata, methods=["POST"]
        )
        self.app.add_url_rule(
            "/load_transition_metadata", "load_transition_metadata", self.load_transition_metadata, methods=["GET"]
        )
        self.app.add_url_rule(
            "/delete_transition_metadata",
            "delete_transition_metadata",
            self.delete_transition_metadata,
            methods=["DELETE"],
        )

    def save_transition_metadata(self):
        """Save transition metadata to MongoDB using the repository pattern."""
        try:
            data = request.get_json()
            metadata = data.get("metadata")

            if not metadata:
                return jsonify({"message": "No metadata provided"}), 400

            # Validate that metadata is a valid JSON object
            if not isinstance(metadata, dict):
                return jsonify({"message": "Metadata must be a JSON object"}), 400

            # Use the class repository that was set up in app.py
            if self.container_class.repository is None:
                return jsonify({"message": "Repository not configured"}), 500

            self.container_class.repository.save_transition_metadata(metadata)

            logging.info("Transition metadata saved successfully")
            return jsonify({"message": "Transition metadata saved successfully"})

        except Exception as e:
            logging.error(f"Error saving transition metadata: {e}")
            return jsonify({"message": "Error saving transition metadata", "error": str(e)}), 500

    def load_transition_metadata(self):
        """Load transition metadata from MongoDB using the repository pattern."""
        try:
            # Use the class repository that was set up in app.py
            if self.container_class.repository is None:
                return jsonify({"message": "Repository not configured"}), 500

            metadata = self.container_class.repository.load_transition_metadata()

            if metadata is None:
                logging.info("No transition metadata found")
                return jsonify({"metadata": None, "message": "No transition metadata found"})

            logging.info("Transition metadata loaded successfully")
            return jsonify({"metadata": metadata, "message": "Transition metadata loaded successfully"})

        except Exception as e:
            logging.error(f"Error loading transition metadata: {e}")
            return jsonify({"message": "Error loading transition metadata", "error": str(e)}), 500

    def delete_transition_metadata(self):
        """Delete transition metadata from MongoDB using the repository pattern."""
        try:
            # Use the class repository that was set up in app.py
            if self.container_class.repository is None:
                return jsonify({"message": "Repository not configured"}), 500

            deleted = self.container_class.repository.delete_transition_metadata()

            if not deleted:
                return jsonify({"message": "No transition metadata found to delete"}), 404

            logging.info("Transition metadata deleted successfully")
            return jsonify({"message": "Transition metadata deleted successfully"})

        except Exception as e:
            logging.error(f"Error deleting transition metadata: {e}")
            return jsonify({"message": "Error deleting transition metadata", "error": str(e)}), 500
