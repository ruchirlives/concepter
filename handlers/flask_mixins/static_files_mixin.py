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
        """Serve a generated HTML file listing API routes and their docstrings."""
        # Collect all routes and their docstrings
        routes = []
        for rule in self.app.url_map.iter_rules():
            endpoint = rule.endpoint
            view_func = self.app.view_functions.get(endpoint)
            doc = view_func.__doc__ if view_func and view_func.__doc__ else ""
            routes.append({"rule": str(rule), "endpoint": endpoint, "doc": doc.strip()})

        # Tailwind CSS CDN
        tailwind = "<script src='https://cdn.tailwindcss.com'></script>"
        # Build HTML table
        table_rows = "".join(
            [
                f"<tr class='border-b'><td class='px-4 py-2 font-mono'>{r['rule']}</td><td class='px-4 py-2'>{r['endpoint']}</td><td class='px-4 py-2'>{r['doc']}</td></tr>"  # noqa
                for r in routes
            ]
        )
        html = f"""
        <!DOCTYPE html>
        <html lang='en'>
        <head>
            <meta charset='UTF-8'>
            <meta name='viewport' content='width=device-width, initial-scale=1.0'>
            <title>API Routes</title>
            {tailwind}
        </head>
        <body class='bg-gray-50 text-gray-900'>
            <div class='max-w-4xl mx-auto my-8 p-6 bg-white rounded shadow'>
                <h1 class='text-2xl font-bold mb-4'>API Routes</h1>
                <table class='min-w-full border border-gray-300 rounded'>
                    <thead class='bg-gray-100'>
                        <tr><th class='px-4 py-2 text-left'>Route</th><th class='px-4 py-2 text-left'>Endpoint</th>
                        <th class='px-4 py-2 text-left'>Description</th></tr>
                    </thead>
                    <tbody>{table_rows}</tbody>
                </table>
            </div>
        </body>
        </html>
        """
        return html, 200, {"Content-Type": "text/html"}
