import os
import sys
import pickle
import json
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv
from typing import List, Any, Dict, Optional
from bson import Binary
from handlers.repository_handler import ContainerRepository
from containers.baseContainer import BaseContainer

# Resolve base and project directories
if getattr(sys, "frozen", False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

project_root = os.path.abspath(os.path.join(base_dir, ".."))
dotenv_path = os.path.join(project_root, ".env")

# Load .env only if the required vars are missing (to allow permanent envs to take priority)
if not os.getenv("MONGO_URL") or not os.getenv("MONGO_CERT_NAME"):
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    else:
        print(f"Warning: .env not found at {dotenv_path}")

# Retrieve the runtime environment
runtime_env = os.getenv("RUNTIME_ENV", "web")
mongo_url = os.getenv("MONGO_URL")
cert_name = os.getenv("MONGO_CERT_NAME")
home_dir = os.getenv("HOME", os.path.expanduser("~"))  # fallback to user profile

# Determine PEM path
if runtime_env == "local":
    pem_path = os.path.join(home_dir, cert_name) if cert_name else None
    print(f"Running in LOCAL mode. PEM path: {pem_path}")
else:
    pem_path = os.getenv("MONGO_CLOUD_PATH")
    print(f"Running in CLOUD mode. PEM path: {pem_path}")

# Check that everything is set correctly
if not mongo_url:
    raise ValueError("❌ MONGO_URL is not set.")
if not pem_path or not os.path.exists(pem_path):
    raise FileNotFoundError(f"❌ PEM file not found at: {pem_path}")

# Connect to MongoDB
client = MongoClient(mongo_url, tls=True, tlsCertificateKeyFile=pem_path)
db = client["Concepter"]
print("✅ Connected to MongoDB.")


class MongoContainerRepository(ContainerRepository):
    @staticmethod
    def merge_unique_field(all_nodes, field_path, field_type="list"):
        """
        Merge unique items from a list field or merge dicts across all nodes.
        field_path: list of keys to traverse, e.g., ["values", "Tags"]
        field_type: "list" or "dict"
        Returns a list of unique items or a merged dict.
        For tags, strips whitespace and filters out empty strings, dedupes case-insensitively.
        """
        # Special handling for tags
        is_tags = field_path == ["values", "Tags"]
        if field_type == "list":
            import json
            merged = []
            seen = set()
            for node in all_nodes:
                val = node
                for key in field_path:
                    val = val.get(key, {}) if isinstance(val, dict) else {}
                if isinstance(val, list):
                    for item in val:
                        if is_tags and isinstance(item, str):
                            tag = item.strip()
                            if not tag:
                                continue
                            tag_key = tag.lower()  # dedupe case-insensitive
                            if tag_key not in seen:
                                merged.append(tag)
                                seen.add(tag_key)
                        else:
                            # Use json.dumps to hash dicts/lists robustly
                            try:
                                item_key = json.dumps(item, sort_keys=True)
                            except Exception:
                                item_key = str(item)
                            if item_key not in seen:
                                merged.append(item)
                                seen.add(item_key)
            return merged
        elif field_type == "dict":
            merged = {}
            for node in all_nodes:
                val = node
                for key in field_path:
                    val = val.get(key, {}) if isinstance(val, dict) else {}
                if isinstance(val, dict):
                    merged.update(val)
            return merged
        else:
            return None

    @staticmethod
    def rehydrate_edges_for_containers(containers: list):
        """Rehydrate edges among all loaded containers (for both single and multiple loads)."""
        # Build id map from all instantiated containers (important for imports)
        from containers.baseContainer import BaseContainer

        full_id_map = {c.getValue("id"): c for c in BaseContainer.instances}

        # Rehydrate edges among all loaded containers
        for inst in BaseContainer.instances:
            unmatched = []
            for edge in getattr(inst, "_pending_edges", []):
                tgt = full_id_map.get(edge["to"])
                if tgt:
                    inst.setPosition(tgt, edge["position"])
                else:
                    unmatched.append(edge)
            # keep only unmatched edges
            inst._pending_edges = unmatched if unmatched else []

    NODES = db["nodes"]
    COLL = db["collections"]

    def load_node(self, node_id: Any) -> Optional[BaseContainer]:
        """Load an individual node document by its id and
        deserialize it into a BaseContainer instance, rehydrating edges."""
        doc = self.NODES.find_one({"_id": node_id})
        if not doc:
            print(f"⚠️ No node found with id: {node_id}")
            return None
        print(f"✅ doc: {doc}")
        inst = BaseContainer.deserialize_node_info(doc)
        # Rehydrate edges for all loaded containers
        self.rehydrate_edges_for_containers([inst])
        # refresh
        return inst

    def search_nodes(self, search_term: str, tags: List[str] = []) -> List[Dict[str, Any]]:
        """Return nodes matching the search term with their id, Name, and children info if present."""
        query = {"values.Name": {"$regex": search_term, "$options": "i"}}
        if tags:
            # All tags in the list must be present in values.Tags
            query = {
                "$and": [
                    query,
                    {"values.Tags": {"$all": tags}}
                ]
            }
        cursor = self.NODES.find(
            query,
            {"_id": 1, "values.Name": 1, "containers": 1},
        )
        results = []
        for doc in cursor:
            children = []
            try:
                for child in doc.get("containers", []):
                    children.append(
                        {"id": child.get("to"), "Name": child.get("Name"), "position": child.get("position")}
                    )
            except Exception as e:
                print(f"❌ Error processing child containers: {e}")
            results.append({"id": doc["_id"], "Name": doc.get("values", {}).get("Name"), "children": children})
        return results

    def deduplicate_nodes(self) -> None:
        """Remove duplicate nodes from the database."""
        pipeline = [
            {
                "$group": {
                    "_id": "$values.Name",
                    "uniqueIds": {"$addToSet": "$_id"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$match": {"count": {"$gt": 1}}
            }
        ]

        duplicates = list(self.NODES.aggregate(pipeline))
        total_removed = 0
        for dup in duplicates:
            # Fetch all duplicate node docs
            all_nodes = list(self.NODES.find({"_id": {"$in": dup["uniqueIds"]}}))
            # If any node is type BudgetContainer, skip this group
            if any(node.get("type") == "BudgetContainer" for node in all_nodes):
                print(f"⏭️ Skipping deduplication for nodes with name: {dup['_id']} (BudgetContainer present)")
                continue

            print(f"⚠️ Found duplicate nodes for name: {dup['_id']}")
            keep_id = dup["uniqueIds"][0]
            remove_ids = dup["uniqueIds"][1:]

            # Merge containers
            merged_containers = self.merge_unique_field(all_nodes, ["containers"], field_type="list")
            # Merge values.Tags
            merged_tags = self.merge_unique_field(all_nodes, ["values", "Tags"], field_type="list")
            # Merge values.allStates (dict)
            merged_states = self.merge_unique_field(all_nodes, ["values", "allStates"], field_type="dict")

            # Prepare update dict
            update_dict = {"containers": merged_containers}
            if merged_tags:
                update_dict["values.Tags"] = merged_tags
            if merged_states:
                update_dict["values.allStates"] = merged_states

            # Use $set with dot notation for nested fields
            self.NODES.update_one({"_id": keep_id}, {"$set": update_dict})

            # Sweep all nodes to update containers.to references
            for old_id in remove_ids:
                # Find all nodes where containers.to == old_id
                cursor = self.NODES.find({"containers.to": old_id})
                for node in cursor:
                    updated = False
                    containers = node.get("containers", [])
                    for c in containers:
                        if c.get("to") == old_id:
                            c["to"] = keep_id
                            updated = True
                    if updated:
                        self.NODES.update_one({"_id": node["_id"]}, {"$set": {"containers": containers}})

            result = self.NODES.delete_many({"_id": {"$in": remove_ids}})
            total_removed += result.deleted_count
            print(f"✅ Removed duplicate nodes: {remove_ids} and merged containers, tags, allStates into {keep_id}")
        return total_removed

    def list_project_names(self) -> List[str]:
        return list(self.COLL.distinct("name"))

    def load_project(self, name: str) -> List[Any]:
        """Load and return the full container list for the given project.
        Supports both legacy pickled format and new nodes-based format."""
        doc = self.COLL.find_one({"name": name})
        if not doc:
            raise KeyError(f"No project named {name}")

        # --- Legacy path (pickled blob) ---
        if "data" in doc:
            return pickle.loads(doc["data"])

        # --- New path (nodes reference) ---
        node_ids = [n["id"] for n in doc.get("nodes", [])]
        if not node_ids:
            return []

        docs = list(self.NODES.find({"_id": {"$in": node_ids}}))

        # deserialize each node
        id_map, containers = {}, []
        for d in docs:
            inst = BaseContainer.deserialize_node_info(d)
            id_map[d["_id"]] = inst
            containers.append(inst)

        # Rehydrate edges for all loaded containers
        self.rehydrate_edges_for_containers(containers)

        return containers

    def save_project(self, name: str, containers: List[Any]) -> None:
        """Save a project and its nodes into MongoDB."""
        ops = []
        proj_nodes = []

        for c in containers:
            doc = c.serialize_node_info()
            ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=True))
            proj_nodes.append({"id": doc["_id"], "Name": doc["values"].get("Name")})

        if ops:
            self.NODES.bulk_write(ops, ordered=False)

        # update project document with membership list
        self.COLL.update_one(
            {"name": name},
            {"$set": {"nodes": proj_nodes}, "$unset": {"data": ""}},  # remove legacy field if present
            upsert=True,
        )

    def delete_project(self, name: str) -> bool:
        result = self.COLL.delete_one({"name": name})
        return result.deleted_count > 0

    def save_transition_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save transition metadata to MongoDB."""
        try:
            # Convert metadata to JSON string for storage
            metadata_json = json.dumps(metadata, indent=2)

            # Save to the collections collection with a special document name
            self.COLL.update_one(
                {"name": "transition_metadata"},
                {"$set": {"data": metadata_json, "type": "transition_metadata"}},
                upsert=True,
            )
            print("✅ Transition metadata saved successfully")
        except Exception as e:
            print(f"❌ Error saving transition metadata: {e}")
            raise

    def load_transition_metadata(self) -> Optional[Dict[str, Any]]:
        """Load transition metadata from MongoDB. Returns None if not found."""
        try:
            # Find the transition metadata document
            doc = self.COLL.find_one({"name": "transition_metadata"})

            if not doc:
                print("ℹ️ No transition metadata found")
                return None

            # Parse the JSON data
            metadata_json = doc.get("data", "{}")

            # If data is stored as a string, parse it; if it's already a dict, use it directly
            if isinstance(metadata_json, str):
                metadata = json.loads(metadata_json)
            else:
                metadata = metadata_json

            print("✅ Transition metadata loaded successfully")
            return metadata
        except json.JSONDecodeError as e:
            print(f"❌ JSON decoding error: {e}")
            raise
        except Exception as e:
            print(f"❌ Error loading transition metadata: {e}")
            raise

    def delete_transition_metadata(self) -> bool:
        """Delete transition metadata. Returns True if successful, False otherwise."""
        try:
            # First save backup
            backup = self.COLL.find_one({"name": "transition_metadata"})
            if not backup:
                print("⚠️ No transition metadata found to backup")
                return False
            # Save backup to a same collection replacing previous backup
            self.COLL.update_one(
                {"name": "transition_metadata_backup"},
                {"$set": {"data": backup}},
                upsert=True,
            )
            result = self.COLL.delete_one({"name": "transition_metadata"})
            if result.deleted_count == 0:
                print("⚠️ No transition metadata found to delete")
                return False
            print("✅ Deleted transition metadata successfully")
            return True
        except Exception as e:
            print(f"❌ Error deleting transition metadata: {e}")
            return False
