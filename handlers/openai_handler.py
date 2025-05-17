from openai import OpenAI
import markdown
import os
import json
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

    prompt = "Generate a label for the following piece without quotes, returning only the label and nothing else. The label should be short but still be able to communicate the key elements in the piece:\n\n"  # noqa
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
        raise ValueError(f"Unbalanced JSON from model:\n{python_text}")

    try:
        relationships_list = json.loads(python_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON:\n{python_text}\n\nError: {e}")

    relationships_list = [
        {"source_id": rel["source_id"], "target_id": rel["target_id"], "relationship": rel["relationship"]}
        for rel in relationships_list
    ]

    return relationships_list
