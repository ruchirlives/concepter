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
    NODES = db["nodes"]
    COLL = db["collections"]

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

        # build id map from all instantiated containers (important for imports)
        full_id_map = {c.getValue("id"): c for c in BaseContainer.instances}

        # rehydrate edges among all loaded containers
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
            {
                "$set": {"nodes": proj_nodes},
                "$unset": {"data": ""}  # remove legacy field if present
            },
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
