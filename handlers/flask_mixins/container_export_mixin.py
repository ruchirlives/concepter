from flask import jsonify, request, send_file, send_from_directory
import os
from handlers.tts_handler import export_pawns_to_json


class ContainerExportMixin:
    """Mixin for container export operations (Mermaid, Gantt, DOCX, etc.)."""

    def setup_export_routes(self):
        """Setup routes for export operations."""
        self.app.add_url_rule("/get_mermaid", "get_mermaid", self.export_mermaid, methods=["POST"])
        self.app.add_url_rule("/get_gantt", "get_gantt", self.export_gantt, methods=["POST"])
        self.app.add_url_rule("/get_docx", "get_word_doc", self.get_docx, methods=["POST"])
        self.app.add_url_rule("/get_onenote", "get_onenote", self.get_onenote, methods=["POST"])
        self.app.add_url_rule("/export_tts", "export_tts", self.export_tts, methods=["POST"])

    def export_mermaid(self):
        """Export container as Mermaid diagram."""
        data = request.get_json()
        container_id = data["container_id"]
        container = self.container_class.get_instance_by_id(container_id)

        if container:
            mermaid = container.export_mermaid()
            return jsonify({"mermaid": mermaid})
        return jsonify({"mermaid": "Container not found"})

    def export_gantt(self):
        """Export container as Gantt chart."""
        data = request.get_json()
        container_id = data["container_id"]
        container = self.container_class.get_instance_by_id(container_id)

        if container:
            mermaid = container.exportGantt()
            return jsonify({"mermaid": mermaid})
        return jsonify({"mermaid": "Container not found"})

    def get_docx(self):
        """Export container as DOCX document."""
        data = request.get_json()
        container_id = data["container_id"]
        container = self.container_class.get_instance_by_id(container_id)

        if container:
            # Assume container.get_docx() returns a BytesIO stream containing the DOCX
            doc_stream = container.get_docx()
            doc_stream.seek(0)  # Ensure the stream is at the beginning
            return send_file(
                doc_stream,
                as_attachment=True,
                download_name="output.docx",
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        return jsonify({"doc": "Container not found"})

    def get_onenote(self):
        """Export container as OneNote document."""
        data = request.get_json()
        container_id = data["container_id"]
        container = self.container_class.get_instance_by_id(container_id)

        if container:
            onenote_content = container.get_onenote()
            return jsonify({"onenote": onenote_content})
        return jsonify({"onenote": "Container not found"})

    def export_tts(self):
        """Export ConceptContainer instances to a Tabletop Simulator save JSON.

        Optional JSON body fields:
        - container_ids: list[str] to limit which containers are exported
        - save_path: override default save location
        """
        data = request.get_json(silent=True) or {}
        container_ids = data.get("container_ids")
        save_path = data.get("save_path")

        containers = None
        if container_ids:
            containers = []
            for cid in container_ids:
                c = self.container_class.get_instance_by_id(cid)
                if c:
                    containers.append(c)

        try:
            count, path = export_pawns_to_json(containers=containers, save_path=save_path)
            return jsonify({
                "ok": True,
                "exported": count,
                "path": path,
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 400
