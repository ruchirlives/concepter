from containers.conceptContainer import ConceptContainer
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
        {"Lead": "", "TimeRequired": 0, "StartDate": None, "EndDate": None, "Cost": 0.0}
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

    def convert_to_budget_container(self):
        """Convert the current project container to a budget container."""
        self.__class__ = BudgetContainer
        # Set Cost to 0
        self.setValue("Cost", 0)
        return self


class BudgetContainer(ProjectContainer):

    class_values = ProjectContainer.class_values.copy()
    class_values.update({"Budget": 0})

    def getValue(self, key, ifNone=None):
        if key == "Budget":
            # First add own Cost
            budget = self.values.get("Cost", 0)

            # Now add children's Budgets recursively
            for child in self.getChildren():
                child_budget = child.getValue("Budget")
                if child_budget is not None:
                    budget += float(child_budget)
            return budget
        return super().getValue(key, ifNone=ifNone)


class FinanceContainer(BudgetContainer):
    """Finance container for managing financial data within a project."""

    class_values = BudgetContainer.class_values.copy()
    class_values.update({"Function": "Budget*2"})

    def getValue(self, key, ifNone=None):
        if key == "Budget":
            # First add own Cost
            budget = self.values.get("Cost", 0)

            # Now add children's Budgets recursively
            for child in self.getChildren():
                child_budget = child.getValue("Budget")
                if child_budget is not None:
                    budget += float(child_budget)

            # Parse and evaluate the Function formula
            function = self.values.get("Function", "")
            if function:
                # Replace 'Budget' with the computed budget value in the formula
                formula = function.replace("Budget", str(budget))
                try:
                    # Evaluate the formula safely
                    result = eval(formula, {"__builtins__": {}})
                    return result
                except Exception:
                    return budget  # fallback to budget if formula fails
            return budget
        return super().getValue(key, ifNone=ifNone)
