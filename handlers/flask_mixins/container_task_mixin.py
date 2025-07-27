from flask import jsonify, request, send_file
import datetime


class ContainerTaskMixin:
    """Mixin for task-specific container operations."""

    def setup_task_routes(self):
        """Setup routes for task operations."""
        self.app.add_url_rule("/get_task_containers", "get_task_containers", self.get_task_containers, methods=["GET"])
        self.app.add_url_rule("/request_rekey", "request_rekey", self.request_rekey, methods=["GET"])
        # request_dedup
        self.app.add_url_rule("/request_dedup", "request_dedup", self.request_dedup, methods=["GET"])

    def get_task_containers(self):
        """Get containers tagged with task."""
        items = []
        for c in self.container_class.get_task_containers():
            sd = c.getValue("StartDate")
            if isinstance(sd, datetime.datetime):
                sd = sd.date().isoformat()
            elif isinstance(sd, datetime.date):
                sd = sd.isoformat()
            else:
                sd = "No start date"

            ed = c.getValue("EndDate")
            if isinstance(ed, datetime.datetime):
                ed = ed.date().isoformat()
            elif isinstance(ed, datetime.date):
                ed = ed.isoformat()
            else:
                ed = "No end date"

            body = "<p>".join(
                [
                    c.getValue("Name") or "",
                    "Starts " + sd,
                    "Ends " + ed,
                ]
            )

            item = {
                "subject": c.getValue("Name"),
                "body": body,
            }

            end_date = c.getValue("EndDate")
            if end_date:
                item["end_date"] = str(end_date)

            items.append(item)

        return jsonify({"containers": items})

    def request_rekey(self):
        """Request a rekey of the containers."""
        self.container_class.rekey_all_ids()
        return jsonify({"message": "Rekey requested successfully"})

    def request_dedup(self):
        """Request deduplication of containers."""
        from container_base import baseTools
        baseTools.deduplicate_all()
        return jsonify({"message": "Deduplication requested successfully"})
