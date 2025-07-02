from container_base import Container
from containers.projectContainer import ConceptContainer
from handlers.openai_handler import generate_reasoning_argument, generate_relationship_description


class ReasoningChainMixin:
    """Mixin for building reasoning chains using beam search."""
    
    def build_reasoning_chain_beam(self, selected_ids, start_id, end_id, max_jumps, beam_width=3):
        """Build a reasoning chain from start to end using beam search algorithm."""
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

        # Build embeddings and names dictionaries
        for node_id in ids_to_use:
            container = Container.get_instance_by_id(node_id)
            if container:
                embeddings[node_id] = container.getValue("z")
                names[node_id] = container.name
            else:
                raise ValueError(f"Container with ID {node_id} not found.")

        if start_id not in embeddings or end_id not in embeddings:
            raise ValueError("Start or end node is missing from embeddings.")

        # Initialize beam search
        beams = [[start_id]]
        completed_chains = []

        # Beam search iterations
        for _ in range(max_jumps):
            new_beams = []

            for path in beams:
                current_id = path[-1]
                current_vec = embeddings[current_id]
                visited = set(path)

                # Find candidate next nodes
                candidates = [
                    (node_id, self.vector_match(current_vec, embeddings[node_id]))
                    for node_id in ids_to_use
                    if node_id not in visited
                ]

                # Select top candidates based on similarity
                top_candidates = sorted(candidates, key=lambda x: x[1], reverse=True)[:beam_width]

                for next_id, _ in top_candidates:
                    new_path = path + [next_id]
                    if next_id == end_id:
                        if new_path not in completed_chains:
                            completed_chains.append(new_path)
                    else:
                        new_beams.append(new_path)

            if not new_beams:
                break  # No further expansions possible

            beams = new_beams

        if not completed_chains:
            print("No valid reasoning chain ends at the target node.")
            return []

        # Select best chain based on average similarity
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
        
        # Create label and tag containers
        label = f"{start_container.getValue('Name')} to {end_container.getValue('Name')}"
        # Shorten label to 20 chars
        if len(label) > 20:
            label = label[:20] + "..."
        start_container.append_tags([label])
        end_container.append_tags([label])

        # Build narrative
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

        # Generate final argument
        argument = generate_reasoning_argument(reasoning=narrative)
        return argument
