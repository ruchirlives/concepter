import os
import sys
import pickle
import json
import numpy as np
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union, Set, Iterable
from bson import Binary
from handlers.repository_handler import ContainerRepository
from containers.baseContainer import BaseContainer
from handlers.openai_handler import openai_handler
import logging
import math
from collections.abc import Iterable
from bson import ObjectId

NumberList = Sequence[Union[int, float]]


class MongoContainerRepository(ContainerRepository):

    def __init__(self) -> None:
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
                logging.warning(".env not found at %s", dotenv_path)

        # Retrieve the runtime environment
        runtime_env = os.getenv("RUNTIME_ENV", "web")
        mongo_url = os.getenv("MONGO_URL")
        cert_name = os.getenv("MONGO_CERT_NAME")
        home_dir = os.getenv("HOME", os.path.expanduser("~"))  # fallback to user profile

        # Determine PEM path
        if runtime_env == "local":
            pem_path = os.path.join(home_dir, cert_name) if cert_name else None
            logging.info("Mongo running in LOCAL mode. PEM path: %s", pem_path)
        else:
            pem_path = os.getenv("MONGO_CLOUD_PATH")
            logging.info("Mongo running in CLOUD mode. PEM path: %s", pem_path)

        # Validate required settings and handle PEM via env content when running in cloud
        if not mongo_url:
            raise ValueError("MONGO_URL is not set.")

        # If pem_path is not present or does not exist, try to source PEM from environment content
        if not pem_path or not os.path.exists(pem_path):
            pem_content = os.getenv("MONGO_PEM_CONTENT") or os.getenv("MONGO_CLIENT_PEM") or os.getenv("MONGO_PEM")
            if pem_content:
                try:
                    # Cloud Run allows writing to /tmp
                    tmp_pem_path = "/tmp/mongo_client.pem"
                    with open(tmp_pem_path, "w", encoding="utf-8") as f:
                        f.write(pem_content)
                    pem_path = tmp_pem_path
                    logging.info("Wrote PEM content from env to %s", pem_path)
                except Exception as e:
                    logging.error("Failed writing PEM content to temp file: %s", e)
                    raise

        if not pem_path or not os.path.exists(pem_path):
            raise FileNotFoundError("PEM file not found. Provide file via MONGO_CLOUD_PATH or set MONGO_PEM_CONTENT env.")

        # Connect to MongoDB and set instance collections
        self.client = MongoClient(mongo_url, tls=True, tlsCertificateKeyFile=pem_path)
        self.db = self.client["Concepter"]
        self.NODES = self.db["nodes"]
        self.COLL = self.db["collections"]
        self.MODELS = self.db["MODELS"]
        logging.info("Connected to MongoDB.")

    def get_top_by_z(self, z_vector: NumberList) -> Optional[Dict[str, Any]]:
        """Return the top matching model document for the supplied embedding."""

        z = self._validate_vector(z_vector)
        if z is None:
            raise ValueError("z_vector must be a non-empty sequence of numbers")

        cursor = self.MODELS.find(
            {"z": {"$type": "array", "$ne": []}},
            {"name": 1, "link": 1, "z": 1},
        )

        best: Optional[Dict[str, Any]] = None
        best_score = -1.0

        for doc in cursor:
            model_z = doc.get("z")
            if not isinstance(model_z, list) or not model_z:
                continue
            if len(model_z) != len(z):
                continue
            score = self._cosine_similarity(z, model_z)
            if score > best_score:
                best_score = score
                best = doc

        if not best:
            return None

        return {
            "name": best.get("name"),
            "url": best.get("link"),
            "score": best_score,
        }

    def get_model_from_id(self, node_id: Union[str, ObjectId]) -> Optional[Dict[str, Any]]:
        """Resolve a node by id and return the closest matching model."""

        node = self.NODES.find_one({"_id": node_id}, {"values.z": 1})
        if not node:
            return None

        values = node.get("values") or {}
        z_vector = values.get("z")
        if not isinstance(z_vector, list) or not z_vector:
            return None

        return self.get_top_by_z(z_vector)

    def remove_relationship(self, container_id: Any, source_id: str, target_id: str) -> bool:
        """Remove a relationship from a node document by exact source/target match.

        Returns True if a relationship entry was removed, False otherwise.
        """
        try:
            src = str(source_id) if source_id is not None else None
            tgt = str(target_id) if target_id is not None else None
            if src is None or tgt is None:
                return False

            res = self.NODES.update_one(
                {"_id": container_id},
                {"$pull": {"relationships": {"source": src, "target": tgt}}},
            )
            return getattr(res, "modified_count", 0) > 0
        except Exception as e:
            logging.error("Failed to remove relationship for node %s: %s", container_id, e)
            return False

    def search_position_z(self, searchTerm: str, top_n=10):
        """Vector search: Find containers whose position.z is most similar to the searchTerm embedding.
        Returns a merged single list of parent_ids and container_ids (flat list, top_n results)."""

        def cosine_similarity(a, b):
            a = np.array(a)
            b = np.array(b)
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

        searchTerm = searchTerm.strip()
        search_embedding = openai_handler.get_embeddings(searchTerm)

        query = {"containers": {"$elemMatch": {"position.z": {"$exists": True}}}}
        cursor = self.NODES.find(query, {"_id": 1, "values": 1, "containers": 1}).limit(500)
        scored = []
        for doc in cursor:
            for child in doc.get("containers", []):
                if isinstance(child, dict) and isinstance(child.get("position"), dict) and "z" in child["position"]:
                    z = child["position"]["z"]
                    score = cosine_similarity(search_embedding, z)
                    scored.append(
                        {
                            "parent_id": doc.get("_id"),
                            "parent_name": doc.get("values", {}).get("Name", ""),
                            "container_id": child.get("to"),
                            "child_name": child.get("Name", ""),
                            "score": score,
                        }
                    )
        scored.sort(key=lambda x: x["score"], reverse=True)
        top = scored[:top_n]
        id_list = []
        names_list = []
        for item in top:
            id_list.append(item["parent_id"])
            id_list.append(item["container_id"])
            names_list.append(item["parent_name"])
            names_list.append(item["child_name"])
        return id_list, names_list

    def find_relationship_influencers(self, pairs: List[Tuple[str, str]]) -> Dict[str, List[Dict[str, Any]]]:
        """Return containers whose relationships match any of the requested source/target pairs."""

        normalized_pairs: List[Tuple[str, str]] = []
        seen: Set[Tuple[str, str]] = set()
        for src, tgt in pairs:
            if not src or not tgt:
                continue
            key = (str(src), str(tgt))
            if key in seen:
                continue
            seen.add(key)
            normalized_pairs.append(key)

        if not normalized_pairs:
            return {}

        pair_key_map: Dict[Tuple[str, str], str] = {}
        result: Dict[str, List[Dict[str, Any]]] = {}
        for src, tgt in normalized_pairs:
            pair_key = f"{src}::{tgt}"
            pair_key_map[(src, tgt)] = pair_key
            result[pair_key] = []

        or_conditions = [{"relationships": {"$elemMatch": {"source": src, "target": tgt}}} for src, tgt in normalized_pairs]

        query: Dict[str, Any]
        if len(or_conditions) == 1:
            query = or_conditions[0]
        else:
            query = {"$or": or_conditions}

        projection = {"_id": 1, "values.Name": 1, "relationships": 1}
        cursor = self.NODES.find(query, projection)

        for doc in cursor:
            container_id = doc.get("_id")
            container_name = ""
            values = doc.get("values") or {}
            if isinstance(values, dict):
                name_value = values.get("Name")
                if isinstance(name_value, str):
                    container_name = name_value

            for rel in doc.get("relationships", []) or []:
                if not isinstance(rel, dict):
                    continue
                src_id = rel.get("source")
                tgt_id = rel.get("target")
                if src_id is None or tgt_id is None:
                    continue
                src_str = str(src_id)
                tgt_str = str(tgt_id)
                pair_key = pair_key_map.get((src_str, tgt_str))
                if not pair_key:
                    continue
                position = rel.get("position")
                if position is None:
                    position = {}
                result[pair_key].append(
                    {
                        "container_id": str(container_id),
                        "container_name": container_name,
                        "source_id": src_str,
                        "target_id": tgt_str,
                        "position": position,
                    }
                )

        return result

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

    def load_node(self, node_id: Any) -> Optional[BaseContainer]:
        """Load an individual node document by its id and
        deserialize it into a BaseContainer instance, rehydrating edges."""
        doc = self.NODES.find_one({"_id": node_id})
        if not doc:
            print(f"⚠️ No node found with id: {node_id}")
            return None
        # print(f"✅ doc: {doc}")
        inst = BaseContainer.deserialize_node_info(doc)
        # Rehydrate edges for all loaded containers
        self.rehydrate_edges_for_containers([inst])
        # refresh
        return inst

    def save_node(self, container: BaseContainer) -> Any:
        """Serialize and save a single container as a node document in MongoDB."""
        doc = container.serialize_node_info()
        result = self.NODES.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
        if result.upserted_id:
            print(f"✅ Saved new node with id: {result.upserted_id}")
            return result.upserted_id
        else:
            print(f"✅ Updated existing node with id: {doc['_id']}")
            return doc["_id"]

    def search_nodes(self, search_term: str, tags: List[str] = []) -> List[Dict[str, Any]]:
        if not search_term and not tags:
            return []
        """Return nodes matching the search term with their id, Name, and children info if present."""
        query = {"values.Name": {"$regex": search_term, "$options": "i"}}
        if tags:
            # All tags in the list must be present in values.Tags
            query = {"$and": [query, {"values.Tags": {"$all": tags}}]}
        cursor = self.NODES.find(
            query,
            {"_id": 1, "values.Name": 1, "containers": 1},
        ).limit(500)
        results = []
        for doc in cursor:
            children = []
            try:
                for child in doc.get("containers", []):
                    children.append({"id": child.get("to"), "Name": child.get("Name"), "position": child.get("position")})
            except Exception as e:
                print(f"❌ Error processing child containers: {e}")
            results.append({"id": doc["_id"], "Name": doc.get("values", {}).get("Name"), "children": children})
        return results

    def deduplicate_nodes(self) -> None:
        """Remove duplicate nodes from the database."""
        pipeline = [
            {"$group": {"_id": "$values.Name", "uniqueIds": {"$addToSet": "$_id"}, "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}},
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

            # For the NODE which has id keep_id, remove any references to itself in its own containers.to
            keep_node = self.NODES.find_one({"_id": keep_id})
            if keep_node:
                containers = keep_node.get("containers", [])
                filtered_containers = [c for c in containers if c.get("to") != keep_id]
                if len(filtered_containers) != len(containers):
                    self.NODES.update_one({"_id": keep_id}, {"$set": {"containers": filtered_containers}})

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

    def save_nodes(self, nodes: List[Any]) -> None:
        """Persist a list of container instances."""
        ops = []
        for c in nodes:
            doc = c.serialize_node_info()
            ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=True))
        if ops:
            self.NODES.bulk_write(ops, ordered=False)
            print(f"✅ Saved/Updated {len(ops)} nodes successfully")
        else:
            print("⚠️ No nodes to save")

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

    def delete_nodes(self, node_ids):
        "Use MongoDb to delete nodes by their ids. Returns the count of deleted nodes."
        result = self.COLL.delete_many({"_id": {"$in": node_ids}})

        # Also remove references from any projects
        self.COLL.update_many(
            {"nodes.id": {"$in": node_ids}},
            {"$pull": {"nodes": {"id": {"$in": node_ids}}}},
        )

        # Also remove references from any other nodes' containers.to
        self.NODES.update_many(
            {"containers.to": {"$in": node_ids}},
            {"$pull": {"containers": {"to": {"$in": node_ids}}}},
        )

        return result.deleted_count

    @staticmethod
    def _validate_vector(vector: Any) -> Optional[List[float]]:
        if not isinstance(vector, Iterable):
            return None
        result: List[float] = []
        for value in vector:
            try:
                result.append(float(value))
            except (TypeError, ValueError):
                return None
        if not result:
            return None
        return result

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return -1.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _normalize_string(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if value is None:
            return ""
        return str(value).strip()
