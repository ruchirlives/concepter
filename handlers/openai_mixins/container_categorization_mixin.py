import json
import re


class ContainerCategorizationMixin:
    """Mixin for categorizing and organizing containers using AI."""
    
    def categorize_containers(self, items: list[dict[str, str]]) -> dict[str, list[str]]:
        """
        Given a list of dicts with 'name' and 'description', call OpenAI to
        group every item into thematic categories and return a mapping of
        category names to lists of item names. Any leftovers go into an
        "Uncategorized" group.
        """
        client = self.get_openai_client()
        
        prompt = (
            "You are a helpful assistant whose ONLY job is to output valid JSON.\n"
            'Given these items, each with a "name" and a "description":\n'
            "  • Every item MUST appear exactly once, under exactly one category.\n"
            "  • Categories are descriptive statements (strings).\n"
            "  • Output exactly one JSON object mapping each category to an array of item names.\n"
            "  • Do NOT include markdown fences, comments, or extra keys.\n"
            "  • Ensure all braces are balanced and fully closed.\n\n"
            "Items:\n"
        )
        
        for item in items:
            prompt += f"- {item['name']}: {item['description']}\n"
        prompt += "\nNow strictly output the JSON object:"

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

        # Remove any markdown fences
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        # Extract the first { ... } block
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        json_text = match.group(0) if match else raw

        # Sanity-check brace balance
        if json_text.count("{") != json_text.count("}"):
            raise ValueError(f"Unbalanced JSON from model:\n{json_text}")

        try:
            categories_map = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON:\n{json_text}\n\nError: {e}")

        # Ensure every item is assigned; if not, add to "Uncategorized"
        all_names = {it["name"] for it in items}
        assigned = {name for names in categories_map.values() for name in names}
        leftover = all_names - assigned
        if leftover:
            categories_map.setdefault("Uncategorized", []).extend(sorted(leftover))

        return categories_map
