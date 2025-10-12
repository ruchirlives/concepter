import json
import os
from datetime import date
import hashlib
import colorsys
from containers.conceptContainer import ConceptContainer

# -----------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------

SAVE_NAME = "TS_Save_ConceptPawns.json"
SAVE_PATH = os.path.join(
    os.environ.get('HOME') + '/My Games/Tabletop Simulator/Saves',
    SAVE_NAME,
)
MAP_PATH = os.path.join(
    os.environ.get('HOME') + '/My Games/Tabletop Simulator/Saves/Saved Objects',
    "map-export.png",
)
# Deterministic color palette to map discovered tags
DEFAULT_COLOR = [1.0, 1.0, 1.0]

PAWN_NAME = "PlayerPawn"  # use a known built-in prefab


def lua_for_tags(tags):
    """Generate Lua code to register tags."""
    if not tags:
        return ""
    return "\n".join([f"self.addTag('{t}')" for t in tags])


def lua_label_script(name: str) -> str:
    # Always-visible world-space label attached to object
    safe_name = (name or "").replace("\\", "\\\\").replace("\"", "\\\"")
    return f'''
function onLoad()
    local xml = [[
    <Defaults>
      <Text fontSize="24" color="#FFFFFF" outline="#000000" />
    </Defaults>
    <Panel id="ws_root" width="400" height="50" rectAlignment="MiddleCenter" allowDragging="false" pointerBlocker="false" worldSpace="true">
      <Text id="ws_label" text="{safe_name}" alignment="MiddleCenter" />
    </Panel>
    ]]
    self.UI.setXml(xml)                 -- attach world-space UI to this object
    -- Place panel above the object using local (object) position in meters
    self.UI.setAttribute('ws_root', 'position', '0 1.2 0')
    self.UI.setAttribute('ws_root', 'rotation', '0 0 0')
    self.UI.setAttribute('ws_root', 'scale', '1 1 1')
end
'''


def pawn_for_container(c, tag_color, pos_provider=None):
    """Convert one ConceptContainer to a pawn object."""
    name = c.getValue("Name")
    desc = c.getValue("Description") or ""
    tags = c.getValue("Tags") or []

    first_tag = tags[0] if tags else "default"
    color = tag_color(first_tag)

    # Always use layout provider; container 'z' is an embedding, not a position
    px, py, pz = pos_provider(c) if pos_provider else (0.0, 0.6, 0.0)
    posX, posY, posZ = float(px), float(py), float(pz)

    return {
        "Name": PAWN_NAME,
        "Nickname": name,
        "Description": desc,
        "Transform": {
            "posX": posX,
            "posY": posY + 1,
            "posZ": posZ,
            "rotX": 0.0,
            "rotY": 0.0,
            "rotZ": 0.0,
            "scaleX": 1.0,
            "scaleY": 1.0,
            "scaleZ": 1.0,
        },
        "GMNotes": "",
        "AltLookAngle": {"x": 0.0, "y": 0.0, "z": 0.0},
        "ColorDiffuse": {"r": color[0], "g": color[1], "b": color[2], "a": 1.0},
        "Locked": False,
        "Grid": True,
        "Snap": False,
        "Autoraise": True,
        "Sticky": False,
        "LuaScript": (lua_for_tags(tags)).strip(),
        "LuaScriptState": "",
        "XmlUI": "",
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

    # Build a tag-clustered position provider
    groups = {}
    for c in containers:
        tags = c.getValue("Tags") or []
        key = (tags[0] if tags else "untagged").strip().lower() or "untagged"
        groups.setdefault(key, []).append(c)

    ordered_keys = sorted(groups.keys())

    def stable_id(obj) -> str:
        try:
            if hasattr(obj, 'getId'):
                return str(obj.getId())
        except Exception:
            pass
        return str(id(obj))

    index_in_group = {}
    for k in ordered_keys:
        index_in_group[k] = {}
        for i, obj in enumerate(groups[k]):
            index_in_group[k][stable_id(obj)] = i

    cols = 8
    dx = 8.0
    dz = 4.0
    base_y = 0.6

    def pos_provider(c):
        tags = c.getValue("Tags") or []
        key = (tags[0] if tags else "untagged").strip().lower() or "untagged"
        gi = ordered_keys.index(key)
        cid = stable_id(c)
        i = index_in_group.get(key, {}).get(cid, 0)
        row = i // cols
        col = i % cols
        x = (col - (cols - 1) / 2.0) * dx
        z = gi * (dz * 4) + row * dz
        return x, base_y, z

    # Add a custom board as the first object
    custom_board = {
        "Name": "Custom_Board",
        "Transform": {
            "posX": 0.0,
            "posY": 0.0,
            "posZ": 0.0,
            "rotX": 0.0,
            "rotY": 180.0,
            "rotZ": 0.0,
            "scaleX": 7,
            "scaleY": 1,
            "scaleZ": 7,
        },
        "Nickname": "Concept Board",
        "Description": "",
        "GMNotes": "",
        "AltLookAngle": {"x": 0.0, "y": 0.0, "z": 0.0},
        "ColorDiffuse": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
        "Locked": True,
        "Grid": False,
        "GridProjection": True,
        "Snap": False,
        "Autoraise": False,
        "Sticky": False,
        "Tooltip": False,
        "LuaScript": "",
        "LuaScriptState": "",
        "XmlUI": "",
        "CustomImage": {"ImageURL": MAP_PATH, "ImageSecondaryURL": "", "ImageScalar": 1.0},
    }

    save_data = {
        "SaveName": "Concept Pawns Board",
        "GameMode": "",
        "Gravity": 0.5,
        "PlayArea": 4.0,
        "Date": str(date.today()),
        "Table": "Table_None",
        "Sky": "Sky_Museum",
        "Rules": "",
        "LuaScript": global_lua,
        "Grid": {
            "Type": 1,
            "Lines": True,
            "Color": {"r": 0.0, "g": 0.0, "b": 0.0},
            "Opacity": 0.75,
            "ThickLines": False,
            "Snapping": False,
            "Offset": True,
            "BothSnapping": False,
            "xSize": 2.0,
            "ySize": 2.0,
            "PosOffset": {"x": 0.0, "y": 1.0, "z": 0.0},
        },
        "ObjectStates": [custom_board] + [pawn_for_container(c, tag_color, pos_provider) for c in containers],
    }

    target_path = save_path or SAVE_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2)
    return len(containers), target_path


__all__ = [
    "export_pawns_to_json",
]
