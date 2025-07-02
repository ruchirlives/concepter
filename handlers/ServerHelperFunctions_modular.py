"""
ServerHelperFunctions - Backward compatibility wrapper.

This module provides the original ServerHelperFunctions class using the new mixin architecture.
"""

from handlers.mixins.container_serialization_mixin import ContainerSerializationMixin
from handlers.mixins.container_tag_mixin import ContainerTagMixin
from handlers.mixins.vector_similarity_mixin import VectorSimilarityMixin
from handlers.mixins.reasoning_chain_mixin import ReasoningChainMixin


class ServerHelperFunctions(
    ContainerSerializationMixin,
    ContainerTagMixin,
    VectorSimilarityMixin,
    ReasoningChainMixin
):
    """
    Server helper functions using modular mixin architecture.
    
    This class combines all helper functionality through mixins while maintaining
    backward compatibility with existing code.
    """
    
    def __init__(self):
        super().__init__()
