import datetime


class ContainerSerializationMixin:
    """Mixin for serializing container data for API responses."""

    def serialize_container_info(self, containers):
        """Serialize container information for JSON responses."""
        export = []
        for container in containers:
            if not container.getValue("id"):
                id = container.assign_id()
                container.setValue("id", id)

            if container not in self.container_class.instances:
                self.container_class.instances.append(container)

            id = container.getValue("id")
            Name = container.getValue("Name")

            # Handle StartDate - only date, never time
            StartDate = container.getValue("StartDate")
            if isinstance(StartDate, datetime.datetime):
                StartDate = StartDate.date().isoformat()
            elif isinstance(StartDate, datetime.date):
                StartDate = StartDate.isoformat()
            else:
                StartDate = None

            # Handle EndDate - only date, never time
            EndDate = container.getValue("EndDate")
            if isinstance(EndDate, datetime.datetime):
                EndDate = EndDate.date().isoformat()
            elif isinstance(EndDate, datetime.date):
                EndDate = EndDate.isoformat()
            else:
                EndDate = None

            TimeRequired = container.getValue("TimeRequired")
            Horizon = container.getValue("Horizon")
            tags = container.getValue("Tags") or []
            tags = ",".join(tags)

            export.append(
                {
                    "id": container.getValue("id"),
                    "Name": container.getValue("Name"),
                    "Tags": tags,
                    "Description": container.getValue("Description"),
                    "StartDate": StartDate,
                    "EndDate": EndDate,
                    "TimeRequired": TimeRequired,
                    "Horizon": Horizon,
                }
            )
        return export
