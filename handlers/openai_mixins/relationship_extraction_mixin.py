import json
import ast
import re


class RelationshipExtractionMixin:
    """Mixin for extracting relationships between entities using AI."""
    
    def get_relationships_from_openai(self, items: list[dict[str, str]]) -> list[dict[str, str]]:
        """
        Given a list of dicts with 'id' and 'description', call OpenAI to
        build a relationship map between items. The output is a python list
        mapping each item id to a list of related item ids: {source_id, target_id, relationship}
        """
        client = self.get_openai_client()
        
        prompt = (
            "You are a helpful assistant whose ONLY job is to output a valid python list.\n"
            'Given these items, each with an "id" and a "description":\n'
            "  • Relationships are short 1 to 3 word descriptive statements relating one id to another id "
            "from the source list based on an expected relationship.\n"
            "  • Each item in the output list should have a source_id, target_id, relationship.\n"
            "  • Do NOT include markdown fences, comments, or extra keys.\n"
            "  • Ensure all braces are balanced and fully closed.\n\n"
            "Items:\n"
        )
        
        for item in items:
            prompt += f"- {item['id']}: {item['description']}\n"
        prompt += "\nNow strictly output the python list:"

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "text"},
            temperature=0.7,
            max_completion_tokens=1500,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            store=False,
        )
        
        raw = response.choices[0].message.content.strip()

        # Remove any markdown fences from the python output
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:python)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        # Extract the first [ ... ] block
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        python_text = match.group(0) if match else raw

        # Sanity-check brace balance
        if python_text.count("[") != python_text.count("]"):
            raise ValueError(f"Unbalanced brackets from model:\n{python_text}")

        try:
            # Use ast.literal_eval for Python-style syntax (single quotes)
            relationships_list = ast.literal_eval(python_text)
        except (ValueError, SyntaxError) as e:
            # Fallback to json.loads in case it's actually JSON format
            try:
                relationships_list = json.loads(python_text)
            except json.JSONDecodeError:
                raise ValueError(f"Failed to parse Python list:\n{python_text}\n\nError: {e}")

        relationships_list = [
            {"source_id": rel["source_id"], "target_id": rel["target_id"], "relationship": rel["relationship"]}
            for rel in relationships_list
        ]

        return relationships_list

    def distill_subject_object_pairs(self, prompt: str, content: str, client=None):
        """Use OpenAI to extract subject-object relationships from text with contextual descriptions."""
        if client is None:
            client = self.get_openai_client()

        base_prompt = (
            f"{prompt}\n"
            "You must only output a valid python list of dictionaries with the keys "
            "'subject', 'object', 'relationship', 'subject_description', and 'object_description'. "
            "Use short phrases from the text for the subject and object and a concise "
            "label for the relationship. For subject_description and object_description, "
            "provide 1-2 sentences of contextual information from the text that explains "
            "or describes each subject and object in more detail. Do not include any extra commentary.\n\n"
            f"Content:\n{content}\n\n"
            "Now strictly output the python list:"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": base_prompt}],
            response_format={"type": "text"},
            temperature=0.7,
            max_completion_tokens=1500,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            store=False,
        )

        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = re.sub(r"^```(?:python)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        match = re.search(r"\[.*\]", raw, re.DOTALL)
        python_text = match.group(0) if match else raw

        if python_text.count("[") != python_text.count("]"):
            raise ValueError(f"Unbalanced brackets from model:\n{python_text}")

        try:
            # Use ast.literal_eval for Python-style syntax (single quotes)
            pairs = ast.literal_eval(python_text)
        except (ValueError, SyntaxError) as e:
            # Fallback to json.loads in case it's actually JSON format
            try:
                pairs = json.loads(python_text)
            except json.JSONDecodeError:
                raise ValueError(f"Failed to parse Python list:\n{python_text}\n\nError: {e}")

        # Validate that all required fields are present in each pair
        required_fields = ["subject", "object", "relationship", "subject_description", "object_description"]
        validated_pairs = []

        for pair in pairs:
            if not isinstance(pair, dict):
                continue

            # Check if all required fields are present
            if all(field in pair for field in required_fields):
                validated_pairs.append({
                    "subject": pair["subject"],
                    "object": pair["object"],
                    "relationship": pair["relationship"],
                    "subject_description": pair["subject_description"],
                    "object_description": pair["object_description"],
                })
            else:
                # If new fields are missing, add empty descriptions for backward compatibility
                validated_pairs.append({
                    "subject": pair.get("subject", ""),
                    "object": pair.get("object", ""),
                    "relationship": pair.get("relationship", ""),
                    "subject_description": pair.get("subject_description", ""),
                    "object_description": pair.get("object_description", ""),
                })

        return validated_pairs
