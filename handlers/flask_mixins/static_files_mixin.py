from flask import send_from_directory
import os


class StaticFilesMixin:
    """Mixin for serving static files (React frontend)."""

    def setup_static_routes(self):
        """Setup routes for static file serving."""
        self.app.add_url_rule("/static/<path:path>", "serve_static", self.serve_static)
        self.app.add_url_rule("/", "index", self.index, methods=["GET"])

    def serve_static(self, path):
        """Serve static files from the React build directory."""
        return send_from_directory(os.path.join(self.app.static_folder, "static"), path)

    def index(self):
        """Serve the main React index.html file."""
        return send_from_directory(self.app.static_folder, "index.html")
