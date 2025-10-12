import json
import os
from datetime import date
import hashlib
import colorsys
from containers.baseContainer import ConceptContainer

# -----------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------

SAVE_NAME = "TS_Save_ConceptPawns.json"
SAVE_PATH = os.path.join(
    os.path.expanduser("~/Documents/My Games/Tabletop Simulator/Saves"),
    SAVE_NAME,
)

# Deterministic color palette to map discovered tags
DEFAULT_COLOR = [1.0, 1.0, 1.0]

PAWN_NAME = "WhitePawn"  # built-in mesh used for all; tinted per colour


def lua_for_tags(tags):
    """Generate Lua code to register tags."""
    if not tags:
        return ""
    return "\n".join([f"self.addTag('{t}')" for t in tags])


def pawn_for_container(c, tag_color):
    """Convert one ConceptContainer to a pawn object."""
    name = c.getValue("Name")
    desc = c.getValue("Description") or ""
    tags = c.getValue("Tags") or []

    first_tag = tags[0] if tags else "default"
    color = tag_color(first_tag)

    z = c.getValue("z") or [0, 0, 0]
    posX, posY, posZ = (
        float(z[0]) if len(z) > 0 else 0,
        float(z[1]) if len(z) > 1 else 1,
        float(z[2]) if len(z) > 2 else 0,
    )

    return {
        "Name": PAWN_NAME,
        "Nickname": name,
        "Description": desc,
        "Transform": {"posX": posX, "posY": posY + 1, "posZ": posZ},
        "ColorDiffuse": color,
        "LuaScript": lua_for_tags(tags),
    }


def export_pawns_to_json(containers=None, save_path: str | None = None):
    """Export ConceptContainer instances to a TTS save JSON file.

    Returns a tuple (count, path) on success.
    """
    containers = containers if containers is not None else ConceptContainer.instances
    if not containers:
        raise ValueError("No ConceptContainers in memory.")

    global_lua = """
function tryObjectEnterContainer(container, object)
    allow_interaction = not container.hasAnyTag() or container.hasMatchingTag(object)
    return allow_interaction
end

function onObjectLeaveContainer(container, object)
    for i, tag in pairs(container.getTags()) do
        object.addTag(tag)
    end
end
"""

    # Hash-based stable mapping from tag text to HSL-derived RGB
    def tag_color(tag: str) -> list[float]:
        if not tag:
            return DEFAULT_COLOR
        # Normalize tag for hashing to avoid case/spacing drift
        norm = str(tag).strip().lower()
        digest = hashlib.sha256(norm.encode("utf-8")).digest()
        # Use bytes to derive hue, saturation, lightness deterministically
        hue = int.from_bytes(digest[0:2], "big") / 65535.0  # 0..1
        sat = 0.55 + (digest[2] / 255.0) * 0.35  # 0.55..0.90
        lig = 0.45 + (digest[3] / 255.0) * 0.15  # 0.45..0.60
        r, g, b = colorsys.hls_to_rgb(hue, lig, sat)
        return [round(r, 3), round(g, 3), round(b, 3)]

    save_data = {
        "SaveName": "Concept Pawns Board",
        "GameMode": "",
        "Gravity": 0.5,
        "PlayArea": 100,
        "Date": str(date.today()),
        "Table": "Table_Default",
        "Sky": "Sky_Default",
        "Lighting": "Lighting_Default",
        "Rules": "",
        "LuaScript": global_lua,
        "ObjectStates": [pawn_for_container(c, tag_color) for c in containers],
    }

    target_path = save_path or SAVE_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2)
    return len(containers), target_path


__all__ = [
    "export_pawns_to_json",
]
