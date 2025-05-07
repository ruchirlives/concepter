class MermaidExporter:
    def __init__(self):
        self.diagram_type = "graph TD"
        self.elements = []

    def set_diagram_type(self, diagram_type):
        if diagram_type.lower() in ["td", "lr", "bt", "rl"]:
            self.diagram_type = f"graph {diagram_type.upper()}"
        else:
            raise ValueError("Invalid diagram type. Use one of: TD, LR, BT, RL.")

    def add_node(self, node_id, description=None):
        if description:
            self.elements.append(f'{node_id}["{description}"]')
        else:
            self.elements.append(f"{node_id}")
        self.elements.append(f'click {node_id} href "javascript:callback(\'{node_id}\');" "{node_id}"')

    def add_edge(self, from_node, to_node, label=None):
        if label:
            self.elements.append(f"{from_node} --> |{label}| {to_node}")
        else:
            self.elements.append(f"{from_node} --> {to_node}")

    def to_mermaid(self):
        mermaid_str = f"{self.diagram_type}\n"
        for element in self.elements:
            mermaid_str += f"  {element}\n"
        return mermaid_str

    # Optional: remove this if you never need to save to file
    def save_to_file(self, filename):
        with open(filename, "w") as file:
            file.write(self.to_mermaid())
