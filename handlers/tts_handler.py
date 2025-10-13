import json
import os
from datetime import date
import hashlib
import colorsys
import math
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


def model_for_container(c, tag_color, pos_provider=None):
    """Convert one ConceptContainer to a TTS Custom_Model object using c.get_model()."""
    name = c.getValue("Name")
    desc = c.getValue("Description") or ""
    tags = c.getValue("Tags") or []
    guid = str(c.getValue("id") or "")

    first_tag = tags[0] if tags else "default"
    color = tag_color(first_tag)

    px, py, pz = pos_provider(c) if pos_provider else (0.0, 0.6, 0.0)
    posX, posY, posZ = float(px), float(py), float(pz)

    # Determine scale from child count but apply to model scale
    try:
        child_count = len(getattr(c, "containers", []) or [])
    except Exception:
        child_count = 0
    scale_factor = min(8, 1.0 + 0.6 * math.sqrt(child_count))

    # Expect container to provide its model URLs or configuration
    model = c.get_model() if hasattr(c, "get_model") else None
    # Fallback to pawn if no model info
    if not model:
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
                "scaleX": scale_factor,
                "scaleY": scale_factor,
                "scaleZ": scale_factor,
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
            **({"GUID": guid} if guid else {}),
        }

    # If model is a dict with expected fields, build a Custom_Model
    mesh_url = model.get("url")
    mesh_name = model.get("name")
    type_flag = model.get("type") or "Custom_Model"
    rot = model.get("rotation") or {"x": 0.0, "y": 0.0, "z": 0.0}
    scl = model.get("scale") or {"x": scale_factor, "y": scale_factor, "z": scale_factor}

    tts_obj = {
        "Name": type_flag,
        "Nickname": name or (mesh_name if mesh_name else "ConceptPawn"),
        "Description": desc,
        "Transform": {
            "posX": posX,
            "posY": posY + 1,
            "posZ": posZ,
            "rotX": float(rot.get("x", 0.0)),
            "rotY": float(rot.get("y", 0.0)),
            "rotZ": float(rot.get("z", 0.0)),
            "scaleX": float(scl.get("x", scale_factor)),
            "scaleY": float(scl.get("y", scale_factor)),
            "scaleZ": float(scl.get("z", scale_factor)),
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
        "CustomMesh": {
            "MeshURL": mesh_url or "",
            "Convex": True,
            "MaterialIndex": 0,
            "TypeIndex": 6,
            "CastShadows": True,
        },
    }
    if guid:
        tts_obj["GUID"] = guid
    return tts_obj


def export_pawns_to_json(containers=None, save_path: str | None = None, update: bool = True):
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
        "ObjectStates": [custom_board] + [model_for_container(c, tag_color, pos_provider) for c in containers],
    }

    target_path = save_path or SAVE_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    if update and os.path.isfile(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing_states = existing.get("ObjectStates", [])
            # Keep existing objects except those we manage and can upsert by GUID
            others = [o for o in existing_states if not o.get("GUID")]
            # Build dict by GUID for everything that has one (pawns or models)
            existing_pawns = {o.get("GUID"): o for o in existing_states if o.get("GUID")}
            # Build new pawns from containers and upsert by GUID (or replace if no GUID)
            new_pawns_list = [model_for_container(c, tag_color, pos_provider) for c in containers]
            for p in new_pawns_list:
                gid = p.get("GUID")
                if gid:
                    existing_pawns[gid] = p
                else:
                    # No GUID: append as unmanaged new pawn
                    others.append(p)
            # Reassemble: others + updated pawns (preserve order of others)
            merged_states = others + list(existing_pawns.values())
            existing["ObjectStates"] = merged_states
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
            return len(new_pawns_list), target_path
        except Exception:
            # Fall back to fresh write on any error
            pass

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2)
    return len(containers), target_path


__all__ = [
    "export_pawns_to_json",
]
