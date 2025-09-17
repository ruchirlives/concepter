import os
import logging
from typing import List, Any, Dict, Optional

from handlers.repository_handler import ContainerRepository
from containers.baseContainer import BaseContainer


class FirestoreContainerRepository(ContainerRepository):
    def __init__(self) -> None:
        try:
            from google.cloud import firestore  # type: ignore
            from google.auth.exceptions import DefaultCredentialsError  # type: ignore
            from google.oauth2 import service_account  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "google-cloud-firestore is not installed or failed to import."
                "Install with: pip install google-cloud-firestore"
                "Also ensure credentials are available (ADC) or set GOOGLE_APPLICATION_CREDENTIALS."
            ) from e

        self._firestore = firestore

        # Database selection (supports Firestore multi-database)
        db_id = os.getenv("FIRESTORE_DATABASE") or os.getenv("FIRESTORE_DB") or "(default)"
        emulator_host = os.getenv("FIRESTORE_EMULATOR_HOST")
        if emulator_host:
            project = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or "demo-project"
            self.client = firestore.Client(project=project, database=db_id)
            logging.info(
                "Connected to Firestore emulator at %s (project=%s, database=%s)", emulator_host, project, db_id
            )
        else:
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if creds_path and os.path.exists(creds_path):
                creds = service_account.Credentials.from_service_account_file(creds_path)
                self.client = firestore.Client(
                    credentials=creds,
                    project=os.getenv("GCP_PROJECT") or getattr(creds, "project_id", None),
                    database=db_id,
                )
                logging.info("Connected to Firestore with explicit service account credentials")
            else:
                try:
                    self.client = firestore.Client(database=db_id)
                except Exception as e:
                    raise DefaultCredentialsError(
                        "Firestore credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS "
                        "to a valid service account JSON, "
                        "configure ADC, or set FIRESTORE_EMULATOR_HOST."
                    ) from e

        self.db = self.client  # alias for parity with Mongo code

        # Collection names for parity with Mongo handler
        self.collections_coll = self.client.collection("collections")
        self.nodes_coll = self.client.collection("nodes")

        logging.info("Connected to Firestore (database=%s).", db_id)

    # ---- Optional helper to rehydrate edges like Mongo handler ----
    @staticmethod
    def rehydrate_edges_for_containers(containers: list):
        from containers.baseContainer import BaseContainer

        full_id_map = {c.getValue("id"): c for c in BaseContainer.instances}
        for inst in BaseContainer.instances:
            unmatched = []
            for edge in getattr(inst, "_pending_edges", []):
                tgt = full_id_map.get(edge["to"])
                if tgt:
                    inst.setPosition(tgt, edge["position"])
                else:
                    unmatched.append(edge)
            inst._pending_edges = unmatched if unmatched else []

    # ---- Required interface methods ----
    def search_position_z(self, searchTerm: str, top_n: int = 10) -> list:
        # Firestore doesn't support server-side vector cosine similarity out of the box.
        # Implementing this requires storing embeddings and computing client-side, which can be expensive.
        # Left unimplemented for now to avoid misleading behavior.
        raise NotImplementedError("Vector similarity search is not implemented for Firestore yet.")

    # ---- Serialization helpers ----
    def _firestore_safe(self, obj):
        """Recursively convert objects into Firestore-compatible values.
        - Converts numpy types/arrays to native Python types/lists
        - Converts sets/tuples to lists
        - Leaves bytes as-is; converts memoryview to bytes
        - Converts unknown objects to strings as a last resort
        """
        import numpy as _np
        import datetime as _dt
        import math as _math

        try:
            from bson import Binary as _Binary  # type: ignore
        except Exception:
            _Binary = None  # optional

        if obj is None or isinstance(obj, (bool, int, str)):
            return obj
        if isinstance(obj, float):
            # Replace non-finite floats with None
            return obj if _math.isfinite(obj) else None
        if isinstance(obj, bytes):
            return obj
        if isinstance(obj, memoryview):
            return bytes(obj)
        if isinstance(obj, (_dt.datetime, _dt.date)):
            return obj.isoformat()
        if isinstance(obj, _np.generic):
            return obj.item()
        if isinstance(obj, _np.ndarray):
            return obj.astype(float).tolist() if _np.issubdtype(obj.dtype, _np.number) else obj.tolist()
        if isinstance(obj, (list, tuple, set)):
            return [self._firestore_safe(v) for v in obj]
        if isinstance(obj, dict):
            safe = {}
            for k, v in obj.items():
                key = str(k)
                if not key:
                    continue
                safe[key] = self._firestore_safe(v)
            return safe
        if _Binary is not None and isinstance(obj, _Binary):
            return bytes(obj)
        return str(obj)

    def load_node(self, node_id: Any) -> Optional[Any]:
        doc_ref = self.nodes_coll.document(str(node_id))
        snap = doc_ref.get()
        if not snap.exists:
            return None
        doc = snap.to_dict()
        inst = BaseContainer.deserialize_node_info(doc)
        # Rehydrate allStates from subcollection if present
        try:
            states_ref = self.nodes_coll.document(str(node_id)).collection("states")
            state_docs = list(states_ref.stream())
            if state_docs:
                all_states: Dict[str, Any] = {}
                for sd in state_docs:
                    d = sd.to_dict() or {}
                    key = str(d.get("state") or sd.id)
                    items = d.get("items") or []
                    if key in all_states and isinstance(all_states[key], list):
                        all_states[key].extend(items)
                    else:
                        all_states[key] = items
                inst.setValue("allStates", all_states)
        except Exception:
            pass
        # Rehydrate allStates from subcollection if present
        try:
            states_ref = self.nodes_coll.document(str(node_id)).collection("states")
            state_docs = list(states_ref.stream())
            if state_docs:
                all_states: Dict[str, Any] = {}
                for sd in state_docs:
                    d = sd.to_dict() or {}
                    key = str(d.get("state") or sd.id)
                    items = d.get("items") or []
                    if key in all_states and isinstance(all_states[key], list):
                        all_states[key].extend(items)
                    else:
                        all_states[key] = items
                inst.setValue("allStates", all_states)
        except Exception:
            pass
        self.rehydrate_edges_for_containers([inst])
        return inst

    def search_nodes(self, search_term: str, tags: List[str]) -> List[Dict[str, Any]]:
        # Basic name search (client-side regex not supported). Use case-insensitive contains.
        # This does a simple contains filter client-side over a limited set for now.
        if not search_term and not tags:
            return []
        # Fetch a window of docs; for production, add indexes/structured queries as needed.
        snaps = self.nodes_coll.limit(500).stream()
        results: List[Dict[str, Any]] = []
        st = (search_term or "").lower()
        req_tags = set([t.strip().lower() for t in (tags or []) if t.strip()])
        for s in snaps:
            d = s.to_dict() or {}
            name = (d.get("values") or {}).get("Name") or ""
            node_tags = [
                (t or "").strip().lower() for t in ((d.get("values") or {}).get("Tags") or []) if isinstance(t, str)
            ]
            if st and st not in name.lower():
                continue
            if req_tags and not req_tags.issubset(set(node_tags)):
                continue
            results.append(
                {
                    "_id": d.get("_id"),
                    "values": {"Name": name},
                    "containers": d.get("containers", []),
                }
            )
        return results

    def deduplicate_nodes(self) -> None:
        # Non-trivial to implement safely across Firestore; skip for now.
        raise NotImplementedError("deduplicate_nodes is not implemented for Firestore.")

    def list_project_names(self) -> List[str]:
        snaps = self.collections_coll.stream()
        return [s.id for s in snaps]

    def load_project(self, name: str) -> List[Any]:
        doc_ref = self.collections_coll.document(name)
        snap = doc_ref.get()
        if not snap.exists:
            raise KeyError(f"No project named {name}")
        d = snap.to_dict() or {}

        # Legacy path
        if "data" in d and isinstance(d["data"], bytes):
            import pickle

            return pickle.loads(d["data"])  # nosec - assumes trusted storage

        node_ids = [n.get("id") for n in d.get("nodes", []) if n.get("id")]
        if not node_ids:
            return []

        containers: List[BaseContainer] = []
        id_map: Dict[str, BaseContainer] = {}
        for nid in node_ids:
            s = self.nodes_coll.document(str(nid)).get()
            if not s.exists:
                continue
            doc = s.to_dict()
            inst = BaseContainer.deserialize_node_info(doc)
            id_map[doc.get("_id")] = inst
            containers.append(inst)

        self.rehydrate_edges_for_containers(containers)
        # Attach allStates from subcollections
        try:
            for inst in containers:
                nid = inst.getValue("id")
                if not nid:
                    continue
                states_ref = self.nodes_coll.document(str(nid)).collection("states")
                state_docs = list(states_ref.stream())
                if state_docs:
                    all_states: Dict[str, Any] = {}
                    for sd in state_docs:
                        d = sd.to_dict() or {}
                        key = str(d.get("state") or sd.id)
                        items = d.get("items") or []
                        if key in all_states and isinstance(all_states[key], list):
                            all_states[key].extend(items)
                        else:
                            all_states[key] = items
                    inst.setValue("allStates", all_states)
        except Exception:
            pass
        return containers

    def save_project(self, name: str, containers: List[Any]) -> None:
        ops = []  # not used; kept for parity with Mongo version
        proj_nodes: List[Dict[str, Any]] = []

        docs_to_write: list[tuple[str, dict]] = []
        for c in containers:
            raw = c.serialize_node_info()
            doc = self._firestore_safe(raw)
            vals = doc.get("values") or {}

            # Persist allStates into a subcollection to avoid nested entity/size limits
            all_states = vals.pop("allStates", None)
            nid = str(doc.get("_id"))
            if isinstance(all_states, dict):
                try:
                    states_ref = self.nodes_coll.document(nid).collection("states")
                    # Clear previous state docs for this node
                    existing = list(states_ref.stream())
                    if existing:
                        batch_del = self.client.batch()
                        for sd in existing:
                            batch_del.delete(sd.reference)
                        batch_del.commit()

                    # Write each state as its own document; chunk large lists
                    for state_key, items in all_states.items():
                        items_safe = self._firestore_safe(items)
                        chunk_size = 200
                        if isinstance(items_safe, list) and len(items_safe) > chunk_size:
                            for idx in range(0, len(items_safe), chunk_size):
                                chunk = items_safe[idx: idx + chunk_size]
                                states_ref.document(f"{state_key}-{idx // chunk_size}").set(
                                    {"state": str(state_key), "items": chunk}, merge=False
                                )
                        else:
                            states_ref.document(str(state_key)).set(
                                {"state": str(state_key), "items": items_safe}, merge=False
                            )
                except Exception:
                    # If persisting states fails, continue with core doc
                    pass

            docs_to_write.append((nid, doc))
            proj_nodes.append({"id": doc["_id"], "Name": (doc.get("values") or {}).get("Name")})
        # Batch write for performance
        batch = self.client.batch()
        for _id, d in docs_to_write:
            batch.set(self.nodes_coll.document(_id), d)
        batch.commit()

        # Save project membership metadata
        self.collections_coll.document(name).set({"nodes": proj_nodes}, merge=True)

    def delete_project(self, name: str) -> bool:
        doc_ref = self.collections_coll.document(name)
        snap = doc_ref.get()
        if not snap.exists:
            return False
        doc_ref.delete()
        return True

    def save_transition_metadata(self, metadata: Dict[str, Any]) -> None:
        self.collections_coll.document("transition_metadata").set(
            {
                "data": metadata,
                "type": "transition_metadata",
            },
            merge=True,
        )

    def load_transition_metadata(self) -> Optional[Dict[str, Any]]:
        snap = self.collections_coll.document("transition_metadata").get()
        if not snap.exists:
            return None
        d = snap.to_dict() or {}
        data = d.get("data")
        return data if isinstance(data, dict) else None

    def delete_transition_metadata(self) -> bool:
        doc_ref = self.collections_coll.document("transition_metadata")
        if not doc_ref.get().exists:
            return False
        # backup
        doc = doc_ref.get().to_dict()
        self.collections_coll.document("transition_metadata_backup").set({"data": doc}, merge=True)
        doc_ref.delete()
        return True
