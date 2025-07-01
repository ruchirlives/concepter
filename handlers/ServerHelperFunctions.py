# HELPER FUNCTIONS =========================================================
from container_base import Container
from containers.projectContainer import ConceptContainer, ProjectContainer
from handlers.openai_handler import generate_reasoning_argument, generate_relationship_description


import numpy as np


import datetime


class ServerHelperFunctions:
    def serialize_container_info(self, containers):
        export = []
        for container in containers:
            if not container.getValue("id"):
                id = container.assign_id()
                container.setValue("id", id)

            if container not in self.container_class.instances:
                self.container_class.instances.append(container)

            id = container.getValue("id")
            Name = container.getValue("Name")
            # only date, never time
            StartDate = container.getValue("StartDate")
            if isinstance(StartDate, datetime.datetime):
                StartDate = StartDate.date().isoformat()
            elif isinstance(StartDate, datetime.date):
                StartDate = StartDate.isoformat()
            else:
                StartDate = None

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

    def add_child_with_tags(self, container: ProjectContainer, child):
        container.add_container(child)
        # For each tag in the parent's Tags array, add it to the child unless it already exists
        parent_tags = container.getValue("Tags", [])
        child.append_tags(parent_tags)

    def vector_match(self, parent_z, child_z):
        # Ensure inputs are numpy arrays
        if parent_z is None or child_z is None:
            return 0.0

        parent_z = np.array(parent_z)
        child_z = np.array(child_z)

        # Normalize vectors
        norm_parent = np.linalg.norm(parent_z)
        norm_child = np.linalg.norm(child_z)

        if norm_parent == 0 or norm_child == 0:
            return 0.0

        similarity = np.dot(parent_z, child_z) / (norm_parent * norm_child)
        return float(similarity)

    def build_reasoning_chain_beam(self, selected_ids, start_id, end_id, max_jumps, beam_width=3):
        embeddings = {}
        names = {}

        # First check if start_id and end_id have valid embeddings
        start_container = Container.get_instance_by_id(start_id)
        end_container = Container.get_instance_by_id(end_id)
        if start_container.getValue("z") is None or end_container.getValue("z") is None:
            ConceptContainer.embed_containers([start_container, end_container])

        # Use a new list to avoid modifying selected_ids
        ids_to_use = list(selected_ids)
        if start_id not in ids_to_use:
            ids_to_use.insert(0, start_id)
        if end_id not in ids_to_use:
            ids_to_use.append(end_id)

        for node_id in ids_to_use:
            container = Container.get_instance_by_id(node_id)
            if container:
                embeddings[node_id] = container.getValue("z")
                names[node_id] = container.name
            else:
                raise ValueError(f"Container with ID {node_id} not found.")

        if start_id not in embeddings or end_id not in embeddings:
            raise ValueError("Start or end node is missing from embeddings.")

        beams = [[start_id]]
        completed_chains = []

        for _ in range(max_jumps):
            new_beams = []

            for path in beams:
                current_id = path[-1]
                current_vec = embeddings[current_id]
                visited = set(path)

                candidates = [
                    (node_id, self.vector_match(current_vec, embeddings[node_id]))
                    for node_id in ids_to_use
                    if node_id not in visited
                ]

                top_candidates = sorted(candidates, key=lambda x: x[1], reverse=True)[:beam_width]

                for next_id, _ in top_candidates:
                    new_path = path + [next_id]
                    if next_id == end_id:
                        if new_path not in completed_chains:
                            completed_chains.append(new_path)
                    else:
                        new_beams.append(new_path)

            if not new_beams:
                break  # no further expansions possible

            beams = new_beams

        if not completed_chains:
            print("No valid reasoning chain ends at the target node.")
            return []

        def average_similarity(path):
            sims = []
            for a, b in zip(path, path[1:]):
                vec_a = embeddings[a]
                vec_b = embeddings[b]
                try:
                    sim = self.vector_match(vec_a, vec_b)
                    sims.append(sim)
                except Exception as e:
                    print(f"Error computing similarity between {a} and {b}: {e}")
                    raise e
            return sum(sims) / len(sims)

        best_chain = max(completed_chains, key=average_similarity)
        label = f"{start_container.getValue('Name')} to {end_container.getValue('Name')}"
        # shorten label to 20 chars
        if len(label) > 20:
            label = label[:20] + "..."
        start_container.append_tags([label])
        end_container.append_tags([label])

        # Also build narrative
        narrative = f"Reasoning chain from {start_container.getValue('Name')} to {end_container.getValue('Name')}"

        for source_id, target_id in zip(best_chain, best_chain[1:]):
            source_container = Container.get_instance_by_id(source_id)
            target_container = Container.get_instance_by_id(target_id)

            subject = source_container.getValue("Description") or source_container.getValue("Name")
            object = target_container.getValue("Description") or target_container.getValue("Name")

            description = generate_relationship_description(subject=subject, object=object)
            source_container.setPosition(target_container, {"label": [label], "description": description})
            target_container.append_tags([label])

            # Add to narrative
            narrative += f"\n\n{subject} -> {object}: {description}"

        # Copy narrative to clipboard
        argument = generate_reasoning_argument(reasoning=narrative)

        return argument