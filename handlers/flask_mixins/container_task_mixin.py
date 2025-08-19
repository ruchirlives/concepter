from flask import jsonify, request, send_file
import datetime

from containers.projectContainer import BudgetContainer, FinanceContainer


class ContainerTaskMixin:
    """Mixin for task-specific container operations."""

    def setup_task_routes(self):
        """Setup routes for task operations."""
        self.app.add_url_rule("/get_task_containers", "get_task_containers", self.get_task_containers, methods=["GET"])
        # return budget
        self.app.add_url_rule(
            "/get_container_budget", "get_container_budget", self.get_container_budget, methods=["POST"]
        )
        # convert to budget container
        self.app.add_url_rule(
            "/convert_to_budget_container",
            "convert_to_budget_container",
            self.convert_to_budget_container,
            methods=["POST"],
        )
        # add FinanceContainer
        self.app.add_url_rule(
            "/add_finance_container",
            "add_finance_container",
            self.add_finance_container,
            methods=["POST"],
        )
        # request_dedup
        self.app.add_url_rule("/request_dedup", "request_dedup", self.request_dedup, methods=["GET"])
        self.app.add_url_rule("/recopy_values", "recopy_values", self.recopy_values, methods=["GET"])
        # request_rekey
        self.app.add_url_rule("/request_rekey", "request_rekey", self.request_rekey, methods=["GET"])

    def add_finance_container(self):
        """Add a finance container."""
        container_ids = request.json.get("container_ids", [])
        for container_id in container_ids:
            container = self.container_class.get_instance_by_id(container_id)
            if container:
                finance_container = FinanceContainer()
                finance_container.setValue("Name", f"Finance - {container.getValue('Name')}")
                finance_container.add_container(container)
        return jsonify({"message": "Finance container added successfully"})

    def convert_to_budget_container(self):
        """Convert the current project container to a budget container."""
        container_ids = request.json.get("container_ids", [])
        for container_id in container_ids:
            container = self.container_class.get_instance_by_id(container_id)
            if container:
                container.convert_to_budget_container()
        return jsonify({"message": "Container converted to budget container successfully"})

    def get_container_budget(self):
        """Get the budget for containers."""
        container_ids = request.json.get("container_ids", [])
        if not container_ids:
            return jsonify({"error": "No container IDs provided"}), 400
        items = []
        for c in self.container_class.get_all_containers():
            if c.getValue("id") in container_ids:
                budget = c.getValue("Budget")
                if budget is not None:
                    items.append({"id": c.getValue("id"), "Name": c.getValue("Name"), "Budget": budget})
        return jsonify({"budgets": items})

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

        # First deduplicate inside the project
        baseTools.deduplicate_all()

        # Then deduplicate the nodes database
        total_removed = self.container_class.deduplicate_nodes()

        return jsonify({"message": "Deduplication requested successfully", "total_removed": total_removed})

    def recopy_values(self):
        """Request recopying of container values."""
        self.container_class.recopy_values()
        return jsonify({"message": "Recopying requested successfully"})
