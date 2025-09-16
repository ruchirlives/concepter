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
                "google-cloud-firestore is not installed or failed to import.\n"
                "Install with: pip install google-cloud-firestore\n"
                "Also ensure credentials are available (ADC) or set GOOGLE_APPLICATION_CREDENTIALS."
            ) from e

        self._firestore = firestore

        # Prefer emulator if configured
        emulator_host = os.getenv('FIRESTORE_EMULATOR_HOST')
        if emulator_host:
            project = os.getenv('GCP_PROJECT') or os.getenv('GOOGLE_CLOUD_PROJECT') or 'demo-project'
            self.client = firestore.Client(project=project)
            logging.info('Connected to Firestore emulator at %s (project=%s)', emulator_host, project)
        else:
            creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if creds_path and os.path.exists(creds_path):
                creds = service_account.Credentials.from_service_account_file(creds_path)
                self.client = firestore.Client(credentials=creds, project=os.getenv('GCP_PROJECT') or getattr(creds, 'project_id', None))
                logging.info('Connected to Firestore with explicit service account credentials')
            else:
                try:
                    self.client = firestore.Client()
                except Exception as e:
                    raise DefaultCredentialsError('Firestore credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS to a valid service account JSON, configure ADC, or set FIRESTORE_EMULATOR_HOST.') from e

        self.db = self.client  # alias for parity with Mongo code

        # Collection names for parity with Mongo handler
        self.collections_coll = self.client.collection('collections')
        self.nodes_coll = self.client.collection('nodes')

        logging.info('Connected to Firestore.')

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

    def load_node(self, node_id: Any) -> Optional[Any]:
        doc_ref = self.nodes_coll.document(str(node_id))
        snap = doc_ref.get()
        if not snap.exists:
            return None
        doc = snap.to_dict()
        inst = BaseContainer.deserialize_node_info(doc)
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
            name = ((d.get("values") or {}).get("Name") or "")
            node_tags = [(t or "").strip().lower() for t in ((d.get("values") or {}).get("Tags") or []) if isinstance(t, str)]
            if st and st not in name.lower():
                continue
            if req_tags and not req_tags.issubset(set(node_tags)):
                continue
            results.append({
                "_id": d.get("_id"),
                "values": {"Name": name},
                "containers": d.get("containers", []),
            })
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
        return containers

    def save_project(self, name: str, containers: List[Any]) -> None:
        ops = []  # not used; kept for parity with Mongo version
        proj_nodes: List[Dict[str, Any]] = []

        batch = self.client.batch()
        for c in containers:
            doc = c.serialize_node_info()
            batch.set(self.nodes_coll.document(str(doc["_id"])), doc)
            proj_nodes.append({"id": doc["_id"], "Name": (doc.get("values") or {}).get("Name")})
        batch.commit()

        self.collections_coll.document(name).set({
            "nodes": proj_nodes,
        }, merge=True)

    def delete_project(self, name: str) -> bool:
        doc_ref = self.collections_coll.document(name)
        snap = doc_ref.get()
        if not snap.exists:
            return False
        doc_ref.delete()
        return True

    def save_transition_metadata(self, metadata: Dict[str, Any]) -> None:
        self.collections_coll.document("transition_metadata").set({
            "data": metadata,
            "type": "transition_metadata",
        }, merge=True)

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



