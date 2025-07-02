from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
from container_base import Container, baseTools
from containers.projectContainer import ProjectContainer
import logging
from time import sleep
from handlers.mongodb_handler import delete_project
import datetime

# Import mixins
from handlers.flask_mixins.container_crud_mixin import ContainerCRUDMixin
from handlers.flask_mixins.container_relationship_mixin import ContainerRelationshipMixin
from handlers.flask_mixins.container_persistence_mixin import ContainerPersistenceMixin
from handlers.flask_mixins.container_ai_mixin import ContainerAIMixin
from handlers.flask_mixins.container_task_mixin import ContainerTaskMixin
from handlers.flask_mixins.container_export_mixin import ContainerExportMixin
from handlers.flask_mixins.static_files_mixin import StaticFilesMixin
from handlers.mixins.container_serialization_mixin import ContainerSerializationMixin
from handlers.mixins.container_tag_mixin import ContainerTagMixin
from handlers.mixins.vector_similarity_mixin import VectorSimilarityMixin
from handlers.mixins.reasoning_chain_mixin import ReasoningChainMixin


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
    ContainerTagMixin,
    VectorSimilarityMixin,
    ReasoningChainMixin
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

        # Detect runtime environment
        runtime_env = os.getenv("RUNTIME_ENV", None)

        # Use the PORT environment variable on Cloud Run or fallback to default_port
        self.port = port

        # Start logging
        logging.basicConfig(level=logging.INFO)
        logging.info("Flask server started")

    def start(self):
        """Start the Flask server."""
        self.app.run(host="0.0.0.0", port=self.port)


if __name__ == "__main__":
    flask_server = FlaskServer(ProjectContainer)
    flask_server.start()
