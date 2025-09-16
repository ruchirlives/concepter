from handlers.flaskHandler import FlaskServer
from containers.projectContainer import ProjectContainer
from containers.conceptContainer import ConceptContainer
import threading
import logging
import os

import dotenv

# path to .env file
path = r".env"
dotenv.load_dotenv(path)


def configure_repository() -> None:
    # Configure ConceptContainer.repository based on CONCEPTER_REPOSITORY
    backend = os.getenv("CONCEPTER_REPOSITORY", "mongo").strip().lower()
    if backend == "mongo":
        from handlers.mongodb_handler import MongoContainerRepository

        ConceptContainer.repository = MongoContainerRepository()
        logging.info("Configured ConceptContainer.repository with Mongo backend")
    elif backend in {"none", "", "disabled"}:
        ConceptContainer.repository = None
        logging.info("ConceptContainer.repository disabled (backend=%s)", backend or "none")
    else:
        logging.warning(
            "Unknown CONCEPTER_REPOSITORY '%s'; ConceptContainer.repository not configured",
            backend,
        )
        ConceptContainer.repository = None


class BaseApp:
    def __init__(self, container_class=ProjectContainer):
        self.container_class = container_class
        # Initialise server
        self.server = FlaskServer(self.container_class)

    def start_background_server(self):
        self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        self.server_thread.start()

    def start_foreground_server(self):
        self.server.start()


if __name__ == "__main__":
    # Create an instance of BaseApp and let its server start

    configure_repository()
    baseApp = BaseApp()
    baseApp.start_foreground_server()
