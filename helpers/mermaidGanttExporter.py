import datetime
from container_base import Container

class MermaidGanttExporter:
    def __init__(self):
        self.diagram_type = "gantt"
        self.title = "Gantt Diagram"
        self.date_format = "YYYY-MM-DD"
        self.sections = []
        self.tasks = set()

    def set_title(self, title):
        self.title = title

    def set_date_format(self, date_format):
        self.date_format = date_format

    def add_section(self, section_name):
        self.sections.append({"name": section_name, "tasks": []})

    def get_instance_by_name(self, name):
        instances = Container.get_all_instances()
        for instance in instances:
            if instance.getValue("Name") == name:
                return instance

    def convert_duration(self, duration):
        if type(duration) is datetime.timedelta:
            return f"{duration.days}d"
        return duration

    def add_task(
        self, section_name, task_name, start_date=None, duration=None, dependency=None, id=None
    ):

        for section in self.sections:
            if section["name"] == section_name:
                task = {"name": task_name}
                if dependency:
                    task["dependency"] = dependency
                if start_date and duration:
                    task["start"] = start_date
                    task["duration"] = self.convert_duration(duration)
                elif duration:
                    task["duration"] = self.convert_duration(duration)
                if id:
                    task["id"] = id
                section["tasks"].append(task)
                self.tasks.add(task_name)
                return
        raise ValueError(f"Section '{section_name}' not found. Add the section first.")

    def to_mermaid(self):
        mermaid_str = f"{self.diagram_type}\n  title {self.title}\n  dateFormat {self.date_format}\n"
        for section in self.sections:
            mermaid_str += f"\n  section {section['name']}\n"
            for task in section["tasks"]:
                if "start" in task and "duration" in task:
                    mermaid_str += f"    {task['name']} :{task['id']}, {task['start']}, {task['duration']}\n"
                elif "duration" in task:
                    mermaid_str += f"    {task['name']} : {task['duration']}\n"

                # Add dependency task if not already added
                if "dependency" in task:
                    if task["dependency"] not in self.tasks:
                        container = self.get_instance_by_name(task["dependency"])
                        name = container.getValue("Name")
                        start_time = container.getValue("StartDate")
                        end_time = container.getValue("EndDate")
                        duration = end_time - start_time
                        duration = self.convert_duration(duration)

                        mermaid_str += f"    {name} :{task['id']}, {start_time}, {duration}\n"
                        self.tasks.add(task["dependency"])

                # Add id of task if provided as a new line
                # if "id" in task:
                #     mermaid_str += f'click {task['id']} href "javascript:callback({task['id']});"\n'

        return mermaid_str

    def replace_spaces(self, string):
        return string.replace(" ", "_")

    def save_to_file(self, filename):
        with open(filename, "w") as file:
            file.write(self.to_mermaid())


# Example usage
if __name__ == "__main__":
    exporter = MermaidGanttExporter()
    exporter.set_title("A Gantt Diagram")
    exporter.set_date_format("YYYY-MM-DD")

    exporter.add_section("Section")
    exporter.add_task("Section", "A task", start_date="2014-01-01", duration="30d")
    exporter.add_task("Section", "Another task", duration="20d", dependency="a1")

    exporter.add_section("Another")
    exporter.add_task("Another", "Task in sec", start_date="2014-01-12", duration="12d")
    exporter.add_task("Another", "another task", duration="24d")

    # Export to Mermaid text
    mermaid_text = exporter.to_mermaid()
    print(mermaid_text)

    # Save to file
    exporter.save_to_file("gantt_output.mmd")
