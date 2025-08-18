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
            export.append(item)
        return export

    def serialize_node_info(self, container):
        """Serialize a single container for MongoDB nodes collection."""
        if not container.getValue("id"):
            cid = container.assign_id()
            container.setValue("id", cid)

        values = {}
        for k, v in container.values.items():
            if isinstance(v, (datetime.date, datetime.datetime)):
                values[k] = v.isoformat()
            else:
                values[k] = v

        edges = [
            {"to": child.getValue("id"), "position": pos}
            for child, pos in container.containers
        ]

        return {
            "_id": container.getValue("id"),
            "type": container.__class__.__name__,
            "values": values,
            "containers": edges,
        }

    @classmethod
    def deserialize_node_info(cls, doc):
        """Rebuild a container from a MongoDB node doc (edges rehydrated later)."""
        inst = cls()
        for k, v in doc.get("values", {}).items():
            if k in ("StartDate", "EndDate") and isinstance(v, str):
                try:
                    inst.setValue(k, datetime.date.fromisoformat(v))
                except Exception:
                    inst.setValue(k, v)
            else:
                inst.setValue(k, v)
        inst._pending_edges = doc.get("containers", [])
        return inst