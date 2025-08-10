from handlers.flaskHandler import FlaskServer
from containers.projectContainer import ProjectContainer
from handlers.mongodb_handler import MongoContainerRepository
from containers.conceptContainer import ConceptContainer
import threading

import dotenv

# path to .env file
path = r".env"
dotenv.load_dotenv(path)


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

    ConceptContainer.repository = MongoContainerRepository()
    baseApp = BaseApp()
    baseApp.start_foreground_server()
