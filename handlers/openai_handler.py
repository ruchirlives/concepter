from openai import OpenAI
import markdown
import os
import json
import ast
from dotenv import load_dotenv
import re

openai_api_key = os.getenv("OPENAI_API_KEY")


def get_openai_client():
    if openai_api_key is not None:
        # Only set the environment variable if it was successfully retrieved
        os.environ["OPENAI_API_KEY"] = openai_api_key
    else:
        print("Warning: OPENAI_API_KEY environment variable is not set.")

    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def get_embeddings(query, client=get_openai_client()):
    embeddings = client.embeddings.create(
        model="text-embedding-ada-002",
        input=[query],
    )

    embedding = embeddings.data[0].embedding

    return embedding


def format_text(text: str) -> str:
    # format markdown to html using the markdown-it library
    html = markdown.markdown(text, extensions=["markdown.extensions.tables"])

    # replace \n with <br> to maintain line breaks
    html = html.replace("\n", "<br>")

    return html


def generate_relationship_description(subject=None, object=None):
    """
    Generate a description of the relationship between the subject and the object.
    """
    if subject is None or object is None:
        raise ValueError("Both subject and object must be provided.")
    client = get_openai_client()

    prompt = (
        "You are a helpful assistant whose ONLY job is to output a descriptive relationship text of max 30 words.\n"
        'Given the following subject and object, each with a "name" and a "description":\n'
        "Please describe the relationship between the two in a short sentence.\n"
        f"Subject: {subject}\n"
        f"Object: {object}\n"
        "Now strictly output the relationship description:"
    )
    # Parse the response
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "text"},
        temperature=0.7,
        max_completion_tokens=1500,  # increased budget
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        store=False,
    )
    raw = response.choices[0].message.content.strip()
    # remove any markdown fences from the python output
    return raw


def generate_reasoning_argument(reasoning):
    """
    Generate a reasoning argument for the given reasoning.
    """
    client = get_openai_client()

    prompt = (
        "Please create a concise argument from the following graph reasoning chain. It needs to take the audience through a step by step yet concise understanding of the reasoning. Please prepend with an appropriate section title:\n"
        f"{reasoning}\n"
    )
    # Parse the response
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "text"},
        temperature=0.7,
        max_completion_tokens=1500,  # increased budget
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        store=False,
    )
    raw = response.choices[0].message.content.strip()
    # remove any markdown fences from the python output
    return raw


def generate_piece_name(descriptions):
    """
    Use embeddings of descriptions to collect the best containers to make its subcontainers
    """
    client = get_openai_client()

    prompt = """
    Generate a concise and really easy to comprehend label for the following text, re-using any acronyms, scheme names, or terminology that already appear in the text, but do not invent new acronyms or abbreviations. The label should capture the unique essence about the description, and avoid generic or broad wording, but use easy to understand phrases like "lack of data at local level", or "The need for [group x] to talk together". No quotes, just the label.:\n\n
    """

    prompt += f"{descriptions}\n\n"

    # Use client to get completion
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "text"},
        temperature=1,
        max_completion_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        store=False,
    )
    name = response.choices[0].message.content.strip()
    return name


def categorize_containers(items: list[dict[str, str]]) -> dict[str, list[str]]:
    """
    Given a list of dicts with 'name' and 'description', call OpenAI to
    group every item into thematic categories and return a mapping of
    category names to lists of item names. Any leftovers go into an
    "Uncategorized" group.
    """
    client = get_openai_client()
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
        # we explicitly feed the exact names
        prompt += f"- {item['name']}: {item['description']}\n"
    prompt += "\nNow strictly output the JSON object:"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "text"},
        temperature=0.7,
        max_completion_tokens=1500,  # increased budget
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        store=False,
    )
    raw = response.choices[0].message.content.strip()

    # remove any markdown fences
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    # extract the first { ... } block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    json_text = match.group(0) if match else raw

    # sanity‐check brace balance
    if json_text.count("{") != json_text.count("}"):
        raise ValueError(f"Unbalanced JSON from model:\n{json_text}")

    try:
        categories_map = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON:\n{json_text}\n\nError: {e}")

    # ensure every item is assigned; if not, add to "Uncategorized"
    all_names = {it["name"] for it in items}
    assigned = {name for names in categories_map.values() for name in names}
    leftover = all_names - assigned
    if leftover:
        categories_map.setdefault("Uncategorized", []).extend(sorted(leftover))

    return categories_map


def get_relationships_from_openai(items: list[dict[str, str]]) -> dict[str, list[str]]:
    """
    Given a list of dicts with 'id' and 'description', call OpenAI to
    build a relationship map between items. The output is a python list
    mapping each item id to a list of related item ids: {source_id, target_id, relationship}
    """

    client = get_openai_client()
    prompt = (
        "You are a helpful assistant whose ONLY job is to output a valid python list.\n"
        'Given these items, each with an "id" and a "description":\n'
        "  • Relationships are short 1 to 3 word descriptive statements relating one id to another id from the source list based on on an expected relationship.\n"  # noqa
        "  • Each item in the output list should have  a source_id, target_id, relationship.\n"
        "  • Do NOT include markdown fences, comments, or extra keys.\n"
        "  • Ensure all braces are balanced and fully closed.\n\n"
        "Items:\n"
    )
    for item in items:
        # we explicitly feed the exact names
        prompt += f"- {item['id']}: {item['description']}\n"
    prompt += "\nNow strictly output the python list:"

    # Parse the response
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "text"},
        temperature=0.7,
        max_completion_tokens=1500,  # increased budget
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        store=False,
    )
    raw = response.choices[0].message.content.strip()

    # remove any markdown fences from the python output
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:python)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    # extract the first [ ... ] block
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    python_text = match.group(0) if match else raw

    # sanity‐check brace balance
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


def distill_subject_object_pairs(prompt: str, content: str, client=get_openai_client()):
    """Use OpenAI to extract subject-object relationships from text with contextual descriptions."""

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
            validated_pairs.append(
                {
                    "subject": pair["subject"],
                    "object": pair["object"],
                    "relationship": pair["relationship"],
                    "subject_description": pair["subject_description"],
                    "object_description": pair["object_description"],
                }
            )
        else:
            # If new fields are missing, add empty descriptions for backward compatibility
            validated_pairs.append(
                {
                    "subject": pair.get("subject", ""),
                    "object": pair.get("object", ""),
                    "relationship": pair.get("relationship", ""),
                    "subject_description": pair.get("subject_description", ""),
                    "object_description": pair.get("object_description", ""),
                }
            )

    return validated_pairs
