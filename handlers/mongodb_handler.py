import os
import sys
import pickle
from pymongo import MongoClient
from dotenv import load_dotenv
from typing import List, Any
from bson import Binary
from handlers.repository_handler import ContainerRepository

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


def delete_project(project_name: str) -> bool:
    """
    Removes a project document by name from the projects collection.
    Returns True if a document was deleted, False otherwise.
    """
    try:
        # Assume all projects are stored in a single collection named "projects"
        result = db["collections"].delete_one({"name": project_name})
        if result.deleted_count == 0:
            print(f"⚠️ No document found for project: {project_name}")
            return False
        print(f"✅ Deleted project document: {project_name}")
        return True
    except Exception as e:
        print(f"❌ Error deleting project document {project_name}: {e}")
        return False


class MongoContainerRepository(ContainerRepository):
    """MongoDB implementation of ContainerRepository using the `collections` collection."""

    COLL = db["collections"]

    def list_project_names(self) -> List[str]:
        """Return all distinct project names in the collection."""
        cursor = self.COLL.find({}, {"name": 1, "_id": 0})
        return [doc["name"] for doc in cursor]

    def load_project(self, name: str) -> List[Any]:
        """Load and return the full container list for the given project."""
        doc = self.COLL.find_one({"name": name})
        if not doc:
            raise KeyError(f"No project named {name}")
        return pickle.loads(doc["data"])

    def save_project(self, name: str, containers: List[Any]) -> None:
        """Serialize and persist the list of containers under the given project name."""
        blob = pickle.dumps(containers)
        self.COLL.update_one(
            {"name": name},
            {"$set": {"data": Binary(blob)}},
            upsert=True,
        )
