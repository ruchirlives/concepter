import datetime


class ContainerSerializationMixin:
    """Mixin for serializing container data for API responses."""

    def serialize_container_info(self, containers):
        """Serialize container information for JSON responses, only specifying special conversions."""
        # Specify only keys that need special conversion
        special_conversions = {
            "StartDate": lambda v: (
                v.date().isoformat()
                if isinstance(v, datetime.datetime)
                else v.isoformat() if isinstance(v, datetime.date) else None
            ),
            "EndDate": lambda v: (
                v.date().isoformat()
                if isinstance(v, datetime.datetime)
                else v.isoformat() if isinstance(v, datetime.date) else None
            ),
            "Tags": lambda v: ",".join(v or []),
        }

        export = []
        for container in containers:
            if not container.getValue("id"):
                id = container.assign_id()
                container.setValue("id", id)

            if container not in self.container_class.instances:
                self.container_class.instances.append(container)

            # Dynamically get all keys from the container's class_values
            export_keys = list(getattr(container.__class__, "class_values", {}).keys())
            # Always include 'id' and 'Name' if not present
            if "id" not in export_keys:
                export_keys.insert(0, "id")
            if "Name" not in export_keys:
                export_keys.insert(1, "Name")

            item = {}
            for key in export_keys:
                value = container.getValue(key)
                if key in special_conversions:
                    value = special_conversions[key](value)
                item[key] = value

            # If pending edges exist, include them in the export
            # if container._pending_edges:
            if hasattr(container, "_pending_edges") and container._pending_edges:
                item["PendingEdges"] = container._pending_edges

            export.append(item)
        return export
