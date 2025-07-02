import numpy as np


class VectorSimilarityMixin:
    """Mixin for vector similarity calculations."""

    def vector_match(self, parent_z, child_z):
        """Calculate cosine similarity between two vectors."""
        # Ensure inputs are numpy arrays
        if parent_z is None or child_z is None:
            return 0.0

        parent_z = np.array(parent_z)
        child_z = np.array(child_z)

        # Normalize vectors
        norm_parent = np.linalg.norm(parent_z)
        norm_child = np.linalg.norm(child_z)

        if norm_parent == 0 or norm_child == 0:
            return 0.0

        similarity = np.dot(parent_z, child_z) / (norm_parent * norm_child)
        return float(similarity)
