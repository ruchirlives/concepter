from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
from container_base import Container, baseTools
from containers.projectContainer import ProjectContainer
import logging
from time import sleep
import datetime
from functools import wraps

# Import mixins
from handlers.flask_mixins.container_crud_mixin import ContainerCRUDMixin
from handlers.flask_mixins.container_relationship_mixin import ContainerRelationshipMixin
from handlers.flask_mixins.container_persistence_mixin import ContainerPersistenceMixin
from handlers.flask_mixins.container_ai_mixin import ContainerAIMixin
from handlers.flask_mixins.container_task_mixin import ContainerTaskMixin
from handlers.flask_mixins.container_export_mixin import ContainerExportMixin
from handlers.flask_mixins.static_files_mixin import StaticFilesMixin
from handlers.flask_mixins.container_serialization_mixin import ContainerSerializationMixin
from handlers.flask_mixins.transition_metadata_mixin import TransitionMetadataMixin
from handlers.openai_mixins.container_tag_mixin import ContainerTagMixin
from handlers.openai_mixins.vector_similarity_mixin import VectorSimilarityMixin
from handlers.openai_mixins.reasoning_chain_mixin import ReasoningChainMixin


# AUTHENTICATION DECORATOR ============================================
def require_passcode(f):
    """Decorator to validate passcode in request headers."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get expected passcode from environment variable
        expected_passcode = os.getenv("API_PASSCODE")

        # If no passcode is configured, skip authentication (for development)
        if not expected_passcode:
            logging.warning("No API_PASSCODE environment variable set - authentication disabled")
            return f(*args, **kwargs)

        # Get passcode from request headers
        passcode = request.headers.get("X-Passcode")

        # Validate passcode
        if not passcode or passcode != expected_passcode:
            return jsonify({"error": "Invalid or missing passcode"}), 401

        # Passcode is valid, continue with request processing
        return f(*args, **kwargs)

    return decorated_function


def authenticate_request():
    """Standalone function to validate passcode - can be called directly in routes."""
    expected_passcode = os.getenv("API_PASSCODE")

    if not expected_passcode:
        logging.warning("No API_PASSCODE environment variable set - authentication disabled")
        return None

    passcode = request.headers.get("X-Passcode")
    if not passcode or passcode != expected_passcode:
        return {"error": "Invalid or missing passcode"}, 401

    return None


# FLASK SERVER =========================================================
class FlaskServer(
    ContainerCRUDMixin,
    ContainerRelationshipMixin,
    ContainerPersistenceMixin,
    ContainerAIMixin,
    ContainerTaskMixin,
    ContainerExportMixin,
    StaticFilesMixin,
    ContainerSerializationMixin,
    TransitionMetadataMixin,
    ContainerTagMixin,
    VectorSimilarityMixin,
    ReasoningChainMixin,
):
    def __init__(self, container_class: Container, port=8080):
        self.app = Flask(__name__, static_folder="../react-build")
        CORS(self.app)
        self.container_class: Container = container_class

        # Setup routes from mixins
        self.setup_container_crud_routes()
        self.setup_relationship_routes()
        self.setup_persistence_routes()
        self.setup_ai_routes()
        self.setup_task_routes()
        self.setup_export_routes()
        self.setup_static_routes()
        self.setup_transition_metadata_routes()

        # Apply authentication to all API routes
        self.apply_authentication_to_routes()

        # Detect runtime environment
        runtime_env = os.getenv("RUNTIME_ENV", None)

        # Use the PORT environment variable on Cloud Run or fallback to default_port
        self.port = port

        # Start logging
        logging.basicConfig(level=logging.INFO)
        logging.info("Flask server started")

    def apply_authentication_to_routes(self):
        """Apply passcode authentication to all API routes except static files."""
        # List of routes to exclude from authentication (static files, health checks, etc.)
        excluded_routes = {
            "static",
            "send_static_file",  # Flask's default static file handler
            "serve_static",  # Custom static file handler
            "index",  # Main index page that shows API documentation
        }

        # Get all registered rules
        for rule in self.app.url_map.iter_rules():
            endpoint = rule.endpoint

            # Skip static file routes and other excluded routes
            if endpoint in excluded_routes or endpoint.startswith("static"):
                continue

            # Skip if endpoint doesn't exist or is already protected
            view_func = self.app.view_functions.get(endpoint)
            if not view_func or hasattr(view_func, "_passcode_protected"):
                continue

            # Apply authentication decorator
            protected_func = require_passcode(view_func)
            protected_func._passcode_protected = True  # Mark as protected to avoid double-wrapping
            self.app.view_functions[endpoint] = protected_func

        logging.info("Applied passcode authentication to all API routes")

    def check_authentication(self):
        """Helper method to manually check authentication in routes."""
        return authenticate_request()

    def start(self):
        """Start the Flask server."""
        self.app.run(host="0.0.0.0", port=self.port)


if __name__ == "__main__":
    flask_server = FlaskServer(ProjectContainer)
    flask_server.start()
