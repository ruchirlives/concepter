from containers.baseContainer import ConceptContainer
from datetime import date, timedelta
from helpers.mermaidGanttExporter import MermaidGanttExporter


class ProjectContainer(ConceptContainer):
    months = [
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
        "Jan",
        "Feb",
        "Mar",
    ]

    class_values = ConceptContainer.class_values.copy()
    class_values.update(
        {
            "Lead": "",
            "TimeRequired": 0,
            "StartDate": None,
            "EndDate": None,
            "Impact": 0.0,
            "Effort": 0.0,
        }
    )

    def export_docx(self, *args):
        return super().export_docx(*args)

    def export_clipboard(self, *args):
        return super().export_clipboard(*args)

    def set_min_max_dates(self):
        min_date = None
        max_date = None
        for container in self.containers:
            start_date = container[0].getValue("StartDate")
            end_date = container[0].getValue("EndDate")
            if start_date is not None:
                if min_date is None or start_date < min_date:
                    min_date = start_date
                    self.setValue("StartDate", min_date)
            if end_date is not None:
                if max_date is None or end_date > max_date:
                    max_date = end_date
                    self.setValue("EndDate", max_date)
        return min_date, max_date

    def update_data(self, field, new_value, selected_index, container, parent_container):
        startDate = self.getValue("StartDate")
        endDate = self.getValue("EndDate")
        timerequired = self.getValue("TimeRequired")

        if field == "StartDate" or field == "EndDate":
            new_value = self.parse_date_auto(new_value)
            if timerequired:
                if field == "StartDate":
                    self.setValue("EndDate", new_value + timedelta(days=timerequired))
                elif field == "EndDate":
                    self.setValue("StartDate", new_value - timedelta(days=timerequired))

        elif field == "TimeRequired":
            try:
                new_value = float(new_value)
            except ValueError:
                print("Invalid time required input")
                return
            # convert to days and check startdate is at or before enddate minus time required

            if not startDate and not endDate:
                self.setValue("StartDate", date.today())
                self.setValue("EndDate", date.today() + timedelta(days=new_value))
            elif startDate and not endDate:
                self.setValue("EndDate", startDate + timedelta(days=new_value))
            elif endDate and not startDate:
                self.setValue("StartDate", endDate - timedelta(days=new_value))

            new_end_date = self.getValue("StartDate") + timedelta(days=new_value)
            if startDate and new_end_date > endDate:
                print("Time required exceeds end date")
                # Set the end date to the new end date
                self.setValue("EndDate", new_end_date)

        self.setValue(field, new_value)

    def exportGantt(self):

        def get_latest_ending_subcontainer(container):
            subcontainers = container.containers
            if not subcontainers:
                return None

            validcontainers = [
                subcontainer for subcontainer in subcontainers if subcontainer[0].getValue("EndDate") is not None
            ]

            if not validcontainers:
                return None
            containerset = max(
                validcontainers,
                key=lambda subcontainer: subcontainer[0].getValue("EndDate"),
            )
            latest = containerset[0]
            if latest is None:
                return None
            return latest

        def add_section(container):
            exporter.add_section(container.getValue("Name"))
            for subcontainertuple in container.containers:
                subcontainer = subcontainertuple[0]
                start_date = subcontainer.getValue("StartDate")
                end_date = subcontainer.getValue("EndDate")
                subcontainer_id = subcontainer.getValue("id") or subcontainer.assign_id()
                if start_date is None or end_date is None:
                    continue
                duration = end_date - start_date

                if subcontainer.containers:
                    latest = get_latest_ending_subcontainer(subcontainer)
                    if latest is None:
                        dependency = None
                    else:
                        dependency = latest.getValue("Name")
                else:
                    dependency = None

                if subcontainer.getValue("StartDate") and subcontainer.getValue("EndDate"):
                    exporter.add_task(
                        container.getValue("Name"),
                        subcontainer.getValue("Name"),
                        start_date=start_date,
                        duration=duration,
                        dependency=dependency if dependency else None,
                        id=subcontainer_id,
                    )

        exporter = MermaidGanttExporter()
        exporter.set_title(f"Gantt Diagram for {self.getValue("Name")}")
        exporter.set_date_format("YYYY-MM-DD")

        top_container = self
        top_level_containers = [subcontainer[0] for subcontainer in top_container.containers]

        for container in top_level_containers:
            add_section(container)

        exporter.save_to_file("gantt.mmd")
        return exporter.to_mermaid()


class BudgetContainer(ProjectContainer):
    # instances = ProjectContainer.instances
    class_values = ProjectContainer.class_values.copy()
    months = ProjectContainer.months

    class_values.update(
        {
            "Budget": 0,
        }
    )
    class_values.update({month: None for month in months})

    def getRawValue(self, key):
        val = self.values.get(key, None)
        return val

    # Overidden method

    def getValue(self, key):

        if key == "Budget":
            # Get all containers that are children of this container
            children = self.getChildren()

            # remove children that have None for the budget
            children = [child for child in children if child.getValue("Budget") is not None]

            if children == []:
                # return raw value
                return self.getRawValue(key)
            else:
                # Sum the budget of all children
                child_sum = sum([float(child.getValue("Budget")) for child in children])
                return child_sum

        # If the key is a month, return the value of the month
        elif key in self.months:
            if self.getRawValue(key) is None:
                # If the month is not set, we shall calculate the month amount
                # First sum all the self.months that are set
                monthly_set = [
                    float(self.getRawValue(month)) for month in self.months if self.getRawValue(month) is not None
                ]
                budget = self.getValue("Budget")
                if monthly_set == [] or budget is None:
                    return self.getRawValue(key)
                else:
                    total = sum(monthly_set)
                    # Calculate the remaining budget
                    remaining = float(budget) - total
                    # Calculate the month amount
                    return remaining / len([month for month in self.months if self.getRawValue(month) is None])

        return super().getValue(key)


class MonthlyBudgetContainer(BudgetContainer):
    # instances = BudgetContainer.instances
    class_values = BudgetContainer.class_values

    def getValue(self, key):
        if key == "Budget":
            # Sum the self.months
            monthly_array = [
                float(self.getRawValue(month)) for month in self.months if self.getRawValue(month) is not None
            ]

            if monthly_array == []:
                return self.getRawValue(key)
            else:
                return sum(monthly_array)

        return super().getValue(key)


# DID THIS WORK
class TESTContainer(ProjectContainer):
    pass
